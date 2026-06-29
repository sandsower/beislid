import { existsSync } from "node:fs";
import { mkdir, readFile, readdir, rename, rm, stat, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

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

const INDEX_LOCK_NAME = ".index.lock";
const INDEX_LOCK_STALE_MS = 60_000;
const INDEX_LOCK_POLL_MS = 50;

export function stateRoot(): string {
	return process.env.BEISLID_STATE_DIR || join(process.env.HOME || process.cwd(), ".local", "state", "beislid");
}

export function showMeRoot(): string {
	return join(stateRoot(), "show-me");
}

export function indexPath(): string {
	return join(showMeRoot(), "index.json");
}

function lockPath(): string {
	return join(showMeRoot(), INDEX_LOCK_NAME);
}

function tempIndexPath(): string {
	return join(showMeRoot(), `index.json.tmp-${process.pid}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
}

function isEexist(error: unknown): boolean {
	return typeof error === "object" && error !== null && "code" in error && (error as { code?: unknown }).code === "EEXIST";
}

function isRenameConflict(error: unknown): boolean {
	return typeof error === "object" && error !== null && "code" in error && ((error as { code?: unknown }).code === "EEXIST" || (error as { code?: unknown }).code === "EPERM");
}

function isIndexEntry(value: unknown): value is ShowMeIndexEntry {
	if (!value || typeof value !== "object" || Array.isArray(value)) return false;
	const entry = value as Partial<ShowMeIndexEntry>;
	return typeof entry.deckId === "string" && typeof entry.title === "string" && typeof entry.mode === "string" && typeof entry.status === "string" && typeof entry.root === "string" && typeof entry.indexHtml === "string" && typeof entry.updatedAt === "string" && typeof entry.createdAt === "string";
}

function normalizeIndex(entries: unknown): ShowMeIndex {
	return {
		version: 1,
		entries: Array.isArray(entries) ? entries.filter(isIndexEntry).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)) : [],
	};
}

async function recoverIndex(): Promise<ShowMeIndex> {
	const root = showMeRoot();
	const entries: ShowMeIndexEntry[] = [];

	async function scan(dir: string): Promise<void> {
		let dirents: Awaited<ReturnType<typeof readdir>> = [];
		try {
			dirents = await readdir(dir, { withFileTypes: true });
		} catch {
			return;
		}

		if (dirents.some((dirent) => dirent.isFile() && dirent.name === "show-me.json")) {
			try {
				const parsed = JSON.parse(await readFile(join(dir, "show-me.json"), "utf-8")) as {
					id?: unknown;
					title?: unknown;
					mode?: unknown;
					status?: unknown;
					createdAt?: unknown;
					updatedAt?: unknown;
				};
				if (typeof parsed.id === "string" && typeof parsed.title === "string" && typeof parsed.mode === "string" && typeof parsed.status === "string" && typeof parsed.createdAt === "string" && typeof parsed.updatedAt === "string") {
					entries.push({
						deckId: parsed.id,
						title: parsed.title,
						mode: parsed.mode,
						status: parsed.status,
						root: dir,
						indexHtml: join(dir, "index.html"),
						createdAt: parsed.createdAt,
						updatedAt: parsed.updatedAt,
					});
				}
			} catch {
				// Ignore unreadable or partially written deck roots during recovery.
			}
			return;
		}

		for (const dirent of dirents) {
			if (!dirent.isDirectory() || dirent.name.startsWith(".")) continue;
			await scan(join(dir, dirent.name));
		}
	}

	await scan(root);
	entries.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
	return { version: 1, entries };
}

async function maybeBreakStaleLock(path: string): Promise<boolean> {
	try {
		const info = await stat(path);
		if (Date.now() - info.mtimeMs < INDEX_LOCK_STALE_MS) return false;
	} catch {
		return true;
	}
	await rm(path, { recursive: true, force: true }).catch(() => undefined);
	return true;
}

async function withIndexLock<T>(operation: () => Promise<T>): Promise<T> {
	await mkdir(showMeRoot(), { recursive: true });
	const path = lockPath();
	while (true) {
		try {
			await mkdir(path);
			try {
				await writeFile(join(path, "owner.json"), `${JSON.stringify({ pid: process.pid, startedAt: new Date().toISOString() }, null, 2)}\n`, "utf-8");
			} catch {
				// Best-effort lock metadata only.
			}
			try {
				return await operation();
			} finally {
				await rm(path, { recursive: true, force: true }).catch(() => undefined);
			}
		} catch (error) {
			if (!isEexist(error)) throw error;
			if (await maybeBreakStaleLock(path)) continue;
			await delay(INDEX_LOCK_POLL_MS);
		}
	}
}

export async function readIndex(): Promise<ShowMeIndex> {
	const path = indexPath();
	if (!existsSync(path)) return recoverIndex();
	try {
		const parsed = JSON.parse(await readFile(path, "utf-8")) as ShowMeIndex;
		return normalizeIndex(parsed.entries);
	} catch {
		return recoverIndex();
	}
}

export async function writeIndex(index: ShowMeIndex): Promise<void> {
	const path = indexPath();
	await mkdir(dirname(path), { recursive: true });
	const tempPath = tempIndexPath();
	await writeFile(tempPath, `${JSON.stringify(index, null, 2)}\n`, "utf-8");
	try {
		await rename(tempPath, path);
	} catch (error) {
		if (!isRenameConflict(error)) throw error;
		await rm(path, { force: true }).catch(() => undefined);
		await rename(tempPath, path);
	}
}

export async function upsertIndexEntry(entry: ShowMeIndexEntry): Promise<void> {
	await withIndexLock(async () => {
		const index = await readIndex();
		const without = index.entries.filter((existing) => existing.deckId !== entry.deckId);
		without.unshift(entry);
		without.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
		await writeIndex({ version: 1, entries: without });
	});
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
	const exact = entries.find((entry) => entry.deckId === deckIdOrLatest);
	if (exact) return exact;
	const matches = entries.filter((entry) => entry.deckId.startsWith(deckIdOrLatest));
	if (matches.length === 1) return matches[0];
	if (matches.length > 1) {
		const matchedIds = matches.map((entry) => entry.deckId).sort().join(", ");
		throw new Error(`Ambiguous show-me deck id '${deckIdOrLatest}'. Matches: ${matchedIds}`);
	}
	return undefined;
}
