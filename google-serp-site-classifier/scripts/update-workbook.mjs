import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { FileBlob, SpreadsheetFile } from "./artifact-tool.mjs";
import { normalizeQueries, validateResearchResults } from "./validate-results.mjs";

const MAIN_HEADERS = [
  "調査ID",
  "自然検索対象件数",
  "個人件数",
  "企業件数",
  "要確認件数",
  "分類状態",
  "色判定",
  "調査日時",
];
const DETAIL_HEADERS = [
  "調査ID",
  "キーワード",
  "順位",
  "サイト名",
  "ドメイン",
  "分類",
  "判定理由",
  "調査日時",
];
const OUTPUT_START_COLUMN = "E";
const OUTPUT_END_COLUMN = "L";

export function parseArgs(argv = process.argv.slice(2)) {
  const options = {
    sheetName: "サジュエストワード",
    keywordColumn: "A",
  };

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--input") {
      options.inputPath = argv[++index];
    } else if (argument === "--results") {
      options.resultsPath = argv[++index];
    } else if (argument === "--output") {
      options.outputPath = argv[++index];
    } else if (argument === "--sheet") {
      options.sheetName = argv[++index];
    } else if (argument === "--keyword-column") {
      options.keywordColumn = String(argv[++index] ?? "").toUpperCase();
    } else {
      throw new Error(`未知の引数です: ${argument}`);
    }
  }

  if (!options.inputPath || !options.resultsPath) {
    throw new Error("使用方法: node update-workbook.mjs --input <input.xlsx> --results <results.json> [--output <output.xlsx>] [--sheet <sheet>] [--keyword-column <A>]");
  }
  if (!/^[A-Z]+$/.test(options.keywordColumn)) {
    throw new Error("--keyword-columnにはA形式の列記号を指定してください。");
  }
  return options;
}

function worksheetNames(workbook) {
  return Array.from(
    { length: workbook.worksheets.getSheetCount() },
    (_, index) => workbook.worksheets.getSheetNameByIndex(index),
  );
}

function getWorksheet(workbook, name) {
  if (!worksheetNames(workbook).includes(name)) {
    throw new Error(`対象シートがありません: ${name}`);
  }
  return workbook.worksheets.getItem(name);
}

function getOrAddWorksheet(workbook, name) {
  return worksheetNames(workbook).includes(name)
    ? workbook.worksheets.getItem(name)
    : workbook.worksheets.add(name);
}

function getLastRow(usedRange) {
  const matches = String(usedRange?.address ?? "").match(/\d+/g) ?? [];
  return matches.length === 0 ? 1 : Math.max(...matches.map(Number));
}

function surveyIdForRow(rowNumber) {
  return `調査-${String(rowNumber - 1).padStart(4, "0")}`;
}

function toWallClockDate(value) {
  if (typeof value !== "string") {
    return null;
  }
  const match = value.match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?(?:Z|[+-]\d{2}:?\d{2})$/,
  );
  if (!match) {
    return null;
  }
  const [, year, month, day, hour, minute, second = "0", fraction = ""] = match;
  return new Date(Date.UTC(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
    Number(second),
    fraction ? Number(fraction.padEnd(3, "0")) : 0,
  ));
}

function toCellValue(value) {
  if (value === undefined || value === null || value === "") {
    return null;
  }
  const date = toWallClockDate(value);
  return date ?? value;
}

function clearWorksheet(sheet) {
  const usedRange = sheet.getUsedRange();
  if (usedRange) {
    usedRange.clear({ applyTo: "all" });
  }
}

function styleHeader(range) {
  range.format = {
    fill: "#1F4E78",
    font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
  range.format.borders = {
    preset: "outside",
    style: "thin",
    color: "#B4C7E7",
  };
  range.format.rowHeight = 28;
}

function setColumnWidths(sheet, widths) {
  for (const [column, width] of Object.entries(widths)) {
    sheet.getRange(`${column}1:${column}2`).format.columnWidth = width;
  }
}

function writeSupportingSheet(sheet, rows) {
  clearWorksheet(sheet);
  const lastRow = rows.length + 1;
  sheet.getRange(`A1:H${lastRow}`).values = [DETAIL_HEADERS, ...rows];
  styleHeader(sheet.getRange("A1:H1"));
  if (rows.length > 0) {
    const body = sheet.getRange(`A2:H${lastRow}`);
    body.format.font = { name: "Arial", size: 10, color: "#222222" };
    body.format.verticalAlignment = "center";
    sheet.getRange(`C2:C${lastRow}`).format.numberFormat = "#,##0";
    sheet.getRange(`H2:H${lastRow}`).format.numberFormat = "yyyy-mm-dd hh:mm";
  }
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  setColumnWidths(sheet, { A: 14, B: 24, C: 8, D: 42, E: 24, F: 10, G: 40, H: 20 });
}

function addColorConditionalFormatting(sheet, lastRow) {
  if (lastRow < 2) {
    return;
  }
  const colorRange = sheet.getRange(`K2:K${lastRow}`);
  colorRange.clear({ applyTo: "formats" });
  colorRange.conditionalFormats.deleteAll();
  colorRange.conditionalFormats.addCustom('=$K2="赤"', {
    fill: "#F4CCCC",
    font: { color: "#9C0006", bold: true },
  });
  colorRange.conditionalFormats.addCustom('=$K2="青"', {
    fill: "#CFE2F3",
    font: { color: "#1155CC", bold: true },
  });
  colorRange.conditionalFormats.addCustom('=$K2="緑"', {
    fill: "#D9EAD3",
    font: { color: "#38761D", bold: true },
  });
}

function inputKeywordRows(sheet, keywordColumn, lastRow) {
  const values = sheet.getRange(`${keywordColumn}2:${keywordColumn}${lastRow}`).values ?? [];
  return values
    .map((row, index) => ({ rowNumber: index + 2, keyword: row?.[0] }))
    .filter(({ keyword }) => typeof keyword === "string" && keyword.trim() !== "")
    .map(({ rowNumber, keyword }) => ({ rowNumber, keyword: keyword.trim() }));
}

function assertCoverage(queries, keywordRows) {
  const workbookKeywords = new Set(keywordRows.map(({ keyword }) => keyword));
  const queryKeywords = new Set(queries.map(({ keyword }) => keyword));
  const absentResults = [...workbookKeywords].filter((keyword) => !queryKeywords.has(keyword));
  const unknownResults = [...queryKeywords].filter((keyword) => !workbookKeywords.has(keyword));
  if (absentResults.length > 0) {
    throw new Error(`結果JSONに未処理のキーワードがあります: ${absentResults.join("、")}`);
  }
  if (unknownResults.length > 0) {
    throw new Error(`入力Excelに存在しないキーワードがあります: ${unknownResults.join("、")}`);
  }
}

export async function updateWorkbook({ inputPath, resultsPath, outputPath = inputPath, sheetName = "サジュエストワード", keywordColumn = "A" }) {
  const payload = JSON.parse(await fs.readFile(resultsPath, "utf8"));
  const validation = validateResearchResults(payload);
  if (!validation.ok) {
    throw new Error(`結果JSONの検証に失敗しました。\n${validation.errors.join("\n")}`);
  }
  const queries = normalizeQueries(payload);
  const queryByKeyword = new Map(queries.map((query) => [query.keyword, query]));

  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
  const mainSheet = getWorksheet(workbook, sheetName);
  const lastRow = getLastRow(mainSheet.getUsedRange());
  if (lastRow < 2) {
    throw new Error("対象シートにキーワード行がありません。");
  }
  const keywordRows = inputKeywordRows(mainSheet, keywordColumn, lastRow);
  if (keywordRows.length === 0) {
    throw new Error("キーワード列に処理対象の値がありません。");
  }
  assertCoverage(queries, keywordRows);

  mainSheet.getRange(`${OUTPUT_START_COLUMN}1:${OUTPUT_END_COLUMN}1`).values = [MAIN_HEADERS];
  styleHeader(mainSheet.getRange(`${OUTPUT_START_COLUMN}1:${OUTPUT_END_COLUMN}1`));
  const keywordByRow = new Map(keywordRows.map(({ rowNumber, keyword }) => [rowNumber, keyword]));
  const outputRows = Array.from({ length: lastRow - 1 }, (_, index) => {
    const keyword = keywordByRow.get(index + 2);
    const query = keyword ? queryByKeyword.get(keyword) : undefined;
    if (!query) {
      return Array(8).fill(null);
    }
    return [
      surveyIdForRow(index + 2),
      query.inspectedCount,
      query.personalCount,
      query.corporateCount,
      query.reviewCount,
      query.status,
      query.color,
      toCellValue(query.checkedAt),
    ];
  });
  mainSheet.getRange(`${OUTPUT_START_COLUMN}2:${OUTPUT_END_COLUMN}${lastRow}`).clear({ applyTo: "contents" });
  mainSheet.getRange(`${OUTPUT_START_COLUMN}2:${OUTPUT_END_COLUMN}${lastRow}`).values = outputRows;
  const outputRange = mainSheet.getRange(`${OUTPUT_START_COLUMN}2:${OUTPUT_END_COLUMN}${lastRow}`);
  outputRange.format.font = { name: "Arial", size: 10, color: "#222222" };
  outputRange.format.verticalAlignment = "center";
  mainSheet.getRange(`F2:I${lastRow}`).format.numberFormat = "#,##0";
  mainSheet.getRange(`L2:L${lastRow}`).format.numberFormat = "yyyy-mm-dd hh:mm";
  mainSheet.getRange("L1:L2").format.columnWidth = 20;
  addColorConditionalFormatting(mainSheet, lastRow);

  const detailRows = [];
  const reviewRows = [];
  for (const { rowNumber, keyword } of keywordRows) {
    const query = queryByKeyword.get(keyword);
    const surveyId = surveyIdForRow(rowNumber);
    for (const detail of query.serpDetails) {
      const row = [
        surveyId,
        keyword,
        detail.rank,
        detail.siteName,
        detail.domain,
        detail.classification,
        detail.classificationReason,
        toCellValue(query.checkedAt),
      ];
      detailRows.push(row);
      if (detail.classification === "要確認") {
        reviewRows.push(row);
      }
    }
  }

  writeSupportingSheet(getOrAddWorksheet(workbook, "検索結果詳細"), detailRows);
  writeSupportingSheet(getOrAddWorksheet(workbook, "要確認"), reviewRows);
  workbook.recalculate();
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);

  return {
    inputPath,
    outputPath,
    sheetName,
    keywordRows: keywordRows.length,
    detailCount: detailRows.length,
    reviewCount: reviewRows.length,
  };
}

function isMainModule() {
  return process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;
}

if (isMainModule()) {
  updateWorkbook(parseArgs())
    .then((result) => process.stdout.write(`${JSON.stringify(result, null, 2)}\n`))
    .catch((error) => {
      process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
      process.exitCode = 1;
    });
}
