"""Run real parent validation for approved CTA providers in an isolated fixture.

Set ARTICLE_TEST_PROJECT_ROOT to the existing Astro project and
ARTICLE_TEST_WORK_ROOT to this task's temporary directory. No site files change.
"""

import copy
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('validate-cloudflare-article.ps1')
REGISTRY = SCRIPT.parents[2] / 'article-internal-linker/references/zkai-affiliate-links.json'


class ParentValidation(unittest.TestCase):
    def run_fixture(self, provider='zkai', course='elementary', mutation=None):
        project = Path(os.environ['ARTICLE_TEST_PROJECT_ROOT'])
        with tempfile.TemporaryDirectory(dir=os.environ['ARTICLE_TEST_WORK_ROOT'], prefix='parent-test-') as work:
            root = Path(work)
            article = root / 'src/content/blog/example/index.md'
            article.parent.mkdir(parents=True)
            (root / 'package.json').write_text('{"type":"module"}\n')
            (root / 'node_modules').symlink_to(project / 'node_modules', target_is_directory=True)
            (article.parent / 'images').mkdir()
            cover = next(project.glob('src/content/blog/*/images/*.webp'))
            shutil.copy2(cover, article.parent / 'images/cover.webp')
            if provider == 'zkai':
                link = next(copy.deepcopy(x) for x in json.loads(REGISTRY.read_text())['links'] if x['target_course'] == course)
                component, css = 'zkai_cta_v1', 'shinken-zemi-cta'
            elif provider == 'smile_zemi':
                link = {'href': 'https://px.a8.net/svt/ejp?a8mat=3H9NZ4+HVBQA+2P76+60WN6',
                        'tracking_image_src': 'https://www16.a8.net/0.gif?a8mat=3H9NZ4+HVBQA+2P76+60WN6'}
                component, css = 'smile_zemi_cta_v1', 'smile-zemi-cta'
            else:
                link = {'href': '//ck.jp.ap.valuecommerce.com/servlet/referral?sid=3613518&pid=892693444',
                        'tracking_image_src': '//ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3613518&pid=892693444'}
                component, css = 'shinken_zemi_cta_v1', 'shinken-zemi-cta'
            moment = {'placement_id': 'CTA-01', 'section_id': 'H2-01', 'section_heading': '教材を確認する',
                      'reader_question': 'どんな教材か', 'official_information_needed': '対象学年の教材見本',
                      'destination_purpose': '教材見本を確認する', 'lead_copy': '学年に合う教材と受講条件を公式サイトで確認できます。'}
            manifest = {**link, 'provider': provider, 'target_course': course, 'presentation': 'cta_button',
                        'component_id': component, 'rel': 'nofollow', 'lead_text': moment['lead_copy'],
                        'button_text': '対象講座の資料を請求する', 'destination_text': 'リンク先：対象講座公式サイト',
                        **{k: v for k, v in moment.items() if k != 'lead_copy'}}
            if mutation in ('wrong_course_url', 'wrong_tracking', 'unsupported_course'):
                if mutation == 'wrong_course_url':
                    manifest['href'] = json.loads(REGISTRY.read_text())['links'][1]['href']
                elif mutation == 'wrong_tracking':
                    manifest['tracking_image_src'] = json.loads(REGISTRY.read_text())['links'][1]['tracking_image_src']
                else:
                    manifest['target_course'] = 'preschool'
            body = f'''## 教材を確認する

**教材と解説**を確認してから受講を検討できます。

<div class="{css}" data-course="{manifest['target_course']}" data-placement-id="CTA-01">
  <p class="{css}__lead">{manifest['lead_text']}</p>
  <a class="{css}__button" href="{html.escape(manifest['href'], quote=True)}" rel="nofollow"><img src="{html.escape(manifest['tracking_image_src'], quote=True)}" width="1" height="1" border="0" alt="">{manifest['button_text']}</a>
  <p class="{css}__destination">{manifest['destination_text']}</p>
</div>
'''
            if mutation == 'missing_nofollow':
                body = body.replace('rel="nofollow"', '')
            if mutation == 'wrong_pixel_size':
                body = body.replace('width="1"', 'width="20"')
            title = '対象講座の教材を確認する'
            source = f'''---
title: '{title}'
date: '2026-10-17'
categories: ['Z会']
coverImage: './images/cover.webp'
promotionDisclosure: true
compactBody: true
draft: true
---

{body}'''
            if mutation == 'unknown_frontmatter':
                source = source.replace('draft: true', 'draft: true\nunknownSetting: true')
            article.write_text(source)
            rendered = root / 'article.html'
            rendered.write_text('<article data-article-content><h2>教材を確認する</h2><p><strong>教材と解説</strong>を確認できます。</p>' + body[body.index('<div'):] + '</article>')
            params = {'ArticlePath': str(article), 'ProjectRoot': str(root), 'ValidationMode': 'parent',
                      'ExpectedTitle': title, 'ExpectedArticleBusinessPurpose': 'conversion',
                      'ExpectedArticleProfileJson': json.dumps({'type': 'conversion_other', 'classification_reason': '教材選択の説明'}),
                      'ExpectedCtaStrategyJson': json.dumps({'default_count': 3, 'planned_count': 1,
                        'count_mode': 'decreased', 'count_reason': '単一の疑問に答える短い記事で確認場面が1件',
                        'official_confirmation_moments': [moment]}),
                      'ExpectedAffiliateDisposition': 'eligible', 'ExpectedAffiliateProvider': provider,
                      'ExpectedAffiliateCourse': manifest['target_course'],
                      'ExpectedEmphasisPlanJson': json.dumps([{'section_id': 'H2-01', 'heading_text': '教材を確認する',
                        'exact_text': '教材と解説', 'role': 'conclusion'}]),
                      'ExpectedInternalLinkManifestJson': '{"new_links":[]}',
                      'ExpectedAffiliateLinkManifestJson': json.dumps({'links': [manifest]}),
                      'ExternalLinkPolicy': 'allow_task_required_only', 'RenderedHtmlPath': str(rendered)}
            if mutation == 'missing_manifest':
                del params['ExpectedAffiliateLinkManifestJson']
            driver = root / 'driver.ps1'
            script_path = str(SCRIPT).replace("'", "''")
            driver.write_text("$params = ConvertFrom-Json -AsHashtable ([Console]::In.ReadToEnd())\n& '" + script_path + "' @params\nexit $LASTEXITCODE\n")
            env = {**os.environ, 'POWERSHELL_TELEMETRY_OPTOUT': '1'}
            result = subprocess.run(['pwsh', '-NoLogo', '-NoProfile', '-NonInteractive', '-File', str(driver)],
                                    input=json.dumps(params), text=True, capture_output=True, env=env, timeout=40)
            self.assertTrue(result.stdout.strip().startswith('{'), result.stdout + result.stderr)
            return json.loads(result.stdout), result.returncode

    def test_approved_zkai_courses_pass(self):
        for course in ('elementary', 'junior_high', 'high'):
            with self.subTest(course=course):
                report, code = self.run_fixture(course=course)
                self.assertEqual((code, report['status'], report['parent_contract_pass']), (0, 'PASS', True), report)

    def test_existing_providers_still_pass(self):
        for provider in ('shinken_zemi', 'smile_zemi'):
            with self.subTest(provider=provider):
                report, code = self.run_fixture(provider=provider)
                self.assertEqual((code, report['status']), (0, 'PASS'), report)

    def test_invalid_inputs_cannot_pass(self):
        for mutation in ('wrong_course_url', 'wrong_tracking', 'unsupported_course', 'missing_nofollow',
                         'wrong_pixel_size', 'unknown_frontmatter', 'missing_manifest'):
            with self.subTest(mutation=mutation):
                report, code = self.run_fixture(mutation=mutation)
                self.assertNotEqual(code, 0, report)
                self.assertFalse(report['parent_contract_pass'], report)


if __name__ == '__main__':
    unittest.main()
