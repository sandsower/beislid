import { access, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";

type TokenArg = {
	args: string;
	tokenBudget?: string;
};

export function splitBabysitTokenBudgetArg(args: string): TokenArg {
	const trimmed = args.trim();
	const tokenFlagPattern = /(?:^|\s)--tokens(?:(?:=|\s+)(\S+))?(?=\s|$)/g;
	const validBudgetPattern = /^([0-9]+(?:\.[0-9]+)?)([kKmM]?)$/;
	let tokenBudget: string | undefined;
	let withoutToken = "";
	let lastIndex = 0;
	for (const match of trimmed.matchAll(tokenFlagPattern)) {
		const candidate = match[1] ?? "";
		const validBudget = candidate.match(validBudgetPattern);
		if (tokenBudget === undefined && validBudget && Number(validBudget[1]) > 0) {
			tokenBudget = candidate;
		}
		withoutToken += `${trimmed.slice(lastIndex, match.index)} `;
		lastIndex = match.index + match[0].length;
	}
	withoutToken += trimmed.slice(lastIndex);
	return { args: withoutToken.replace(/\s+/g, " ").trim(), tokenBudget };
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
	if (!value || Number(value.replace(/\s*[kKmM]$/, "")) <= 0) return undefined;
	return value.replace(/\s+/g, "");
}

export async function configuredBabysitTokenBudget(cwd: string): Promise<string | undefined> {
	const workflowPath = await findWorkflowPath(cwd);
	if (!workflowPath) return undefined;
	const workflow = await readFile(workflowPath, "utf-8").catch(() => undefined);
	return workflow ? extractBabysitTokenBudget(workflow) : undefined;
}
