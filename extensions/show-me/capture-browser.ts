import { createRequire } from "node:module";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { addAsset } from "./asset-manager.js";
import { addNeedsCaptureBlock } from "./needs-capture.js";
import { resolveOptionalPackage } from "./doctor.js";
import { readDeck } from "./store.js";

export interface CaptureBrowserScreenshotInput {
	deckId: string;
	url: string;
	sectionId?: string;
	caption?: string;
	alt?: string;
	fullPage?: boolean;
	viewportWidth?: number;
	viewportHeight?: number;
	waitUntil?: "load" | "domcontentloaded" | "networkidle";
	waitForSelector?: string;
	timeoutSeconds?: number;
	sensitivity?: string;
}

export interface CaptureBrowserScreenshotResult {
	deckId: string;
	status: "captured" | "needs-capture";
	assetId?: string;
	blockId?: string;
	assetPath?: string;
	url: string;
	reason?: string;
}

type PlaywrightModule = {
	chromium: {
		launch(options?: { headless?: boolean }): Promise<{
			newPage(options?: { viewport?: { width: number; height: number } }): Promise<{
				goto(url: string, options?: { waitUntil?: string; timeout?: number }): Promise<unknown>;
				waitForSelector(selector: string, options?: { timeout?: number }): Promise<unknown>;
				screenshot(options: { path: string; fullPage?: boolean; timeout?: number }): Promise<unknown>;
			}>;
			close(): Promise<void>;
		}>;
	};
};

async function loadPlaywright(cwd: string): Promise<PlaywrightModule | undefined> {
	const resolved = resolveOptionalPackage("playwright", cwd);
	if (!resolved) return undefined;
	try {
		const requireFromCwd = createRequire(join(cwd, "package.json"));
		return requireFromCwd("playwright") as PlaywrightModule;
	} catch {
		const module = await import(pathToFileURL(resolved).href);
		return module as unknown as PlaywrightModule;
	}
}

function timeoutMs(input?: number): number {
	const seconds = Math.max(1, Math.min(input ?? 30, 120));
	return seconds * 1000;
}

async function validateDeckAndSection(deckId: string, sectionId?: string) {
	const { doc } = await readDeck(deckId);
	if (sectionId && !doc.sections.some((section) => section.id === sectionId)) {
		throw new Error(`Unknown section id ${sectionId} in deck ${deckId}; screenshot was not captured.`);
	}
}

async function needsCapture(input: CaptureBrowserScreenshotInput, reason: string): Promise<CaptureBrowserScreenshotResult> {
	let blockId: string | undefined;
	if (input.sectionId) {
		blockId = (await addNeedsCaptureBlock({
			deckId: input.deckId,
			sectionId: input.sectionId,
			title: input.caption ?? "Browser screenshot needed",
			reason,
			request: `Capture browser screenshot for ${input.url}`,
			status: "NEEDS CAPTURE",
		})).blockId;
	}
	return { deckId: input.deckId, status: "needs-capture", blockId, url: input.url, reason };
}

export async function captureBrowserScreenshot(input: CaptureBrowserScreenshotInput, cwd: string): Promise<CaptureBrowserScreenshotResult> {
	await validateDeckAndSection(input.deckId, input.sectionId);
	const playwright = await loadPlaywright(cwd);
	if (!playwright) {
		return needsCapture(input, "Playwright is not installed in the project or extension environment.");
	}

	const tempRoot = await mkdtemp(join(tmpdir(), "show-me-browser-"));
	const screenshotPath = join(tempRoot, "screenshot.png");
	let browser: Awaited<ReturnType<PlaywrightModule["chromium"]["launch"]>> | undefined;
	try {
		const timeout = timeoutMs(input.timeoutSeconds);
		browser = await playwright.chromium.launch({ headless: true });
		const page = await browser.newPage({
			viewport: {
				width: Math.max(320, Math.min(input.viewportWidth ?? 1440, 3840)),
				height: Math.max(240, Math.min(input.viewportHeight ?? 1000, 2160)),
			},
		});
		await page.goto(input.url, { waitUntil: input.waitUntil ?? "load", timeout });
		if (input.waitForSelector) await page.waitForSelector(input.waitForSelector, { timeout });
		await page.screenshot({ path: screenshotPath, fullPage: input.fullPage ?? true, timeout });
		const asset = await addAsset(
			{
				deckId: input.deckId,
				path: screenshotPath,
				type: "image",
				sectionId: input.sectionId,
				caption: input.caption ?? `Browser screenshot: ${input.url}`,
				alt: input.alt ?? `Browser screenshot of ${input.url}`,
				sensitivity: input.sensitivity ?? "Browser screenshots may contain sensitive page content; inspect before sharing.",
			},
			cwd,
		);
		return { deckId: input.deckId, status: "captured", assetId: asset.assetId, blockId: asset.blockId, assetPath: asset.assetPath, url: input.url };
	} catch (error) {
		return needsCapture(input, error instanceof Error ? error.message : String(error));
	} finally {
		await browser?.close().catch(() => undefined);
		await rm(tempRoot, { recursive: true, force: true }).catch(() => undefined);
	}
}
