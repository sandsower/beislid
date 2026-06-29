import assert from "node:assert/strict";
import { existsSync } from "node:fs";
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
	await writeFile(join(root, ".show-me-deck"), `${deckId}\n`, "utf-8");
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

type ShowMeCommandCtx = {
	cwd: string;
	hasUI: boolean;
	ui?: {
		notify(message: string, level: string): void;
		confirm(title: string, message: string): Promise<boolean>;
	};
};

type ShowMeCommandRegistration = {
	handler: (args: string, ctx: ShowMeCommandCtx) => Promise<void>;
};

interface ShowMeSandbox {
	sandboxDir: string;
	runCommandEvidence: typeof import("../extensions/show-me/command-runner.ts").runCommandEvidence;
	readIndex: typeof import("../extensions/show-me/index-store.ts").readIndex;
	showMeRoot: typeof import("../extensions/show-me/index-store.ts").showMeRoot;
	upsertIndexEntry: typeof import("../extensions/show-me/index-store.ts").upsertIndexEntry;
	renderShowMeDocument: typeof import("../extensions/show-me/renderer.ts").renderShowMeDocument;
	redactShowMeDocument: typeof import("../extensions/show-me/redaction.ts").redactShowMeDocument;
	redactText: typeof import("../extensions/show-me/redaction.ts").redactText;
	findIndexEntry: typeof import("../extensions/show-me/index-store.ts").findIndexEntry;
	showMeExtension: typeof import("../extensions/show-me/index.ts").default;
	getShowMeDoctorReport: typeof import("../extensions/show-me/doctor.ts").getShowMeDoctorReport;
	formatDoctorReport: typeof import("../extensions/show-me/doctor.ts").formatDoctorReport;
}

async function prepareShowMeSandbox(): Promise<ShowMeSandbox> {
	const sandboxDir = await mkdtemp(join(tmpdir(), "show-me-sandbox-"));
	const sourceDir = join(process.cwd(), "extensions/show-me");
	const copy = async (name: string) => {
		await writeFile(join(sandboxDir, name), await readFile(join(sourceDir, name), "utf-8"), "utf-8");
	};
	for (const name of ["asset-manager.ts", "capture-browser.ts", "capture-helpers.ts", "command-runner.ts", "doctor.ts", "index-store.ts", "index.ts", "needs-capture.ts", "redaction.ts", "renderer.ts", "store.ts", "tooling.ts"]) {
		await copy(name);
	}
	await writeFile(join(sandboxDir, "schema.js"), `const schema = (kind) => ({ kind });\n\nexport const SHOW_ME_MODES = [\n  'verification',\n  'review',\n  'code-walkthrough',\n  'ui-demo',\n  'cli-demo',\n  'docs',\n  'understanding',\n  'mixed',\n];\n\nexport const SHOW_ME_STATUSES = [\n  'PASS',\n  'FAIL',\n  'INCOMPLETE',\n  'NOT SHOWN',\n  'NEEDS CAPTURE',\n  'EXPLANATORY',\n  'CONFLICTING',\n  'LOW_CONFIDENCE',\n];\n\nexport const SHOW_ME_PRESENTATIONS = ['report', 'visual-deck', 'evidence-deck'];\n\nexport const CreateDeckSchema = schema('CreateDeckSchema');\nexport const DeckIdSchema = schema('DeckIdSchema');\nexport const AddSectionSchema = schema('AddSectionSchema');\nexport const AddBlockSchema = schema('AddBlockSchema');\nexport const RunCommandSchema = schema('RunCommandSchema');\nexport const AddAssetSchema = schema('AddAssetSchema');\nexport const AddNeedsCaptureSchema = schema('AddNeedsCaptureSchema');\nexport const CaptureBrowserScreenshotSchema = schema('CaptureBrowserScreenshotSchema');\nexport const CaptureScreenScreenshotSchema = schema('CaptureScreenScreenshotSchema');\nexport const RecordTerminalSessionSchema = schema('RecordTerminalSessionSchema');\nexport const ConvertVideoToGifSchema = schema('ConvertVideoToGifSchema');\nexport const ConvertGifToVideoSchema = schema('ConvertGifToVideoSchema');\n\nexport function isShowMeMode(value) {\n  return typeof value === 'string' && SHOW_ME_MODES.includes(value);\n}\n\nexport function isShowMeStatus(value) {\n  return typeof value === 'string' && SHOW_ME_STATUSES.includes(value);\n}\n`, "utf-8");
	for (const name of ["asset-manager.js", "capture-browser.js", "capture-helpers.js", "command-runner.js", "doctor.js", "index-store.js", "needs-capture.js", "redaction.js", "renderer.js", "store.js", "tooling.js"]) {
		await writeFile(join(sandboxDir, name), `export * from './${name.replace(/\.js$/, '.ts')}';\n`, "utf-8");
	}
	const modules = {
		showMeExtension: (await import(pathToFileURL(join(sandboxDir, "index.ts")).href)).default,
		getShowMeDoctorReport: (await import(pathToFileURL(join(sandboxDir, "doctor.ts")).href)).getShowMeDoctorReport,
		formatDoctorReport: (await import(pathToFileURL(join(sandboxDir, "doctor.ts")).href)).formatDoctorReport,
		renderShowMeDocument: (await import(pathToFileURL(join(sandboxDir, "renderer.ts")).href)).renderShowMeDocument,
		runCommandEvidence: (await import(pathToFileURL(join(sandboxDir, "command-runner.ts")).href)).runCommandEvidence,
		readIndex: (await import(pathToFileURL(join(sandboxDir, "index-store.ts")).href)).readIndex,
		findIndexEntry: (await import(pathToFileURL(join(sandboxDir, "index-store.ts")).href)).findIndexEntry,
		showMeRoot: (await import(pathToFileURL(join(sandboxDir, "index-store.ts")).href)).showMeRoot,
		upsertIndexEntry: (await import(pathToFileURL(join(sandboxDir, "index-store.ts")).href)).upsertIndexEntry,
		redactShowMeDocument: (await import(pathToFileURL(join(sandboxDir, "redaction.ts")).href)).redactShowMeDocument,
		redactText: (await import(pathToFileURL(join(sandboxDir, "redaction.ts")).href)).redactText,
	};
	return { sandboxDir, ...modules };
}

const sandbox = await prepareShowMeSandbox();
const { runCommandEvidence, readIndex, showMeRoot, upsertIndexEntry, renderShowMeDocument, findIndexEntry, showMeExtension, redactShowMeDocument, redactText, getShowMeDoctorReport, formatDoctorReport } = sandbox;
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

	const source: Parameters<typeof redactShowMeDocument>[0] = {
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
	const first = redactShowMeDocument(structuredClone(source));
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

test("show-me deck lookup rejects ambiguous prefixes and keeps exact matches", async () => {
	await withTempState(async (stateDir) => {
		const exactRoot = await makeDeckRoot(stateDir, "deck-alpha-1");
		const siblingRoot = await makeDeckRoot(stateDir, "deck-alpha-2");
		await upsertIndexEntry({
			deckId: "deck-alpha-1",
			title: "Deck alpha 1",
			mode: "verification",
			status: "PASS",
			root: exactRoot,
			indexHtml: join(exactRoot, "index.html"),
			createdAt: "2026-06-26T00:00:00.000Z",
			updatedAt: "2026-06-26T00:00:00.000Z",
		});
		await upsertIndexEntry({
			deckId: "deck-alpha-2",
			title: "Deck alpha 2",
			mode: "verification",
			status: "PASS",
			root: siblingRoot,
			indexHtml: join(siblingRoot, "index.html"),
			createdAt: "2026-06-26T00:00:01.000Z",
			updatedAt: "2026-06-26T00:00:01.000Z",
		});

		await assert.rejects(() => findIndexEntry("deck-alpha"), /Ambiguous show-me deck id 'deck-alpha'/);
		assert.equal((await findIndexEntry("deck-alpha-1"))?.deckId, "deck-alpha-1");
	});
});

test("show-me renderer pins CDN libraries and clean-all tolerates corrupt deck roots", async () => {
	const html = renderShowMeDocument({
		id: "deck-render",
		title: "Deck render",
		mode: "verification",
		status: "PASS",
		createdAt: "2026-06-26T00:00:00.000Z",
		updatedAt: "2026-06-26T00:00:00.000Z",
		sections: [{
			id: "section-1",
			title: "Evidence",
			blocks: [{
				id: "block-1",
				type: "command-log",
				logId: "log-1",
				command: "asciinema rec -q -c 'echo hi' session.cast",
				cwd: "/tmp/show-me",
				startedAt: "2026-06-26T00:00:00.000Z",
				finishedAt: "2026-06-26T00:00:01.000Z",
				exitCode: 0,
				timedOut: false,
				logPath: "logs/terminal/log-1.cast",
				recordingPath: "logs/terminal/log-1.cast",
				recordingFormat: "cast",
				stdoutPreview: "hi",
			}],
		}],
		assets: [],
		logs: [],
		provenance: { cwd: "/tmp/show-me" },
	});
	assert.match(html, /marked@18\.0\.5\/lib\/marked\.umd\.js/);
	assert.match(html, /dompurify@3\.4\.11\/dist\/purify\.min\.js/);
	assert.match(html, /mermaid@11\.16\.0\/dist\/mermaid\.min\.js/);
	assert.match(html, /integrity="sha384-ZD0fTOwPMHi7zM6WTVIWJR21I07lq0ccnqz3J6WMvQKG9thh4y7TA1QE6PJu0Af8" crossorigin="anonymous"/);
	assert.match(html, /integrity="sha384-o44XUELLEnv\/iSlA1NWxBweqbD4TSR0qgq2VzVsxtkHS989JJjGKSE9vkfo5MN4K" crossorigin="anonymous"/);
	assert.match(html, /integrity="sha384-T\/0lMUdJpd2S1ZHtRiofG3htU3xPCrFVeAQ1UUE2TJwlEJSV5NUwn30kP28n238E" crossorigin="anonymous"/);
	assert.match(html, /integrity="sha384-F\/bZzf7p3Joyp5psL90p\/p89AZJsndkSoGwRpXcZhleCWhd8SnRuoYo4d0yirjJp" crossorigin="anonymous"/);
	assert.match(html, /integrity="sha384-wH75j6z1lH97ZOpMOInqhgKzFkAInZPPSPlZpYKYTOqsaizPvhQZmAtLcPKXpLyH" crossorigin="anonymous"/);
	assert.doesNotMatch(html, /cdn\.jsdelivr\.net\/npm\/marked\/marked\.min\.js/);
	assert.match(html, /recording: logs\/terminal\/log-1\.cast \(cast\)/);

	await withTempState(async (stateDir) => {
		const commands = new Map<string, ShowMeCommandRegistration>();
		const tools: string[] = [];
		showMeExtension({
			registerTool: (tool: { name: string }) => {
				tools.push(tool.name);
			},
			registerCommand: (name: string, command: ShowMeCommandRegistration) => {
				commands.set(name, command);
			},
			on: () => undefined,
		} as never);
		assert.ok(tools.includes("show_me_capture_screen_screenshot"));
		assert.ok(tools.includes("show_me_record_terminal"));
		assert.ok(tools.includes("show_me_convert_video_to_gif"));
		assert.ok(tools.includes("show_me_convert_gif_to_video"));
		const command = commands.get("show-me");
		assert.ok(command);

		await command!.handler("doctor", { cwd: stateDir, hasUI: false });

		const cleanRoot = await makeDeckRoot(stateDir, "deck-clean");
		const corruptRoot = await makeDeckRoot(stateDir, "deck-corrupt");
		await upsertIndexEntry({
			deckId: "deck-clean",
			title: "Deck clean",
			mode: "verification",
			status: "PASS",
			root: cleanRoot,
			indexHtml: join(cleanRoot, "index.html"),
			createdAt: "2026-06-26T00:00:00.000Z",
			updatedAt: "2026-06-26T00:00:00.000Z",
		});
		await upsertIndexEntry({
			deckId: "deck-corrupt",
			title: "Deck corrupt",
			mode: "verification",
			status: "PASS",
			root: corruptRoot,
			indexHtml: join(corruptRoot, "index.html"),
			createdAt: "2026-06-26T00:00:01.000Z",
			updatedAt: "2026-06-26T00:00:01.000Z",
		});
		await writeFile(join(corruptRoot, "show-me.json"), "{\n  \"id\": \"deck-corrupt\",\n", "utf-8");

		const notifications: Array<{ message: string; level: string }> = [];
		await command!.handler("clean all", {
			cwd: stateDir,
			hasUI: true,
			ui: {
				notify: (message, level) => notifications.push({ message, level }),
				confirm: async () => true,
			},
		});

		assert.equal(existsSync(cleanRoot), false);
		assert.equal(existsSync(corruptRoot), false);
		assert.match(notifications.at(-1)?.message ?? "", /Deleted 2 show-me deck directories\./);
	});
});

test("show-me doctor reports the new capture helpers and actionable remediation", async () => {
	const report = await getShowMeDoctorReport("/tmp/show-me-doctor");
	const labels = report.capture.map((capability) => capability.label);
	assert.ok(labels.includes("browser screenshots"));
	assert.ok(labels.includes("screen/window screenshots"));
	assert.ok(labels.includes("terminal recordings"));
	assert.ok(labels.includes("video → GIF conversion"));
	assert.ok(labels.includes("GIF → video conversion"));

	const doctorText = formatDoctorReport({
		builder: [{ id: "extension", label: "extension loaded", status: "available", detail: "Pi loaded the show-me extension." }],
		capture: [
			{ id: "browser-screenshot", label: "browser screenshots", status: "missing", detail: "Playwright is not installed.", remediation: "Install Playwright." },
			{ id: "screen-screenshot", label: "screen/window screenshots", status: "missing", detail: "No supported screenshot tool was found.", remediation: "Install screencapture, grim, gnome-screenshot, scrot, or PowerShell." },
		],
	} as never);
	assert.match(doctorText, /Remediation: Install Playwright\./);
	assert.match(doctorText, /Remediation: Install screencapture, grim, gnome-screenshot, scrot, or PowerShell\./);
});

test("beislid show-me command is namespaced when the show-me deck extension is enabled", async () => {
	const { commandNameForSkill } = await import(pathToFileURL(join(process.cwd(), "extensions/beislid/skill-commands.ts")).href);
	assert.equal(commandNameForSkill("show-me"), "show-me-skill");
});
