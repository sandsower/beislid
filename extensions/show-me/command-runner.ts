import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { join, posix, resolve } from "node:path";
import { StringDecoder } from "node:string_decoder";
import { redactText, type RedactionSummary } from "./redaction.js";
import type { CommandLogBlock, ShowMeDocument, ShowMeLog } from "./schema.js";
import { addBlock, readDeck, writeDeck, writeManifest } from "./store.js";

function nowIso(): string {
	return new Date().toISOString();
}

function shortId(): string {
	return Math.random().toString(36).slice(2, 8);
}

function clampTimeout(timeoutSeconds: number | undefined): number {
	const seconds = timeoutSeconds ?? 60;
	return Math.max(1, Math.min(600, Math.floor(seconds))) * 1000;
}

function preview(value: string, max = 4000): string | undefined {
	if (!value) return undefined;
	return value.length > max ? `${value.slice(0, max)}\n[truncated preview; see full log]` : value;
}

const DEFAULT_STREAM_CAPTURE_LIMIT_BYTES = 20 * 1024 * 1024;

function captureLimitBytes(): number {
	const raw = Number(process.env.BEISLID_SHOW_ME_CAPTURE_LIMIT_BYTES ?? DEFAULT_STREAM_CAPTURE_LIMIT_BYTES);
	return Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : DEFAULT_STREAM_CAPTURE_LIMIT_BYTES;
}

interface CapturedStream {
	text: string;
	bytes: number;
	truncated: boolean;
	decoder: StringDecoder;
}

function createCapturedStream(): CapturedStream {
	return { text: "", bytes: 0, truncated: false, decoder: new StringDecoder("utf8") };
}

function appendChunk(captured: CapturedStream, chunk: Buffer, limitBytes: number): CapturedStream {
	const nextBytes = captured.bytes + chunk.length;
	if (captured.truncated || captured.bytes >= limitBytes) {
		return { ...captured, bytes: nextBytes, truncated: true };
	}
	const remaining = limitBytes - captured.bytes;
	const kept = chunk.length > remaining ? chunk.subarray(0, remaining) : chunk;
	return {
		...captured,
		text: captured.text + captured.decoder.write(kept),
		bytes: nextBytes,
		truncated: captured.truncated || chunk.length > remaining,
	};
}

function finalizeCapturedStream(captured: CapturedStream): CapturedStream {
	if (captured.truncated) return captured;
	return { ...captured, text: captured.text + captured.decoder.end() };
}

const RISKY_PATTERNS = [
	/\brm\s+(-[rfRi-]*\s+)*[/~.$*]/,
	/\bsudo\b/,
	/\bchmod\s+(-R\s+)?777\b/,
	/\bchown\s+(-R\s+)?/,
	/\bmkfs\b/,
	/\bdd\s+.*\bof=/,
	/\bshutdown\b|\breboot\b/,
	/\bgit\s+push\b/,
	/\bgh\s+pr\s+(merge|close|review)\b/,
	/\bcurl\b.*\|\s*(sh|bash)\b/,
];

function looksRisky(command: string): string | undefined {
	const normalized = command.trim();
	const match = RISKY_PATTERNS.find((pattern) => pattern.test(normalized));
	return match ? `Command matches risky pattern ${match}` : undefined;
}

export interface RunCommandInput {
	deckId: string;
	command: string;
	sectionId?: string;
	title?: string;
	cwd?: string;
	timeoutSeconds?: number;
	allowRisky?: boolean;
}

export interface RunCommandResult {
	deckId: string;
	logId: string;
	blockId?: string;
	logPath: string;
	command: string;
	cwd: string;
	startedAt: string;
	finishedAt: string;
	exitCode: number | null;
	timedOut: boolean;
	stdoutTruncated: boolean;
	stderrTruncated: boolean;
	redactions: RedactionSummary;
}

export async function runCommandEvidence(input: RunCommandInput, defaultCwd: string): Promise<RunCommandResult> {
	const riskyReason = looksRisky(input.command);
	if (riskyReason && !input.allowRisky) {
		throw new Error(`${riskyReason}. Re-run with allowRisky=true only after explicit user approval.`);
	}

	const { root, doc } = await readDeck(input.deckId);
	if (input.sectionId && !doc.sections.some((section) => section.id === input.sectionId)) {
		throw new Error(`Unknown section id ${input.sectionId} in deck ${input.deckId}; command was not run.`);
	}
	const cwd = resolve(defaultCwd, input.cwd ?? ".");
	const timeoutMs = clampTimeout(input.timeoutSeconds);
	const startedAt = nowIso();
	const redactedCommand = redactText(input.command);
	const streamCaptureLimitBytes = captureLimitBytes();
	let stdout: CapturedStream = createCapturedStream();
	let stderr: CapturedStream = createCapturedStream();
	let exitCode: number | null = null;
	let timedOut = false;

	await new Promise<void>((resolvePromise) => {
		let resolved = false;
		let killTimer: NodeJS.Timeout | undefined;
		let forceResolveTimer: NodeJS.Timeout | undefined;
		const child = spawn("sh", ["-c", input.command], { cwd, stdio: ["ignore", "pipe", "pipe"], detached: process.platform !== "win32" });
		const finish = (code: number | null) => {
			if (resolved) return;
			resolved = true;
			clearTimeout(timer);
			if (killTimer) clearTimeout(killTimer);
			if (forceResolveTimer) clearTimeout(forceResolveTimer);
			exitCode = code;
			resolvePromise();
		};
		const killChild = (signal: NodeJS.Signals) => {
			try {
				if (process.platform !== "win32" && child.pid) process.kill(-child.pid, signal);
				else child.kill(signal);
			} catch {
				try {
					child.kill(signal);
				} catch {
					// Ignore kill failures; the force-resolve timer below prevents hangs.
				}
			}
		};
		const timer = setTimeout(() => {
			timedOut = true;
			killChild("SIGTERM");
			killTimer = setTimeout(() => killChild("SIGKILL"), 2000);
			forceResolveTimer = setTimeout(() => finish(null), 5000);
		}, timeoutMs);
		child.stdout.on("data", (chunk: Buffer) => {
			stdout = appendChunk(stdout, chunk, streamCaptureLimitBytes);
		});
		child.stderr.on("data", (chunk: Buffer) => {
			stderr = appendChunk(stderr, chunk, streamCaptureLimitBytes);
		});
		child.on("error", (error) => {
			stderr = appendChunk(stderr, Buffer.from(String(error)));
			finish(null);
		});
		child.on("close", (code) => {
			stdout = finalizeCapturedStream(stdout);
			stderr = finalizeCapturedStream(stderr);
			finish(code);
		});
	});

	const finishedAt = nowIso();
	const redactedStdout = redactText(stdout.text);
	const redactedStderr = redactText(stderr.text);
	const redactions: RedactionSummary = { total: 0, byRule: {} };
	for (const summary of [redactedCommand.summary, redactedStdout.summary, redactedStderr.summary]) {
		redactions.total += summary.total;
		for (const [rule, count] of Object.entries(summary.byRule)) {
			redactions.byRule[rule] = (redactions.byRule[rule] ?? 0) + count;
		}
	}

	const logId = `cmd-${Date.now()}-${shortId()}`;
	const relPath = posix.join("logs", "commands", `${logId}.txt`);
	const logPath = join(root, relPath);
	await mkdir(join(root, "logs", "commands"), { recursive: true });
	const logContent = [
		`command: ${redactedCommand.text}`,
		`cwd: ${cwd}`,
		`startedAt: ${startedAt}`,
		`finishedAt: ${finishedAt}`,
		`exitCode: ${exitCode ?? "null"}`,
		`timedOut: ${timedOut}`,
		`stdoutBytes: ${stdout.bytes}`,
		`stderrBytes: ${stderr.bytes}`,
		`stdoutTruncated: ${stdout.truncated}`,
		`stderrTruncated: ${stderr.truncated}`,
		`redactions: ${JSON.stringify(redactions)}`,
		"",
		"--- stdout ---",
		redactedStdout.text,
		stdout.truncated ? "\n[stdout truncated by show-me capture limit]" : "",
		"",
		"--- stderr ---",
		redactedStderr.text,
		stderr.truncated ? "\n[stderr truncated by show-me capture limit]" : "",
		"",
	].join("\n");
	await writeFile(logPath, logContent, "utf-8");

	const logEntry: ShowMeLog = {
		id: logId,
		path: relPath,
		command: redactedCommand.text,
		cwd,
		startedAt,
		finishedAt,
		exitCode,
		timedOut,
		stdoutBytes: stdout.bytes,
		stderrBytes: stderr.bytes,
		stdoutTruncated: stdout.truncated,
		stderrTruncated: stderr.truncated,
		redactions,
	};
	(doc.logs ??= []).push(logEntry);
	doc.provenance = updateCommandProvenance(doc, logEntry);
	await writeDeck(root, doc);
	await writeManifest(root, doc);

	let blockId: string | undefined;
	if (input.sectionId) {
		const block: Omit<CommandLogBlock, "id"> = {
			type: "command-log",
			logId,
			title: input.title,
			command: redactedCommand.text,
			cwd,
			startedAt,
			finishedAt,
			exitCode,
			timedOut,
			stdoutPreview: preview(redactedStdout.text),
			stderrPreview: preview(redactedStderr.text),
			logPath: relPath,
			stdoutTruncated: stdout.truncated,
			stderrTruncated: stderr.truncated,
		};
		blockId = (await addBlock(input.deckId, input.sectionId, block)).blockId;
	}

	return { deckId: doc.id, logId, blockId, logPath, command: redactedCommand.text, cwd, startedAt, finishedAt, exitCode, timedOut, stdoutTruncated: stdout.truncated, stderrTruncated: stderr.truncated, redactions };
}

function updateCommandProvenance(doc: ShowMeDocument, log: ShowMeLog): ShowMeDocument["provenance"] {
	const existing = Array.isArray(doc.provenance.commands) ? doc.provenance.commands : [];
	return {
		...doc.provenance,
		commands: [
			...existing,
			{
				id: log.id,
				command: log.command,
				cwd: log.cwd,
				startedAt: log.startedAt,
				finishedAt: log.finishedAt,
				exitCode: log.exitCode,
				timedOut: log.timedOut,
				path: log.path,
				redactions: log.redactions,
			},
		],
	};
}
