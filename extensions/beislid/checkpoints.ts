import { readFile } from "node:fs/promises";
import { isAbsolute, join, normalize } from "node:path";

export type LatestCheckpointEntry = {
	event?: string;
	path?: string;
	branch?: string;
	source_skill?: string;
	written_at?: string;
	ticket?: { id?: string; title?: string };
	[key: string]: unknown;
};

export type BoundaryIdentity = {
	event: string;
	path: string;
	branch?: string;
	ticketId?: string;
	writtenAt?: string;
	runId?: string;
	id: string;
};

export type CheckpointPointerSnapshot = {
	latestPath: string;
	entries: LatestCheckpointEntry[];
	identities: BoundaryIdentity[];
};

function isObject(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function normalizeEntry(cwd: string, value: unknown): Promise<LatestCheckpointEntry | undefined> {
	if (!isObject(value)) return undefined;
	const entry = value as LatestCheckpointEntry;
	if (typeof entry.event !== "string" || typeof entry.path !== "string") return undefined;
	const artifactPath = normalize(entry.path);
	if (isAbsolute(artifactPath) || artifactPath === ".." || artifactPath.startsWith(`..${"/"}`)) return undefined;
	try {
		await readFile(join(cwd, artifactPath), "utf8");
	} catch {
		return undefined;
	}
	return { ...entry, path: artifactPath };
}

export function identityForEntry(entry: LatestCheckpointEntry): BoundaryIdentity | undefined {
	if (typeof entry.event !== "string" || typeof entry.path !== "string") return undefined;
	const ticketId = isObject(entry.ticket) && typeof entry.ticket.id === "string" ? entry.ticket.id : undefined;
	const runId = typeof entry.run_id === "string" ? entry.run_id : typeof entry.runId === "string" ? entry.runId : undefined;
	const parts = [entry.event, entry.path, entry.branch ?? "", ticketId ?? "", entry.written_at ?? "", runId ?? ""];
	return {
		event: entry.event,
		path: entry.path,
		branch: typeof entry.branch === "string" ? entry.branch : undefined,
		ticketId,
		writtenAt: typeof entry.written_at === "string" ? entry.written_at : undefined,
		runId,
		id: parts.join("|"),
	};
}

export async function readLatestCheckpoint(cwd: string): Promise<CheckpointPointerSnapshot | undefined> {
	const latestPath = join(cwd, ".beislid", "checkpoints", "latest.json");
	let raw: string;
	try {
		raw = await readFile(latestPath, "utf8");
	} catch {
		return undefined;
	}

	let parsed: unknown;
	try {
		parsed = JSON.parse(raw);
	} catch {
		return undefined;
	}
	if (!isObject(parsed) || !isObject(parsed.latest)) return undefined;

	const entries = (await Promise.all(Object.values(parsed.latest).map((entry) => normalizeEntry(cwd, entry)))).filter(
		(entry) => entry !== undefined,
	);
	const identities = entries.map(identityForEntry).filter((identity) => identity !== undefined);
	return { latestPath: ".beislid/checkpoints/latest.json", entries, identities };
}

export function pickNewBoundary(
	before: CheckpointPointerSnapshot | undefined,
	after: CheckpointPointerSnapshot | undefined,
	allowedEvents: Set<string> | "all",
	excludedEvents: Set<string>,
	consumed: Set<string>,
): BoundaryIdentity | undefined {
	if (!after) return undefined;
	const beforeIds = new Set(before?.identities.map((identity) => identity.id) ?? []);
	const candidates = after.identities.filter((identity) => {
		if (excludedEvents.has(identity.event)) return false;
		if (allowedEvents !== "all" && !allowedEvents.has(identity.event)) return false;
		if (consumed.has(identity.id)) return false;
		return !beforeIds.has(identity.id);
	});
	return candidates.at(-1);
}
