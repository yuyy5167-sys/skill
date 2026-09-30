import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { FileBlob, SpreadsheetFile, Workbook } from "../scripts/artifact-tool.mjs";
import { updateWorkbook } from "../scripts/update-workbook.mjs";
import { verifyWorkbook } from "../scripts/verify-workbook.mjs";

async function createInput(filePath) {
  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add("サジュエストワード");
  sheet.getRange("A1:D3").values = [
    ["キーワード", "検索Vol", "CPC", "競合性"],
    ["テスト 個人優先", 100, 0, 1],
    ["テスト 企業", 200, 0, 2],
  ];
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(filePath);
}

function payload() {
  return {
    queries: [
      {
        keyword: "テスト 個人優先",
        inspectedCount: 2,
        personalCount: 2,
        corporateCount: 0,
        reviewCount: 0,
        status: "確定",
        color: "青",
        checkedAt: "2026-09-14T10:00:00+09:00",
        serpDetails: [
          { rank: 1, siteName: "note", domain: "note.com", classification: "個人", classificationReason: "個人ブログ・投稿プラットフォーム指定" },
          { rank: 2, siteName: "Yahoo!知恵袋", domain: "detail.chiebukuro.yahoo.co.jp", classification: "個人", classificationReason: "個人ブログ・投稿プラットフォーム指定" },
        ],
      },
      {
        keyword: "テスト 企業",
        inspectedCount: 1,
        personalCount: 0,
        corporateCount: 1,
        reviewCount: 0,
        status: "確定",
        color: "赤",
        checkedAt: "2026-09-14T10:00:00+09:00",
        serpDetails: [
          { rank: 1, siteName: "公式サイト", domain: "example.jp", classification: "企業", classificationReason: "JPドメイン規則" },
        ],
      },
    ],
  };
}

test("元列を保ち、主表・詳細・要確認を一貫して更新する", async () => {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "serp-classifier-"));
  const inputPath = path.join(tempDir, "input.xlsx");
  const resultsPath = path.join(tempDir, "results.json");
  try {
    await createInput(inputPath);
    await fs.writeFile(resultsPath, JSON.stringify(payload()), "utf8");
    const before = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
    const source = before.worksheets.getItem("サジュエストワード").getRange("A1:D3").values;

    const update = await updateWorkbook({ inputPath, resultsPath });
    assert.deepEqual(update, {
      inputPath,
      outputPath: inputPath,
      sheetName: "サジュエストワード",
      keywordRows: 2,
      detailCount: 3,
      reviewCount: 0,
    });
    const verification = await verifyWorkbook({ inputPath, resultsPath });
    assert.equal(verification.ok, true, verification.errors.join("\n"));
    assert.deepEqual(verification.summary, { keywordRows: 2, detailRows: 3, reviewRows: 0 });

    const after = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
    assert.deepEqual(after.worksheets.getItem("サジュエストワード").getRange("A1:D3").values, source);
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true });
  }
});
