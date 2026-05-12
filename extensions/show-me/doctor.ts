import { execFile } from "node:child_process";
import { createRequire } from "node:module";
import { join } from "node:path";

export type CapabilityStatus = "available" | "missing" | "unknown";

export interface ShowMeCapability {
	id: string;
	label: string;
	status: CapabilityStatus;
	detail: string;
	command?: string;
}

export interface ShowMeDoctorReport {
	builder: ShowMeCapability[];
	capture: ShowMeCapability[];
}

async function commandExists(command: string): Promise<string | undefined> {
	const probe = process.platform === "win32" ? `where ${command}` : `command -v ${command}`;
	return new Promise((resolve) => {
		execFile(process.platform === "win32" ? "cmd" : "sh", process.platform === "win32" ? ["/c", probe] : ["-c", probe], { timeout: 1500 }, (error, stdout) => {
			resolve(error ? undefined : stdout.trim().split(/\r?\n/)[0]);
		});
	});
}

export function resolveOptionalPackage(packageName: string, cwd: string): string | undefined {
	const candidates = [
		() => createRequire(join(cwd, "package.json")).resolve(packageName),
		() => createRequire(import.meta.url).resolve(packageName),
	];
	for (const candidate of candidates) {
		try {
			return candidate();
		} catch {
			// Try the next resolution root.
		}
	}
	return undefined;
}

async function screenshotCapability(): Promise<ShowMeCapability> {
	if (process.platform === "darwin") {
		const command = await commandExists("screencapture");
		return command
			? { id: "screen-screenshot", label: "screen/window screenshot binary", status: "available", detail: `macOS screencapture found at ${command}; show-me screen/window capture automation is deferred.`, command }
			: { id: "screen-screenshot", label: "screen/window screenshot binary", status: "missing", detail: "macOS screencapture was not found; show-me screen/window capture automation is deferred." };
	}
	if (process.platform === "linux") {
		for (const tool of ["grim", "gnome-screenshot", "import", "scrot"]) {
			const command = await commandExists(tool);
			if (command) return { id: "screen-screenshot", label: "screen/window screenshot binary", status: "available", detail: `${tool} found at ${command}; show-me screen/window capture automation is deferred.`, command };
		}
		return { id: "screen-screenshot", label: "screen/window screenshot binary", status: "missing", detail: "No supported Linux screenshot tool found (grim, gnome-screenshot, import, scrot); show-me screen/window capture automation is deferred." };
	}
	if (process.platform === "win32") {
		const command = await commandExists("powershell");
		return command
			? { id: "screen-screenshot", label: "screen/window screenshot binary", status: "available", detail: `PowerShell found at ${command}; show-me screen/window capture automation is deferred.`, command }
			: { id: "screen-screenshot", label: "screen/window screenshot binary", status: "missing", detail: "PowerShell screenshot fallback was not found; show-me screen/window capture automation is deferred." };
	}
	return { id: "screen-screenshot", label: "screen/window screenshot binary", status: "unknown", detail: `No screenshot detector for platform ${process.platform}; show-me screen/window capture automation is deferred.` };
}

export async function getShowMeDoctorReport(cwd: string): Promise<ShowMeDoctorReport> {
	const playwright = resolveOptionalPackage("playwright", cwd);
	const ffmpeg = await commandExists("ffmpeg");
	const gifski = await commandExists("gifski");
	const asciinema = await commandExists("asciinema");

	return {
		builder: [
			{ id: "extension", label: "extension loaded", status: "available", detail: "Pi loaded the show-me extension." },
			{ id: "typed-blocks", label: "typed blocks", status: "available", detail: "Deck builder, sections, media blocks, command logs, and renderer are available." },
			{ id: "text-redaction", label: "text redaction", status: "available", detail: "Best-effort text redaction is applied before persistence/rendering." },
		],
		capture: [
			playwright
				? { id: "browser-screenshot", label: "browser screenshots", status: "available", detail: `Playwright resolves from ${playwright}` }
				: { id: "browser-screenshot", label: "browser screenshots", status: "missing", detail: "Playwright is not installed in the project or extension environment. Install it in the project to enable browser screenshot capture." },
			await screenshotCapability(),
			ffmpeg
				? { id: "ffmpeg", label: "ffmpeg binary", status: "available", detail: `ffmpeg found at ${ffmpeg}; show-me video conversion automation is deferred.`, command: ffmpeg }
				: { id: "ffmpeg", label: "ffmpeg binary", status: "missing", detail: "ffmpeg not found; show-me video conversion automation is deferred." },
			gifski
				? { id: "gifski", label: "gifski binary", status: "available", detail: `gifski found at ${gifski}; show-me GIF conversion automation is deferred.`, command: gifski }
				: { id: "gifski", label: "gifski binary", status: "missing", detail: "gifski not found; show-me GIF conversion automation is deferred." },
			asciinema
				? { id: "asciinema", label: "asciinema binary", status: "available", detail: `asciinema found at ${asciinema}; show-me terminal recording automation is deferred.`, command: asciinema }
				: { id: "asciinema", label: "asciinema binary", status: "missing", detail: "asciinema not found; show-me terminal recording automation is deferred." },
		],
	};
}

function mark(status: CapabilityStatus): string {
	if (status === "available") return "✓";
	if (status === "missing") return "✗";
	return "?";
}

export function formatDoctorReport(report: ShowMeDoctorReport): string {
	const renderGroup = (title: string, capabilities: ShowMeCapability[]) => [
		`${title}:`,
		...capabilities.map((capability) => `  ${mark(capability.status)} ${capability.label} — ${capability.detail}`),
	].join("\n");
	return `show-me doctor\n\n${renderGroup("Builder", report.builder)}\n\n${renderGroup("Capture", report.capture)}\n\nMissing capture tools are not fatal. Use show_me_add_needs_capture or let capture helpers add NEEDS_CAPTURE blocks when a requested capture cannot run.`;
}
