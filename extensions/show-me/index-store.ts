import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

export interface ShowMeIndexEntry {
	deckId: string;
	title: string;
	mode: string;
	status: string;
	root: string;
	indexHtml: string;
	updatedAt: string;
	createdAt: string;
}

export interface ShowMeIndex {
	version: 1;
	entries: ShowMeIndexEntry[];
}

export function stateRoot(): string {
	return process.env.BEISLID_STATE_DIR || join(process.env.HOME || process.cwd(), ".local", "state", "beislid");
}

export function showMeRoot(): string {
	return join(stateRoot(), "show-me");
}

export function indexPath(): string {
	return join(showMeRoot(), "index.json");
}

export async function readIndex(): Promise<ShowMeIndex> {
	const path = indexPath();
	if (!existsSync(path)) return { version: 1, entries: [] };
	try {
		const parsed = JSON.parse(await readFile(path, "utf-8")) as ShowMeIndex;
		return { version: 1, entries: Array.isArray(parsed.entries) ? parsed.entries : [] };
	} catch {
		return { version: 1, entries: [] };
	}
}

export async function writeIndex(index: ShowMeIndex): Promise<void> {
	const path = indexPath();
	await mkdir(dirname(path), { recursive: true });
	await writeFile(path, `${JSON.stringify(index, null, 2)}\n`, "utf-8");
}

export async function upsertIndexEntry(entry: ShowMeIndexEntry): Promise<void> {
	const index = await readIndex();
	const without = index.entries.filter((existing) => existing.deckId !== entry.deckId);
	without.unshift(entry);
	without.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
	await writeIndex({ version: 1, entries: without });
}

export async function listIndexEntries(): Promise<ShowMeIndexEntry[]> {
	const index = await readIndex();
	return index.entries.filter((entry) => existsSync(entry.root));
}

export async function latestIndexEntry(): Promise<ShowMeIndexEntry | undefined> {
	return (await listIndexEntries())[0];
}

export async function findIndexEntry(deckIdOrLatest: string): Promise<ShowMeIndexEntry | undefined> {
	if (!deckIdOrLatest || deckIdOrLatest === "latest") return latestIndexEntry();
	const entries = await listIndexEntries();
	return entries.find((entry) => entry.deckId === deckIdOrLatest || entry.deckId.startsWith(deckIdOrLatest));
}
