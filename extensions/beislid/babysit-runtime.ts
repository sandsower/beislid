import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import { configuredBabysitTokenBudget, splitBabysitTokenBudgetArg } from "./babysit-config.js";

const RUN_ENTRY = "beislid-babysit-run";
const EVENT_ENTRY = "beislid-babysit-event";
const TOOL_NAMES = ["get_beislid_babysit", "update_beislid_babysit"];

type BabysitStatus = "active" | "complete" | "blocked" | "budget_limited";

type BabysitRun = {
	version: 1;
	id: string;
	args: string;
	status: BabysitStatus;
	tokenBudget: number | null;
	tokensUsed: number;
	createdAt: number;
	updatedAt: number;
	summary?: string;
};

type UsageSnapshot = {
	totalTokens?: number;
	input?: number;
	output?: number;
	cacheRead?: number;
	cacheWrite?: number;
} | null | undefined;

let run: BabysitRun | null = null;
let continuationQueued = false;

function tokenDeltaFromUsage(usage: UsageSnapshot): number {
	if (!usage) return 0;
	if (typeof usage.totalTokens === "number") return Math.max(0, usage.totalTokens);
	const input = Number(usage.input) || 0;
	const output = Number(usage.output) || 0;
	const cacheRead = Number(usage.cacheRead) || 0;
	const cacheWrite = Number(usage.cacheWrite) || 0;
	return Math.max(0, input + output + cacheRead + cacheWrite);
}

function parseTokenBudget(raw: string | undefined): number | null {
	if (!raw) return null;
	const match = raw.match(/^([0-9]+(?:\.[0-9]+)?)([kKmM]?)$/);
	if (!match) return null;
	const value = Number(match[1]);
	if (!Number.isFinite(value) || value <= 0) return null;
	const suffix = match[2].toLowerCase();
	const multiplier = suffix === "m" ? 1_000_000 : suffix === "k" ? 1_000 : 1;
	return Math.round(value * multiplier);
}

function formatTokens(value: number): string {
	if (value >= 1_000_000) return `${Math.round(value / 100_000) / 10}M`;
	if (value >= 1_000) return `${Math.round(value / 100) / 10}K`;
	return String(value);
}

function syncTools(pi: ExtensionAPI) {
	const active = new Set(pi.getActiveTools());
	const want = run?.status === "active";
	for (const name of TOOL_NAMES) (want ? active.add(name) : active.delete(name));
	pi.setActiveTools(Array.from(active));
}

function persist(pi: ExtensionAPI, ctx: ExtensionContext, next: BabysitRun | null) {
	run = next;
	pi.appendEntry(RUN_ENTRY, { run: next });
	syncTools(pi);
	if (ctx.hasUI) {
		if (!run) ctx.ui.setStatus(RUN_ENTRY, "");
		else {
			const budget = run.tokenBudget == null ? "" : ` (${formatTokens(run.tokensUsed)} / ${formatTokens(run.tokenBudget)})`;
			ctx.ui.setStatus(RUN_ENTRY, run.status === "active" ? `Babysitting PR${budget}` : `Babysit ${run.status}${budget}`);
		}
	}
}

function latestRunFromSession(ctx: ExtensionContext): BabysitRun | null {
	const entries = ctx.sessionManager.getBranch?.() ?? ctx.sessionManager.getEntries();
	for (let i = entries.length - 1; i >= 0; i--) {
		const entry = entries[i] as { type?: string; customType?: string; data?: { run?: BabysitRun | null } };
		if (entry.type === "custom" && entry.customType === RUN_ENTRY) return entry.data?.run ?? null;
	}
	return null;
}

function emitEvent(pi: ExtensionAPI, kind: BabysitStatus, current: BabysitRun) {
	pi.sendMessage({
		customType: EVENT_ENTRY,
		content: `Beislið babysit status: ${kind}\n\nArgs: ${current.args || "(none)"}${current.summary ? `\n\nSummary: ${current.summary}` : ""}`,
		display: true,
		details: { kind, run: current, timestamp: Date.now() },
	});
}

function startPrompt(current: BabysitRun): string {
	return `Load and follow the Beislið babysit skill for the current pull request.

Invocation args: ${current.args || "(none)"}

Pi babysit persistence is active for this run. Use get_beislid_babysit only if you need the current run state. When the babysit workflow reaches its configured green endpoint, after final audit and configured closeout are complete, call update_beislid_babysit({status:"complete", summary:"..."}). If you hit a human-decision, policy, credential, conflict, or unsafe-blocker stop condition, call update_beislid_babysit({status:"blocked", summary:"..."}) and explain the blocker. Do not call update_beislid_babysit while substantive babysit work remains.`;
}

function continuationPrompt(current: BabysitRun): string {
	const tokenBudget = current.tokenBudget == null ? "none" : String(current.tokenBudget);
	const remainingTokens = current.tokenBudget == null ? "n/a" : String(Math.max(0, current.tokenBudget - current.tokensUsed));
	return `Continue the active Beislið babysit workflow for the current pull request.

Invocation args: ${current.args || "(none)"}

Budget:
- Tokens used: ${current.tokensUsed}
- Token budget: ${tokenBudget}
- Tokens remaining: ${remainingTokens}

Re-read live PR evidence before deciding what to do next. Continue using the babysit skill workflow. Only call update_beislid_babysit({status:"complete"}) after the configured green endpoint and final audit are actually complete. If blocked on human judgment, policy approval, credentials, conflicts, or unsafe state, call update_beislid_babysit({status:"blocked"}) with a summary.`;
}

function queueContinuation(pi: ExtensionAPI, current: BabysitRun) {
	if (continuationQueued || current.status !== "active") return;
	continuationQueued = true;
	queueMicrotask(() => {
		continuationQueued = false;
		if (!run || run.id !== current.id || run.status !== "active") return;
		pi.sendUserMessage(continuationPrompt(run), { deliverAs: "followUp" });
	});
}

export function registerBabysitRuntime(pi: ExtensionAPI) {
	pi.registerTool({
		name: "get_beislid_babysit",
		label: "Get Beislið Babysit Run",
		description: "Read the active Beislið babysit run state.",
		promptSnippet: "Read current Beislið babysit loop status and budget",
		promptGuidelines: ["Only call this when you need the current babysit loop status; the continuation prompt usually includes enough context."],
		parameters: Type.Object({}),
		async execute() {
			return { content: [{ type: "text", text: JSON.stringify({ run }, null, 2) }], details: { run } };
		},
	});

	pi.registerTool({
		name: "update_beislid_babysit",
		label: "Update Beislið Babysit Run",
		description: "Mark the active Beislið babysit run complete or blocked.",
		promptSnippet: "Complete or block the active Beislið babysit loop after audit",
		promptGuidelines: [
			"Call with status=complete only when the configured babysit green endpoint and final audit are complete.",
			"Call with status=blocked when babysit cannot proceed without human judgment, credentials, policy approval, or unsafe conflict handling.",
		],
		parameters: Type.Object({
			status: Type.Union([Type.Literal("complete"), Type.Literal("blocked")]),
			summary: Type.Optional(Type.String()),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			if (!run || run.status !== "active") {
				return { content: [{ type: "text", text: "No active Beislið babysit run." }], isError: true };
			}
			const next: BabysitRun = { ...run, status: params.status, summary: params.summary, updatedAt: Date.now() };
			persist(pi, ctx, next);
			emitEvent(pi, params.status, next);
			return { content: [{ type: "text", text: JSON.stringify({ run: next }, null, 2) }], details: { run: next } };
		},
	});

	pi.on("session_start", (_event, ctx) => {
		run = latestRunFromSession(ctx);
		continuationQueued = false;
		syncTools(pi);
	});

	pi.on("turn_end", (event, ctx) => {
		if (!run || run.status !== "active") return;
		let next: BabysitRun = { ...run, tokensUsed: run.tokensUsed + tokenDeltaFromUsage((event.message as { usage?: UsageSnapshot } | undefined)?.usage), updatedAt: Date.now() };
		if (next.tokenBudget != null && next.tokensUsed >= next.tokenBudget) next = { ...next, status: "budget_limited" };
		persist(pi, ctx, next);
		if (next.status === "budget_limited") emitEvent(pi, "budget_limited", next);
	});

	pi.on("agent_end", (_event, ctx) => {
		if (!run || run.status !== "active" || ctx.hasPendingMessages()) return;
		queueContinuation(pi, run);
	});

	return {
		async start(args: string, ctx: ExtensionContext) {
			const parsed = splitBabysitTokenBudgetArg(args);
			const rawBudget = parsed.tokenBudget ?? (await configuredBabysitTokenBudget(ctx.cwd));
			const now = Date.now();
			const next: BabysitRun = {
				version: 1,
				id: `${now}-${Math.random().toString(16).slice(2)}`,
				args: parsed.args,
				status: "active",
				tokenBudget: parseTokenBudget(rawBudget),
				tokensUsed: 0,
				createdAt: now,
				updatedAt: now,
			};
			persist(pi, ctx, next);
			emitEvent(pi, "active", next);
			await pi.sendUserMessage(startPrompt(next), { deliverAs: "followUp" });
		},
	};
}
