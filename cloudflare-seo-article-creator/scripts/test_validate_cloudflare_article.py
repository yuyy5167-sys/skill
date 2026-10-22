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
    def run_fixture(self, provider='zkai', course='elementary', mutation=None, new_design=False, traffic=False, approved_sapuri_fixture=False):
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
            elif provider == 'study_sapuri':
                link = {'href':'https://fixture.test/study-sapuri/'+course, 'tracking_image_src':'https://fixture.test/pixel/'+course+'.gif'}
                component, css = 'study_sapuri_cta_v1','shinken-zemi-cta'
            else:
                link = {'href': '//ck.jp.ap.valuecommerce.com/servlet/referral?sid=3613518&pid=892693444',
                        'tracking_image_src': '//ad.jp.ap.valuecommerce.com/servlet/gifbanner?sid=3613518&pid=892693444'}
                component, css = ('study_sapuri_cta_v1' if provider=='study_sapuri' else 'shinken_zemi_cta_v1'), 'shinken-zemi-cta'
            moment = {'placement_id': 'CTA-01', 'section_id': 'H2-01', 'section_heading': '教材を確認する',
                      'reader_question': 'どんな教材か', 'official_information_needed': '対象学年の教材見本',
                      'destination_purpose': '教材見本を確認する', 'lead_copy': '学年に合う教材と受講条件を公式サイトで確認できます。',
                      'placement_context': {'before':'教材と解説','after':'利用条件を確認する','rationale':'教材の範囲を説明した後に確認するため'}}
            manifest = {**link, 'provider': provider, 'target_course': course, 'presentation': 'cta_button',
                        'component_id': component, 'rel': 'nofollow', 'lead_text': moment['lead_copy'],
                        'button_text': '対象講座の資料を請求する',
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
</div>
'''
            if mutation == 'legacy_manifest':
                manifest['destination_text'] = 'リンク先：対象講座公式サイト'
            if mutation in ('destination_caption', 'plain_destination_caption'):
                caption = (f'<p class="{css}__destination">リンク先：対象講座公式サイト</p>'
                           if mutation == 'destination_caption' else '<p>リンク先：対象講座公式サイト</p>')
                body = body.replace('</div>', caption + '\n</div>')
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
            if mutation == 'rendered_only_caption':
                rendered.write_text(rendered.read_text().replace('</div>', '<small>リンク先：対象講座公式サイト</small></div>'))
            params = {'ArticlePath': str(article), 'ProjectRoot': str(root), 'ValidationMode': 'parent',
                      'ExpectedTitle': title, 'ExpectedArticleBusinessPurpose': 'conversion',
                      'ExpectedArticleProfileJson': json.dumps({'type': 'conversion_other', 'classification_reason': '教材選択の説明'}),
                      'ExpectedCtaStrategyJson': json.dumps({'policy_version':'minimum-two-v1','default_count': 3, 'planned_count': 2,
                        'count_mode': 'decreased', 'count_reason': '教材と受講条件の独立した疑問に答えるため2件',
                        'official_confirmation_moments': [moment]}),
                      'ExpectedAffiliateDisposition': 'eligible', 'ExpectedAffiliateProvider': provider,
                      'ExpectedAffiliateCourse': manifest['target_course'],
                      'ExpectedEmphasisPlanJson': json.dumps([{'section_id': 'H2-01', 'heading_text': '教材を確認する',
                        'exact_text': '教材と解説', 'role': 'conclusion'}]),
                      'ExpectedInternalLinkManifestJson': '{"new_links":[]}',
                      'ExpectedAffiliateLinkManifestJson': json.dumps({'links': [manifest]}),
                      'ExternalLinkPolicy': 'allow_task_required_only', 'RenderedHtmlPath': str(rendered)}
            if new_design:
                (root / 'src/lib').mkdir(parents=True, exist_ok=True)
                shutil.copy2(project / 'src/lib/articleDesignMetadata.mjs', root / 'src/lib/articleDesignMetadata.mjs')
                shutil.copy2(cover, article.parent / 'images/h2-01.webp')
                metadata = {'profile': 'cream-manga-mustard-v1', 'design': 'C', 'label': '比較の検証', 'showMaterialFinder': False}
                lead = '<figure class="edition-thumbnail">\n\n![教材の選び方](./images/cover.webp)\n\n</figure>\n\n導入です。'
                new_body = body.replace('## 教材を確認する', '## 教材を確認する\n\n![教材と解説](./images/h2-01.webp)')
                new_source = source.replace('draft: true', 'articleDesign: ' + json.dumps(metadata, ensure_ascii=False) + '\ndraft: true').replace(body, lead + '\n\n<!--article-lead-end-->\n\n' + new_body)
                article.write_text(new_source)
                new_html_body = rendered.read_text().replace('<article data-article-content>', '<div data-article-content>').replace('</article>', '</div>').replace('<h2>', '<h2 id="test">').replace('</h2>', '</h2><p><img src="/assets/h2.webp" alt="教材と解説"></p>', 1)
                rendered.write_text('<main class="article-page article-edition" data-article-design="C" data-article-design-origin="frontmatter" data-article-profile="cream-manga-mustard-v1"><div data-article-lead><figure class="edition-thumbnail"><img src="/assets/cover.webp" alt="教材の選び方"></figure><p>導入です。</p></div><nav class="edition-outline"><p class="edition-outline__title">目次</p><a href="#test"><span>01</span><span>教材を確認する</span><span>›</span></a></nav>' + new_html_body + '</main>')
                params.update({'RequireArticleDesign': True, 'ExpectedArticleDesignJson': json.dumps(metadata),
                  'ExpectedArticleDesignStateJson': json.dumps({'design_version':1,'ui_used_design_version':1,'thumbnail_accepted_design_version':1,'section_images_accepted_design_version':1})})

            moment2 = {**copy.deepcopy(moment), 'placement_id':'CTA-02','section_id':'H2-02',
                       'section_heading':'利用条件を確認する','reader_question':'継続条件はどうか',
                       'official_information_needed':'受講期間と継続条件','destination_purpose':'受講条件を確認する',
                       'lead_copy':'学習内容と合わせて受講期間・継続条件を公式サイトで確認できます。',
                       'placement_context':{'before':'料金と継続条件','after':'','rationale':'継続条件の説明が完結したため'}}
            manifest2 = {**copy.deepcopy(manifest), **{k:v for k,v in moment2.items() if k!='lead_copy'},
                         'lead_text':moment2['lead_copy'],'button_text':'受講条件を公式サイトで確認する'}
            source1 = article.read_text()
            cta1 = source1[source1.index('<div class="' + css):]
            cta2 = cta1.replace('CTA-01','CTA-02').replace(manifest['lead_text'],manifest2['lead_text']).replace(manifest['button_text'],manifest2['button_text'])
            image2='![教材と解説](./images/h2-01.webp)\n\n' if new_design else ''
            second_source = '\n\n## 利用条件を確認する\n\n'+image2+'**料金と継続条件**を確認することも大切です。\n\n'+cta2
            article.write_text(source1+second_source)
            current_html=rendered.read_text()
            second_html='<h2 id="conditions">利用条件を確認する</h2>'+('<p><img src="/assets/h2.webp" alt="教材と解説"></p>' if new_design else '')+'<p><strong>料金と継続条件</strong>を確認することも大切です。</p>'+cta2
            closing='</div></main>' if new_design else '</article>'
            index=current_html.rfind(closing)
            rendered.write_text(current_html[:index]+second_html+current_html[index:])
            if new_design:
                rendered.write_text(rendered.read_text().replace('</nav>','<a href="#conditions"><span>02</span><span>利用条件を確認する</span><span>›</span></a></nav>',1))
            params['ExpectedEmphasisPlanJson']=json.dumps([{'section_id':'H2-01','heading_text':'教材を確認する','exact_text':'教材と解説','role':'conclusion'},{'section_id':'H2-02','heading_text':'利用条件を確認する','exact_text':'料金と継続条件','role':'conclusion'}])
            all_moments=[moment,moment2];all_links=[manifest,manifest2]
            strategy={'policy_version':'minimum-two-v1','default_count':3,'planned_count':2,'count_mode':'decreased',
                      'first_cta_position_note':'短い検証原稿でも、最初に教材説明を完結してから案内するため','count_reason':'教材と受講条件の独立した確認目的が2つあるため','official_confirmation_moments':all_moments}
            if traffic:
                destination='/2026/10/02/study-sapuri-junior-20261002/'
                description='講座の内容と受講条件を確認できます。'
                bridge='学習内容と受講条件を整理してから、次の解説も参考にできます。'
                moment2['placement_context']['after']=bridge
                manifest2['placement_context']['after']=bridge
                article.write_text(article.read_text()+'\n\n'+bridge+'\n\n【内部リンクカード】\nURL: '+destination+'\n紹介文: '+description+'\n')
                current_html=rendered.read_text();index=current_html.rfind(closing)
                card='<p>'+bridge+'</p><a class="article-link-card" href="'+destination+'"><img src="/fixture.webp" alt="講座の解説">'+description+'</a>'
                rendered.write_text(current_html[:index]+card+current_html[index:])
                params.update({'ExpectedArticleBusinessPurpose':'traffic',
                  'ExpectedArticleProfileJson':json.dumps({'type':'traffic','classification_reason':'疑問へ回答して成約記事へ案内する'}),
                  'ExpectedInternalLinkManifestJson':json.dumps({'new_links':[{'href':destination,'destination_role':'conversion_direct','presentation':'image_card','required':True,'primary_destination':True,'card_description':description}]})})
                strategy.update({'default_count':2,'count_mode':'standard'})
            params['ExpectedCtaStrategyJson']=json.dumps(strategy)
            params['ExpectedAffiliateLinkManifestJson']=json.dumps({'links':all_links})
            if mutation=='one_cta':
                strategy.update({'planned_count':1,'official_confirmation_moments':[moment]})
                params['ExpectedCtaStrategyJson']=json.dumps(strategy)
                params['ExpectedAffiliateLinkManifestJson']=json.dumps({'links':[manifest]})
            if mutation=='old_policy':
                strategy.pop('policy_version')
                params['ExpectedCtaStrategyJson']=json.dumps(strategy)
            if mutation=='rendered_missing_card':
                rendered.write_text(rendered.read_text().replace(card,''))
            if mutation=='rendered_missing_cta':
                rendered.write_text(rendered.read_text().replace(cta2,''))
            if mutation=='rendered_duplicate_id':
                rendered.write_text(rendered.read_text().replace('CTA-02','CTA-01'))
            if mutation=='rendered_hidden':
                rendered.write_text(rendered.read_text().replace('data-placement-id="CTA-02"','data-placement-id="CTA-02" hidden'))
            if mutation=='context_mismatch':
                manifest2['placement_context']['before']='原稿に存在しない別の話題'
                params['ExpectedAffiliateLinkManifestJson']=json.dumps({'links':all_links})
            if mutation=='rendered_wrong_course':
                rendered.write_text(rendered.read_text().replace('data-course="'+manifest['target_course']+'"','data-course="wrong-course"'))
            if mutation=='double_buttons':
                rendered.write_text(rendered.read_text().replace('</a>','</a><a href="'+manifest['href']+'">追加ボタン</a>',1))
            if mutation == 'missing_manifest':
                del params['ExpectedAffiliateLinkManifestJson']
            driver = root / 'driver.ps1'
            validator_script=SCRIPT
            if approved_sapuri_fixture:
                isolated=root/'test-skills'
                shutil.copytree(SCRIPT.parent,isolated/'cloudflare-seo-article-creator/scripts',ignore=shutil.ignore_patterns('__pycache__'))
                shutil.copytree(SCRIPT.parents[2]/'article-internal-linker/references',isolated/'article-internal-linker/references')
                registry=isolated/'article-internal-linker/references/study-sapuri-affiliate-links.json'
                registry.write_text(json.dumps({'links':[{'target_course':course,**link,'approved_by_user':True,'user_instruction':'隔離テスト用の架空タグのみ','source_ref':'isolated-test-fixture'}]}))
                validator_script=isolated/'cloudflare-seo-article-creator/scripts/validate-cloudflare-article.ps1'
            script_path = str(validator_script).replace("'", "''")
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

    def test_new_comparison_design_preserves_all_provider_contracts(self):
        for provider in ('zkai', 'shinken_zemi', 'smile_zemi'):
            with self.subTest(provider=provider):
                report, code = self.run_fixture(provider=provider, new_design=True)
                self.assertEqual((code, report['status'], report['checks']['article_design']), (0, 'PASS', 'pass'), report)

    def test_comparison_design_traffic_has_two_cta_and_primary_card(self):
        report, code = self.run_fixture(new_design=True, traffic=True)
        self.assertEqual((code, report['status'], report['checks']['article_design']), (0, 'PASS', 'pass'), report)
        self.assertEqual(report['affiliate_markup_count'], 2, report)
        self.assertEqual(report['internal_link_card_count'], 1, report)

    def test_new_design_does_not_weaken_pixel_validation(self):
        report, code = self.run_fixture(mutation='wrong_pixel_size', new_design=True)
        self.assertNotEqual(code, 0, report)
        self.assertFalse(report['parent_contract_pass'], report)

    def test_registered_provider_url_and_pixel_pairs_cannot_be_forged(self):
        for provider in ('shinken_zemi','smile_zemi'):
            for mutation in ('wrong_course_url','wrong_tracking'):
                with self.subTest(provider=provider,mutation=mutation):
                    report,code=self.run_fixture(provider=provider,mutation=mutation)
                    self.assertNotEqual(code,0,report)
                    self.assertFalse(report['parent_contract_pass'],report)

    def test_registered_sapuri_courses_work_only_with_isolated_approved_fixture(self):
        for course in ('high','elementary_junior','toeic_basic'):
            with self.subTest(course=course):
                report,code=self.run_fixture(provider='study_sapuri',course=course,traffic=True,approved_sapuri_fixture=True)
                self.assertEqual((code,report['status'],report['parent_contract_pass']),(0,'PASS',True),report)

    def test_unregistered_study_sapuri_is_blocked(self):
        report,code=self.run_fixture(provider='study_sapuri')
        self.assertNotEqual(code,0,report)
        self.assertIn('スタディサプリ',str(report))

    def test_legacy_manifest_does_not_require_a_caption(self):
        report, code = self.run_fixture(mutation='legacy_manifest')
        self.assertEqual((code, report['status']), (0, 'PASS'), report)

    def test_destination_captions_are_rejected(self):
        for provider in ('zkai', 'shinken_zemi', 'smile_zemi'):
            for mutation in ('destination_caption', 'plain_destination_caption', 'rendered_only_caption'):
                with self.subTest(provider=provider, mutation=mutation):
                    report, code = self.run_fixture(provider=provider, mutation=mutation)
                    self.assertNotEqual(code, 0, report)
                    self.assertFalse(report['parent_contract_pass'], report)
                    self.assertIn('CTAボタン下のリンク先補足表記は禁止', str(report))


    def test_two_cta_contract_rejects_missing_duplicate_and_context_failures(self):
        for mutation in ('one_cta','old_policy','rendered_missing_cta','rendered_duplicate_id','rendered_hidden','context_mismatch','rendered_wrong_course','double_buttons','rendered_missing_card'):
            with self.subTest(mutation=mutation):
                report,code=self.run_fixture(mutation=mutation,traffic=True)
                self.assertNotEqual(code,0,report)
                self.assertFalse(report['parent_contract_pass'],report)

    def test_invalid_inputs_cannot_pass(self):
        for mutation in ('wrong_course_url', 'wrong_tracking', 'unsupported_course', 'missing_nofollow',
                         'wrong_pixel_size', 'unknown_frontmatter', 'missing_manifest'):
            with self.subTest(mutation=mutation):
                report, code = self.run_fixture(mutation=mutation)
                self.assertNotEqual(code, 0, report)
                self.assertFalse(report['parent_contract_pass'], report)


if __name__ == '__main__':
    unittest.main()
