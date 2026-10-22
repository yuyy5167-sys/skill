import test from 'node:test';
import assert from 'node:assert/strict';
import {auditPlacements} from './affiliate-placement-audit.mjs';
const t=value=>({type:'text',value});
const el=(tagName,properties={},children=[])=>({type:'element',tagName,properties,children});
function fixture(count=2){
 const flow=[],links=[];
 for(let i=1;i<=count;i++){
  const title='説明'+i,before='判断材料'+i,after=i===count?'':'説明'+(i+1),lead='公式で確認する内容'+i,button='講座の確認'+i;
  const link={provider:'shinken_zemi',target_course:'elementary',placement_id:'CTA-'+i,section_heading:title,href:'https://example.test/approved',tracking_image_src:'https://example.test/pixel',lead_text:lead,button_text:button,placement_context:{before,after,rationale:'独立した判断材料'+i+'の説明後'}};
  links.push(link);
  flow.push(el('h2',{},[t(title)]),el('p',{},[t(before)]),el('div',{className:['shinken-zemi-cta'],dataCourse:'elementary',dataPlacementId:link.placement_id},[
   el('p',{className:['shinken-zemi-cta__lead']},[t(lead)]),
   el('a',{className:['shinken-zemi-cta__button'],href:link.href,rel:['nofollow']},[
    el('img',{src:link.tracking_image_src,width:1,height:1,border:'0'}),t(button)])
  ]));
 }
 return {roots:[{type:'root',children:flow}],input:{article_business_purpose:'traffic',cta_strategy:{policy_version:'minimum-two-v1',default_count:2,planned_count:count},affiliate_manifest:{links}}};
}
const result=f=>auditPlacements(f.roots,f.input,'rendered');
test('two contextual placements sharing one URL pass',()=>assert.equal(result(fixture()).status,'PASS'));
test('three independent placements pass',()=>assert.equal(result(fixture(3)).status,'PASS'));
for(const count of [0,1]) test('minimum rejects '+count,()=>assert.equal(result(fixture(count)).status,'FAIL'));
test('duplicate IDs fail',()=>{const f=fixture();f.roots[0].children[5].properties.dataPlacementId='CTA-1';assert.equal(result(f).status,'FAIL');});
test('rendered loss fails',()=>{const f=fixture();f.roots[0].children.pop();assert.equal(result(f).status,'FAIL');});
test('two buttons in one CTA fail',()=>{const f=fixture();const n=f.roots[0].children[2];n.children.push(structuredClone(n.children[1]));assert.equal(result(f).status,'FAIL');});
test('wrong immediate context fails',()=>{const f=fixture();f.roots[0].children[1].children=[t('違う話題')];assert.equal(result(f).status,'FAIL');});
test('hidden attribute fails even when its value is empty',()=>{const f=fixture();f.roots[0].children[2].properties.hidden='';assert.equal(result(f).status,'FAIL');});
test('CTA outside selected body does not count',()=>{const f=fixture();f.roots=[{type:'root',children:f.roots[0].children.slice(0,3)}];assert.equal(result(f).status,'FAIL');});
test('consecutive internal card fails',()=>{const f=fixture();f.roots[0].children.splice(3,0,el('a',{className:['article-link-card']},[t('関連記事')]));assert.equal(result(f).status,'FAIL');});
test('wrong course fails',()=>{const f=fixture();f.roots[0].children[2].properties.dataCourse='high';assert.equal(result(f).status,'FAIL');});
test('old policy cannot bypass minimum',()=>{const f=fixture();delete f.input.cta_strategy.policy_version;assert.equal(result(f).status,'FAIL');});
test('late first CTA needs a reason, not forced relocation',()=>{const f=fixture();f.roots[0].children.unshift(el('p',{},[t('疑問への回答'.repeat(60))]));assert.equal(result(f).status,'FAIL');f.input.cta_strategy.first_cta_position_note='先に契約終了と必要な手続きの説明を完結するため';assert.equal(result(f).status,'PASS');});
test('tracking size stays fixed',()=>{const f=fixture();f.roots[0].children[2].children[1].children[0].properties.width=20;assert.equal(result(f).status,'FAIL');});

