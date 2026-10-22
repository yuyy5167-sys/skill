// Deterministic placement checks. Semantic fit still requires the link skill's audit.
const norm = value => String(value ?? '').replace(/\s+/gu, '');
const excluded = new Set(['script','style','pre','code','template','textarea']);
const rootsByProvider = {shinken_zemi:'shinken-zemi-cta', smile_zemi:'smile-zemi-cta', zkai:'shinken-zemi-cta', study_sapuri:'shinken-zemi-cta'};
const classes = node => Array.isArray(node.properties?.className) ? node.properties.className : String(node.properties?.className ?? '').split(/\s+/);
const text = node => node.type === 'comment' || excluded.has(node.tagName) || node.properties?.ariaHidden === 'true' ? '' : node.type === 'text' ? node.value : (node.children ?? []).map(text).join('');
const prop = (node, camel, dashed) => node.properties?.[camel] ?? node.properties?.[dashed];
const descendants = (node, tag) => (node.children ?? []).flatMap(child => [...(child.tagName === tag ? [child] : []), ...descendants(child,tag)]);
const url = value => String(value ?? '').replace(/&amp;/g,'&').trim();
const concealed = node => ('hidden' in (node.properties ?? {})) || node.properties?.ariaHidden === 'true' || /(?:display\s*:\s*none|visibility\s*:\s*hidden)/i.test(node.properties?.style ?? '');

export function auditPlacements(roots, input, phase) {
  const errors = [];
  const fail = message => errors.push(phase + ': ' + message);
  const strategy = input.cta_strategy;
  const links = input.affiliate_manifest?.links;
  if (!['conversion','traffic'].includes(input.article_business_purpose)) fail('事業目的が未確定です');
  if (!strategy || strategy.policy_version !== 'minimum-two-v1') fail('現行のCTA方針 minimum-two-v1 が必要です');
  const baseline = input.article_business_purpose === 'traffic' ? 2 : 3;
  if (strategy?.default_count !== baseline) fail('目的別のdefault_countが一致しません');
  if (!Number.isInteger(strategy?.planned_count) || strategy.planned_count < 2) fail('CTA計画は最低2件必要です');
  if (!Array.isArray(links) || links.length !== strategy?.planned_count) fail('計画とマニフェストの件数が一致しません');
  const expected = Array.isArray(links) ? links : [];
  const seen = new Set();
  for (const link of expected) {
    if (!link.placement_id || seen.has(link.placement_id)) fail('マニフェストの配置IDが欠落・重複しています');
    seen.add(link.placement_id);
    if (!rootsByProvider[link.provider]) fail('未対応の広告主です');
    const c = link.placement_context;
    if (!c || typeof c.before !== 'string' || !c.before.trim() || typeof c.after !== 'string' || typeof c.rationale !== 'string' || !c.rationale.trim()) {
      fail('各配置に直前・直後の引用と配置理由が必要です');
    }
  }
  const flow = [];
  let heading = '';
  function walk(node, hidden = false) {
    if (node.type === 'comment' || excluded.has(node.tagName)) return;
    hidden ||= concealed(node);
    const cs = classes(node);
    if (cs.some(c => ['shinken-zemi-cta','smile-zemi-cta'].includes(c))) {
      flow.push({kind:'cta',node,hidden,heading,id:prop(node,'dataPlacementId','data-placement-id')});
      return;
    }
    if (node.tagName === 'h2') { heading = norm(text(node)); flow.push({kind:'heading',value:heading}); return; }
    if (['h3','h4'].includes(node.tagName)) { flow.push({kind:'heading',value:norm(text(node))}); return; }
    if (cs.includes('article-link-card') || (node.tagName === 'p' && text(node).includes('【内部リンクカード】'))) {
      flow.push({kind:'card',value:norm(text(node))}); return;
    }
    if (['p','ul','ol','table','blockquote'].includes(node.tagName)) {
      const value=norm(text(node)); if (value) flow.push({kind:'text',value,heading}); return;
    }
    for (const child of node.children ?? []) walk(child,hidden);
  }
  roots.forEach(root => walk(root));
  const actual = flow.filter(x => x.kind === 'cta');
  if (actual.length < 2 || actual.length !== expected.length) fail('本文CTA実件数が最低2件または計画件数を満たしません');
  const actualIds = new Set();
  for (const item of actual) {
    if (!item.id || actualIds.has(item.id)) fail('実CTAの配置IDが欠落・重複しています');
    actualIds.add(item.id);
    const link = expected.find(x => x.placement_id === item.id);
    if (!link) { fail('計画外のCTAがあります'); continue; }
    if (item.hidden) fail('非表示のCTAは設置件数に数えられません');
    const root = rootsByProvider[link.provider];
    if (!classes(item.node).includes(root)) fail('広告主とCTA部品が一致しません');
    if (prop(item.node,'dataCourse','data-course') !== link.target_course) fail('対象講座が一致しません');
    if (item.heading !== norm(link.section_heading)) fail('配置先のH2が一致しません');
    const buttons = descendants(item.node,'a');
    if (buttons.length !== 1) fail('1つの配置は1つの申込案内である必要があります');
    const button = buttons[0];
    if (!button || !classes(button).includes(root+'__button') || url(button.properties?.href) !== url(link.href)) fail('CTAボタン・URLが一致しません');
    if (!String(button?.properties?.rel ?? '').split(/[,\s]+/).includes('nofollow')) fail('nofollowがありません');
    if (norm(text(button ?? {})) !== norm(link.button_text)) fail('ボタンの表示文が一致しません');
    const lead = descendants(item.node,'p').find(n => classes(n).includes(root+'__lead'));
    if (!lead || norm(text(lead)) !== norm(link.lead_text)) fail('案内文が一致しません');
    const pixels = descendants(item.node,'img').filter(n => url(n.properties?.src) === url(link.tracking_image_src));
    if (pixels.length !== 1 || !pixels.every(n => Number(n.properties?.width) === 1 && Number(n.properties?.height) === 1 && Number(n.properties?.border) === 0)) fail('計測画像・固定属性が一致しません');
    const index = flow.indexOf(item), previous = flow[index-1], next=flow[index+1], context=link.placement_context;
    if (context && (!previous || previous.kind !== 'text' || !previous.value.includes(norm(context.before)))) fail('直前の本文が配置文脈と一致しません');
    if (context && (next ? !norm(context.after) || !norm(next.value).includes(norm(context.after)) : norm(context.after))) fail('直後の本文が配置文脈と一致しません');
    const lastInduction = flow.slice(0,index).findLastIndex(n => n.kind === 'cta' || n.kind === 'card');
    if (lastInduction >= 0 && !flow.slice(lastInduction+1,index).some(n => n.kind === 'text')) fail('CTA・内部カードが説明なしで近接しています');
    const nextInduction = flow.slice(index+1).findIndex(n => n.kind === 'cta' || n.kind === 'card');
    if (nextInduction >= 0 && !flow.slice(index+1,index+1+nextInduction).some(n => n.kind === 'text')) fail('CTA直後に別の誘導が連続しています');
  }
  if (phase === 'rendered' && input.article_business_purpose === 'traffic' && Array.isArray(input.expected_internal_links)) {
    const primary=input.expected_internal_links.filter(n=>n.destination_role==='conversion_direct' && n.required===true && n.primary_destination===true);
    if (primary.length!==1) fail('必須の主成約記事カード計画が1件必要です');
    for (const expectedCard of primary) {
      const anchors=roots.flatMap(root=>[root,...descendants(root,'a')]).filter(n=>n.tagName==='a' && url(n.properties?.href)===url(expectedCard.href));
      const cards=anchors.filter(n=>classes(n).includes('article-link-card') && descendants(n,'img').length>0 && norm(text(n)).includes(norm(expectedCard.card_description)));
      if (cards.length!==1) fail('完成HTMLの主成約記事画像カードが欠落・不一致・重複しています');
    }
  }
  const first=actual[0];
  if (first) {
    const index=flow.indexOf(first);
    const before=flow.slice(0,index).reduce((n,b)=>n+(b.kind==='text'?b.value.length:0),0);
    const total=flow.reduce((n,b)=>n+(b.kind==='text'?b.value.length:0),0);
    if (total && before > total/2 && !strategy?.first_cta_position_note?.trim()) fail('最初のCTAが後半になる理由の記録が必要です');
  }
  return {status:errors.length?'FAIL':'PASS',actual_count:actual.length,placement_ids:actual.map(n=>n.id),errors,semantic_review:'required_separately'};
}

