import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { basename, join, resolve } from "node:path";
import { renderShowMeDocument } from "./renderer.js";
import type { MediaBlock, ShowMeBlock, ShowMeDocument, ShowMeMode, ShowMePresentation, ShowMeSection, ShowMeStatus } from "./schema.js";
import { isShowMeMode, isShowMeStatus } from "./schema.js";
import { findIndexEntry, showMeRoot, upsertIndexEntry } from "./index-store.js";
import { redactShowMeDocument } from "./redaction.js";

function nowIso(): string {
	return new Date().toISOString();
}

function shortId(): string {
	return Math.random().toString(36).slice(2, 8);
}

function safeSlug(value: string): string {
	return value
		.toLowerCase()
		.replace(/[^a-z0-9._-]+/g, "-")
		.replace(/^-|-$/g, "") || "deck";
}

async function commandOutput(command: string, cwd: string): Promise<string | undefined> {
	const { execFile } = await import("node:child_process");
	return new Promise((resolveOutput) => {
		execFile("sh", ["-c", command], { cwd, timeout: 1500 }, (error, stdout) => {
			if (error) resolveOutput(undefined);
			else resolveOutput(stdout.trim() || undefined);
		});
	});
}

export interface CreateDeckInput {
	title: string;
	subtitle?: string;
	mode: ShowMeMode;
	status?: ShowMeStatus;
	presentation?: ShowMePresentation;
	summary?: string;
	outputRoot?: string;
	repoLocal?: boolean;
}

function inferPresentation(mode: ShowMeMode, status: ShowMeStatus): ShowMePresentation {
	if (mode === "understanding" && status === "EXPLANATORY") return "visual-deck";
	if (mode === "verification" || mode === "cli-demo" || mode === "ui-demo") return "evidence-deck";
	return "report";
}

export interface DeckPaths {
	deckId: string;
	root: string;
	showMeJson: string;
	manifestJson: string;
	indexHtml: string;
}

export async function createDeck(input: CreateDeckInput, cwd: string): Promise<DeckPaths> {
	if (!isShowMeMode(input.mode)) throw new Error(`Invalid show-me mode: ${input.mode}`);
	if (input.status && !isShowMeStatus(input.status)) throw new Error(`Invalid show-me status: ${input.status}`);

	const createdAt = nowIso();
	const id = `${createdAt.replace(/[:.]/g, "-")}-${shortId()}`;
	const repoName = safeSlug(basename(await commandOutput("git rev-parse --show-toplevel", cwd).then((root) => root || cwd)));
	const root = input.outputRoot
		? join(resolve(cwd, input.outputRoot), id)
		: input.repoLocal
			? join(cwd, ".beislid", "show-me", id)
			: join(showMeRoot(), repoName, id);

	await mkdir(join(root, "assets", "images"), { recursive: true });
	await mkdir(join(root, "assets", "videos"), { recursive: true });
	await mkdir(join(root, "assets", "gifs"), { recursive: true });
	await mkdir(join(root, "assets", "diagrams"), { recursive: true });
	await mkdir(join(root, "logs", "commands"), { recursive: true });
	await writeFile(join(root, ".show-me-deck"), `${id}\n`, "utf-8");

	const repoRoot = await commandOutput("git rev-parse --show-toplevel", cwd);
	const branch = await commandOutput("git branch --show-current", cwd);
	const commit = await commandOutput("git rev-parse HEAD", cwd);
	const dirty = await commandOutput("git status --short", cwd);

	const status = input.status ?? "EXPLANATORY";
	const doc: ShowMeDocument = {
		id,
		title: input.title,
		subtitle: input.subtitle,
		mode: input.mode,
		status,
		presentation: input.presentation ?? inferPresentation(input.mode, status),
		summary: input.summary,
		createdAt,
		updatedAt: createdAt,
		sections: [],
		assets: [],
		logs: [],
		provenance: {
			cwd,
			repoRoot,
			branch,
			commit,
			dirty: Boolean(dirty),
			createdBy: "beislid show-me pi extension",
		},
	};

	await writeDeck(root, doc);
	await writeManifest(root, doc);
	await upsertIndexEntry({
		deckId: doc.id,
		title: doc.title,
		mode: doc.mode,
		status: doc.status,
		root,
		indexHtml: join(root, "index.html"),
		createdAt: doc.createdAt,
		updatedAt: doc.updatedAt,
	});
	return deckPaths(root, id);
}

export function deckPaths(root: string, deckId: string): DeckPaths {
	return {
		deckId,
		root,
		showMeJson: join(root, "show-me.json"),
		manifestJson: join(root, "manifest.json"),
		indexHtml: join(root, "index.html"),
	};
}

export async function resolveDeckRoot(deckId: string): Promise<string> {
	const entry = await findIndexEntry(deckId);
	if (entry) return entry.root;
	throw new Error(`Unknown show-me deck id: ${deckId}. Rendered decks are discoverable through the index; create a deck first or use a full id from /show-me list.`);
}

export async function readDeckByRoot(root: string): Promise<ShowMeDocument> {
	return JSON.parse(await readFile(join(root, "show-me.json"), "utf-8")) as ShowMeDocument;
}

export async function readDeck(deckId: string): Promise<{ root: string; doc: ShowMeDocument }> {
	const root = await resolveDeckRoot(deckId);
	return { root, doc: await readDeckByRoot(root) };
}

export async function writeDeck(root: string, doc: ShowMeDocument): Promise<void> {
	doc.updatedAt = nowIso();
	const redacted = redactShowMeDocument(doc).doc;
	Object.assign(doc, redacted);
	await writeFile(join(root, "show-me.json"), `${JSON.stringify(doc, null, 2)}\n`, "utf-8");
}

export async function writeManifest(root: string, doc: ShowMeDocument): Promise<void> {
	const manifest = {
		version: 1,
		deckId: doc.id,
		title: doc.title,
		mode: doc.mode,
		status: doc.status,
		presentation: doc.presentation,
		createdAt: doc.createdAt,
		updatedAt: doc.updatedAt,
		paths: {
			root,
			indexHtml: join(root, "index.html"),
			showMeJson: join(root, "show-me.json"),
			manifestJson: join(root, "manifest.json"),
		},
		provenance: doc.provenance,
	};
	await writeFile(join(root, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf-8");
}

export async function addSection(deckId: string, title: string, purpose?: string): Promise<{ root: string; doc: ShowMeDocument; section: ShowMeSection }> {
	const { root, doc } = await readDeck(deckId);
	const section: ShowMeSection = { id: `section-${doc.sections.length + 1}-${shortId()}`, title, purpose, blocks: [] };
	doc.sections.push(section);
	await writeDeck(root, doc);
	await writeManifest(root, doc);
	return { root, doc, section };
}

export async function addBlock(deckId: string, sectionId: string, block: Omit<ShowMeBlock, "id"> & { id?: string }): Promise<{ root: string; doc: ShowMeDocument; blockId: string }> {
	const { root, doc } = await readDeck(deckId);
	const section = doc.sections.find((candidate) => candidate.id === sectionId);
	if (!section) throw new Error(`Unknown section id ${sectionId} in deck ${deckId}`);
	const normalized = normalizeBlock(block as any) as Omit<ShowMeBlock, "id"> & { id?: string };
	validateBlock(doc, normalized);
	const blockId = normalized.id || `block-${section.blocks.length + 1}-${shortId()}`;
	section.blocks.push({ ...normalized, id: blockId } as ShowMeBlock);
	await writeDeck(root, doc);
	await writeManifest(root, doc);
	return { root, doc, blockId };
}

function stringValue(value: unknown): string {
	return String(value ?? "");
}

function stringArray(values: unknown): string[] {
	return Array.isArray(values) ? values.map(stringValue) : [];
}

function stringRows(rows: unknown): string[][] {
	if (!Array.isArray(rows)) return [];
	return rows.map((row) => Array.isArray(row) ? row.map(stringValue) : Object.values(row as Record<string, unknown>).map(stringValue));
}

function normalizeBlock(block: Record<string, any>): Record<string, any> {
	switch (block.type) {
		case "markdown":
			return { ...block, markdown: stringValue(block.markdown ?? block.content ?? block.text) };
		case "table":
			return { ...block, columns: stringArray(block.columns ?? block.headers), rows: stringRows(block.rows) };
		case "code":
			return { ...block, code: stringValue(block.code ?? block.content ?? block.text) };
		case "diff":
			return { ...block, diff: stringValue(block.diff ?? block.content ?? block.text) };
		case "callout":
			return { ...block, text: stringValue(block.text ?? block.content ?? block.body) };
		case "verdict":
			return { ...block, text: stringValue(block.text ?? block.content ?? block.body) };
		case "file-role-table":
			return {
				...block,
				rows: Array.isArray(block.rows) ? block.rows.map((row: Record<string, unknown>) => ({
					area: stringValue(row.area ?? row.path ?? row.file),
					files: Array.isArray(row.files) ? row.files.map(stringValue) : [stringValue(row.file ?? row.path)].filter(Boolean),
					role: stringValue(row.role ?? row.description),
					observation: row.observation === undefined && row.note === undefined ? undefined : stringValue(row.observation ?? row.note),
				})) : [],
			};
		case "diagram":
			if (block.path) return block;
			return { ...block, diagram: stringValue(block.diagram ?? block.content ?? block.mermaid ?? block.source), language: block.language ?? "mermaid" };
		default:
			return block;
	}
}

function validateBlock(doc: ShowMeDocument, block: Omit<ShowMeBlock, "id"> & { id?: string }) {
	if (!isMediaBlock(block)) return;
	if (block.path.startsWith("/") || /^[a-z]+:/i.test(block.path) || block.path.split(/[\\/]+/).includes("..")) {
		throw new Error("Media blocks must reference copied deck assets with safe relative paths. Use show_me_add_asset for media files.");
	}
	const expectedPrefix = mediaPathPrefix(block.type);
	if (!block.path.startsWith(expectedPrefix)) {
		throw new Error(`Media block path for ${block.type} must live under ${expectedPrefix}. Use show_me_add_asset.`);
	}
	const asset = doc.assets.find((candidate) => candidate.id === block.assetId);
	if (!asset || asset.path !== block.path || asset.type !== block.type) {
		throw new Error("Media blocks must reference an existing deck asset by assetId/path/type. Use show_me_add_asset.");
	}
}

function isMediaBlock(block: { type?: string; path?: unknown }): block is Omit<MediaBlock, "id"> & { id?: string } {
	return (block.type === "image" || block.type === "video" || block.type === "gif" || block.type === "diagram") && typeof block.path === "string";
}

function mediaPathPrefix(type: MediaBlock["type"]): string {
	if (type === "image") return "assets/images/";
	if (type === "video") return "assets/videos/";
	if (type === "gif") return "assets/gifs/";
	return "assets/diagrams/";
}

export async function renderDeck(deckId: string): Promise<DeckPaths> {
	const { root, doc } = await readDeck(deckId);
	const redacted = redactShowMeDocument(doc).doc;
	Object.assign(doc, redacted);
	const html = renderShowMeDocument(doc);
	await writeDeck(root, doc);
	await writeFile(join(root, "index.html"), html, "utf-8");
	await writeManifest(root, doc);
	await upsertIndexEntry({
		deckId: doc.id,
		title: doc.title,
		mode: doc.mode,
		status: doc.status,
		root,
		indexHtml: join(root, "index.html"),
		createdAt: doc.createdAt,
		updatedAt: doc.updatedAt,
	});
	return deckPaths(root, doc.id);
}

export async function pathExists(path: string): Promise<boolean> {
	return existsSync(path);
}
