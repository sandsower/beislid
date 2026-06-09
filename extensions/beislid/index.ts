import type { ExtensionAPI, ExtensionCommandContext, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { access, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { readLatestCheckpoint, pickNewBoundary, type BoundaryIdentity, type CheckpointPointerSnapshot } from "./checkpoints.js";
import { resolveHandoffConfig } from "./config.js";
import { BEISLID_SKILLS, BOUNDARY_CAPABLE_SKILLS, commandNameForSkill, skillPrompt, type BeislidSkill } from "./skill-commands.js";

const CONSUMED_ENTRY = "beislid-auto-handoff-consumed";
const INTERNAL_HANDOFF_COMMAND = "beislid-auto-handoff";
const BABYSIT_GOAL = `Run the Beislið babysit workflow for the current pull request until the configured stop condition is met. First load and follow the babysit skill. Treat /goal support as mandatory for this workflow. Use the current repo's .beislid/workflow.md for PR review sources, reply/update commands, gates/scopes/gate sets, action policy, and babysit closeout settings. Identify the current PR from the branch or ask for the PR URL/number if needed. Loop on live PR evidence: checks/status rollup, mergeability/conflicts, review decision, PR comments, and inline review threads. When actionable feedback exists and loop.use_review_response is enabled or absent, use the repo's review-response workflow to categorize, fix, run configured gates, push, and reply using safe temp JSON payloads. When loop.use_review_response is false, do not fix, reply, commit, or push automatically; stop with the loaded feedback summary and ask the user how to proceed. After each push or CI transition, wait with bounded polling or host monitor facilities, then re-audit live PR state. Consider the PR green only when all required checks are successful, it is mergeable with no conflicts, the review state is acceptable, and no unaddressed actionable review feedback remains. Then perform only the configured closeout steps: optional merge, memento capture, and retro/apply-findings, each subject to Beislið action policy and any required approval. Stop and ask for judgment calls, unsafe conflicts, red or pending required checks at merge time, missing credentials/services, policy ask/deny boundaries, or ambiguous retro/setup edits. Never force-push, never amend published commits, never merge to bypass failing or pending required checks, and never interpolate review reply bodies into shell commands. Only mark the goal complete after the final audit and configured closeout are complete.`;

type ManagedRun = {
	skill: BeislidSkill;
	command: string;
	startedAt: number;
	before?: CheckpointPointerSnapshot;
};

type ConsumedEntry = {
	boundary: BoundaryIdentity;
	consumedAt: string;
};

function notify(ctx: ExtensionContext, message: string, level: "info" | "warning" | "error" | "success" = "info") {
	if (ctx.hasUI) ctx.ui.notify(message, level);
}

function refreshConsumed(ctx: ExtensionContext, consumed: Set<string>) {
	consumed.clear();
	for (const entry of ctx.sessionManager.getEntries() as Array<{ type?: string; customType?: string; data?: unknown }>) {
		if (entry.type !== "custom" || entry.customType !== CONSUMED_ENTRY) continue;
		const data = entry.data as Partial<ConsumedEntry> | undefined;
		const id = data?.boundary?.id;
		if (typeof id === "string") consumed.add(id);
	}
}

function hasGoalCommand(pi: ExtensionAPI): boolean {
	return pi.getCommands().some((command) => command.name === "goal" || command.name.startsWith("goal:"));
}

function argsContainTokenBudget(args: string): boolean {
	return /(?:^|\s)--tokens(?:=|\s+)/.test(args);
}

async function pathExists(path: string): Promise<boolean> {
	return access(path).then(
		() => true,
		() => false,
	);
}

async function findWorkflowPath(cwd: string): Promise<string | undefined> {
	let current = cwd;
	for (;;) {
		const candidate = join(current, ".beislid", "workflow.md");
		if (await pathExists(candidate)) return candidate;
		const parent = dirname(current);
		if (parent === current) return undefined;
		current = parent;
	}
}

function extractBabysitTokenBudget(workflow: string): string | undefined {
	const block = workflow.match(/^```beislid:babysit\s*\n([\s\S]*?)^```/m)?.[1];
	if (!block) return undefined;
	const value = block.match(/^\s*token_budget:\s*['"]?([0-9][0-9_]*(?:\.[0-9]+)?\s*[kKmM]?)['"]?\s*$/m)?.[1];
	return value?.replace(/\s+/g, "");
}

async function configuredBabysitTokenBudget(ctx: ExtensionCommandContext): Promise<string | undefined> {
	const workflowPath = await findWorkflowPath(ctx.cwd);
	if (!workflowPath) return undefined;
	const workflow = await readFile(workflowPath, "utf-8").catch(() => undefined);
	return workflow ? extractBabysitTokenBudget(workflow) : undefined;
}

async function buildBabysitGoalCommand(args: string, ctx: ExtensionCommandContext): Promise<string> {
	const trimmed = args.trim();
	const tokenBudget = argsContainTokenBudget(trimmed) ? undefined : await configuredBabysitTokenBudget(ctx);
	const tokenArg = tokenBudget ? `--tokens ${tokenBudget} ` : "";
	const invocationArgs = trimmed ? `${trimmed} ` : "";
	return `/goal ${tokenArg}${invocationArgs}${BABYSIT_GOAL}`;
}

function continuationPrompt(boundary: BoundaryIdentity, workflow: string): string {
	return `Continue the Beislið ${workflow} workflow from a fresh Pi session.\n\nRead .beislid/checkpoints/latest.json, then read the referenced checkpoint artifact for event ${boundary.event} at ${boundary.path}. Use that artifact as the primary context seed. Do not synthesize missing context from prior chat history. Do not auto-handoff again for this same checkpoint boundary: ${boundary.id}.`;
}

export default function beislidExtension(pi: ExtensionAPI) {
	let activeRun: ManagedRun | undefined;
	let pendingBoundary: BoundaryIdentity | undefined;
	let pendingWorkflow: string | undefined;
	const consumed = new Set<string>();

	pi.on("session_start", async (_event, ctx) => {
		refreshConsumed(ctx, consumed);
	});

	for (const skill of BEISLID_SKILLS) {
		const command = commandNameForSkill(skill);
		pi.registerCommand(command, {
			description: `Run the Beislið ${skill} skill through the managed Pi wrapper`,
			handler: async (args, ctx) => {
				if (skill === "babysit") {
					if (!hasGoalCommand(pi)) {
						notify(ctx, "/babysit requires /goal. Install or enable pi-goal, reload/restart Pi, then run /babysit again.", "warning");
						return;
					}
					await pi.sendUserMessage(await buildBabysitGoalCommand(args, ctx), { deliverAs: "followUp" });
					return;
				}

				const prompt = skillPrompt(skill, args);
				if (BOUNDARY_CAPABLE_SKILLS.has(skill)) {
					activeRun = {
						skill,
						command,
						startedAt: Date.now(),
						before: await readLatestCheckpoint(ctx.cwd),
					};
				}
				await pi.sendUserMessage(prompt, { deliverAs: "followUp" });
			},
		});
	}

	pi.registerCommand(INTERNAL_HANDOFF_COMMAND, {
		description: "Internal Beislið command: start a fresh Pi session from the latest checkpoint",
		handler: async (_args, ctx) => {
			const boundary = pendingBoundary;
			const workflow = pendingWorkflow ?? "managed";
			pendingBoundary = undefined;
			pendingWorkflow = undefined;
			if (!boundary) return;

			if (ctx.mode === "print" || ctx.mode === "json") {
				notify(ctx, "Beislið auto-handoff skipped in this Pi mode; use the checkpoint pointer manually.", "warning");
				return;
			}

			consumed.add(boundary.id);
			pi.appendEntry<ConsumedEntry>(CONSUMED_ENTRY, { boundary, consumedAt: new Date().toISOString() });
			notify(ctx, `Starting fresh Pi session from checkpoint ${boundary.path}`, "info");
			const parentSession = ctx.sessionManager.getSessionFile();
			const prompt = continuationPrompt(boundary, workflow);
			const result = await ctx.newSession({
				parentSession,
				setup: async (sessionManager) => {
					sessionManager.appendCustomEntry(CONSUMED_ENTRY, { boundary, consumedAt: new Date().toISOString() });
				},
				withSession: async (replacementCtx) => {
					await replacementCtx.sendUserMessage(prompt);
				},
			});
			if (result.cancelled) notify(ctx, "Beislið auto-handoff cancelled by Pi session guard.", "warning");
		},
	});

	pi.on("agent_end", async (_event, ctx) => {
		if (!activeRun) return;
		const run = activeRun;
		activeRun = undefined;
		refreshConsumed(ctx, consumed);
		const config = await resolveHandoffConfig(ctx.cwd);
		if (!config.autoHandoff) return;
		const after = await readLatestCheckpoint(ctx.cwd);
		const allowedEvents = config.events;
		const boundary = pickNewBoundary(run.before, after, allowedEvents, config.exclude, consumed);
		if (!boundary) return;
		pendingBoundary = boundary;
		pendingWorkflow = run.skill;
		await pi.sendUserMessage(`/${INTERNAL_HANDOFF_COMMAND}`, { deliverAs: "followUp" });
	});
}
