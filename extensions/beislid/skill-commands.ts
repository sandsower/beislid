export const BEISLID_SKILLS = [
	"babysit",
	"blueprint",
	"break-spec",
	"debug",
	"doctor",
	"envelope",
	"fresh-eyes",
	"handoff",
	"implement",
	"kickoff",
	"poke-holes",
	"pr-patrol",
	"ready-for-review",
	"retro",
	"review",
	"review-response",
	"rinse",
	"setup",
	"show-me",
	"spec",
	"verify",
	"walk-the-diff",
] as const;

export type BeislidSkill = (typeof BEISLID_SKILLS)[number];

export const COMMAND_COLLISIONS: Partial<Record<BeislidSkill, string>> = {
	"show-me": "show-me-skill",
};

export const BOUNDARY_CAPABLE_SKILLS = new Set<BeislidSkill>([
	"break-spec",
	"blueprint",
	"envelope",
	"handoff",
	"implement",
	"kickoff",
	"ready-for-review",
	"review-response",
	"spec",
]);

export function commandNameForSkill(skill: BeislidSkill): string {
	return COMMAND_COLLISIONS[skill] ?? skill;
}

export function skillPrompt(skill: BeislidSkill, args: string): string {
	const trimmed = args.trim();
	return trimmed ? `/skill:${skill} ${trimmed}` : `/skill:${skill}`;
}
