import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { copyFile, mkdir, stat } from "node:fs/promises";
import { basename, extname, join, posix, resolve } from "node:path";
import type { MediaBlock, ShowMeAsset, ShowMeAssetType } from "./schema.js";
import { addBlock, readDeck, writeDeck, writeManifest } from "./store.js";

function nowIso(): string {
	return new Date().toISOString();
}

function shortId(): string {
	return Math.random().toString(36).slice(2, 8);
}

function safeFilename(value: string): string {
	return value
		.toLowerCase()
		.replace(/[^a-z0-9._-]+/g, "-")
		.replace(/^-|-$/g, "") || "asset";
}

function assetSubdir(type: ShowMeAssetType): string {
	switch (type) {
		case "image":
			return "images";
		case "video":
			return "videos";
		case "gif":
			return "gifs";
		case "diagram":
			return "diagrams";
	}
}

const IMAGE_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".webp", ".avif", ".bmp"]);
const VIDEO_EXTENSIONS = new Set([".mp4", ".webm", ".mov", ".m4v"]);

function inferType(path: string): ShowMeAssetType {
	const ext = extname(path).toLowerCase();
	if (VIDEO_EXTENSIONS.has(ext)) return "video";
	if (ext === ".gif") return "gif";
	if (ext === ".svg") return "diagram";
	if (IMAGE_EXTENSIONS.has(ext)) return "image";
	throw new Error(`Unsupported show-me asset extension '${ext || "none"}'. Phase 4 accepts PNG/JPEG/WebP/AVIF/BMP images, GIFs, MP4/WebM/MOV/M4V videos, and SVG diagrams.`);
}

function assertSupportedAsset(type: ShowMeAssetType, path: string) {
	const ext = extname(path).toLowerCase();
	if (type === "image" && !IMAGE_EXTENSIONS.has(ext)) {
		throw new Error(`Image assets must be browser-renderable image files; got '${ext || "none"}'.`);
	}
	if (type === "video" && !VIDEO_EXTENSIONS.has(ext)) {
		throw new Error(`Video assets must be MP4/WebM/MOV/M4V files; got '${ext || "none"}'.`);
	}
	if (type === "gif" && ext !== ".gif") {
		throw new Error(`GIF assets must use .gif files; got '${ext || "none"}'.`);
	}
	if (type === "diagram" && ext !== ".svg") {
		throw new Error("Diagram assets must be browser-renderable SVG files. For Mermaid source, add a diagram block with a `diagram` field instead of using show_me_add_asset.");
	}
}

async function sha256(path: string): Promise<string> {
	return new Promise((resolveHash, reject) => {
		const hash = createHash("sha256");
		const stream = createReadStream(path);
		stream.on("data", (chunk) => hash.update(chunk));
		stream.on("error", reject);
		stream.on("end", () => resolveHash(`sha256:${hash.digest("hex")}`));
	});
}

export interface AddAssetInput {
	deckId: string;
	path: string;
	type?: ShowMeAssetType;
	sectionId?: string;
	caption?: string;
	alt?: string;
	sensitivity?: string;
}

export interface AddAssetResult {
	deckId: string;
	assetId: string;
	blockId?: string;
	assetPath: string;
	originalPath: string;
	hash: string;
	bytes: number;
	type: ShowMeAssetType;
}

export async function addAsset(input: AddAssetInput, defaultCwd: string): Promise<AddAssetResult> {
	const { root, doc } = await readDeck(input.deckId);
	if (input.sectionId && !doc.sections.some((section) => section.id === input.sectionId)) {
		throw new Error(`Unknown section id ${input.sectionId} in deck ${input.deckId}; asset was not copied.`);
	}

	const originalPath = resolve(defaultCwd, input.path);
	const info = await stat(originalPath);
	if (!info.isFile()) throw new Error(`Asset path is not a file: ${originalPath}`);

	const type = input.type ?? inferType(originalPath);
	assertSupportedAsset(type, originalPath);
	const id = `asset-${Date.now()}-${shortId()}`;
	const ext = extname(originalPath) || (type === "diagram" ? ".txt" : "");
	const filename = `${id}-${safeFilename(basename(originalPath, ext))}${ext}`;
	const relPath = posix.join("assets", assetSubdir(type), filename);
	const destPath = join(root, relPath);
	await mkdir(join(root, "assets", assetSubdir(type)), { recursive: true });
	await copyFile(originalPath, destPath);
	const copiedInfo = await stat(destPath);
	const hash = await sha256(destPath);
	const sensitivity = input.sensitivity ?? "Local media may contain sensitive information; not redacted by show-me.";

	const asset: ShowMeAsset = {
		id,
		type,
		path: relPath,
		originalPath,
		caption: input.caption,
		alt: input.alt,
		hash,
		bytes: copiedInfo.size,
		createdAt: nowIso(),
		sensitivity,
	};
	(doc.assets ??= []).push(asset);
	doc.provenance = {
		...doc.provenance,
		assets: [
			...(Array.isArray(doc.provenance.assets) ? doc.provenance.assets : []),
			{ id, type, path: relPath, originalPath, hash, bytes: copiedInfo.size, caption: input.caption, alt: input.alt, sensitivity },
		],
	};
	await writeDeck(root, doc);
	await writeManifest(root, doc);

	let blockId: string | undefined;
	if (input.sectionId) {
		const block: Omit<MediaBlock, "id"> = {
			type,
			assetId: id,
			path: relPath,
			caption: input.caption,
			alt: input.alt,
			sensitivity,
		};
		blockId = (await addBlock(input.deckId, input.sectionId, block)).blockId;
	}

	return { deckId: doc.id, assetId: id, blockId, assetPath: destPath, originalPath, hash, bytes: copiedInfo.size, type };
}
