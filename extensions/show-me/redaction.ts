import type { ShowMeDocument } from "./schema.js";

interface RedactionRule {
	name: string;
	pattern: RegExp;
	replacement: string;
}

const RULES: RedactionRule[] = [
	{
		name: "authorization-bearer",
		pattern: /\b(Authorization\s*:\s*Bearer\s+)[A-Za-z0-9._~+/=-]+/gi,
		replacement: "$1[REDACTED]",
	},
	{
		name: "github-token",
		pattern: /\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b/g,
		replacement: "[REDACTED_GITHUB_TOKEN]",
	},
	{
		name: "openai-style-key",
		pattern: /\bsk-[A-Za-z0-9_-]{20,}\b/g,
		replacement: "[REDACTED_API_KEY]",
	},
	{
		name: "slack-token",
		pattern: /\bxox[a-z]-[A-Za-z0-9-]{10,}\b/gi,
		replacement: "[REDACTED_SLACK_TOKEN]",
	},
	{
		name: "aws-access-key",
		pattern: /\bA(KIA|SIA)[A-Z0-9]{16}\b/g,
		replacement: "[REDACTED_AWS_ACCESS_KEY]",
	},
	{
		name: "aws-secret-access-key",
		pattern: /\b((?:AWS_)?SECRET_ACCESS_KEY\s*[:=]\s*['"]?)[A-Za-z0-9/+=]{16,}(['"]?)/gi,
		replacement: "$1[REDACTED_AWS_SECRET_KEY]$2",
	},
	{
		name: "pem-block",
		pattern: /-----BEGIN [^-]+-----[\s\S]*?-----END [^-]+-----/g,
		replacement: "[REDACTED_PEM_BLOCK]",
	},
	{
		name: "jwt",
		pattern: /\b[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/g,
		replacement: "[REDACTED_JWT]",
	},
	{
		name: "cli-flag-secret",
		pattern: /((?:^|[^\w-])--(?:token|secret|password|api[-_]?key)(?:=|\s+)(?:['"]?))([^\s'"`]+)(['"]?)/gi,
		replacement: "$1[REDACTED]$3",
	},
	{
		name: "generic-secret-assignment",
		pattern: /(^|[^A-Za-z0-9_])((?:token|secret|password|api[_-]?key)\s*[:=]\s*['"]?)([^\s'"`]{8,})(['"]?)/gi,
		replacement: "$1$2[REDACTED]$4",
	},
];

export interface RedactionSummary {
	total: number;
	byRule: Record<string, number>;
}

function emptySummary(): RedactionSummary {
	return { total: 0, byRule: {} };
}

function toCount(value: unknown): number {
	const count = typeof value === "number" ? value : Number(value);
	return Number.isFinite(count) && count > 0 ? count : 0;
}

function coerceSummary(value: unknown): RedactionSummary {
	if (!value || typeof value !== "object" || Array.isArray(value)) return emptySummary();
	const source = value as { total?: unknown; byRule?: unknown };
	const byRule: Record<string, number> = {};
	if (source.byRule && typeof source.byRule === "object" && !Array.isArray(source.byRule)) {
		for (const [rule, count] of Object.entries(source.byRule as Record<string, unknown>)) {
			const normalized = toCount(count);
			if (normalized > 0) byRule[rule] = normalized;
		}
	}
	const total = Math.max(toCount(source.total), Object.values(byRule).reduce((sum, count) => sum + count, 0));
	return { total, byRule };
}

function mergeSummary(target: RedactionSummary, source: RedactionSummary): RedactionSummary {
	const merged: RedactionSummary = {
		total: target.total + source.total,
		byRule: { ...target.byRule },
	};
	for (const [key, value] of Object.entries(source.byRule)) {
		merged.byRule[key] = (merged.byRule[key] ?? 0) + value;
	}
	return merged;
}

function isRedactionMarker(value: string): boolean {
	return /\[REDACTED(?:_[A-Z0-9]+)?\]/.test(value);
}

function applyReplacement(template: string, match: string, captures: string[], offset: number, input: string): string {
	return template.replace(/\$(\$|&|`|'|\d{1,2})/g, (_token, key: string) => {
		if (key === "$") return "$";
		if (key === "&") return match;
		if (key === "`") return input.slice(0, offset);
		if (key === "'") return input.slice(offset + match.length);
		const index = Number(key);
		return index > 0 && index <= captures.length ? captures[index - 1] ?? "" : `$${key}`;
	});
}

export function redactText(input: string): { text: string; summary: RedactionSummary } {
	let text = input;
	const byRule: Record<string, number> = {};
	for (const rule of RULES) {
		text = text.replace(rule.pattern, (...args: unknown[]) => {
			const maybeGroups = args[args.length - 1];
			const hasGroups = typeof maybeGroups === "object" && maybeGroups !== null;
			const match = String(args[0]);
			if (isRedactionMarker(match)) return match;
			const inputText = String(args[hasGroups ? args.length - 2 : args.length - 1]);
			const offset = Number(args[hasGroups ? args.length - 3 : args.length - 2]);
			const captures = args.slice(1, hasGroups ? -3 : -2).map((value) => String(value ?? ""));
			byRule[rule.name] = (byRule[rule.name] ?? 0) + 1;
			return applyReplacement(rule.replacement, match, captures, offset, inputText);
		});
	}
	return { text, summary: { total: Object.values(byRule).reduce((sum, value) => sum + value, 0), byRule } };
}

function redactValue(value: unknown, summary: RedactionSummary): unknown {
	if (typeof value === "string") {
		const redacted = redactText(value);
		summary.total += redacted.summary.total;
		for (const [rule, count] of Object.entries(redacted.summary.byRule)) {
			summary.byRule[rule] = (summary.byRule[rule] ?? 0) + count;
		}
		return redacted.text;
	}
	if (Array.isArray(value)) return value.map((item) => redactValue(item, summary));
	if (value && typeof value === "object") {
		const out: Record<string, unknown> = {};
		for (const [key, child] of Object.entries(value)) out[key] = redactValue(child, summary);
		return out;
	}
	return value;
}

export function redactShowMeDocument(doc: ShowMeDocument): { doc: ShowMeDocument; summary: RedactionSummary } {
	const summary = emptySummary();
	const redacted = redactValue(doc, summary) as ShowMeDocument;
	const previous = coerceSummary((redacted.provenance as { redactions?: unknown } | undefined)?.redactions);
	const merged = mergeSummary(previous, summary);
	redacted.provenance = {
		...redacted.provenance,
		redactions: merged,
	};
	return { doc: redacted, summary: merged };
}
