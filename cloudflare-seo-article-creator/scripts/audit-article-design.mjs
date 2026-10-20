import { readFileSync, existsSync, statSync, realpathSync } from 'node:fs';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { dirname, join, resolve, sep, basename } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const excluded = new Set(['pre', 'code', 'script', 'style', 'textarea', 'template']);
const classes = (node) => {
  const value = node.properties?.className ?? [];
  return Array.isArray(value) ? value : String(value).split(/\s+/);
};
const prop = (node, camel, dashed) => node.properties?.[camel] ?? node.properties?.[dashed];
const text = (node) => node.type === 'text' ? node.value : (node.children ?? []).map(text).join('');
const elements = (node) => (node.children ?? []).filter((child) => child.type === 'element');
function find(node, predicate, out = []) {
  if (excluded.has(node.tagName)) return out;
  if (predicate(node)) out.push(node);
  for (const child of node.children ?? []) find(child, predicate, out);
  return out;
}

/** Structural validation only. Content, rights, business funnel and visual QA remain separate gates. */
export async function auditDesignText(input, source, renderedHtml) {
  const errors = [];
  const project = resolve(input.project_root);
  const require = createRequire(join(project, 'package.json'));
  const dependencyRoot = dirname(realpathSync(join(project, 'node_modules')));
  const tooling = createRequire(join(dependencyRoot, 'tooling/article-admin/package.json'));
  const yaml = tooling('yaml');
  const { markdownToHtml, markdownToMdast, htmlToHast } = await import(pathToFileURL(require.resolve('satteri')).href);
  const match = source.replace(/^\uFEFF/, '').match(/^---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/);
  if (!match) throw new Error('YAML frontmatter is required.');
  const data = yaml.parse(match[1], { uniqueKeys: true });
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('Frontmatter must be a mapping.');
  if (data.articleDesign === undefined) {
    if (input.require_design || input.expected_design) return { status: 'FAIL', errors: ['New articles require articleDesign.'] };
    return { status: 'PASS', applicability: 'legacy_unconfigured', errors: [] };
  }
  const { parseArticleDesign, splitArticleLead } = await import(pathToFileURL(join(project, 'src/lib/articleDesignMetadata.mjs')).href);
  let design;
  try { design = parseArticleDesign(data.articleDesign); }
  catch (error) { return { status: 'FAIL', errors: [error.message] }; }
  if (input.require_design && !input.expected_design) errors.push('Expected article design is required for new-article completion.');
  if (input.expected_design) {
    const expected = parseArticleDesign(input.expected_design);
    if (JSON.stringify(expected) !== JSON.stringify(design)) errors.push('articleDesign does not match the accepted design.');
  }
  const state = input.design_state;
  if (input.require_design && !state) errors.push('Accepted design_state is required for new-article completion.');
  if (state) {
    const keys = ['design_version', 'ui_used_design_version', 'thumbnail_accepted_design_version', 'section_images_accepted_design_version'];
    if (keys.some((key) => !Number.isInteger(state[key]) || state[key] < 1 || state[key] !== state.design_version)) errors.push('UI/image acceptance is missing or uses a stale design version.');
  }
  const body = source.replace(/^\uFEFF/, '').slice(match[0].length);
  const mdast = markdownToMdast(body);
  const html = markdownToHtml(body).html;
  let lead = '', content = '';
  try { [lead, content] = splitArticleLead(html); }
  catch (error) { errors.push(error.message); }
  const leadTree = htmlToHast(lead);
  const parsedBody = htmlToHast(content);
  const bodyTree = find(parsedBody, (n) => n.tagName === 'body')[0] ?? parsedBody;
  const sourceTree = htmlToHast(html);
  const registryPath = resolve(dirname(fileURLToPath(import.meta.url)), '../../study-article-ui-coder/references/cream-manga-component-registry.json');
  const registry = JSON.parse(readFileSync(registryPath, 'utf8'));
  if (registry.profile !== design.profile) throw new Error('UI class registry profile mismatch.');
  for (const node of find(sourceTree, (n) => n.type === 'element')) {
    for (const name of classes(node)) {
      if (name.startsWith('edition-') && !registry.body_classes.includes(name)) errors.push(`Unregistered or layout-owned class in source: ${name}`);
    }
  }
  const thumbnails = find(leadTree, (n) => classes(n).includes('edition-thumbnail'));
  const thumbImages = thumbnails.flatMap((n) => find(n, (c) => c.tagName === 'img'));
  if (thumbnails.length !== 1 || thumbImages.length !== 1) errors.push('Lead requires exactly one edition-thumbnail image.');
  if (find(bodyTree, (n) => classes(n).includes('edition-thumbnail')).length) errors.push('Thumbnail must be in the lead only.');
  const articleDir = dirname(resolve(input.article_path));
  function checkImage(image, role) {
    const src = image?.url ?? image?.properties?.src;
    const alt = image?.alt ?? image?.properties?.alt;
    if (typeof alt !== 'string' || !alt.trim()) errors.push(`${role} image needs meaningful alt.`);
    if (typeof src !== 'string' || !src.startsWith('./images/') || !src.endsWith('.webp')) {
      errors.push(`${role} must reference an article-local WebP image.`); return;
    }
    const path = resolve(articleDir, src);
    if (!path.startsWith(articleDir + sep) || !existsSync(path) || !statSync(path).isFile() || statSync(path).size === 0 || !realpathSync(path).startsWith(realpathSync(articleDir) + sep)) errors.push(`${role} image is missing or escapes the article: ${src}`);
    if (role === 'H2' && !/^h2-.+\.webp$/.test(basename(src))) errors.push(`H2 image filename must begin h2-: ${src}`);
    return src;
  }
  if (thumbImages[0]) {
    const src = checkImage(thumbImages[0], 'Thumbnail');
    if (src !== data.coverImage) errors.push('Lead thumbnail must match coverImage.');
    const coverInstances = find(sourceTree, (n) => n.tagName === 'img' && n.properties?.src === data.coverImage);
    if (coverInstances.length !== 1) errors.push('coverImage must appear exactly once in the source body.');
  }
  const h2Nodes = (mdast.children ?? []).filter((n) => n.type === 'heading' && n.depth === 2);
  const directH2s = elements(bodyTree).filter((n) => n.tagName === 'h2');
  const allH2s = find(sourceTree, (n) => n.tagName === 'h2');
  if (!h2Nodes.length || directH2s.length !== h2Nodes.length || allH2s.length !== h2Nodes.length) errors.push('All H2s must be direct Markdown headings in the body after the lead.');
  for (const heading of h2Nodes) {
    const index = mdast.children.indexOf(heading);
    const following = mdast.children[index + 1];
    if (following?.type !== 'paragraph' || following.children?.length !== 1 || following.children[0].type !== 'image') errors.push(`H2 requires an immediate Markdown image: ${text(heading)}`);
    else checkImage(following.children[0], 'H2');
  }
  if (design.design === 'E') {
    const nodes = elements(bodyTree);
    const answers = find(bodyTree, (n) => classes(n).includes('edition-answer'));
    if (answers.length !== h2Nodes.length) errors.push('E requires one explicit edition-answer per H2.');
    for (let i = 0; i < nodes.length; i++) {
      if (nodes[i].tagName !== 'h2') continue;
      const end = nodes.findIndex((n, j) => j > i && n.tagName === 'h2');
      const section = nodes.slice(i + 1, end < 0 ? nodes.length : end);
      if (section.filter((n) => classes(n).includes('edition-answer')).length !== 1) errors.push('Each E section must own its explicit direct answer.');
    }
  }
  let rendered = { status: 'NOT_CHECKED' };
  if (renderedHtml !== undefined) {
    const tree = htmlToHast(renderedHtml);
    const pages = find(tree, (n) => classes(n).includes('article-page'));
    const page = pages[0];
    if (pages.length !== 1 || prop(page ?? {}, 'dataArticleDesignOrigin', 'data-article-design-origin') !== 'frontmatter' || prop(page ?? {}, 'dataArticleDesign', 'data-article-design') !== design.design || prop(page ?? {}, 'dataArticleProfile', 'data-article-profile') !== design.profile) errors.push('Rendered profile/design/origin does not match frontmatter.');
    const leads = find(page ?? tree, (n) => prop(n, 'dataArticleLead', 'data-article-lead') !== undefined);
    const bodies = find(page ?? tree, (n) => prop(n, 'dataArticleContent', 'data-article-content') !== undefined);
    const outlines = find(page ?? tree, (n) => classes(n).includes('edition-outline'));
    if (leads.length !== 1 || bodies.length !== 1 || outlines.length !== 1) errors.push('Rendered lead/TOC/body must each occur once.');
    const ordered = find(page ?? tree, (n) => n === leads[0] || n === bodies[0] || n === outlines[0]);
    if (ordered[0] !== leads[0] || ordered[1] !== outlines[0] || ordered[2] !== bodies[0]) errors.push('Rendered order must be lead, TOC, body.');
    if (find(tree, (n) => n.type === 'comment' && n.value?.trim() === 'article-lead-end').length) errors.push('Authored boundary must be removed from final HTML.');
    const labels = find(outlines[0] ?? {}, (n) => classes(n).includes('edition-outline__title'));
    if (labels.length !== 1 || text(labels[0]).trim() !== '目次') errors.push('TOC must be labelled 目次 once.');
    const headings = find(bodies[0] ?? {}, (n) => n.tagName === 'h2');
    const links = find(outlines[0] ?? {}, (n) => n.tagName === 'a');
    if (headings.length !== h2Nodes.length || links.length !== headings.length) errors.push('Rendered TOC/H2 count mismatch.');
    headings.forEach((heading, i) => {
      const label = elements(links[i] ?? {})[1];
      if (links[i]?.properties?.href !== '#' + heading.properties?.id || text(label ?? {}).trim() !== text(heading).trim()) errors.push('TOC must follow actual H2 text, anchors and order.');
    });
    const finalThumb = find(leads[0] ?? {}, (n) => classes(n).includes('edition-thumbnail'));
    if (finalThumb.length !== 1 || find(finalThumb[0] ?? {}, (n) => n.tagName === 'img').length !== 1) errors.push('Rendered lead thumbnail missing or duplicated.');
    const finders = find(page ?? tree, (n) => classes(n).includes('edition-next'));
    if (finders.length !== Number(design.showMaterialFinder)) errors.push('End finder does not match showMaterialFinder.');
    if (design.design === 'E' && find(bodies[0] ?? {}, (n) => classes(n).includes('edition-answer')).length !== h2Nodes.length) errors.push('Rendered E answers missing or duplicated.');
    rendered = { status: errors.length ? 'FAIL' : 'PASS', h2_count: headings.length, toc_count: links.length };
  }
  return { status: errors.length ? 'FAIL' : 'PASS', profile: design.profile, design: design.design, source_h2_count: h2Nodes.length, rendered, errors };
}

export async function auditDesignFiles(input) {
  const bytes = readFileSync(input.article_path);
  const html = input.rendered_html_path ? readFileSync(input.rendered_html_path) : undefined;
  const result = await auditDesignText(input, bytes.toString('utf8'), html?.toString('utf8'));
  if (!bytes.equals(readFileSync(input.article_path)) || (html && !html.equals(readFileSync(input.rendered_html_path)))) throw new Error('Files changed during design audit.');
  return { ...result, article_sha256: sha(bytes), rendered_html_sha256: html ? sha(html) : null };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  try {
    const result = await auditDesignFiles(JSON.parse(readFileSync(0, 'utf8').replace(/^\uFEFF/, '')));
    console.log(JSON.stringify(result).replace(/[\u007f-\uffff]/g, (c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`));
    process.exitCode = result.status === 'PASS' ? 0 : 1;
  } catch (error) {
    console.log(JSON.stringify({ status: 'FAIL', error: error.message }));
    process.exitCode = 1;
  }
}
