import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { homedir } from "node:os";

export type HandoffConfig = {
	autoHandoff: boolean;
	events: Set<string> | "all";
	exclude: Set<string>;
};

type PartialConfig = {
	autoHandoff?: boolean;
	enabled?: boolean;
	events?: string[] | "all";
	exclude?: string[];
};

const DEFAULT_CONFIG: HandoffConfig = {
	autoHandoff: true,
	events: "all",
	exclude: new Set(),
};

function parseScalar(value: string): string | boolean | string[] {
	const trimmed = value.trim().replace(/^['"]|['"]$/g, "");
	if (/^(true|yes|on)$/i.test(trimmed)) return true;
	if (/^(false|no|off)$/i.test(trimmed)) return false;
	if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
		return trimmed
			.slice(1, -1)
			.split(",")
			.map((item) => item.trim().replace(/^['"]|['"]$/g, ""))
			.filter(Boolean);
	}
	return trimmed;
}

function parseRepoPiHandoff(workflow: string): PartialConfig | undefined {
	const match = workflow.match(/```beislid:pi_handoff\s*\n([\s\S]*?)\n```/m);
	if (!match) return undefined;
	const config: PartialConfig = {};
	for (const rawLine of match[1].split(/\r?\n/)) {
		const line = rawLine.trim();
		if (!line || line.startsWith("#")) continue;
		const split = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
		if (!split) continue;
		const [, key, rawValue] = split;
		const value = parseScalar(rawValue);
		if ((key === "enabled" || key === "autoHandoff") && typeof value === "boolean") config.autoHandoff = value;
		if (key === "events") config.events = value === "all" ? "all" : Array.isArray(value) ? value : [String(value)];
		if (key === "exclude") config.exclude = Array.isArray(value) ? value : [String(value)];
	}
	return config;
}

async function readJsonConfig(path: string): Promise<PartialConfig | undefined> {
	try {
		const parsed = JSON.parse(await readFile(path, "utf8")) as unknown;
		if (!parsed || typeof parsed !== "object") return undefined;
		const value = (parsed as { beislid?: unknown }).beislid ?? parsed;
		if (!value || typeof value !== "object") return undefined;
		return value as PartialConfig;
	} catch {
		return undefined;
	}
}

function normalizeEvents(events: PartialConfig["events"]): Set<string> | "all" | undefined {
	if (events === undefined) return undefined;
	if (events === "all") return "all";
	if (Array.isArray(events)) return new Set(events);
	return new Set([String(events)]);
}

function applyConfig(base: HandoffConfig, override: PartialConfig | undefined): HandoffConfig {
	if (!override) return base;
	const autoHandoff = override.autoHandoff ?? override.enabled ?? base.autoHandoff;
	const events = normalizeEvents(override.events) ?? base.events;
	const exclude = new Set([...(base.exclude ?? []), ...(override.exclude ?? [])]);
	return { autoHandoff, events, exclude };
}

export async function resolveHandoffConfig(cwd: string): Promise<HandoffConfig> {
	let config = DEFAULT_CONFIG;
	try {
		const workflow = await readFile(join(cwd, ".beislid", "workflow.md"), "utf8");
		config = applyConfig(config, parseRepoPiHandoff(workflow));
	} catch {
		// Missing workflow config keeps Pi extension defaults. Portable skills still own hard-fail behavior.
	}

	// Local Pi settings are the final override. Project-local settings override user-global settings.
	const userConfig = await readJsonConfig(join(homedir(), ".pi", "agent", "beislid.json"));
	config = applyConfig(config, userConfig);
	const projectConfig = await readJsonConfig(join(cwd, ".pi", "beislid.json"));
	config = applyConfig(config, projectConfig);
	if (config.events !== "all") {
		config.events = new Set([...config.events].filter((event) => !config.exclude.has(event)));
	}
	return config;
}
