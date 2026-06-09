import type { ExtensionAPI, ExtensionCommandContext } from "@mariozechner/pi-coding-agent";
import { access, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";

const BABYSIT_GOAL = `Run the Beislið babysit workflow for the current pull request until the configured stop condition is met. First load and follow the babysit skill. Treat /goal support as mandatory for this workflow. Use the current repo's .beislid/workflow.md for PR review sources, reply/update commands, gates/scopes/gate sets, action policy, and babysit closeout settings. Identify the current PR from the branch or ask for the PR URL/number if needed. Loop on live PR evidence: checks/status rollup, mergeability/conflicts, review decision, PR comments, and inline review threads. When actionable feedback exists and loop.use_review_response is enabled or absent, use the repo's review-response workflow to categorize, fix, run configured gates, push, and reply using safe temp JSON payloads. When loop.use_review_response is false, do not fix, reply, commit, or push automatically; stop with the loaded feedback summary and ask the user how to proceed. After each push or CI transition, wait with bounded polling or host monitor facilities, then re-audit live PR state. Consider the PR green only when all required checks are successful, it is mergeable with no conflicts, the review state is acceptable, and no unaddressed actionable review feedback remains. Then perform only the configured closeout steps: optional merge, memento capture, and retro/apply-findings, each subject to Beislið action policy and any required approval. Stop and ask for judgment calls, unsafe conflicts, red or pending required checks at merge time, missing credentials/services, policy ask/deny boundaries, or ambiguous retro/setup edits. Never force-push, never amend published commits, never merge to bypass failing or pending required checks, and never interpolate review reply bodies into shell commands. Only mark the goal complete after the final audit and configured closeout are complete.`;

function hasGoalCommand(pi: ExtensionAPI): boolean {
	return pi.getCommands().some((command) => command.name === "goal" || command.name.startsWith("goal:"));
}

function argsContainTokenBudget(args: string): boolean {
	return /(?:^|\s)--tokens(?:=|\s+)/.test(args);
}

async function pathExists(path: string): Promise<boolean> {
	return access(path).then(() => true, () => false);
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

async function configuredTokenBudget(ctx: ExtensionCommandContext): Promise<string | undefined> {
	const workflowPath = await findWorkflowPath(ctx.cwd);
	if (!workflowPath) return undefined;
	const workflow = await readFile(workflowPath, "utf-8").catch(() => undefined);
	return workflow ? extractBabysitTokenBudget(workflow) : undefined;
}

async function buildGoalCommand(args: string, ctx: ExtensionCommandContext): Promise<string> {
	const trimmed = args.trim();
	const tokenBudget = argsContainTokenBudget(trimmed) ? undefined : await configuredTokenBudget(ctx);
	const tokenArg = tokenBudget ? `--tokens ${tokenBudget} ` : "";
	const invocationArgs = trimmed ? `${trimmed} ` : "";
	return `/goal ${tokenArg}${invocationArgs}${BABYSIT_GOAL}`;
}

export default function babysitExtension(pi: ExtensionAPI) {
	pi.registerCommand("babysit", {
		description: "Start a required /goal to babysit the current PR through configured review, gates, and closeout",
		handler: async (args, ctx) => {
			if (!hasGoalCommand(pi)) {
				ctx.ui.notify(
					"/babysit requires /goal. Install or enable pi-goal, reload/restart Pi, then run /babysit again.",
					"warning",
				);
				return;
			}

			pi.sendUserMessage(await buildGoalCommand(args, ctx));
		},
	});
}
