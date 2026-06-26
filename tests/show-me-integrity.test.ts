import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { pathToFileURL } from "node:url";
import { after, test } from "node:test";

async function withTempState<T>(fn: (stateDir: string) => Promise<T>): Promise<T> {
	const stateDir = await mkdtemp(join(tmpdir(), "show-me-state-"));
	const previousState = process.env.BEISLID_STATE_DIR;
	process.env.BEISLID_STATE_DIR = stateDir;
	try {
		return await fn(stateDir);
	} finally {
		if (previousState === undefined) delete process.env.BEISLID_STATE_DIR;
		else process.env.BEISLID_STATE_DIR = previousState;
		await rm(stateDir, { recursive: true, force: true });
	}
}

async function makeDeckRoot(stateDir: string, deckId: string, repoName = "repo"): Promise<string> {
	const root = join(showMeRoot(), repoName, deckId);
	await mkdir(root, { recursive: true });
	const doc = {
		id: deckId,
		title: `Deck ${deckId}`,
		mode: "verification",
		status: "PASS",
		createdAt: "2026-06-26T00:00:00.000Z",
		updatedAt: "2026-06-26T00:00:00.000Z",
		sections: [],
		assets: [],
		logs: [],
		provenance: { cwd: stateDir },
	};
	await writeFile(join(root, "show-me.json"), `${JSON.stringify(doc, null, 2)}\n`, "utf-8");
	return root;
}

interface ShowMeSandbox {
	sandboxDir: string;
	runCommandEvidence: typeof import("../extensions/show-me/command-runner.ts").runCommandEvidence;
	readIndex: typeof import("../extensions/show-me/index-store.ts").readIndex;
	showMeRoot: typeof import("../extensions/show-me/index-store.ts").showMeRoot;
	upsertIndexEntry: typeof import("../extensions/show-me/index-store.ts").upsertIndexEntry;
	redactShowMeDocument: typeof import("../extensions/show-me/redaction.ts").redactShowMeDocument;
	redactText: typeof import("../extensions/show-me/redaction.ts").redactText;
}

async function prepareShowMeSandbox(): Promise<ShowMeSandbox> {
	const sandboxDir = await mkdtemp(join(tmpdir(), "show-me-sandbox-"));
	const sourceDir = join(process.cwd(), "extensions/show-me");
	const copy = async (name: string) => {
		await writeFile(join(sandboxDir, name), await readFile(join(sourceDir, name), "utf-8"), "utf-8");
	};
	for (const name of ["command-runner.ts", "index-store.ts", "redaction.ts", "renderer.ts", "store.ts"]) {
		await copy(name);
	}
	await writeFile(join(sandboxDir, "schema.js"), `export const SHOW_ME_MODES = [\n  'verification',\n  'review',\n  'code-walkthrough',\n  'ui-demo',\n  'cli-demo',\n  'docs',\n  'understanding',\n  'mixed',\n];\n\nexport const SHOW_ME_STATUSES = [\n  'PASS',\n  'FAIL',\n  'INCOMPLETE',\n  'NOT SHOWN',\n  'NEEDS CAPTURE',\n  'EXPLANATORY',\n  'CONFLICTING',\n  'LOW_CONFIDENCE',\n];\n\nexport const SHOW_ME_PRESENTATIONS = ['report', 'visual-deck', 'evidence-deck'];\n\nexport function isShowMeMode(value) {\n  return typeof value === 'string' && SHOW_ME_MODES.includes(value);\n}\n\nexport function isShowMeStatus(value) {\n  return typeof value === 'string' && SHOW_ME_STATUSES.includes(value);\n}\n`, "utf-8");
	for (const name of ["redaction.js", "index-store.js", "renderer.js", "store.js", "command-runner.js"]) {
		await writeFile(join(sandboxDir, name), `export * from './${name.replace(/\.js$/, '.ts')}';\n`, "utf-8");
	}
	const modules = {
		runCommandEvidence: (await import(pathToFileURL(join(sandboxDir, "command-runner.ts")).href)).runCommandEvidence,
		readIndex: (await import(pathToFileURL(join(sandboxDir, "index-store.ts")).href)).readIndex,
		showMeRoot: (await import(pathToFileURL(join(sandboxDir, "index-store.ts")).href)).showMeRoot,
		upsertIndexEntry: (await import(pathToFileURL(join(sandboxDir, "index-store.ts")).href)).upsertIndexEntry,
		redactShowMeDocument: (await import(pathToFileURL(join(sandboxDir, "redaction.ts")).href)).redactShowMeDocument,
		redactText: (await import(pathToFileURL(join(sandboxDir, "redaction.ts")).href)).redactText,
	};
	return { sandboxDir, ...modules };
}

const sandbox = await prepareShowMeSandbox();
const { runCommandEvidence, readIndex, showMeRoot, upsertIndexEntry, redactShowMeDocument, redactText } = sandbox;
after(async () => {
	await rm(sandbox.sandboxDir, { recursive: true, force: true });
});

test("show-me redaction covers the verified secret formats and stays idempotent", () => {
	const githubPat = ["github_pat", "abcdefghijklmnopqrstuvwxyz012345"].join("_");
	const pem = ["-----BEGIN PRIVATE KEY-----", "abc", "-----END PRIVATE KEY-----"].join("\n");
	const jwt = ["eyJhbGciOiJIUzI1NiJ9", "eyJzdWIiOiIxIn0", "signature"].join(".");
	const slack = ["xoxb", "1234567890", "abcdefABCDEFghij"].join("-");
	const awsSecret = ["AWS_SECRET_ACCESS_KEY", "abcdabcdabcdabcdabcd"].join("=");
	const sample = [
		githubPat,
		pem,
		jwt,
		slack,
		awsSecret,
		"--token abc123def456",
		"--token \"abc123def456\"",
		"token: \"abc123def456\"",
	].join("\n");
	const redacted = redactText(sample);
	assert.match(redacted.text, /\[REDACTED_GITHUB_TOKEN\]/);
	assert.match(redacted.text, /\[REDACTED_PEM_BLOCK\]/);
	assert.match(redacted.text, /\[REDACTED_JWT\]/);
	assert.match(redacted.text, /\[REDACTED_SLACK_TOKEN\]/);
	assert.match(redacted.text, /AWS_SECRET_ACCESS_KEY=\[REDACTED_AWS_SECRET_KEY\]/);
	assert.match(redacted.text, /--token \[REDACTED\]/);
	assert.match(redacted.text, /--token \"\[REDACTED\]\"/);
	assert.match(redacted.text, /token: \"\[REDACTED\]\"/);
	assert.equal(redacted.summary.total, 8);

	const source = {
		id: "deck-1",
		title: "Deck",
		mode: "verification",
		status: "PASS",
		createdAt: "2026-06-26T00:00:00.000Z",
		updatedAt: "2026-06-26T00:00:00.000Z",
		sections: [{ id: "section-1", title: "Evidence", blocks: [{ id: "block-1", type: "markdown", markdown: "token: abc123def456" }]}],
		assets: [],
		logs: [],
		provenance: { cwd: "/tmp/show-me", redactions: { total: 5, byRule: { previous: 5 } } },
	};
	const first = redactShowMeDocument(structuredClone(source as any));
	assert.equal(first.doc.provenance.redactions.total, 6);
	assert.equal((first.doc.provenance.redactions as { byRule: Record<string, number> }).byRule.previous, 5);
	const second = redactShowMeDocument(structuredClone(first.doc));
	assert.deepEqual(second.doc.provenance.redactions, first.doc.provenance.redactions);
});

test("show-me command capture preserves split UTF-8 and truncates without corruption", async () => {
	await withTempState(async (stateDir) => {
		const root = await makeDeckRoot(stateDir, "deck-utf8");
		await upsertIndexEntry({
			deckId: "deck-utf8",
			title: "Deck deck-utf8",
			mode: "verification",
			status: "PASS",
			root,
			indexHtml: join(root, "index.html"),
			createdAt: "2026-06-26T00:00:00.000Z",
			updatedAt: "2026-06-26T00:00:00.000Z",
		});
		const previousLimit = process.env.BEISLID_SHOW_ME_CAPTURE_LIMIT_BYTES;
		delete process.env.BEISLID_SHOW_ME_CAPTURE_LIMIT_BYTES;
		try {
			const result = await runCommandEvidence(
				{
					deckId: "deck-utf8",
					command: "node -e 'process.stdout.write(\"start\"); process.stdout.write(Buffer.from([0xF0,0x9F])); setTimeout(() => { process.stdout.write(Buffer.from([0x98,0x8A])); process.stdout.write(\"end\"); }, 10); setTimeout(() => {}, 30);'",
				},
				stateDir,
			);
			const log = await readFile(result.logPath, "utf-8");
			assert.match(log, /start😊end/);
			assert.equal(result.stdoutTruncated, false);
		} finally {
			if (previousLimit === undefined) delete process.env.BEISLID_SHOW_ME_CAPTURE_LIMIT_BYTES;
			else process.env.BEISLID_SHOW_ME_CAPTURE_LIMIT_BYTES = previousLimit;
		}
	});

	await withTempState(async (stateDir) => {
		const root = await makeDeckRoot(stateDir, "deck-trunc");
		await upsertIndexEntry({
			deckId: "deck-trunc",
			title: "Deck deck-trunc",
			mode: "verification",
			status: "PASS",
			root,
			indexHtml: join(root, "index.html"),
			createdAt: "2026-06-26T00:00:00.000Z",
			updatedAt: "2026-06-26T00:00:00.000Z",
		});
		const previousLimit = process.env.BEISLID_SHOW_ME_CAPTURE_LIMIT_BYTES;
		process.env.BEISLID_SHOW_ME_CAPTURE_LIMIT_BYTES = "3";
		try {
			const result = await runCommandEvidence(
				{
					deckId: "deck-trunc",
					command: "node -e 'process.stdout.write(\"a😊b\")'",
				},
				stateDir,
			);
			const log = await readFile(result.logPath, "utf-8");
			assert.equal(result.stdoutTruncated, true);
			assert.match(log, /stdoutTruncated: true/);
			assert.match(log, /--- stdout ---\na/);
			assert.doesNotMatch(log, /\uFFFD/);
		} finally {
			if (previousLimit === undefined) delete process.env.BEISLID_SHOW_ME_CAPTURE_LIMIT_BYTES;
			else process.env.BEISLID_SHOW_ME_CAPTURE_LIMIT_BYTES = previousLimit;
		}
	});
});

test("show-me index recovery tolerates a corrupt index and keeps concurrent upserts", async () => {
	await withTempState(async (stateDir) => {
		const roots = ["deck-a", "deck-b", "deck-c", "deck-d", "deck-e"];
		for (const [index, deckId] of roots.entries()) await makeDeckRoot(stateDir, deckId, index < 3 ? "repo-a" : "repo-b");
		await writeFile(join(showMeRoot(), "index.json"), "{\"version\":1,\"entries\":", "utf-8");

		const recovered = await readIndex();
		assert.equal(recovered.entries.length, roots.length);
		assert.deepEqual(recovered.entries.map((entry) => entry.deckId).sort(), roots.slice().sort());

		await Promise.all(
			Array.from({ length: 12 }, async (_value, index) => {
				const deckId = `deck-${index + 10}`;
				const root = await makeDeckRoot(stateDir, deckId);
				await upsertIndexEntry({
					deckId,
					title: `Deck ${deckId}`,
					mode: "verification",
					status: "PASS",
					root,
					indexHtml: join(root, "index.html"),
					createdAt: `2026-06-26T00:00:${String(index).padStart(2, "0")}.000Z`,
					updatedAt: `2026-06-26T00:00:${String(index).padStart(2, "0")}.000Z`,
				});
			}),
		);

		const finalIndex = await readIndex();
		for (const deckId of [...roots, ...Array.from({ length: 12 }, (_value, index) => `deck-${index + 10}`)]) {
			assert.ok(finalIndex.entries.some((entry) => entry.deckId === deckId), `missing ${deckId}`);
		}
	});
});
