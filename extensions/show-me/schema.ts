import { Type } from "typebox";

export const SHOW_ME_MODES = [
	"verification",
	"review",
	"code-walkthrough",
	"ui-demo",
	"cli-demo",
	"docs",
	"understanding",
	"mixed",
] as const;

export const SHOW_ME_STATUSES = [
	"PASS",
	"FAIL",
	"INCOMPLETE",
	"NOT SHOWN",
	"NEEDS CAPTURE",
	"EXPLANATORY",
	"CONFLICTING",
	"LOW_CONFIDENCE",
] as const;

export const SHOW_ME_PRESENTATIONS = ["report", "visual-deck", "evidence-deck"] as const;

export type ShowMeMode = (typeof SHOW_ME_MODES)[number];
export type ShowMeStatus = (typeof SHOW_ME_STATUSES)[number];
export type ShowMePresentation = (typeof SHOW_ME_PRESENTATIONS)[number];

export type CalloutTone = "info" | "warning" | "danger" | "success";

export interface MarkdownBlock {
	id: string;
	type: "markdown";
	markdown: string;
}

export interface TableBlock {
	id: string;
	type: "table";
	columns: string[];
	rows: string[][];
}

export interface CodeBlock {
	id: string;
	type: "code";
	language?: string;
	code: string;
}

export interface DiffBlock {
	id: string;
	type: "diff";
	diff: string;
}

export interface SourceDiagramBlock {
	id: string;
	type: "diagram";
	diagram: string;
	language?: "mermaid";
	title?: string;
}

export interface CalloutBlock {
	id: string;
	type: "callout";
	title?: string;
	tone?: CalloutTone;
	text: string;
}

export interface VerdictBlock {
	id: string;
	type: "verdict";
	status: ShowMeStatus;
	text: string;
}

export type NeedsCaptureStatus = "NEEDS CAPTURE" | "NOT SHOWN" | "INCOMPLETE";

export interface NeedsCaptureBlock {
	id: string;
	type: "needs-capture";
	title?: string;
	reason: string;
	request?: string;
	status?: NeedsCaptureStatus;
}

export interface CommandLogBlock {
	id: string;
	type: "command-log";
	logId: string;
	title?: string;
	command: string;
	cwd: string;
	startedAt: string;
	finishedAt: string;
	exitCode: number | null;
	timedOut: boolean;
	stdoutPreview?: string;
	stderrPreview?: string;
	logPath: string;
	stdoutTruncated?: boolean;
	stderrTruncated?: boolean;
}

export type ShowMeAssetType = "image" | "video" | "gif" | "diagram";

export interface MediaBlock {
	id: string;
	type: "image" | "video" | "gif" | "diagram";
	assetId: string;
	path: string;
	caption?: string;
	alt?: string;
	sensitivity?: string;
}

export interface FileRoleRow {
	area: string;
	files: string[];
	role: string;
	observation?: string;
}

export interface FileRoleTableBlock {
	id: string;
	type: "file-role-table";
	rows: FileRoleRow[];
}

export type ShowMeBlock =
	| MarkdownBlock
	| TableBlock
	| CodeBlock
	| DiffBlock
	| SourceDiagramBlock
	| CalloutBlock
	| VerdictBlock
	| NeedsCaptureBlock
	| CommandLogBlock
	| MediaBlock
	| FileRoleTableBlock;

export interface ShowMeSection {
	id: string;
	title: string;
	purpose?: string;
	blocks: ShowMeBlock[];
}

export interface ShowMeAsset {
	id: string;
	type: ShowMeAssetType;
	path: string;
	originalPath: string;
	caption?: string;
	alt?: string;
	hash?: string;
	bytes?: number;
	createdAt?: string;
	sensitivity?: string;
}

export interface ShowMeLog {
	id: string;
	path: string;
	command?: string;
	cwd?: string;
	startedAt?: string;
	finishedAt?: string;
	exitCode?: number | null;
	timedOut?: boolean;
	stdoutBytes?: number;
	stderrBytes?: number;
	stdoutTruncated?: boolean;
	stderrTruncated?: boolean;
	redactions?: unknown;
}

export interface ShowMeProvenance {
	cwd?: string;
	repoRoot?: string;
	branch?: string;
	commit?: string;
	dirty?: boolean;
	createdBy?: string;
	[key: string]: unknown;
}

export interface ShowMeDocument {
	id: string;
	title: string;
	subtitle?: string;
	mode: ShowMeMode;
	status: ShowMeStatus;
	presentation?: ShowMePresentation;
	summary?: string;
	createdAt: string;
	updatedAt: string;
	sections: ShowMeSection[];
	assets: ShowMeAsset[];
	logs: ShowMeLog[];
	provenance: ShowMeProvenance;
}

const ModeSchema = Type.Union(SHOW_ME_MODES.map((value) => Type.Literal(value)) as any);
const StatusSchema = Type.Union(SHOW_ME_STATUSES.map((value) => Type.Literal(value)) as any);
const PresentationSchema = Type.Union(SHOW_ME_PRESENTATIONS.map((value) => Type.Literal(value)) as any);

export const CreateDeckSchema = Type.Object({
	title: Type.String({ description: "Deck/report title" }),
	subtitle: Type.Optional(Type.String({ description: "Optional subtitle or context line" })),
	mode: ModeSchema,
	status: Type.Optional(StatusSchema),
	presentation: Type.Optional(PresentationSchema),
	summary: Type.Optional(Type.String({ description: "Short summary shown in the hero" })),
	outputRoot: Type.Optional(Type.String({ description: "Explicit output root. Defaults to BEISLID_STATE_DIR/show-me/..." })),
	repoLocal: Type.Optional(Type.Boolean({ description: "Write under .beislid/show-me in the current repo" })),
});

export const DeckIdSchema = Type.Object({
	deckId: Type.String({ description: "Show Me deck id" }),
});

export const AddSectionSchema = Type.Object({
	deckId: Type.String(),
	title: Type.String(),
	purpose: Type.Optional(Type.String()),
});

export const AddBlockSchema = Type.Object({
	deckId: Type.String(),
	sectionId: Type.String(),
	block: Type.Any({ description: "ShowMeBlock JSON object. Canonical keys: markdown.markdown, table.columns/rows, code.code/language, diff.diff, diagram.diagram/language for Mermaid source, callout.text, verdict.text/status, file-role-table.rows. Common aliases like content/body and headers are normalized." }),
});

export const RunCommandSchema = Type.Object({
	deckId: Type.String({ description: "Show Me deck id" }),
	command: Type.String({ description: "Command to run and capture" }),
	sectionId: Type.Optional(Type.String({ description: "Optional section id to append a command-log block" })),
	title: Type.Optional(Type.String({ description: "Optional display title for the command evidence" })),
	cwd: Type.Optional(Type.String({ description: "Working directory. Defaults to current pi cwd" })),
	timeoutSeconds: Type.Optional(Type.Number({ description: "Timeout in seconds. Default 60, max 600" })),
	allowRisky: Type.Optional(Type.Boolean({ description: "Allow commands that look mutating/destructive. Default false" })),
});

export const AddAssetSchema = Type.Object({
	deckId: Type.String({ description: "Show Me deck id" }),
	path: Type.String({ description: "Path to an existing asset file to copy into the deck" }),
	type: Type.Optional(Type.Union([Type.Literal("image"), Type.Literal("video"), Type.Literal("gif"), Type.Literal("diagram")], { description: "Asset type. Inferred from extension when omitted." })),
	sectionId: Type.Optional(Type.String({ description: "Optional section id to append a media block" })),
	caption: Type.Optional(Type.String({ description: "Caption shown under the media" })),
	alt: Type.Optional(Type.String({ description: "Alt text for image/diagram blocks" })),
	sensitivity: Type.Optional(Type.String({ description: "Sensitivity warning. Defaults to a local/private media warning." })),
});

export const AddNeedsCaptureSchema = Type.Object({
	deckId: Type.String({ description: "Show Me deck id" }),
	sectionId: Type.String({ description: "Section id where the NEEDS_CAPTURE block should be appended" }),
	title: Type.Optional(Type.String({ description: "Short capture title" })),
	reason: Type.String({ description: "Why the evidence could not be captured yet" }),
	request: Type.Optional(Type.String({ description: "What should be captured manually or with extra tooling" })),
	status: Type.Optional(Type.Union([Type.Literal("NEEDS CAPTURE"), Type.Literal("NOT SHOWN"), Type.Literal("INCOMPLETE")], { description: "Missing-evidence status. Defaults to NEEDS CAPTURE." })),
});

export const CaptureBrowserScreenshotSchema = Type.Object({
	deckId: Type.String({ description: "Show Me deck id" }),
	url: Type.String({ description: "URL to open in Playwright and screenshot" }),
	sectionId: Type.Optional(Type.String({ description: "Optional section id to append the screenshot or NEEDS_CAPTURE block" })),
	caption: Type.Optional(Type.String({ description: "Caption shown under the screenshot" })),
	alt: Type.Optional(Type.String({ description: "Alt text for the screenshot" })),
	fullPage: Type.Optional(Type.Boolean({ description: "Capture full page. Default true." })),
	viewportWidth: Type.Optional(Type.Number({ description: "Viewport width. Default 1440, clamped 320-3840." })),
	viewportHeight: Type.Optional(Type.Number({ description: "Viewport height. Default 1000, clamped 240-2160." })),
	waitUntil: Type.Optional(Type.Union([Type.Literal("load"), Type.Literal("domcontentloaded"), Type.Literal("networkidle")], { description: "Navigation wait condition. Default load." })),
	waitForSelector: Type.Optional(Type.String({ description: "Optional selector to wait for before screenshot" })),
	timeoutSeconds: Type.Optional(Type.Number({ description: "Timeout in seconds. Default 30, max 120." })),
	sensitivity: Type.Optional(Type.String({ description: "Sensitivity warning for the screenshot block" })),
});

export function isShowMeMode(value: unknown): value is ShowMeMode {
	return typeof value === "string" && (SHOW_ME_MODES as readonly string[]).includes(value);
}

export function isShowMeStatus(value: unknown): value is ShowMeStatus {
	return typeof value === "string" && (SHOW_ME_STATUSES as readonly string[]).includes(value);
}
