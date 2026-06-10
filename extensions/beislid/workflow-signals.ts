import type { ExtensionContext } from "@mariozechner/pi-coding-agent";
import { execFile } from "node:child_process";
import type { BeislidSkill } from "./skill-commands.js";

export const WORKFLOW_SIGNAL_STATES = ["working", "blocked", "waiting", "verify", "review", "done", "explore"] as const;
export type WorkflowSignalState = (typeof WORKFLOW_SIGNAL_STATES)[number];

export type WorkflowSignal = {
	state: WorkflowSignalState;
	skill?: BeislidSkill;
	phase?: string;
	event?: string;
};

const STATE_LABELS: Record<WorkflowSignalState, string> = {
	working: "🛠 working",
	blocked: "⛔ blocked",
	waiting: "⏳ waiting",
	verify: "🧪 verify",
	review: "👀 review",
	done: "✅ done",
	explore: "🔎 explore",
};

export const INITIAL_SKILL_SIGNALS: Partial<Record<BeislidSkill, WorkflowSignalState>> = {
	babysit: "working",
	blueprint: "working",
	"break-spec": "working",
	debug: "explore",
	doctor: "verify",
	"fresh-eyes": "review",
	handoff: "working",
	implement: "working",
	kickoff: "working",
	"poke-holes": "working",
	"pr-patrol": "review",
	"ready-for-review": "working",
	retro: "review",
	review: "review",
	"review-response": "working",
	rinse: "review",
	setup: "working",
	"show-me": "working",
	spec: "working",
	verify: "verify",
	"walk-the-diff": "review",
};

export function initialSignalForSkill(skill: BeislidSkill): WorkflowSignal | undefined {
	const state = INITIAL_SKILL_SIGNALS[skill];
	return state ? { state, skill, phase: "start" } : undefined;
}

function titleForSignal(signal: WorkflowSignal): string {
	const skill = signal.skill ? ` ${signal.skill}` : "";
	const phase = signal.phase ? `:${signal.phase}` : "";
	return `Beislið ${STATE_LABELS[signal.state]}${skill}${phase}`;
}

export function surfaceWorkflowSignal(ctx: ExtensionContext, signal: WorkflowSignal) {
	if (!ctx.hasUI) return;
	const title = titleForSignal(signal);
	ctx.ui.setStatus("beislid-workflow", title);
	ctx.ui.setTitle(title);
}

export function emitWorkflowSignal(ctx: ExtensionContext, signal: WorkflowSignal) {
	surfaceWorkflowSignal(ctx, signal);
	const args = ["workflow-signal", "emit", signal.state];
	if (signal.skill) args.push("--skill", signal.skill);
	if (signal.phase) args.push("--phase", signal.phase);
	if (signal.event) args.push("--event", signal.event);
	args.push("--repo", ctx.cwd);

	execFile("beislid", args, { cwd: ctx.cwd, timeout: 2000 }, () => {
		// Best-effort local signal fan-out. Missing CLI, unconfigured workflow_signals,
		// non-tmux sessions, and sink failures must not block the Pi workflow.
	});
}

function parseFlag(args: string, flag: "skill" | "phase" | "event"): string | undefined {
	const match = args.match(new RegExp(`(?:^|\\s)--${flag}(?:=|\\s+)(['\"]?)([^'\"\\s;&|]+)\\1`));
	return match?.[2];
}

export function surfaceWorkflowSignalsFromCommand(ctx: ExtensionContext, command: string) {
	const re = /(?:^|[\s;&|])beislid\s+workflow-signal\s+emit\s+(working|blocked|waiting|verify|review|done|explore)\b([^\n;&|]*)/g;
	let match: RegExpExecArray | null;
	while ((match = re.exec(command))) {
		const state = match[1] as WorkflowSignalState;
		const rest = match[2] ?? "";
		const skill = parseFlag(rest, "skill") as BeislidSkill | undefined;
		const phase = parseFlag(rest, "phase");
		const event = parseFlag(rest, "event");
		surfaceWorkflowSignal(ctx, { state, skill, phase, event });
	}
}
