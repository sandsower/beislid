import { createRequire } from "node:module";
import { join } from "node:path";
import { getGifToVideoCapability, getScreenCaptureCapability, getTerminalRecordingCapability, getVideoToGifCapability } from "./capture-helpers.js";

export type CapabilityStatus = "available" | "missing" | "unknown";

export interface ShowMeCapability {
	id: string;
	label: string;
	status: CapabilityStatus;
	detail: string;
	command?: string;
	remediation?: string;
}

export interface ShowMeDoctorReport {
	builder: ShowMeCapability[];
	capture: ShowMeCapability[];
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

function playwrightCapability(cwd: string): ShowMeCapability {
	const playwright = resolveOptionalPackage("playwright", cwd);
	return playwright
		? {
			id: "browser-screenshot",
			label: "browser screenshots",
			status: "available",
			detail: `Playwright resolves from ${playwright}.`,
			command: playwright,
			remediation: "Playwright is installed and browser screenshots can run.",
		}
		: {
			id: "browser-screenshot",
			label: "browser screenshots",
			status: "missing",
			detail: "Playwright is not installed in the project or extension environment.",
			remediation: "Install Playwright in the project or extension environment (for example: pnpm add -D playwright).",
		};
}

function mark(status: CapabilityStatus): string {
	if (status === "available") return "✓";
	if (status === "missing") return "✗";
	return "?";
}

export async function getShowMeDoctorReport(cwd: string): Promise<ShowMeDoctorReport> {
	return {
		builder: [
			{ id: "extension", label: "extension loaded", status: "available", detail: "Pi loaded the show-me extension." },
			{ id: "typed-blocks", label: "typed blocks", status: "available", detail: "Deck builder, sections, media blocks, command logs, and renderer are available." },
			{ id: "text-redaction", label: "text redaction", status: "available", detail: "Best-effort text redaction is applied before persistence/rendering." },
		],
		capture: [
			playwrightCapability(cwd),
			await getScreenCaptureCapability(),
			await getTerminalRecordingCapability(),
			await getVideoToGifCapability(),
			await getGifToVideoCapability(),
		],
	};
}

export function formatDoctorReport(report: ShowMeDoctorReport): string {
	const renderGroup = (title: string, capabilities: ShowMeCapability[]) => [
		`${title}:`,
		...capabilities.map((capability) => {
			const lines = [`  ${mark(capability.status)} ${capability.label} — ${capability.detail}`];
			if (capability.remediation) lines.push(`    Remediation: ${capability.remediation}`);
			return lines.join("\n");
		}),
	].join("\n");
	return `show-me doctor\n\n${renderGroup("Builder", report.builder)}\n\n${renderGroup("Capture", report.capture)}\n\nMissing capture tools are not fatal. Use show_me_add_needs_capture or let capture helpers add NEEDS_CAPTURE blocks when a requested capture cannot run.`;
}
