import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { auditText } from './audit-article-links.mjs';

const projectRoot = process.env.ARTICLE_LINK_TEST_PROJECT_ROOT ?? 'C:\\AIフォルダ\\ブログ\\site';
const origin = 'https://xn--5ckip8c4fq970ahbya2o7acu2a.com';
const affiliate = 'https://ck.jp.ap.valuecommerce.com/servlet/referral?sid=3613518&pid=892693444';
const input = { project_root: projectRoot, affiliate_manifest: { links: [{ href: affiliate }] } };
const official = 'https://sho.benesse.co.jp/';
const research = 'https://www.jstage.jst.go.jp/article/example/';

for (const [name, body] of [
  ['公式通常リンク', `[公式](${official})`],
  ['研究出典リンク', `[研究](${research})`],
  ['参照形式リンク', `[公式][official]\n\n[official]: ${official}`],
  ['脚注の外部リンク', `説明[^1]\n\n[^1]: [根拠](${research})`],
  ['オートリンク', `<${official}>`],
  ['裸URL', `確認先 ${official}`],
  ['HTMLボタン', `<a class="button" href="${official}">確認</a>`],
  ['引用符なしHTML', `<a href=${official}>確認</a>`],
  ['プロトコル省略', '<a href="//sho.benesse.co.jp/">公式</a>'],
  ['画像リンク', `[![説明](./images/photo.webp)](${official})`],
  ['内部カードに外部URL', `【内部リンクカード】\nURL: ${official}\n紹介文: 確認`],
  ['自サイトと同じパスの別ホスト', '[確認](https://example.org/2023/08/30/article/)'],
  ['自サイトに似たホスト', `[確認](${origin}.example.org/)`],
  ['同じASPの未承認PID', `<a href="${affiliate.replace('892693444', '000000000')}">資料</a>`],
]) {
  test(`${name}を検出する`, async () => {
    const result = await auditText(input, body);
    assert.equal(result.status, 'FAIL');
    assert.ok(result.disallowed_external_link_count > 0);
  });
}

test('承認CTA・自サイト相対/絶対リンク・画像・計測画像を維持する', async () => {
  const body = `[内部](/2023/08/30/article/)\n\n[内部](${origin}/2023/08/30/article/)\n\n<a href="${affiliate.replace('https:', '').replace('&', '&amp;')}"><img src="https://ad.jp.ap.valuecommerce.com/pixel" width="1" height="1">公式</a>\n\n![写真](https://images.example.org/photo.webp)`;
  const result = await auditText(input, body);
  assert.equal(result.status, 'PASS');
  assert.equal(result.source.affiliate, 1);
  assert.equal(result.source.internal, 2);
  assert.equal(result.rendered.status, 'NOT_CHECKED');
});

test('原稿にリンクがなくても最終HTMLに追加されたリンクを検出する', async () => {
  const html = `<header><a href="https://nav.example.org/">共通ナビ</a></header><div data-article-content><a href="${official}">公式</a></div>`;
  const result = await auditText(input, '本文', html);
  assert.equal(result.source.status, 'PASS');
  assert.equal(result.rendered.status, 'FAIL');
  assert.equal(result.disallowed_external_link_count, 1);
});

test('ブラウザで導入が移動した本文領域も検査する', async () => {
  const result = await auditText(input, '本文', `<div data-article-lead><a href="${official}">確認</a></div><div data-article-content>本文</div>`);
  assert.equal(result.rendered.status, 'FAIL');
});

test('本文外のナビは対象外・承認済み本文は両方合格する', async () => {
  const body = `<a href="${affiliate}">資料</a>`;
  const result = await auditText(input, body, `<nav><a href="${official}">共通</a></nav><div data-article-content>${body}</div>`);
  assert.equal(result.source.status, 'PASS');
  assert.equal(result.rendered.status, 'PASS');
});

test('本文領域がないHTMLを空の合格にしない', async () => {
  await assert.rejects(auditText(input, '本文', '<main>別ページ</main>'), /本文領域/);
});

test('AI理由文だけの外部例外は拒否する', async () => {
  await assert.rejects(auditText({ ...input, allowed_external_links: [{ href: official, reason: '手続きに必要' }] }, `[公式](${official})`), /明示許可原文/);
});

test('ユーザー明示許可はその完全一致URLだけに限定する', async () => {
  const permitted = { ...input, allowed_external_links: [{ href: official, approved_by_user: true, user_instruction: 'テスト用の明示許可', source_ref: 'test:explicit-permission' }] };
  assert.equal((await auditText(permitted, `[公式](${official})`)).status, 'PASS');
  assert.equal((await auditText(permitted, `[別のURL](${official}faq/)`)).status, 'FAIL');
});

test('許可マニフェスト未提供を推測補完しない', async () => {
  await assert.rejects(auditText({ project_root: projectRoot }, '本文'), /affiliate_manifest/);
});

test('検査対象外のコメント・コード・画像srcをリンク扱いしない', async () => {
  const result = await auditText(input, `<!-- ${official} -->\n\n\`${official}\`\n\n![写真](${official}image.webp)`);
  assert.equal(result.status, 'PASS');
});

test('親検査は外部リンク引数省略時も検出し、旧not_applicable指定も通さない', () => {
  const fixture = mkdtempSync(join(tmpdir(), 'article-link-regression-'));
  try {
    const article = join(fixture, 'index.md');
    writeFileSync(article, `---\ntitle: "検査用"\ndate: 2026-09-22\ndraft: true\n---\n\n## 見出し\n\n[公式](${official})\n`);
    const script = join(dirname(fileURLToPath(import.meta.url)), 'validate-cloudflare-article.ps1');
    for (const extra of [[], ['-ExternalLinkPolicy', 'not_applicable']]) {
      const run = spawnSync('pwsh', ['-NoProfile', '-File', script, '-ArticlePath', article, '-ProjectRoot', projectRoot, ...extra], { encoding: 'utf8' });
      assert.equal(run.error, undefined);
      assert.equal(run.status, 1, run.stderr || run.stdout);
      const report = JSON.parse(run.stdout.replace(/^\uFEFF/, ''));
      assert.equal(report.checks.external_links, 'fail');
      assert.ok(report.disallowed_external_link_count >= 1);
    }
    const parent = spawnSync('pwsh', ['-NoProfile', '-File', script, '-ArticlePath', article, '-ProjectRoot', projectRoot, '-ValidationMode', 'parent'], { encoding: 'utf8' });
    const parentReport = JSON.parse(parent.stdout.replace(/^\uFEFF/, ''));
    assert.equal(parent.status, 1);
    assert.equal(parentReport.parent_contract_pass, false);
    assert.ok(parentReport.errors.some(error => error.includes('RenderedHtmlPath')));
  } finally {
    // mkdtempが作成した検査専用ディレクトリだけを片付ける。
    rmSync(fixture, { recursive: true, force: true });
  }
});
