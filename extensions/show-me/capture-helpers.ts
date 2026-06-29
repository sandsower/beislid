import { join, posix, resolve } from "node:path";
import { copyFile, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import type { ShowMeCapability } from "./doctor.js";
import { addAsset } from "./asset-manager.js";
import { addNeedsCaptureBlock } from "./needs-capture.js";
import { commandExists, execFileResult, psQuote, resolvePowerShell } from "./tooling.js";
import { readDeck, writeDeck, writeManifest, addBlock } from "./store.js";

export type ScreenCaptureTarget = "screen" | "window";

export interface CaptureScreenScreenshotInput {
	deckId: string;
	sectionId?: string;
	target?: ScreenCaptureTarget;
	caption?: string;
	alt?: string;
	timeoutSeconds?: number;
	sensitivity?: string;
}

export interface CaptureScreenScreenshotResult {
	deckId: string;
	status: "captured" | "needs-capture";
	assetId?: string;
	blockId?: string;
	assetPath?: string;
	target: ScreenCaptureTarget;
	tool?: string;
	reason?: string;
}

export interface RecordTerminalSessionInput {
	deckId: string;
	command: string;
	sectionId?: string;
	title?: string;
	cwd?: string;
	timeoutSeconds?: number;
	sensitivity?: string;
}

export interface RecordTerminalSessionResult {
	deckId: string;
	status: "recorded" | "needs-capture";
	logId?: string;
	blockId?: string;
	recordingPath?: string;
	recordingFormat?: "cast";
	command: string;
	cwd: string;
	exitCode?: number | null;
	timedOut?: boolean;
	reason?: string;
	tool?: string;
}

export interface ConvertVideoToGifInput {
	deckId: string;
	path: string;
	sectionId?: string;
	caption?: string;
	alt?: string;
	fps?: number;
	width?: number;
	timeoutSeconds?: number;
	sensitivity?: string;
}

export interface ConvertGifToVideoInput {
	deckId: string;
	path: string;
	sectionId?: string;
	caption?: string;
	alt?: string;
	format?: "mp4" | "webm";
	timeoutSeconds?: number;
	sensitivity?: string;
}

export interface ConvertMediaResult {
	deckId: string;
	status: "converted" | "needs-capture";
	assetId?: string;
	blockId?: string;
	assetPath?: string;
	sourcePath: string;
	targetType: "gif" | "video";
	tool?: string;
	reason?: string;
}

function timeoutMs(seconds?: number): number {
	return Math.max(1, Math.min(seconds ?? 30, 120)) * 1000;
}

async function validateDeckAndSection(deckId: string, sectionId?: string): Promise<void> {
	const { doc } = await readDeck(deckId);
	if (sectionId && !doc.sections.some((section) => section.id === sectionId)) {
		throw new Error(`Unknown section id ${sectionId} in deck ${deckId}; capture was not added.`);
	}
}

async function addNeedsCapture(input: { deckId: string; sectionId?: string; title: string; reason: string; request: string; status?: "NEEDS CAPTURE" | "NOT SHOWN" | "INCOMPLETE" }): Promise<{ blockId?: string }> {
	if (!input.sectionId) return {};
	const result = await addNeedsCaptureBlock({
		deckId: input.deckId,
		sectionId: input.sectionId,
		title: input.title,
		reason: input.reason,
		request: input.request,
		status: input.status,
	});
	return { blockId: result.blockId };
}

async function writeTerminalLog(root: string, relPath: string, content: string): Promise<string> {
	const fullPath = join(root, relPath);
	await writeFile(fullPath, content, "utf-8");
	return fullPath;
}

function screenCaptureUnavailable(target: ScreenCaptureTarget): ShowMeCapability {
	return {
		id: `screen-${target}`,
		label: "screen/window screenshots",
		status: "missing",
		detail: target === "window"
			? "No supported active-window screenshot tool was found for this platform."
			: "No supported screen screenshot tool was found for this platform.",
		remediation: process.platform === "darwin"
			? target === "window"
				? "Install or use the built-in macOS screencapture tool."
				: "Install or use the built-in macOS screencapture tool."
			: process.platform === "linux"
				? target === "window"
					? "Install gnome-screenshot, scrot, or import to capture the active window."
					: "Install grim, gnome-screenshot, scrot, or import to capture the screen."
				: process.platform === "win32"
					? "Install PowerShell desktop access support so the built-in screenshot script can run."
					: "Install a platform screenshot tool for this OS.",
	};
}

async function planScreenCapture(target: ScreenCaptureTarget): Promise<{ command: string; args: string[]; tool: string; detail: string; remediation: string } | undefined> {
	if (process.platform === "darwin") {
		const command = await commandExists("screencapture");
		if (!command) return undefined;
		return {
			command,
			args: target === "window" ? ["-x", "-W"] : ["-x"],
			tool: "screencapture",
			detail: `macOS screencapture found at ${command}.`,
			remediation: "macOS includes screencapture by default.",
		};
	}

	if (process.platform === "linux") {
		const linuxPlans = target === "window"
			? [
				{ name: "gnome-screenshot", args: ["-w", "-f"], remediation: "Install gnome-screenshot for focused-window captures." },
				{ name: "scrot", args: ["-u"], remediation: "Install scrot for focused-window captures." },
				{ name: "import", args: [], remediation: "Install ImageMagick import for focused-window captures." },
			]
			: [
				{ name: "grim", args: [], remediation: "Install grim for fast Wayland screen captures." },
				{ name: "gnome-screenshot", args: ["-f"], remediation: "Install gnome-screenshot for screen captures." },
				{ name: "scrot", args: [], remediation: "Install scrot for screen captures." },
				{ name: "import", args: ["-window", "root"], remediation: "Install ImageMagick import for screen captures." },
			];
		for (const candidate of linuxPlans) {
			const command = await commandExists(candidate.name);
			if (!command) continue;
			return {
				command,
				args: candidate.name === "grim" ? [] : [...candidate.args],
				tool: candidate.name,
				detail: `${candidate.name} found at ${command}.`,
				remediation: candidate.remediation,
			};
		}
		return undefined;
	}

	if (process.platform === "win32") {
		const command = await resolvePowerShell();
		if (!command) return undefined;
		return {
			command,
			args: [],
			tool: command,
			detail: `${command} found for PowerShell screenshot capture.`,
			remediation: "Install PowerShell with desktop access to enable screenshot capture.",
		};
	}

	return undefined;
}

function powershellScreenScript(outputPath: string, target: ScreenCaptureTarget): string {
	if (target === "window") {
		return [
			"Add-Type -AssemblyName System.Drawing",
			"Add-Type @'",
			"using System;",
			"using System.Runtime.InteropServices;",
			"public class Win32 {",
			"    [StructLayout(LayoutKind.Sequential)]",
			"    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }",
			"    [DllImport(\"user32.dll\")] public static extern IntPtr GetForegroundWindow();",
			"    [DllImport(\"user32.dll\")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);",
			"}",
			"'@",
			"$hwnd = [Win32]::GetForegroundWindow()",
			"$rect = New-Object Win32+RECT",
			"[Win32]::GetWindowRect($hwnd, [ref]$rect) | Out-Null",
			"$width = $rect.Right - $rect.Left",
			"$height = $rect.Bottom - $rect.Top",
			`$bitmap = New-Object System.Drawing.Bitmap $width, $height`,
			"$graphics = [System.Drawing.Graphics]::FromImage($bitmap)",
			"$graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)",
			`$bitmap.Save(${psQuote(outputPath)}, [System.Drawing.Imaging.ImageFormat]::Png)`,
			"$graphics.Dispose()",
			"$bitmap.Dispose()",
		].join("\n");
	}
	return [
		"Add-Type -AssemblyName System.Windows.Forms",
		"Add-Type -AssemblyName System.Drawing",
		`$screen = [System.Windows.Forms.SystemInformation]::VirtualScreen`,
		"$width = $screen.Width",
		"$height = $screen.Height",
		"$left = $screen.Left",
		"$top = $screen.Top",
		"$bitmap = New-Object System.Drawing.Bitmap $width, $height",
		"$graphics = [System.Drawing.Graphics]::FromImage($bitmap)",
		"$graphics.CopyFromScreen($left, $top, 0, 0, $bitmap.Size)",
		`$bitmap.Save(${psQuote(outputPath)}, [System.Drawing.Imaging.ImageFormat]::Png)`,
		"$graphics.Dispose()",
		"$bitmap.Dispose()",
	].join("\n");
}

async function captureScreenWithPlan(plan: { command: string; args: string[]; tool: string }, outputPath: string, target: ScreenCaptureTarget, timeoutSeconds?: number): Promise<{ exitCode: number | null; timedOut: boolean; stderr: string }> {
	if (process.platform === "win32") {
		const script = powershellScreenScript(outputPath, target);
		const result = await execFileResult(plan.command, ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script], { timeoutMs: timeoutMs(timeoutSeconds) });
		return { exitCode: result.exitCode, timedOut: result.timedOut, stderr: result.stderr };
	}

	const args = [...plan.args];
	if (plan.tool === "grim") {
		args.push(outputPath);
	} else if (plan.tool === "gnome-screenshot") {
		args.push(outputPath);
	} else if (plan.tool === "scrot") {
		args.push(outputPath);
	} else if (plan.tool === "import") {
		if (target === "screen") args.push(outputPath);
		else args.push(outputPath);
	} else if (process.platform === "darwin") {
		args.push(outputPath);
	}
	const result = await execFileResult(plan.command, args, { timeoutMs: timeoutMs(timeoutSeconds) });
	return { exitCode: result.exitCode, timedOut: result.timedOut, stderr: result.stderr };
}

export async function getScreenCaptureCapability(target: ScreenCaptureTarget = "screen"): Promise<ShowMeCapability> {
	const plan = await planScreenCapture(target);
	if (!plan) return screenCaptureUnavailable(target);
	return {
		id: `screen-${target}`,
		label: "screen/window screenshots",
		status: "available",
		detail: plan.detail,
		command: plan.command,
		remediation: plan.remediation,
	};
}

export async function captureScreenScreenshot(input: CaptureScreenScreenshotInput, cwd: string): Promise<CaptureScreenScreenshotResult> {
	await validateDeckAndSection(input.deckId, input.sectionId);
	const target = input.target ?? "screen";
	const plan = await planScreenCapture(target);
	if (!plan) {
		const capability = screenCaptureUnavailable(target);
		const block = await addNeedsCapture({
			deckId: input.deckId,
			sectionId: input.sectionId,
			title: input.caption ?? (target === "window" ? "Window screenshot needed" : "Screen screenshot needed"),
			reason: capability.detail,
			request: capability.remediation,
			status: "NEEDS CAPTURE",
		});
		return { deckId: input.deckId, status: "needs-capture", blockId: block.blockId, target, reason: capability.detail };
	}

	const tempRoot = await mkdtemp(join(tmpdir(), `show-me-screen-${target}-`));
	const screenshotPath = join(tempRoot, `${target}.png`);
	try {
		const capture = await captureScreenWithPlan(plan, screenshotPath, target, input.timeoutSeconds);
		if (capture.exitCode !== 0 || capture.timedOut) {
			const block = await addNeedsCapture({
				deckId: input.deckId,
				sectionId: input.sectionId,
				title: input.caption ?? (target === "window" ? "Window screenshot needed" : "Screen screenshot needed"),
				reason: capture.stderr.trim() || `${plan.tool} failed to capture the ${target}.`,
				request: `Retry the ${target} screenshot with ${plan.tool} or another supported capture tool.`,
				status: "NEEDS CAPTURE",
			});
			return { deckId: input.deckId, status: "needs-capture", blockId: block.blockId, target, tool: plan.tool, reason: capture.stderr.trim() || `${plan.tool} failed to capture the ${target}.` };
		}

		const asset = await addAsset(
			{
				deckId: input.deckId,
				path: screenshotPath,
				type: "image",
				sectionId: input.sectionId,
				caption: input.caption ?? `${target === "window" ? "Window" : "Screen"} screenshot`,
				alt: input.alt ?? `${target === "window" ? "Window" : "Screen"} screenshot`,
				sensitivity: input.sensitivity ?? "Local screenshots may contain sensitive information; inspect before sharing.",
			},
			cwd,
		);
		return { deckId: input.deckId, status: "captured", assetId: asset.assetId, blockId: asset.blockId, assetPath: asset.assetPath, target, tool: plan.tool };
	} finally {
		await rm(tempRoot, { recursive: true, force: true }).catch(() => undefined);
	}
}

export async function getTerminalRecordingCapability(): Promise<ShowMeCapability> {
	const asciinema = await commandExists("asciinema");
	if (!asciinema) {
		return {
			id: "terminal-recording",
			label: "terminal recordings",
			status: "missing",
			detail: "asciinema is not installed, so terminal recordings fall back to NEEDS_CAPTURE.",
			remediation: "Install asciinema to record terminal sessions as cast files.",
		};
	}
	return {
		id: "terminal-recording",
		label: "terminal recordings",
		status: "available",
		detail: `asciinema found at ${asciinema}; terminal recording helper is available.`,
		command: asciinema,
		remediation: "asciinema is installed.",
	};
}

export async function recordTerminalSession(input: RecordTerminalSessionInput, cwd: string): Promise<RecordTerminalSessionResult> {
	await validateDeckAndSection(input.deckId, input.sectionId);
	const asciinema = await commandExists("asciinema");
	if (!asciinema) {
		const capability = await getTerminalRecordingCapability();
		const block = await addNeedsCapture({
			deckId: input.deckId,
			sectionId: input.sectionId,
			title: input.title ?? "Terminal recording needed",
			reason: capability.detail,
			request: capability.remediation,
			status: "NEEDS CAPTURE",
		});
		return { deckId: input.deckId, status: "needs-capture", blockId: block.blockId, command: input.command, cwd: resolve(cwd, input.cwd ?? "."), reason: capability.detail };
	}

	const { root, doc } = await readDeck(input.deckId);
	const tempRoot = await mkdtemp(join(tmpdir(), "show-me-terminal-"));
	const recordingPath = join(tempRoot, "session.cast");
	const startedAt = new Date().toISOString();
	try {
		const result = await execFileResult(asciinema, ["rec", "-q", "-c", input.command, recordingPath], {
			cwd: resolve(cwd, input.cwd ?? "."),
			timeoutMs: timeoutMs(input.timeoutSeconds),
		});
		const finishedAt = new Date().toISOString();
		const logId = `terminal-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
		const relPath = posix.join("logs", "terminal", `${logId}.cast`);
		const textPath = relPath.replace(/\.cast$/, ".txt");
		await mkdir(join(root, "logs", "terminal"), { recursive: true });
		await copyFile(recordingPath, join(root, relPath));
		await writeTerminalLog(root, textPath, [
			`terminal recording: ${input.command}`,
			`cwd: ${resolve(cwd, input.cwd ?? ".")}`,
			`startedAt: ${startedAt}`,
			`finishedAt: ${finishedAt}`,
			`exitCode: ${result.exitCode}`,
			`timedOut: ${result.timedOut}`,
			`recordingPath: ${relPath}`,
			"",
		].join("\n"));
		doc.logs.push({
			id: logId,
			path: relPath,
			command: input.command,
			cwd: resolve(cwd, input.cwd ?? "."),
			startedAt,
			finishedAt,
			exitCode: result.exitCode,
			timedOut: result.timedOut,
		});
		doc.provenance = { ...doc.provenance, terminalRecordings: [...(Array.isArray(doc.provenance.terminalRecordings) ? doc.provenance.terminalRecordings : []), { id: logId, path: relPath, command: input.command, cwd: resolve(cwd, input.cwd ?? ".") }] };
		await writeDeck(root, doc);
		await writeManifest(root, doc);

		let blockId: string | undefined;
		if (input.sectionId) {
			blockId = (await addBlock(input.deckId, input.sectionId, {
				type: "command-log",
				logId,
				title: input.title ?? "Terminal recording",
				command: input.command,
				cwd: resolve(cwd, input.cwd ?? "."),
				startedAt,
				finishedAt,
				exitCode: result.exitCode,
				timedOut: result.timedOut,
				stdoutPreview: result.stdout.trim() || undefined,
				stderrPreview: result.stderr.trim() || undefined,
				logPath: relPath,
				recordingPath: relPath,
				recordingFormat: "cast",
			} as never)).blockId;
		}

		return { deckId: input.deckId, status: "recorded", logId, blockId, recordingPath: relPath, recordingFormat: "cast", command: input.command, cwd: resolve(cwd, input.cwd ?? "."), exitCode: result.exitCode, timedOut: result.timedOut, tool: "asciinema" };
	} finally {
		await rm(tempRoot, { recursive: true, force: true }).catch(() => undefined);
	}
}

async function convertSourceFile(command: string, args: string[], timeoutSeconds?: number): Promise<{ exitCode: number | null; timedOut: boolean; stderr: string }> {
	const result = await execFileResult(command, args, { timeoutMs: timeoutMs(timeoutSeconds) });
	return { exitCode: result.exitCode, timedOut: result.timedOut, stderr: result.stderr };
}

export async function getVideoToGifCapability(): Promise<ShowMeCapability> {
	const gifski = await commandExists("gifski");
	if (gifski) {
		return {
			id: "video-to-gif",
			label: "video → GIF conversion",
			status: "available",
			detail: `gifski found at ${gifski}; video-to-GIF conversion uses gifski.`,
			command: gifski,
			remediation: "gifski is installed.",
		};
	}
	const ffmpeg = await commandExists("ffmpeg");
	if (ffmpeg) {
		return {
			id: "video-to-gif",
			label: "video → GIF conversion",
			status: "available",
			detail: `ffmpeg found at ${ffmpeg}; video-to-GIF conversion uses ffmpeg fallback.`,
			command: ffmpeg,
			remediation: "Install gifski for the best GIF quality or keep using ffmpeg.",
		};
	}
	return {
		id: "video-to-gif",
		label: "video → GIF conversion",
		status: "missing",
		detail: "Neither gifski nor ffmpeg is installed, so video-to-GIF conversion is unavailable.",
		remediation: "Install gifski or ffmpeg to enable video-to-GIF conversion.",
	};
}

export async function getGifToVideoCapability(): Promise<ShowMeCapability> {
	const ffmpeg = await commandExists("ffmpeg");
	if (!ffmpeg) {
		return {
			id: "gif-to-video",
			label: "GIF → video conversion",
			status: "missing",
			detail: "ffmpeg is not installed, so GIF-to-video conversion is unavailable.",
			remediation: "Install ffmpeg to enable GIF-to-video conversion.",
		};
	}
	return {
		id: "gif-to-video",
		label: "GIF → video conversion",
		status: "available",
		detail: `ffmpeg found at ${ffmpeg}; GIF-to-video conversion is available.`,
		command: ffmpeg,
		remediation: "ffmpeg is installed.",
	};
}

export async function convertVideoToGif(input: ConvertVideoToGifInput, cwd: string): Promise<ConvertMediaResult> {
	await validateDeckAndSection(input.deckId, input.sectionId);
	const gifski = await commandExists("gifski");
	const ffmpeg = gifski ? undefined : await commandExists("ffmpeg");
	if (!gifski && !ffmpeg) {
		const capability = await getVideoToGifCapability();
		const block = await addNeedsCapture({
			deckId: input.deckId,
			sectionId: input.sectionId,
			title: input.caption ?? "GIF conversion needed",
			reason: capability.detail,
			request: capability.remediation,
			status: "NEEDS CAPTURE",
		});
		return { deckId: input.deckId, status: "needs-capture", blockId: block.blockId, sourcePath: input.path, targetType: "gif", reason: capability.detail };
	}

	const sourcePath = input.path;
	const tempRoot = await mkdtemp(join(tmpdir(), "show-me-gif-"));
	const outputPath = join(tempRoot, "converted.gif");
	try {
		const absoluteSource = resolve(cwd, sourcePath);
		const result = gifski
			? await convertSourceFile(gifski, ["--fps", String(Math.max(1, Math.min(input.fps ?? 12, 60))), "--width", String(Math.max(64, Math.min(input.width ?? 960, 3840))), "-o", outputPath, absoluteSource], input.timeoutSeconds)
			: await convertSourceFile(ffmpeg!, ["-y", "-i", absoluteSource, "-vf", `fps=${Math.max(1, Math.min(input.fps ?? 12, 60))},scale=${Math.max(64, Math.min(input.width ?? 960, 3840))}:-1:flags=lanczos`, outputPath], input.timeoutSeconds);
		if (result.exitCode !== 0 || result.timedOut) {
			const block = await addNeedsCapture({
				deckId: input.deckId,
				sectionId: input.sectionId,
				title: input.caption ?? "GIF conversion needed",
				reason: result.stderr.trim() || "Video-to-GIF conversion failed.",
				request: "Retry the conversion with gifski or ffmpeg.",
				status: "NEEDS CAPTURE",
			});
			return { deckId: input.deckId, status: "needs-capture", blockId: block.blockId, sourcePath: input.path, targetType: "gif", reason: result.stderr.trim() || "Video-to-GIF conversion failed." };
		}
		const asset = await addAsset(
			{
				deckId: input.deckId,
				path: outputPath,
				type: "gif",
				sectionId: input.sectionId,
				caption: input.caption ?? "Converted GIF",
				alt: input.alt ?? "Converted GIF",
				sensitivity: input.sensitivity ?? "Local media may contain sensitive information; inspect before sharing.",
			},
			cwd,
		);
		return { deckId: input.deckId, status: "converted", assetId: asset.assetId, blockId: asset.blockId, assetPath: asset.assetPath, sourcePath: input.path, targetType: "gif", tool: gifski ? "gifski" : "ffmpeg" };
	} finally {
		await rm(tempRoot, { recursive: true, force: true }).catch(() => undefined);
	}
}

export async function convertGifToVideo(input: ConvertGifToVideoInput, cwd: string): Promise<ConvertMediaResult> {
	await validateDeckAndSection(input.deckId, input.sectionId);
	const ffmpeg = await commandExists("ffmpeg");
	if (!ffmpeg) {
		const capability = await getGifToVideoCapability();
		const block = await addNeedsCapture({
			deckId: input.deckId,
			sectionId: input.sectionId,
			title: input.caption ?? "Video conversion needed",
			reason: capability.detail,
			request: capability.remediation,
			status: "NEEDS CAPTURE",
		});
		return { deckId: input.deckId, status: "needs-capture", blockId: block.blockId, sourcePath: input.path, targetType: "video", reason: capability.detail };
	}

	const sourcePath = input.path;
	const outputFormat = input.format ?? "mp4";
	const tempRoot = await mkdtemp(join(tmpdir(), "show-me-video-"));
	const outputPath = join(tempRoot, `converted.${outputFormat}`);
	try {
		const absoluteSource = resolve(cwd, sourcePath);
		const args = outputFormat === "webm"
			? ["-y", "-i", absoluteSource, "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", outputPath]
			: ["-y", "-i", absoluteSource, "-movflags", "+faststart", "-c:v", "libx264", "-pix_fmt", "yuv420p", outputPath];
		const result = await convertSourceFile(ffmpeg, args, input.timeoutSeconds);
		if (result.exitCode !== 0 || result.timedOut) {
			const block = await addNeedsCapture({
				deckId: input.deckId,
				sectionId: input.sectionId,
				title: input.caption ?? "Video conversion needed",
				reason: result.stderr.trim() || "GIF-to-video conversion failed.",
				request: "Retry the conversion with ffmpeg.",
				status: "NEEDS CAPTURE",
			});
			return { deckId: input.deckId, status: "needs-capture", blockId: block.blockId, sourcePath: input.path, targetType: "video", reason: result.stderr.trim() || "GIF-to-video conversion failed." };
		}
		const asset = await addAsset(
			{
				deckId: input.deckId,
				path: outputPath,
				type: "video",
				sectionId: input.sectionId,
				caption: input.caption ?? `Converted ${outputFormat.toUpperCase()} video`,
				alt: input.alt ?? `Converted ${outputFormat.toUpperCase()} video`,
				sensitivity: input.sensitivity ?? "Local media may contain sensitive information; inspect before sharing.",
			},
			cwd,
		);
		return { deckId: input.deckId, status: "converted", assetId: asset.assetId, blockId: asset.blockId, assetPath: asset.assetPath, sourcePath: input.path, targetType: "video", tool: "ffmpeg" };
	} finally {
		await rm(tempRoot, { recursive: true, force: true }).catch(() => undefined);
	}
}
