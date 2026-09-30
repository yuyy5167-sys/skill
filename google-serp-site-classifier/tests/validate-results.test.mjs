import assert from "node:assert/strict";
import test from "node:test";
import { validateResearchResults } from "../scripts/validate-results.mjs";

function validPayload() {
  return {
    queries: [{
      keyword: "テスト キーワード",
      inspectedCount: 3,
      personalCount: 2,
      corporateCount: 0,
      reviewCount: 1,
      status: "要確認",
      color: "要確認",
      checkedAt: "2026-09-14T10:00:00+09:00",
      serpDetails: [
        { rank: 1, siteName: "アメーバブログ", domain: "ameblo.jp", classification: "個人", classificationReason: "個人ブログ・投稿プラットフォーム指定" },
        { rank: 2, siteName: "Yahoo!知恵袋", domain: "detail.chiebukuro.yahoo.co.jp", classification: "個人", classificationReason: "個人ブログ・投稿プラットフォーム指定" },
        { rank: 3, siteName: "不明なサイト", domain: "example.org", classification: "要確認", classificationReason: "判定根拠不足" },
      ],
    }],
  };
}

test("正しい結果JSONを受け入れる", () => {
  const result = validateResearchResults(validPayload());
  assert.equal(result.ok, true);
  assert.deepEqual(result.summary, {
    keywordCount: 1,
    detailCount: 3,
    personalCount: 2,
    corporateCount: 0,
    reviewCount: 1,
  });
});

test("件数・順位・色が矛盾するJSONを拒否する", () => {
  const payload = validPayload();
  payload.queries[0].personalCount = 1;
  payload.queries[0].color = "青";
  payload.queries[0].serpDetails[2].rank = 5;
  const result = validateResearchResults(payload);
  assert.equal(result.ok, false);
  assert.ok(result.errors.some((error) => error.includes("順位")));
  assert.ok(result.errors.some((error) => error.includes("分類別件数")));
  assert.ok(result.errors.some((error) => error.includes("color")));
});
