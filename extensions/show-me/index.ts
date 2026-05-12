import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { execFile } from "node:child_process";
import { readFile, rm } from "node:fs/promises";
import { AddAssetSchema, AddBlockSchema, AddNeedsCaptureSchema, AddSectionSchema, CaptureBrowserScreenshotSchema, CreateDeckSchema, DeckIdSchema, RunCommandSchema } from "./schema.js";
import { addAsset } from "./asset-manager.js";
import { captureBrowserScreenshot } from "./capture-browser.js";
import { getShowMeDoctorReport, formatDoctorReport } from "./doctor.js";
import { addNeedsCaptureBlock } from "./needs-capture.js";
import { runCommandEvidence } from "./command-runner.js";
import { addBlock, addSection, createDeck, pathExists, readDeck, renderDeck } from "./store.js";
import { findIndexEntry, latestIndexEntry, listIndexEntries } from "./index-store.js";

function textResult(text: string, details: Record<string, unknown> = {}) {
	return { content: [{ type: "text" as const, text }], details };
}

function jsonResult(value: unknown) {
	return textResult(JSON.stringify(value, null, 2), typeof value === "object" && value ? (value as Record<string, unknown>) : {});
}

async function assertSafeToDeleteDeck(root: string, deckId: string): Promise<void> {
	const marker = await readFile(`${root}/.show-me-deck`, "utf-8").catch(() => undefined);
	if (marker?.trim() !== deckId) {
		throw new Error(`Refusing to delete ${root}: missing or mismatched .show-me-deck marker`);
	}
	const source = await readFile(`${root}/show-me.json`, "utf-8").catch(() => undefined);
	if (!source) throw new Error(`Refusing to delete ${root}: missing show-me.json`);
	const parsed = JSON.parse(source) as { id?: string };
	if (parsed.id !== deckId) throw new Error(`Refusing to delete ${root}: show-me.json id does not match ${deckId}`);
}

async function deleteDeckRoot(root: string, deckId: string): Promise<void> {
	await assertSafeToDeleteDeck(root, deckId);
	await rm(root, { recursive: true, force: true });
}

async function openPath(path: string): Promise<boolean> {
	const candidates = process.platform === "darwin" ? [["open", path]] : process.platform === "win32" ? [["cmd", "/c", "start", "", path]] : [["xdg-open", path]];
	for (const [cmd, ...args] of candidates) {
		const ok = await new Promise<boolean>((resolve) => {
			execFile(cmd, args, { timeout: 2000 }, (error) => resolve(!error));
		});
		if (ok) return true;
	}
	return false;
}

async function doctorText(cwd: string): Promise<string> {
	return formatDoctorReport(await getShowMeDoctorReport(cwd));
}

export default function showMeExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "show_me_create",
		label: "Show Me: create deck",
		description: "Create a Show Me HTML portfolio/deck workspace and source JSON.",
		parameters: CreateDeckSchema,
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			const result = await createDeck(params as any, ctx.cwd);
			return jsonResult(result);
		},
	});

	pi.registerTool({
		name: "show_me_add_section",
		label: "Show Me: add section",
		description: "Add a section/chapter to a Show Me deck.",
		parameters: AddSectionSchema,
		async execute(_toolCallId, params) {
			const result = await addSection(params.deckId, params.title, params.purpose);
			return jsonResult({ deckId: result.doc.id, sectionId: result.section.id, title: result.section.title });
		},
	});

	pi.registerTool({
		name: "show_me_add_block",
		label: "Show Me: add block",
		description: "Add a typed block to a Show Me section. Supports markdown, table, code, diff, command-log, image/video/gif/diagram, Mermaid diagram source, callout, verdict, and file-role-table blocks.",
		parameters: AddBlockSchema,
		async execute(_toolCallId, params) {
			const result = await addBlock(params.deckId, params.sectionId, params.block as any);
			return jsonResult({ deckId: result.doc.id, blockId: result.blockId, sectionId: params.sectionId });
		},
	});

	pi.registerTool({
		name: "show_me_add_asset",
		label: "Show Me: add asset",
		description: "Copy an existing image/video/GIF/diagram into a Show Me deck, record hash/provenance, and optionally add a media block to a section.",
		parameters: AddAssetSchema,
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			const result = await addAsset(params as any, ctx.cwd);
			return jsonResult(result);
		},
	});

	pi.registerTool({
		name: "show_me_add_needs_capture",
		label: "Show Me: add NEEDS_CAPTURE block",
		description: "Add a NEEDS_CAPTURE block when visual evidence could not be captured yet.",
		parameters: AddNeedsCaptureSchema,
		async execute(_toolCallId, params) {
			const result = await addNeedsCaptureBlock(params as any);
			return jsonResult(result);
		},
	});

	pi.registerTool({
		name: "show_me_capture_browser_screenshot",
		label: "Show Me: capture browser screenshot",
		description: "Capture a browser screenshot with Playwright when available, ingest it as an image asset, or add a NEEDS_CAPTURE block when unavailable/failing.",
		parameters: CaptureBrowserScreenshotSchema,
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			const result = await captureBrowserScreenshot(params as any, ctx.cwd);
			return jsonResult(result);
		},
	});

	pi.registerTool({
		name: "show_me_run_command",
		label: "Show Me: run command evidence",
		description: "Run a command, store redacted stdout/stderr logs with metadata, and optionally add a command-log block to a section. Blocks risky commands unless allowRisky=true after explicit user approval.",
		parameters: RunCommandSchema,
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			const result = await runCommandEvidence(params as any, ctx.cwd);
			return jsonResult(result);
		},
	});

	pi.registerTool({
		name: "show_me_render",
		label: "Show Me: render",
		description: "Render a Show Me deck to index.html and update the deck index.",
		parameters: DeckIdSchema,
		async execute(_toolCallId, params) {
			const result = await renderDeck(params.deckId);
			return jsonResult(result);
		},
	});

	pi.registerTool({
		name: "show_me_get",
		label: "Show Me: get deck",
		description: "Read the current Show Me source document for a deck.",
		parameters: DeckIdSchema,
		async execute(_toolCallId, params) {
			const { root, doc } = await readDeck(params.deckId);
			return jsonResult({ root, doc });
		},
	});

	pi.registerCommand("show-me", {
		description: "Manage Show Me decks: doctor, list, open [latest|deck-id], clean",
		getArgumentCompletions: (prefix) => {
			const values = ["doctor", "list", "open", "clean"];
			return values.filter((value) => value.startsWith(prefix)).map((value) => ({ value, label: value }));
		},
		handler: async (args, ctx) => {
			const [subcommand = "doctor", target = "latest"] = args.trim().split(/\s+/).filter(Boolean);

			if (subcommand === "doctor") {
				ctx.ui.notify(await doctorText(ctx.cwd), "info");
				return;
			}

			if (subcommand === "list") {
				const entries = await listIndexEntries();
				if (entries.length === 0) {
					ctx.ui.notify("No show-me decks found.", "info");
					return;
				}
				const lines = entries
					.slice(0, 20)
					.map((entry) => `${entry.deckId}  ${entry.status}  ${entry.mode}  ${entry.title}\n  ${entry.indexHtml}`)
					.join("\n");
				ctx.ui.notify(`Recent show-me decks:\n${lines}`, "info");
				return;
			}

			if (subcommand === "open") {
				const entry = await findIndexEntry(target);
				if (!entry) {
					ctx.ui.notify(`No show-me deck found for '${target}'.`, "error");
					return;
				}
				if (!(await pathExists(entry.indexHtml))) {
					ctx.ui.notify(`Deck exists but index.html is missing. Render it first: ${entry.root}`, "warning");
					return;
				}
				const opened = await openPath(entry.indexHtml);
				ctx.ui.notify(opened ? `Opened ${entry.indexHtml}` : `Open unavailable. Deck path: ${entry.indexHtml}`, opened ? "success" : "info");
				return;
			}

			if (subcommand === "clean") {
				const entry = target === "all" ? undefined : await findIndexEntry(target);
				if (target !== "all" && !entry) {
					ctx.ui.notify(`No show-me deck found for '${target}'.`, "error");
					return;
				}
				const message = target === "all" ? "Delete all indexed show-me deck directories?" : `Delete show-me deck '${entry!.title}' at ${entry!.root}?`;
				const ok = await ctx.ui.confirm("show-me clean", message);
				if (!ok) return;
				if (target === "all") {
					const entries = await listIndexEntries();
					let deleted = 0;
					for (const current of entries) {
						await deleteDeckRoot(current.root, current.deckId);
						deleted += 1;
					}
					ctx.ui.notify(`Deleted ${deleted} show-me deck directories.`, "success");
				} else {
					await deleteDeckRoot(entry!.root, entry!.deckId);
					ctx.ui.notify(`Deleted ${entry!.root}`, "success");
				}
				return;
			}

			const latest = await latestIndexEntry();
			ctx.ui.notify(`Unknown /show-me subcommand '${subcommand}'. Try: doctor, list, open ${latest ? "latest" : "<deck-id>"}, clean.`, "warning");
		},
	});
}
