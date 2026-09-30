import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { FileBlob, SpreadsheetFile } from "./artifact-tool.mjs";
import { normalizeQueries, validateResearchResults } from "./validate-results.mjs";

const MAIN_HEADERS = ["調査ID", "自然検索対象件数", "個人件数", "企業件数", "要確認件数", "分類状態", "色判定", "調査日時"];
const DETAIL_HEADERS = ["調査ID", "キーワード", "順位", "サイト名", "ドメイン", "分類", "判定理由", "調査日時"];

export function parseArgs(argv = process.argv.slice(2)) {
  const options = { sheetName: "サジュエストワード", keywordColumn: "A" };
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === "--input") options.inputPath = argv[++index];
    else if (argv[index] === "--results") options.resultsPath = argv[++index];
    else if (argv[index] === "--sheet") options.sheetName = argv[++index];
    else if (argv[index] === "--keyword-column") options.keywordColumn = String(argv[++index] ?? "").toUpperCase();
    else throw new Error(`未知の引数です: ${argv[index]}`);
  }
  if (!options.inputPath || !options.resultsPath) {
    throw new Error("使用方法: node verify-workbook.mjs --input <input.xlsx> --results <results.json> [--sheet <sheet>] [--keyword-column <A>]");
  }
  return options;
}

function sheetNames(workbook) {
  return Array.from({ length: workbook.worksheets.getSheetCount() }, (_, index) => workbook.worksheets.getSheetNameByIndex(index));
}

function surveyIdForRow(rowNumber) {
  return `調査-${String(rowNumber - 1).padStart(4, "0")}`;
}

function columnIndexFromLetters(letters) {
  return [...String(letters).toUpperCase()].reduce(
    (result, letter) => result * 26 + letter.charCodeAt(0) - 64,
    0,
  ) - 1;
}

function usedDataRows(sheet) {
  const values = sheet.getUsedRange()?.values ?? [];
  return values.slice(1).filter((row) => row.some((value) => value !== null && value !== undefined && value !== ""));
}

function findFormulaErrors(workbook) {
  const errors = [];
  for (const name of sheetNames(workbook)) {
    const rows = workbook.worksheets.getItem(name).getUsedRange()?.values ?? [];
    for (const [rowIndex, row] of rows.entries()) {
      for (const [columnIndex, value] of row.entries()) {
        if (typeof value === "string" && value.startsWith("#")) {
          errors.push(`${name}!R${rowIndex + 1}C${columnIndex + 1}: ${value}`);
        }
      }
    }
  }
  return errors;
}

export async function verifyWorkbook({ inputPath, resultsPath, sheetName = "サジュエストワード", keywordColumn = "A" }) {
  const payload = JSON.parse(await fs.readFile(resultsPath, "utf8"));
  const validation = validateResearchResults(payload);
  if (!validation.ok) {
    throw new Error(`結果JSONが不正です。\n${validation.errors.join("\n")}`);
  }
  const queryByKeyword = new Map(normalizeQueries(payload).map((query) => [query.keyword, query]));
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
  const errors = [];
  if (!sheetNames(workbook).includes(sheetName)) {
    throw new Error(`対象シートがありません: ${sheetName}`);
  }
  for (const requiredSheet of ["検索結果詳細", "要確認"]) {
    if (!sheetNames(workbook).includes(requiredSheet)) errors.push(`補助シートがありません: ${requiredSheet}`);
  }

  const main = workbook.worksheets.getItem(sheetName);
  const used = main.getUsedRange();
  const rowNumbers = String(used?.address ?? "").match(/\d+/g) ?? [];
  const lastRow = rowNumbers.length ? Math.max(...rowNumbers.map(Number)) : 1;
  const mainValues = main.getRange(`A1:L${lastRow}`).values ?? [];
  const keywordIndex = columnIndexFromLetters(keywordColumn);
  if (keywordIndex < 0 || keywordIndex > 11) {
    throw new Error("--keyword-columnはA～Lの範囲で指定してください。");
  }
  if (JSON.stringify(mainValues[0]?.slice(4, 12)) !== JSON.stringify(MAIN_HEADERS)) {
    errors.push("主表のE1:L1見出しが不正です。");
  }

  let keywordRows = 0;
  let expectedDetails = 0;
  let expectedReviews = 0;
  for (let index = 1; index < mainValues.length; index += 1) {
    const row = mainValues[index];
    const keyword = row[keywordIndex];
    if (typeof keyword !== "string" || keyword.trim() === "") continue;
    keywordRows += 1;
    const query = queryByKeyword.get(keyword.trim());
    if (!query) {
      errors.push(`結果JSONにキーワードがありません: ${keyword}`);
      continue;
    }
    const rowNumber = index + 1;
    const expected = [surveyIdForRow(rowNumber), query.inspectedCount, query.personalCount, query.corporateCount, query.reviewCount, query.status, query.color];
    const actual = row.slice(4, 11);
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
      errors.push(`${sheetName}!E${rowNumber}: 集計値が結果JSONと一致しません。`);
    }
    if (row[11] === null || row[11] === undefined || row[11] === "") {
      errors.push(`${sheetName}!L${rowNumber}: 調査日時がありません。`);
    }
    expectedDetails += query.serpDetails.length;
    expectedReviews += query.reviewCount;
  }
  const workbookKeywords = new Set(
    mainValues.slice(1)
      .map((row) => row[keywordIndex])
      .filter((keyword) => typeof keyword === "string" && keyword.trim() !== "")
      .map((keyword) => keyword.trim()),
  );
  for (const keyword of queryByKeyword.keys()) {
    if (!workbookKeywords.has(keyword)) {
      errors.push(`入力Excelに存在しない結果JSONのキーワードです: ${keyword}`);
    }
  }

  const details = workbook.worksheets.getItem("検索結果詳細");
  const reviews = workbook.worksheets.getItem("要確認");
  const detailHeader = details.getUsedRange()?.values?.[0]?.slice(0, 8) ?? [];
  const reviewHeader = reviews.getUsedRange()?.values?.[0]?.slice(0, 8) ?? [];
  if (JSON.stringify(detailHeader) !== JSON.stringify(DETAIL_HEADERS)) errors.push("検索結果詳細の見出しが不正です。");
  if (JSON.stringify(reviewHeader) !== JSON.stringify(DETAIL_HEADERS)) errors.push("要確認の見出しが不正です。");
  if (usedDataRows(details).length !== expectedDetails) errors.push("検索結果詳細の行数が結果JSONと一致しません。");
  if (usedDataRows(reviews).length !== expectedReviews) errors.push("要確認の行数が結果JSONと一致しません。");
  if (main.getRange(`K2:K${lastRow}`).conditionalFormats.items.length < 3) errors.push("色判定の条件付き書式が不足しています。");
  errors.push(...findFormulaErrors(workbook));

  return {
    ok: errors.length === 0,
    errors,
    summary: {
      keywordRows,
      detailRows: usedDataRows(details).length,
      reviewRows: usedDataRows(reviews).length,
    },
  };
}

function isMainModule() {
  return process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;
}

if (isMainModule()) {
  try {
    const result = await verifyWorkbook(parseArgs());
    if (!result.ok) {
      process.stderr.write(`${result.errors.join("\n")}\n`);
      process.exitCode = 1;
    } else {
      process.stdout.write(`${JSON.stringify(result.summary, null, 2)}\n`);
    }
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  }
}
