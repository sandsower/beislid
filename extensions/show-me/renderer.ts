import type { FileRoleTableBlock, MediaBlock, ShowMeBlock, ShowMeDocument, ShowMeMode, ShowMePresentation, ShowMeStatus, TableBlock } from "./schema.js";

function escapeHtml(value: unknown): string {
	return String(value ?? "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#39;");
}

function slug(value: string): string {
	return value
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/^-|-$/g, "") || "section";
}

function statusClass(status: ShowMeStatus): string {
	if (status === "PASS" || status === "EXPLANATORY") return "good";
	if (status === "FAIL" || status === "CONFLICTING") return "bad";
	return "warn";
}

function inferPresentation(mode: ShowMeMode, status: ShowMeStatus): ShowMePresentation {
	if (mode === "understanding" && status === "EXPLANATORY") return "visual-deck";
	if (mode === "verification" || mode === "cli-demo" || mode === "ui-demo") return "evidence-deck";
	return "report";
}

function renderInlineMarkdown(value: string): string {
	let text = escapeHtml(value);
	text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
	text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
	return text;
}

function renderMarkdownFallback(markdown: string): string {
	return `<pre class="markdown-fallback"><code>${escapeHtml(markdown)}</code></pre>`;
}

function classToken(value: string): string {
	return value.toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-|-$/g, "") || "text";
}

function diffLineClass(line: string): string {
	if (line.startsWith("@@")) return "diff-line diff-hunk";
	if (/^(diff --git|index |--- |\+\+\+ )/.test(line)) return "diff-line diff-meta";
	if (line.startsWith("+") && !line.startsWith("+++")) return "diff-line diff-add";
	if (line.startsWith("-") && !line.startsWith("---")) return "diff-line diff-del";
	return "diff-line diff-context";
}

function renderDiffCode(diff: string): string {
	return `<pre class="diff"><code class="language-diff">${escapeHtml(diff)}</code></pre>`;
}

function renderDiffStatLine(line: string): string {
	const match = line.match(/^(.*\|\s+\d+\s+)([+-]+)(.*)$/);
	if (match) {
		const graph = [...match[2]].map((char) => char === "+" ? '<span class="terminal-add">+</span>' : '<span class="terminal-del">-</span>').join("");
		return `${escapeHtml(match[1])}${graph}${escapeHtml(match[3])}`;
	}
	let text = escapeHtml(line);
	text = text.replace(/(\d+ insertions?\(\+\))/g, '<span class="terminal-add">$1</span>');
	text = text.replace(/(\d+ deletions?\(-\))/g, '<span class="terminal-del">$1</span>');
	return text;
}

function renderTerminalPreview(value: string, stream: "stdout" | "stderr" = "stdout"): string {
	const text = String(value ?? "");
	if (stream === "stdout" && (/^diff --git /m.test(text) || /^@@ /m.test(text))) return renderDiffCode(text);
	const lines = text.split(/\r?\n/);
	const rendered = lines.map((line) => {
		if (/^#{1,6}\s+/.test(line)) return `<span class="terminal-heading">${escapeHtml(line)}</span>`;
		if (/\|\s+\d+\s+[+-]+/.test(line) || /\d+ insertions?\(\+\)|\d+ deletions?\(-\)/.test(line)) return renderDiffStatLine(line);
		if (/^\s*(A|M|D|R|C)\s+/.test(line)) return `<span class="terminal-modified">${escapeHtml(line)}</span>`;
		if (/^\?\?\s+/.test(line)) return `<span class="terminal-untracked">${escapeHtml(line)}</span>`;
		return escapeHtml(line);
	}).join("\n");
	return `<pre class="terminal-preview ${stream}"><code class="nohighlight">${rendered}</code></pre>`;
}

function renderSourceDiagram(block: { diagram: string; language?: string; title?: string }): string {
	const language = block.language ?? "mermaid";
	const title = block.title ? `<div class="code-label">${escapeHtml(block.title)}</div>` : "";
	if (language === "mermaid") {
		return `<figure class="diagram-source">${title}<div class="mermaid">${escapeHtml(block.diagram)}</div></figure>`;
	}
	return `${title}<pre class="language-${classToken(language)}"><code>${escapeHtml(block.diagram)}</code></pre>`;
}

function renderCodeFence(language: string, code: string): string {
	const normalized = language.trim().toLowerCase();
	if (normalized === "mermaid") return renderSourceDiagram({ diagram: code, language: "mermaid" });
	if (normalized === "diff" || normalized === "patch") return renderDiffCode(code);
	const label = normalized ? `<div class="code-label">${escapeHtml(normalized)}</div>` : "";
	const klass = normalized ? ` class="language-${classToken(normalized)}"` : "";
	return `${label}<pre${klass}><code>${escapeHtml(code)}</code></pre>`;
}

function blockHasMermaid(block: ShowMeBlock): boolean {
	if (block.type === "markdown") return /```\s*mermaid\b/i.test(block.markdown);
	if (block.type === "code") return (block.language ?? "").toLowerCase() === "mermaid";
	if (block.type === "diagram" && "diagram" in block) return (block.language ?? "mermaid") === "mermaid";
	return false;
}

function documentHasMermaid(doc: ShowMeDocument): boolean {
	return doc.sections.some((section) => section.blocks.some(blockHasMermaid));
}

const SHOW_ME_HIGHLIGHT_CSS_SRI = "sha384-wH75j6z1lH97ZOpMOInqhgKzFkAInZPPSPlZpYKYTOqsaizPvhQZmAtLcPKXpLyH";
const SHOW_ME_HIGHLIGHT_JS_SRI = "sha384-F/bZzf7p3Joyp5psL90p/p89AZJsndkSoGwRpXcZhleCWhd8SnRuoYo4d0yirjJp";
const SHOW_ME_MARKED_JS_SRI = "sha384-ZD0fTOwPMHi7zM6WTVIWJR21I07lq0ccnqz3J6WMvQKG9thh4y7TA1QE6PJu0Af8";
const SHOW_ME_DOMPURIFY_JS_SRI = "sha384-o44XUELLEnv/iSlA1NWxBweqbD4TSR0qgq2VzVsxtkHS989JJjGKSE9vkfo5MN4K";
const SHOW_ME_MERMAID_JS_SRI = "sha384-T/0lMUdJpd2S1ZHtRiofG3htU3xPCrFVeAQ1UUE2TJwlEJSV5NUwn30kP28n238E";

function showMeLibraryHead(): string {
	return `<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github-dark.min.css" integrity="${SHOW_ME_HIGHLIGHT_CSS_SRI}" crossorigin="anonymous">`;
}

function showMeLibraryScripts(): string {
	return `<script src="https://cdn.jsdelivr.net/npm/marked@18.0.5/lib/marked.umd.js" integrity="${SHOW_ME_MARKED_JS_SRI}" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.4.11/dist/purify.min.js" integrity="${SHOW_ME_DOMPURIFY_JS_SRI}" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11.16.0/dist/mermaid.min.js" integrity="${SHOW_ME_MERMAID_JS_SRI}" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js" integrity="${SHOW_ME_HIGHLIGHT_JS_SRI}" crossorigin="anonymous"></script>
<script>
(function () {
  function renderMarkdownBlocks() {
    if (!window.marked || !window.DOMPurify) return;
    document.querySelectorAll('[data-show-me-markdown]').forEach(function (el) {
      var source = decodeURIComponent(el.getAttribute('data-show-me-markdown') || '');
      var html = window.marked.parse(source, { gfm: true, breaks: false });
      el.innerHTML = window.DOMPurify.sanitize(html);
    });
  }
  function promoteMermaidFences() {
    document.querySelectorAll('pre > code.language-mermaid').forEach(function (code) {
      var div = document.createElement('div');
      div.className = 'mermaid';
      div.textContent = code.textContent || '';
      if (code.parentElement) code.parentElement.replaceWith(div);
    });
  }
  renderMarkdownBlocks();
  promoteMermaidFences();
  if (window.hljs) window.hljs.highlightAll();
  if (window.mermaid) {
    window.mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'strict' });
    window.mermaid.run({ querySelector: '.mermaid' }).catch(function (error) { console.error('show-me mermaid render failed', error); });
  }
}());
</script>`;
}

function flushParagraph(out: string[], paragraph: string[]) {
	if (paragraph.length === 0) return;
	out.push(`<p>${renderInlineMarkdown(paragraph.join(" "))}</p>`);
	paragraph.length = 0;
}

function flushList(out: string[], list: string[], ordered: boolean) {
	if (list.length === 0) return;
	const tag = ordered ? "ol" : "ul";
	out.push(`<${tag}>${list.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</${tag}>`);
	list.length = 0;
}

function renderMarkdown(markdown: string): string {
	return `<div class="markdown" data-show-me-markdown="${escapeHtml(encodeURIComponent(markdown))}">${renderMarkdownFallback(markdown)}</div>`;
}

function renderTable(block: TableBlock): string {
	const headers = block.columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("");
	const rows = block.rows
		.map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`)
		.join("\n");
	return `<div class="table-wrap"><table><thead><tr>${headers}</tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderFileRoleTable(block: FileRoleTableBlock): string {
	const table: TableBlock = {
		id: block.id,
		type: "table",
		columns: ["Area", "Primary files", "Role", "Observation"],
		rows: block.rows.map((row) => [row.area, row.files.join("\n"), row.role, row.observation ?? ""]),
	};
	return renderTable(table);
}

function renderMediaBlock(block: MediaBlock): string {
	const caption = block.caption ? `<div class="caption">${escapeHtml(block.caption)}</div>` : "";
	const sensitivity = block.sensitivity ? `<div class="media-warning">${escapeHtml(block.sensitivity)}</div>` : "";
	if (block.type === "video") {
		return `<figure class="media"><video controls preload="metadata" src="${escapeHtml(block.path)}"></video>${caption}${sensitivity}</figure>`;
	}
	if (block.type === "image" || block.type === "gif" || block.type === "diagram") {
		return `<figure class="media"><img src="${escapeHtml(block.path)}" alt="${escapeHtml(block.alt ?? block.caption ?? block.type)}">${caption}${sensitivity}</figure>`;
	}
	return `<div class="callout warning">Unsupported media block ${escapeHtml(block.type)}</div>`;
}

function renderBlock(block: ShowMeBlock): string {
	switch (block.type) {
		case "markdown":
			return `<div class="block">${renderMarkdown(block.markdown)}</div>`;
		case "table":
			return `<div class="block">${renderTable(block)}</div>`;
		case "code":
			return `<div class="block">${renderCodeFence(block.language ?? "code", block.code)}</div>`;
		case "diff":
			return `<div class="block"><div class="code-label">diff</div>${renderDiffCode(block.diff)}</div>`;
		case "callout":
			return `<div class="block callout ${escapeHtml(block.tone ?? "info")}">${block.title ? `<strong>${escapeHtml(block.title)}</strong>` : ""}${block.title ? "<br>" : ""}${escapeHtml(block.text)}</div>`;
		case "verdict":
			return `<div class="block verdict ${statusClass(block.status)}"><strong>${escapeHtml(block.status)}</strong><span>${escapeHtml(block.text)}</span></div>`;
		case "needs-capture":
			return `<div class="block needs-capture"><div><strong>${escapeHtml(block.status ?? "NEEDS CAPTURE")}</strong>${block.title ? `<span>${escapeHtml(block.title)}</span>` : ""}</div><p>${escapeHtml(block.reason)}</p>${block.request ? `<p class="capture-request">Request: ${escapeHtml(block.request)}</p>` : ""}</div>`;
		case "command-log":
			return `<div class="block command-log"><div class="command-header"><span>${escapeHtml(block.title ?? "Command evidence")}</span><span class="${block.exitCode === 0 && !block.timedOut ? "good" : "bad"}">exit ${escapeHtml(block.exitCode ?? "null")}${block.timedOut ? " · timed out" : ""}</span></div><div class="command-meta"><span>command: ${escapeHtml(block.command)}</span><span>cwd: ${escapeHtml(block.cwd)}</span><span>started: ${escapeHtml(block.startedAt)}</span><span>finished: ${escapeHtml(block.finishedAt)}</span><span>log: ${escapeHtml(block.logPath)}</span>${block.stdoutTruncated ? "<span>stdout truncated</span>" : ""}${block.stderrTruncated ? "<span>stderr truncated</span>" : ""}</div>${block.stdoutPreview ? renderTerminalPreview(block.stdoutPreview, "stdout") : ""}${block.stderrPreview ? renderTerminalPreview(block.stderrPreview, "stderr") : ""}</div>`;
		case "image":
		case "video":
		case "gif":
			return `<div class="block">${renderMediaBlock(block)}</div>`;
		case "diagram":
			if ("diagram" in block) return `<div class="block">${renderSourceDiagram(block)}</div>`;
			return `<div class="block">${renderMediaBlock(block)}</div>`;
		case "file-role-table":
			return `<div class="block">${renderFileRoleTable(block)}</div>`;
		default: {
			const neverBlock = block as never;
			return `<div class="block callout warning">Unsupported block: ${escapeHtml(JSON.stringify(neverBlock))}</div>`;
		}
	}
}

function renderVisualTable(block: TableBlock): string {
	if (block.rows.length > 0 && block.rows.length <= 6 && block.columns.length >= 3 && block.columns.length <= 5) {
		return `<div class="compare-cards">${block.rows
			.map((row, rowIndex) => {
				const title = row[0] ?? `Option ${rowIndex + 1}`;
				const details = block.columns
					.slice(1)
					.map((column, index) => `<div class="card-field"><span>${escapeHtml(column)}</span><p>${renderInlineMarkdown(row[index + 1] ?? "")}</p></div>`)
					.join("");
				return `<article class="comparison-card"><div class="card-number">${String(rowIndex + 1).padStart(2, "0")}</div><h4>${renderInlineMarkdown(title)}</h4>${details}</article>`;
			})
			.join("")}</div>`;
	}
	return renderTable(block);
}

function renderVisualBlock(block: ShowMeBlock): string {
	switch (block.type) {
		case "markdown":
			return `<div class="visual-block visual-copy">${renderMarkdown(block.markdown)}</div>`;
		case "table":
			return `<div class="visual-block">${renderVisualTable(block)}</div>`;
		case "callout":
			return `<div class="visual-block visual-callout ${escapeHtml(block.tone ?? "info")}">${block.title ? `<h4>${escapeHtml(block.title)}</h4>` : ""}<p>${renderInlineMarkdown(block.text)}</p></div>`;
		case "verdict":
			return `<div class="visual-block visual-verdict ${statusClass(block.status)}"><strong>${escapeHtml(block.status)}</strong><p>${escapeHtml(block.text)}</p></div>`;
		default:
			return renderBlock(block);
	}
}

function renderVisualDeck(doc: ShowMeDocument): string {
	const navItems = doc.sections
		.map((section, index) => `<a href="#${slug(section.title)}-${index + 1}"><span>${String(index + 1).padStart(2, "0")}</span>${escapeHtml(section.title)}</a>`)
		.join("");
	const sections = doc.sections
		.map((section, index) => {
			const id = `${slug(section.title)}-${index + 1}`;
			const blocks = section.blocks.map(renderVisualBlock).join("\n");
			return `<section id="${id}" class="visual-section"><div class="eyebrow">${String(index + 1).padStart(2, "0")}</div><h2>${escapeHtml(section.title)}</h2>${section.purpose ? `<p class="section-purpose">${escapeHtml(section.purpose)}</p>` : ""}${blocks || `<div class="visual-callout warning"><p>No evidence added to this section yet.</p></div>`}</section>`;
		})
		.join("\n");
	const provenance = escapeHtml(JSON.stringify(doc.provenance ?? {}, null, 2));
	return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(doc.title)}</title>${showMeLibraryHead()}<style>
:root{color-scheme:dark;--bg:#08111f;--panel:#111d31;--panel2:#172640;--line:#2b3f5d;--text:#f2f7ff;--muted:#a7b7cf;--blue:#8fb0ff;--green:#49d9a9;--yellow:#ffd166;--red:#ff7b92;--purple:#c59cff;--code:#07111f;--shadow:0 24px 90px rgba(0,0,0,.35)}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 10% 0%,rgba(143,176,255,.26),transparent 32rem),radial-gradient(circle at 95% 8%,rgba(73,217,169,.15),transparent 28rem),var(--bg);color:var(--text);font:16px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.layout{display:grid;grid-template-columns:280px 1fr;min-height:100vh}.side{position:sticky;top:0;height:100vh;padding:22px;border-right:1px solid var(--line);background:rgba(8,17,31,.86);backdrop-filter:blur(16px);overflow:auto}.brand{padding:18px;border:1px solid var(--line);border-radius:22px;background:linear-gradient(180deg,var(--panel2),var(--panel));box-shadow:var(--shadow)}.brand h1{font-size:23px;line-height:1.05;margin:8px 0}.muted,.section-purpose{color:var(--muted)}.eyebrow{color:var(--blue);font-size:12px;text-transform:uppercase;letter-spacing:.18em;font-weight:900}.toc{display:grid;gap:8px;margin-top:18px}.toc a{display:flex;gap:10px;text-decoration:none;color:var(--muted);padding:10px 12px;border-radius:12px}.toc a:hover{background:rgba(143,176,255,.12);color:var(--text)}main{max-width:1240px;padding:44px 56px 80px}.hero{border:1px solid var(--line);border-radius:32px;padding:48px;background:linear-gradient(135deg,rgba(23,38,64,.94),rgba(17,29,49,.8));box-shadow:var(--shadow)}.hero h1{font-size:clamp(44px,7vw,76px);line-height:.9;letter-spacing:-.065em;margin:10px 0 18px;max-width:900px}.badges{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}.badge{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:999px;padding:7px 12px;background:rgba(255,255,255,.05);font-weight:800;color:var(--muted)}.badge.good{color:var(--green)}.badge.warn{color:var(--yellow)}.badge.bad{color:var(--red)}.visual-section{margin-top:34px;border:1px solid var(--line);border-radius:30px;padding:34px;background:rgba(17,29,49,.88);box-shadow:0 18px 70px rgba(0,0,0,.22)}.visual-section h2{font-size:clamp(34px,5vw,52px);line-height:.95;letter-spacing:-.045em;margin:8px 0 16px}.visual-block{margin-top:18px}.markdown{display:grid;gap:14px}.markdown h2,.markdown h3,.markdown h4{margin:0;color:var(--text);letter-spacing:-.035em}.markdown h2{font-size:32px}.markdown h3{font-size:26px}.markdown h4{font-size:22px}.markdown p{margin:0;color:var(--muted)}.markdown ul,.markdown ol{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:0;padding:0;list-style:none}.markdown li{border:1px solid var(--line);border-radius:18px;padding:16px;background:rgba(255,255,255,.045);color:var(--muted)}code{font-family:"SFMono-Regular",Consolas,monospace;background:rgba(143,176,255,.12);border:1px solid rgba(143,176,255,.18);border-radius:6px;padding:.08em .3em}pre{margin:0;padding:16px;overflow:auto;border:1px dashed rgba(143,176,255,.55);border-radius:18px;background:rgba(143,176,255,.08);color:#d8e6ff}.markdown-fallback{white-space:pre-wrap}.diff-line{display:block;min-height:1.4em}.diff-add,.terminal-add{color:#9ff2c8;background:rgba(73,217,169,.10)}.diff-del,.terminal-del{color:#ffb3c0;background:rgba(255,123,146,.10)}.diff-hunk{color:#c59cff;background:rgba(197,156,255,.12)}.diff-meta{color:#8fb0ff}.terminal-heading{display:block;color:#8fb0ff;font-weight:800}.terminal-modified{color:#ffd166}.terminal-untracked{color:#c59cff}.mermaid,.diagram-source{padding:18px;border:1px solid var(--line);border-radius:18px;background:rgba(255,255,255,.045);overflow:auto}.compare-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}.comparison-card{position:relative;border:1px solid var(--line);border-radius:24px;padding:24px;background:rgba(255,255,255,.045);overflow:hidden}.comparison-card:before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:linear-gradient(90deg,var(--blue),var(--green))}.card-number{color:var(--blue);font-size:12px;font-weight:900;letter-spacing:.18em}.comparison-card h4{font-size:26px;line-height:1.05;margin:8px 0 16px}.card-field{border-top:1px solid rgba(255,255,255,.08);padding-top:12px;margin-top:12px}.card-field span{display:block;color:var(--muted);font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.14em}.card-field p{margin:.35rem 0 0;color:var(--text)}.visual-callout,.visual-verdict{border:1px solid rgba(255,209,102,.45);border-radius:24px;background:rgba(255,209,102,.09);padding:24px;color:#ffe9af}.visual-callout.info{border-color:rgba(143,176,255,.45);background:rgba(143,176,255,.1);color:#dbe6ff}.visual-callout.success{border-color:rgba(73,217,169,.4);background:rgba(73,217,169,.1);color:#caffef}.visual-callout.danger{border-color:rgba(255,123,146,.4);background:rgba(255,123,146,.1);color:#ffd6de}.visual-callout h4{font-size:28px;margin:0 0 8px}.visual-callout p,.visual-verdict p{margin:0}.media{overflow:hidden;margin:0;border:1px solid var(--line);border-radius:1.2rem;background:#050b14}.media img,.media video{display:block;width:100%;max-height:70vh;object-fit:contain;background:#050b14}.caption,.media-warning{padding:.8rem 1rem;color:var(--muted);border-top:1px solid var(--line)}.command-log{border:1px solid #24415f;border-radius:1rem;overflow:hidden;background:#050b14}.command-header,.command-meta{display:flex;flex-wrap:wrap;gap:.75rem;padding:.75rem 1rem;border-bottom:1px solid #24415f;color:var(--muted);background:#0d1726;font-size:.82rem}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:1rem}table{width:100%;border-collapse:collapse;background:var(--panel2)}th,td{padding:.85rem 1rem;text-align:left;border-bottom:1px solid var(--line);vertical-align:top;white-space:pre-line}footer{margin-top:28px;color:var(--muted)}@media(max-width:1000px){.layout{grid-template-columns:1fr}.side{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}main{padding:24px}.markdown ul,.markdown ol,.compare-cards{grid-template-columns:1fr}}
</style></head><body><div class="layout"><aside class="side"><div class="brand"><div class="eyebrow">Visual deck</div><h1>${escapeHtml(doc.title)}</h1><p class="muted">${escapeHtml(doc.subtitle ?? "Local explanatory deck")}</p></div><nav class="toc">${navItems}</nav></aside><main><header class="hero"><div class="eyebrow">Visual explanation</div><h1>${escapeHtml(doc.title)}</h1><p class="muted">${escapeHtml(doc.summary ?? doc.subtitle ?? "Generated Show Me artifact.")}</p><div class="badges"><span class="badge ${statusClass(doc.status)}">● ${escapeHtml(doc.status)}</span><span class="badge">Mode: ${escapeHtml(doc.mode)}</span><span class="badge">Presentation: visual-deck</span></div></header>${sections}<section class="visual-section" id="provenance"><div class="eyebrow">Provenance</div><h2>Artifact metadata</h2><p class="section-purpose">Enough context to audit where this deck came from without dumping the full chat transcript.</p><pre><code>${provenance}</code></pre></section><footer>Generated by Beislið show-me. Generated decks are local artifacts and should not be committed by default.</footer></main></div>${showMeLibraryScripts()}</body></html>`;
}

export function renderShowMeDocument(doc: ShowMeDocument): string {
	const presentation = doc.presentation ?? inferPresentation(doc.mode, doc.status);
	if (presentation === "visual-deck") return renderVisualDeck(doc);
	const navItems = doc.sections
		.map((section, index) => {
			const href = `${slug(section.title)}-${index + 1}`;
			return `<li><a href="#${href}">${String(index + 1).padStart(2, "0")} ${escapeHtml(section.title)}</a></li>`;
		})
		.join("\n");

	const sections = doc.sections
		.map((section, index) => {
			const id = `${slug(section.title)}-${index + 1}`;
			const blocks = section.blocks.map(renderBlock).join("\n");
			return `<section id="${id}">
				<p class="eyebrow">${String(index + 1).padStart(2, "0")}</p>
				<h3>${escapeHtml(section.title)}</h3>
				${section.purpose ? `<p class="section-purpose">${escapeHtml(section.purpose)}</p>` : ""}
				${blocks || `<div class="callout warning">No evidence added to this section yet.</div>`}
			</section>`;
		})
		.join("\n");

	const provenance = escapeHtml(JSON.stringify(doc.provenance ?? {}, null, 2));
	const status = escapeHtml(doc.status);
	const mode = escapeHtml(doc.mode);

	return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(doc.title)}</title>
${showMeLibraryHead()}
<style>
:root{color-scheme:dark;--bg:#08111f;--panel:#101b2d;--panel2:#16243a;--text:#eef5ff;--muted:#9fb0c8;--line:#26364e;--accent:#7c9cff;--good:#44d7a8;--warn:#f7c873;--bad:#ff7a90;--code:#07101d;--shadow:0 24px 80px rgba(0,0,0,.35)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font:16px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--text);background:radial-gradient(circle at top left,rgba(124,156,255,.22),transparent 28rem),radial-gradient(circle at 80% 10%,rgba(68,215,168,.12),transparent 24rem),var(--bg)}
code,pre{font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace}.shell{display:grid;grid-template-columns:18rem minmax(0,1fr);min-height:100vh}nav{position:sticky;top:0;height:100vh;padding:2rem 1.25rem;border-right:1px solid var(--line);background:rgba(8,17,31,.72);backdrop-filter:blur(18px);overflow-y:auto}.brand{padding:1rem;border:1px solid var(--line);border-radius:1.25rem;background:linear-gradient(180deg,rgba(22,36,58,.9),rgba(16,27,45,.72));box-shadow:var(--shadow)}.eyebrow{margin:0 0 .4rem;color:#7fb2ff;font-size:.72rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase}.brand h1{margin:0;font-size:1.35rem;line-height:1.1}.brand p{margin:.75rem 0 0;color:var(--muted);font-size:.88rem}.toc{margin:1.5rem 0 0;padding:0;list-style:none}.toc a{display:block;padding:.65rem .8rem;color:var(--muted);text-decoration:none;border-radius:.8rem}.toc a:hover{color:var(--text);background:rgba(124,156,255,.12)}main{width:min(100%,76rem);padding:3rem clamp(1.25rem,4vw,4rem) 5rem}.hero{padding:clamp(2rem,5vw,4rem);border:1px solid var(--line);border-radius:2rem;background:linear-gradient(135deg,rgba(22,36,58,.92),rgba(16,27,45,.72));box-shadow:var(--shadow)}.hero h2{max-width:14ch;margin:.35rem 0;font-size:clamp(2.4rem,7vw,5.2rem);line-height:.92;letter-spacing:-.06em}.summary{max-width:62rem;color:var(--muted);font-size:1.1rem}.badges{display:flex;flex-wrap:wrap;gap:.6rem;margin-top:1.25rem}.badge{display:inline-flex;align-items:center;gap:.45rem;padding:.45rem .7rem;border:1px solid var(--line);border-radius:999px;color:var(--muted);background:rgba(255,255,255,.04);font-size:.82rem;font-weight:700}.good{color:var(--good)}.warn{color:var(--warn)}.bad{color:var(--bad)}section{margin-top:2rem;padding:clamp(1.25rem,3vw,2rem);border:1px solid var(--line);border-radius:1.5rem;background:rgba(16,27,45,.86);box-shadow:0 18px 60px rgba(0,0,0,.22)}section h3{margin:0 0 .45rem;font-size:clamp(1.6rem,4vw,3rem);line-height:1;letter-spacing:-.04em}.section-purpose{margin:0 0 1.25rem;color:var(--muted)}.block{margin-top:1rem}.markdown{padding:1rem;border:1px solid var(--line);border-radius:1rem;background:rgba(255,255,255,.035)}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:1rem}table{width:100%;border-collapse:collapse;background:var(--panel2)}th,td{padding:.85rem 1rem;text-align:left;border-bottom:1px solid var(--line);vertical-align:top;white-space:pre-line}th{color:var(--muted);font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;background:rgba(255,255,255,.04)}tr:last-child td{border-bottom:0}pre{margin:0;padding:1rem;overflow:auto;border:1px solid var(--line);border-radius:1rem;color:#d8e6ff;background:var(--code)}.markdown-fallback{white-space:pre-wrap}.diff{border-color:#24415f}.diff-line{display:block;min-height:1.35em}.diff-add,.terminal-add{color:#9ff2c8;background:rgba(68,215,168,.10)}.diff-del,.terminal-del{color:#ffb3c0;background:rgba(255,122,144,.10)}.diff-hunk{color:#d8c2ff;background:rgba(124,156,255,.10)}.diff-meta{color:#8fb3ff}.terminal-heading{display:block;color:#8fb3ff;font-weight:800}.terminal-modified{color:#f7c873}.terminal-untracked{color:#d8c2ff}.mermaid,.diagram-source{padding:1rem;border:1px solid var(--line);border-radius:1rem;background:rgba(255,255,255,.035);overflow:auto}.code-label{display:inline-block;margin:0 0 .4rem;padding:.25rem .5rem;border-radius:.5rem;color:var(--muted);background:rgba(255,255,255,.06);font-size:.75rem}.callout{padding:1rem;border:1px solid rgba(124,156,255,.32);border-radius:1rem;background:rgba(124,156,255,.08)}.callout.warning{border-color:rgba(247,200,115,.34);color:#ffe6aa;background:rgba(247,200,115,.08)}.callout.danger{border-color:rgba(255,122,144,.34);color:#ffd1da;background:rgba(255,122,144,.08)}.callout.success{border-color:rgba(68,215,168,.34);color:#c8ffef;background:rgba(68,215,168,.08)}.verdict{display:flex;gap:1rem;align-items:flex-start;padding:1rem;border:1px solid var(--line);border-radius:1rem;background:rgba(255,255,255,.04)}.needs-capture{padding:1rem;border:1px dashed rgba(247,200,115,.52);border-radius:1rem;background:rgba(247,200,115,.08);color:#ffe6aa}.needs-capture div{display:flex;gap:.75rem;align-items:center}.needs-capture p{margin:.65rem 0 0}.capture-request{color:var(--muted)}.media{overflow:hidden;margin:0;border:1px solid var(--line);border-radius:1.2rem;background:#050b14}.media img,.media video{display:block;width:100%;max-height:70vh;object-fit:contain;background:#050b14}.caption{padding:.8rem 1rem;color:var(--muted);border-top:1px solid var(--line)}.media-warning{padding:.65rem 1rem;color:#ffe6aa;background:rgba(247,200,115,.08);border-top:1px solid rgba(247,200,115,.24);font-size:.85rem}.command-log{border:1px solid #24415f;border-radius:1rem;overflow:hidden;background:#050b14}.command-header{display:flex;flex-wrap:wrap;justify-content:space-between;gap:.5rem;padding:.75rem 1rem;border-bottom:1px solid #24415f;color:var(--muted);background:#0d1726;font-size:.82rem}.command-meta{display:flex;flex-wrap:wrap;gap:.75rem;padding:.65rem 1rem;color:var(--muted);font-size:.78rem;border-bottom:1px solid #16243a}.command-log pre{border:0;border-radius:0}.command-log pre.stderr{border-top:1px solid #3a2430;color:#ffd1da}footer{margin-top:2rem;color:var(--muted);font-size:.9rem}@media(max-width:840px){.shell{grid-template-columns:1fr}nav{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}main{padding-top:1.25rem}}
</style>
</head>
<body>
<div class="shell">
<nav aria-label="Deck navigation"><div class="brand"><p class="eyebrow">Show Me</p><h1>${escapeHtml(doc.title)}</h1><p>${escapeHtml(doc.subtitle ?? "Local visual evidence deck")}</p></div><ol class="toc">${navItems}</ol></nav>
<main>
<header class="hero"><p class="eyebrow">Visual evidence portfolio</p><h2>${escapeHtml(doc.title)}</h2><p class="summary">${escapeHtml(doc.summary ?? doc.subtitle ?? "Generated Show Me artifact.")}</p><div class="badges"><span class="badge ${statusClass(doc.status)}">● ${status}</span><span class="badge">Mode: ${mode}</span><span class="badge">Updated: ${escapeHtml(doc.updatedAt)}</span></div></header>
${sections}
<section id="provenance"><p class="eyebrow">Provenance</p><h3>Artifact metadata</h3><p class="section-purpose">Enough context to audit where this deck came from without dumping the full chat transcript.</p><pre><code>${provenance}</code></pre></section>
<footer>Generated by Beislið show-me. Generated decks are local artifacts and should not be committed by default.</footer>
</main>
</div>
${showMeLibraryScripts()}
</body>
</html>`;
}
