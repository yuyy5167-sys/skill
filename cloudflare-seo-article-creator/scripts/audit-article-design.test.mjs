import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { auditDesignText } from './audit-article-design.mjs';

const project = resolve(process.env.ARTICLE_TEST_PROJECT_ROOT);
const require = createRequire(join(project, 'package.json'));
const {markdownToHtml} = await import(pathToFileURL(require.resolve('satteri')).href);
const temporary = mkdtempSync(join(resolve(process.env.ARTICLE_TEST_WORK_ROOT), 'design-audit-'));
mkdirSync(join(temporary, 'images'));
for (const name of ['cover.webp','h2-01.webp','h2-02.webp']) writeFileSync(join(temporary, 'images', name), 'fixture-image; asset bytes validated by the image gate');
const state = {design_version:1,ui_used_design_version:1,thumbnail_accepted_design_version:1,section_images_accepted_design_version:1};
function fixture(design = 'A') {
 const meta = {profile:'cream-manga-mustard-v1',design,label:'検証記事',showMaterialFinder:false};
 const lead = '<figure class="edition-thumbnail">\n\n![教材を選ぶ親子](./images/cover.webp)\n\n</figure>\n\n導入本文です。';
 const answer = design === 'E' ? '<div class="edition-answer">\n\n手続き先を先に確認します。\n\n</div>' : '回答本文です。';
 const body = `## 教材の選び方\n\n![選び方の比較](./images/h2-01.webp)\n\n${answer}\n\n## 教材の確認手順\n\n![確認順序](./images/h2-02.webp)\n\n${answer}`;
 const source = `---\ntitle: 検証記事\ncoverImage: './images/cover.webp'\narticleDesign: ${JSON.stringify(meta)}\n---\n${lead}\n\n<!--article-lead-end-->\n\n${body}`;
 const renderedBody=markdownToHtml(body).html.replace('<h2>教材の選び方</h2>','<h2 id="one">教材の選び方</h2>').replace('<h2>教材の確認手順</h2>','<h2 id="two">教材の確認手順</h2>');
 const html=`<main class="article-page article-edition" data-article-design="${design}" data-article-design-origin="frontmatter" data-article-profile="${meta.profile}"><div data-article-lead>${markdownToHtml(lead).html}</div><nav class="edition-outline"><p class="edition-outline__title">目次</p><a href="#one"><span>01</span><span>教材の選び方</span><span>›</span></a><a href="#two"><span>02</span><span>教材の確認手順</span><span>›</span></a></nav><div data-article-content>${renderedBody}</div></main>`;
 return {source,html,input:{project_root:project,article_path:join(temporary,'index.md'),require_design:true,expected_design:meta,design_state:{...state}}};
}
for (const d of ['A','B','C','D','E']) test(`new ID ${d} passes without ID dictionary`,async()=>{const f=fixture(d); const r=await auditDesignText(f.input,f.source,f.html);assert.equal(r.status,'PASS',JSON.stringify(r));});
const negatives={
 'unknown design':s=>s.replace('"design":"A"','"design":"F"'),
 'unknown profile':s=>s.replace('cream-manga-mustard-v1','unknown'),
 'string finder':s=>s.replace('"showMaterialFinder":false','"showMaterialFinder":"false"'),
 'unknown nested key':s=>s.replace('"showMaterialFinder":false','"showMaterialFinder":false,"extra":true'),
 'missing boundary':s=>s.replace('<!--article-lead-end-->',''),
 'double boundary':s=>s.replace('<!--article-lead-end-->','<!--article-lead-end-->\n\n<!--article-lead-end-->'),
 'unknown edition class':s=>s+'\n\n<div class="edition-imaginary">text</div>',
 'layout-owned class':s=>s+'\n\n<div class="edition-next">text</div>',
 'missing H2 image':s=>s.replace('![選び方の比較](./images/h2-01.webp)',''),
 'missing asset':s=>s.replace('./images/h2-01.webp','./images/h2-missing.webp'),
 'empty alt':s=>s.replace('![選び方の比較]','![]'),
 'duplicate thumbnail':s=>s.replace('導入本文です。','<figure class="edition-thumbnail"><img src="./images/cover.webp" alt="dup"></figure>'),
 'wrapped H2':s=>s.replace('## 教材の選び方','<div class="edition-note">\n\n## 教材の選び方').replace('回答本文です。','回答本文です。\n\n</div>'),
};
for(const [name,mutate]of Object.entries(negatives))test(name,async()=>{const f=fixture();const r=await auditDesignText(f.input,mutate(f.source),f.html);assert.equal(r.status,'FAIL',name);});
test('code and escaped boundary examples do not count',async()=>{const f=fixture(); f.source=f.source.replace('導入本文です。','導入本文です。\n\n```html\n<!--article-lead-end-->\n```\n\n&lt;!--article-lead-end--&gt;');const r=await auditDesignText(f.input,f.source);assert.equal(r.status,'PASS',JSON.stringify(r));});
test('stale image acceptance fails',async()=>{const f=fixture();f.input.design_state.thumbnail_accepted_design_version=2;assert.equal((await auditDesignText(f.input,f.source)).status,'FAIL');});
test('missing current design state fails',async()=>{const f=fixture();delete f.input.design_state;assert.equal((await auditDesignText(f.input,f.source)).status,'FAIL');});
test('actual H2 order/text must match TOC',async()=>{const f=fixture();assert.equal((await auditDesignText(f.input,f.source,f.html.replace('<span>教材の選び方</span>','<span>古い見出し</span>'))).status,'FAIL');});
test('E note cannot stand in for explicit answer',async()=>{const f=fixture('E');assert.equal((await auditDesignText(f.input,f.source.replaceAll('edition-answer','edition-note'),f.html)).status,'FAIL');});
test('end finder flag must match',async()=>{const f=fixture();assert.equal((await auditDesignText(f.input,f.source,f.html.replace('</main>','<aside class="edition-next">診断</aside></main>'))).status,'FAIL');});
test('legacy unconfigured article retains old contract',async()=>{const f=fixture();const s='---\ntitle: legacy\n---\n## 本文\n本文';const r=await auditDesignText({...f.input,require_design:false,expected_design:undefined,design_state:undefined},s);assert.equal(r.applicability,'legacy_unconfigured');assert.equal(r.status,'PASS');});
test.after(()=>rmSync(temporary,{recursive:true}));
