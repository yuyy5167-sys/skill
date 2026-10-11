import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const siteOrigin = 'https://xn--5ckip8c4fq970ahbya2o7acu2a.com';
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
const excluded = new Set(['script', 'style', 'pre', 'code', 'template', 'textarea']);

function normalizedUrl(href) {
  return new URL(String(href).trim(), `${siteOrigin}/`);
}

function policySets(input) {
  if (!Array.isArray(input.affiliate_manifest?.links)) {
    throw new Error('承認済み affiliate_manifest.links を渡してください。CTAなしの場合は空配列です。');
  }
  const affiliates = new Set(input.affiliate_manifest.links.map(link => {
    if (typeof link.href !== 'string' || !/^(?:https?:)?\/\//i.test(link.href)) {
      throw new Error('承認済みアフィリエイトマニフェストのhrefが不正です。');
    }
    const url = normalizedUrl(link.href.replace(/&amp;/g, '&'));
    if (!['http:', 'https:'].includes(url.protocol) || url.origin === siteOrigin) {
      throw new Error('アフィリエイトhrefは承認済み外部HTTP(S) URLが必要です。');
    }
    return url.href;
  }));
  const exceptions = new Set();
  for (const entry of input.allowed_external_links ?? []) {
    if (entry.approved_by_user !== true || !entry.user_instruction?.trim() || !entry.source_ref?.trim() || !entry.href?.trim()) {
      throw new Error('外部リンク例外には、URL・ユーザーの明示許可原文・発言出典が必要です。AIの必要性判断だけでは許可できません。');
    }
    const url = normalizedUrl(entry.href);
    if (!['http:', 'https:'].includes(url.protocol) || url.origin === siteOrigin) throw new Error('外部リンク例外URLが不正です。');
    exceptions.add(url.href);
  }
  return { affiliates, exceptions };
}

function inspectRoots(roots, policy, phase) {
  const links = [];
  const violations = [];
  const inspectHref = (href, kind = 'link') => {
    if (!href?.trim()) return;
    let url;
    try { url = normalizedUrl(href); }
    catch { violations.push({ phase, href, kind, reason: 'invalid_url' }); return; }
    let classification = 'disallowed';
    if (['http:', 'https:'].includes(url.protocol) && url.origin === siteOrigin) classification = 'internal';
    else if (policy.affiliates.has(url.href)) classification = 'affiliate';
    else if (policy.exceptions.has(url.href)) classification = 'user_approved_exception';
    if (kind === 'link' || kind === 'card') links.push({ href, classification });
    if (classification === 'disallowed') violations.push({ phase, href, kind, reason: 'unapproved_external_destination' });
  };
  function walk(node, insideLink = false) {
    if (node.type === 'comment' || excluded.has(node.tagName)) return;
    if (node.tagName === 'a' || node.tagName === 'area') {
      inspectHref(String(node.properties?.href ?? ''));
      insideLink = true;
    }
    if (node.type === 'text' && !insideLink) {
      // 裸URLを調査記録の代わりに本文へ残す抜け道も検出する。画像src・計測画像は対象外。
      for (const match of node.value.matchAll(/(?:https?:\/\/|\/\/)[^\s<>「」『』]+/giu)) {
        inspectHref(match[0], 'visible_url');
      }
    }
    for (const child of node.children ?? []) walk(child, insideLink);
  }
  for (const root of roots) walk(root);
  return { links, violations, inspectHref };
}

export async function auditText(input, source, renderedHtml) {
  const policy = policySets(input);
  const resolver = createRequire(join(resolve(input.project_root), 'package.json'));
  const { markdownToHtml, htmlToHast } = await import(pathToFileURL(resolver.resolve('satteri')).href);
  const body = source.replace(/^\uFEFF/, '').replace(/^---[ \t]*\r?\n[\s\S]*?\r?\n---[ \t]*(?:\r?\n|$)/, '');
  const tree = htmlToHast(markdownToHtml(body).html);
  const sourceAudit = inspectRoots([tree], policy, 'source');
  // サイト独自のカードはMarkdownパーサーではアンカーにならないため、別途URLを検査する。
  for (const match of body.matchAll(/^\s*【内部リンクカード】\s*\r?\n\s*URL:\s*([^\r\n]+)/gm)) {
    sourceAudit.inspectHref(match[1].trim(), 'card');
  }
  let renderedAudit;
  if (renderedHtml !== undefined) {
    const roots = [];
    function select(node) {
      const p = node.properties ?? {};
      if ('dataArticleContent' in p || 'data-article-content' in p || 'dataArticleLead' in p || 'data-article-lead' in p) {
        roots.push(node);
        return;
      }
      for (const child of node.children ?? []) select(child);
    }
    select(htmlToHast(renderedHtml));
    if (!roots.length) throw new Error('最終HTMLに記事本文領域がありません。空の検査結果を合格にできません。');
    renderedAudit = inspectRoots(roots, policy, 'rendered');
  }
  const violations = [...sourceAudit.violations, ...(renderedAudit?.violations ?? [])];
  const summarize = audit => audit ? {
    status: audit.violations.length ? 'FAIL' : 'PASS',
    internal: audit.links.filter(link => link.classification === 'internal').length,
    affiliate: audit.links.filter(link => link.classification === 'affiliate').length,
    user_approved_exception: audit.links.filter(link => link.classification === 'user_approved_exception').length,
    links: audit.links,
  } : { status: 'NOT_CHECKED' };
  return { status: violations.length ? 'FAIL' : 'PASS', source: summarize(sourceAudit), rendered: summarize(renderedAudit),
    disallowed_external_link_count: violations.length, violations };
}

export async function auditFiles(input) {
  const bytes = readFileSync(input.article_path);
  const html = input.rendered_html_path ? readFileSync(input.rendered_html_path) : undefined;
  const result = await auditText(input, bytes.toString('utf8'), html?.toString('utf8'));
  if (!bytes.equals(readFileSync(input.article_path)) || (html && !html.equals(readFileSync(input.rendered_html_path)))) {
    throw new Error('検査中に対象ファイルが変更されました。再検査が必要です。');
  }
  return { ...result, article_path: resolve(input.article_path), article_sha256: sha256(bytes),
    rendered_html_path: html ? resolve(input.rendered_html_path) : null,
    rendered_html_sha256: html ? sha256(html) : null };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    const result = await auditFiles(JSON.parse(readFileSync(0, 'utf8').replace(/^\uFEFF/, '')));
    // Windows PowerShellでも日本語の結果をJSONとして損失なく読み戻す。
    console.log(JSON.stringify(result).replace(/[\u007f-\uffff]/g, c => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`));
    process.exitCode = result.status === 'PASS' ? 0 : 1;
  } catch (error) {
    console.log(JSON.stringify({ status: 'FAIL', error: error.message }));
    process.exitCode = 1;
  }
}
