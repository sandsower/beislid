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
		pattern: /\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b/g,
		replacement: "[REDACTED_GITHUB_TOKEN]",
	},
	{
		name: "openai-style-key",
		pattern: /\bsk-[A-Za-z0-9_-]{20,}\b/g,
		replacement: "[REDACTED_API_KEY]",
	},
	{
		name: "aws-access-key",
		pattern: /\bA(KIA|SIA)[A-Z0-9]{16}\b/g,
		replacement: "[REDACTED_AWS_KEY]",
	},
	{
		name: "generic-secret-assignment",
		pattern: /\b(token|secret|password|api[_-]?key)\s*[:=]\s*['\"]?[^'\"\s]{12,}/gi,
		replacement: "$1=[REDACTED]",
	},
];

export interface RedactionSummary {
	total: number;
	byRule: Record<string, number>;
}

export function redactText(input: string): { text: string; summary: RedactionSummary } {
	let text = input;
	const byRule: Record<string, number> = {};
	for (const rule of RULES) {
		let count = 0;
		text = text.replace(rule.pattern, (...args) => {
			count += 1;
			return typeof rule.replacement === "string" ? args[0].replace(rule.pattern, rule.replacement) : rule.replacement;
		});
		if (count > 0) byRule[rule.name] = count;
	}
	return { text, summary: { total: Object.values(byRule).reduce((sum, value) => sum + value, 0), byRule } };
}

function mergeSummary(target: RedactionSummary, source: RedactionSummary) {
	target.total += source.total;
	for (const [key, value] of Object.entries(source.byRule)) {
		target.byRule[key] = (target.byRule[key] ?? 0) + value;
	}
}

function redactValue(value: unknown, summary: RedactionSummary): unknown {
	if (typeof value === "string") {
		const redacted = redactText(value);
		mergeSummary(summary, redacted.summary);
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
	const summary: RedactionSummary = { total: 0, byRule: {} };
	const redacted = redactValue(doc, summary) as ShowMeDocument;
	redacted.provenance = {
		...redacted.provenance,
		redactions: summary,
	};
	return { doc: redacted, summary };
}
