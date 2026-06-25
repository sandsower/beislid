import { access, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";

export const BABYSIT_GOAL_OBJECTIVE = `Run the Beislið babysit workflow for the current pull request until the configured stop condition is met. First load and follow the babysit skill. Treat /goal support as mandatory for this workflow. Use the current repo's .beislid/workflow.md for PR review sources, reply/update commands, gates/scopes/gate sets, action policy, and babysit closeout settings. Identify the current PR from the branch or ask for the PR URL/number if needed. Loop on live PR evidence: checks/status rollup, mergeability/conflicts, review decision, PR comments, and inline review threads. When actionable feedback exists and loop.use_review_response is enabled or absent, use the repo's review-response workflow to categorize, fix, run configured gates, push, and reply using safe temp JSON payloads. When loop.use_review_response is false, do not fix, reply, commit, or push automatically; stop with the loaded feedback summary and ask the user how to proceed. Before any babysit-owned push or merge preparation, run the configured applicable gates and do not invent hardcoded gates. After each push or CI transition, wait with bounded polling or host monitor facilities, then re-audit live PR state. Consider the PR green only when all required checks are successful, it is mergeable with no conflicts, the review state is acceptable, and no unaddressed actionable review feedback remains. Then perform only the configured closeout steps: optional merge, memento capture, and retro/apply-findings, each subject to Beislið action policy and any required approval. Stop and ask for judgment calls, unsafe conflicts, red or pending required checks at merge time, missing credentials/services, policy ask/deny boundaries, or ambiguous retro/setup edits. Never force-push, never amend published commits, never merge to bypass failing or pending required checks, and never interpolate review reply bodies into shell commands. Call update_goal({status:"complete"}) only after the final audit and configured closeout are complete, or after reaching the configured stop-when-green endpoint.`;

export type BuildBabysitGoalCommandOptions = {
	cwd: string;
};

type TokenArg = {
	args: string;
	tokenBudget?: string;
};

export function hasGoalCommandName(commands: Array<{ name?: string }>): boolean {
	return commands.some((command) => command.name === "goal");
}

export function splitBabysitTokenBudgetArg(args: string): TokenArg {
	const trimmed = args.trim();
	const match = trimmed.match(/(?:^|\s)--tokens(?:=|\s+)([0-9]+(?:\.[0-9]+)?\s*[kKmM]?)(?=\s|$)/);
	if (!match) return { args: trimmed };
	const tokenBudget = match[1].replace(/\s+/g, "");
	const start = match.index ?? 0;
	const end = start + match[0].length;
	const withoutToken = `${trimmed.slice(0, start)} ${trimmed.slice(end)}`.replace(/\s+/g, " ").trim();
	return { args: withoutToken, tokenBudget };
}

async function pathExists(path: string): Promise<boolean> {
	return access(path).then(
		() => true,
		() => false,
	);
}

export async function findWorkflowPath(cwd: string): Promise<string | undefined> {
	let current = cwd;
	for (;;) {
		const candidate = join(current, ".beislid", "workflow.md");
		if (await pathExists(candidate)) return candidate;
		const parent = dirname(current);
		if (parent === current) return undefined;
		current = parent;
	}
}

export function extractBabysitTokenBudget(workflow: string): string | undefined {
	const block = workflow.match(/^```beislid:babysit\s*\n([\s\S]*?)^```/m)?.[1];
	if (!block) return undefined;
	const value = block.match(/^\s*token_budget:\s*['"]?([0-9]+(?:\.[0-9]+)?\s*[kKmM]?)['"]?\s*$/m)?.[1];
	return value?.replace(/\s+/g, "");
}

export async function configuredBabysitTokenBudget(cwd: string): Promise<string | undefined> {
	const workflowPath = await findWorkflowPath(cwd);
	if (!workflowPath) return undefined;
	const workflow = await readFile(workflowPath, "utf-8").catch(() => undefined);
	return workflow ? extractBabysitTokenBudget(workflow) : undefined;
}

function babysitGoalObjective(args: string): string {
	return args ? `${BABYSIT_GOAL_OBJECTIVE}\n\nUser babysit args: ${args}` : BABYSIT_GOAL_OBJECTIVE;
}

export async function buildBabysitGoalCommand(args: string, options: BuildBabysitGoalCommandOptions): Promise<string> {
	const parsed = splitBabysitTokenBudgetArg(args);
	const tokenBudget = parsed.tokenBudget ?? (await configuredBabysitTokenBudget(options.cwd));
	const tokenArg = tokenBudget ? `--tokens ${tokenBudget} ` : "";
	return `/goal ${tokenArg}${babysitGoalObjective(parsed.args)}`;
}
