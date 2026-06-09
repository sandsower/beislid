import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { readLatestCheckpoint, pickNewBoundary, type BoundaryIdentity, type CheckpointPointerSnapshot } from "./checkpoints.js";
import { resolveHandoffConfig } from "./config.js";
import { BEISLID_SKILLS, BOUNDARY_CAPABLE_SKILLS, commandNameForSkill, skillPrompt, type BeislidSkill } from "./skill-commands.js";

const CONSUMED_ENTRY = "beislid-auto-handoff-consumed";
const INTERNAL_HANDOFF_COMMAND = "beislid-auto-handoff";

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
