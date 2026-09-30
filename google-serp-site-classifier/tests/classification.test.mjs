import assert from "node:assert/strict";
import test from "node:test";
import {
  CLASSIFICATION,
  REASON,
  classifySerpResult,
  deriveColor,
  deriveStatus,
} from "../scripts/classification.mjs";

test(".jpは原則として企業", () => {
  assert.deepEqual(
    classifySerpResult({ domain: "www.example.co.jp" }),
    { classification: CLASSIFICATION.CORPORATE, classificationReason: REASON.JP_DOMAIN },
  );
});

test("一般ドメインは企業根拠なしなら個人、根拠ありなら企業", () => {
  assert.equal(classifySerpResult({ domain: "example.com" }).classification, CLASSIFICATION.PERSONAL);
  assert.equal(
    classifySerpResult({ domain: "youtube.com", siteName: "YouTube", corporateEvidence: true }).classification,
    CLASSIFICATION.CORPORATE,
  );
});

test("Ameblo、note、Yahoo!知恵袋は最優先で個人", () => {
  for (const input of [
    { domain: "ameblo.jp", siteName: "アメーバブログ", corporateEvidence: true },
    { domain: "note.com", siteName: "企業公式note", corporateEvidence: true },
    { domain: "detail.chiebukuro.yahoo.co.jp", siteName: "Yahoo!知恵袋", corporateEvidence: true },
    { siteName: "Yahoo!知恵袋" },
  ]) {
    assert.deepEqual(
      classifySerpResult(input),
      { classification: CLASSIFICATION.PERSONAL, classificationReason: REASON.PERSONAL_PLATFORM },
    );
  }
});

test("判定根拠がないドメインは要確認", () => {
  assert.deepEqual(
    classifySerpResult({ domain: "example.org" }),
    { classification: CLASSIFICATION.REVIEW, classificationReason: REASON.INSUFFICIENT },
  );
  assert.equal(
    classifySerpResult({ siteName: "Notebook情報" }).classification,
    CLASSIFICATION.REVIEW,
  );
});

test("色判定と状態は件数から決まる", () => {
  assert.equal(deriveStatus(0), "確定");
  assert.equal(deriveStatus(1), "要確認");
  assert.equal(deriveColor(0, 0), "赤");
  assert.equal(deriveColor(2, 0), "青");
  assert.equal(deriveColor(3, 0), "緑");
  assert.equal(deriveColor(10, 1), "要確認");
});
