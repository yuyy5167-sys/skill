import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import {
  CLASSIFICATION,
  deriveColor,
  deriveStatus,
} from "./classification.mjs";

const VALID_CLASSIFICATIONS = new Set(Object.values(CLASSIFICATION));

export function normalizeQueries(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.queries)) {
    return payload.queries;
  }
  throw new Error("結果JSONはqueries配列またはquery配列そのものを指定してください。");
}

function nonNegativeInteger(value) {
  return Number.isInteger(value) && value >= 0;
}

function nonBlankString(value) {
  return typeof value === "string" && value.trim() !== "";
}

export function validateResearchResults(payload) {
  const errors = [];
  let queries;
  try {
    queries = normalizeQueries(payload);
  } catch (error) {
    return { ok: false, queries: [], errors: [error.message] };
  }

  const seenKeywords = new Set();
  let detailCount = 0;
  let personalCount = 0;
  let corporateCount = 0;
  let reviewCount = 0;

  for (const [queryIndex, query] of queries.entries()) {
    const prefix = `queries[${queryIndex}]`;
    if (!query || typeof query !== "object" || Array.isArray(query)) {
      errors.push(`${prefix}: オブジェクトではありません。`);
      continue;
    }
    if (!nonBlankString(query.keyword)) {
      errors.push(`${prefix}.keyword: 空でない文字列が必要です。`);
      continue;
    }
    if (seenKeywords.has(query.keyword)) {
      errors.push(`${prefix}.keyword: 重複しています: ${query.keyword}`);
    }
    seenKeywords.add(query.keyword);

    for (const field of ["inspectedCount", "personalCount", "corporateCount", "reviewCount"]) {
      if (!nonNegativeInteger(query[field])) {
        errors.push(`${prefix}.${field}: 0以上の整数が必要です。`);
      }
    }

    const details = query.serpDetails;
    if (!Array.isArray(details)) {
      errors.push(`${prefix}.serpDetails: 配列が必要です。`);
      continue;
    }

    const classified = {
      [CLASSIFICATION.PERSONAL]: 0,
      [CLASSIFICATION.CORPORATE]: 0,
      [CLASSIFICATION.REVIEW]: 0,
    };
    for (const [detailIndex, detail] of details.entries()) {
      const detailPrefix = `${prefix}.serpDetails[${detailIndex}]`;
      if (!detail || typeof detail !== "object" || Array.isArray(detail)) {
        errors.push(`${detailPrefix}: オブジェクトではありません。`);
        continue;
      }
      if (detail.rank !== detailIndex + 1) {
        errors.push(`${detailPrefix}.rank: 1から連続した順位が必要です。`);
      }
      for (const field of ["siteName", "domain", "classification", "classificationReason"]) {
        if (!nonBlankString(detail[field])) {
          errors.push(`${detailPrefix}.${field}: 空でない文字列が必要です。`);
        }
      }
      if (VALID_CLASSIFICATIONS.has(detail.classification)) {
        classified[detail.classification] += 1;
      } else {
        errors.push(`${detailPrefix}.classification: 許可されない分類です。`);
      }
    }

    if (details.length !== query.inspectedCount) {
      errors.push(`${prefix}: inspectedCountと詳細件数が一致しません。`);
    }
    if (classified[CLASSIFICATION.PERSONAL] !== query.personalCount
      || classified[CLASSIFICATION.CORPORATE] !== query.corporateCount
      || classified[CLASSIFICATION.REVIEW] !== query.reviewCount) {
      errors.push(`${prefix}: 分類別件数と詳細が一致しません。`);
    }
    if (query.inspectedCount !== query.personalCount + query.corporateCount + query.reviewCount) {
      errors.push(`${prefix}: inspectedCountと分類別件数の合計が一致しません。`);
    }
    if (query.status !== deriveStatus(query.reviewCount)) {
      errors.push(`${prefix}.status: 要確認件数に対応していません。`);
    }
    if (query.color !== deriveColor(query.personalCount, query.reviewCount)) {
      errors.push(`${prefix}.color: 個人件数・要確認件数に対応していません。`);
    }
    if (!nonBlankString(query.checkedAt)) {
      errors.push(`${prefix}.checkedAt: 調査日時が必要です。`);
    }

    detailCount += details.length;
    personalCount += classified[CLASSIFICATION.PERSONAL];
    corporateCount += classified[CLASSIFICATION.CORPORATE];
    reviewCount += classified[CLASSIFICATION.REVIEW];
  }

  return {
    ok: errors.length === 0,
    queries,
    errors,
    summary: {
      keywordCount: queries.length,
      detailCount,
      personalCount,
      corporateCount,
      reviewCount,
    },
  };
}

export function parseArgs(argv = process.argv.slice(2)) {
  let resultsPath;
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] === "--results") {
      resultsPath = argv[++index];
    } else {
      throw new Error(`未知の引数です: ${argv[index]}`);
    }
  }
  if (!resultsPath) {
    throw new Error("使用方法: node validate-results.mjs --results <results.json>");
  }
  return { resultsPath };
}

function isMainModule() {
  return process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;
}

if (isMainModule()) {
  try {
    const { resultsPath } = parseArgs();
    const payload = JSON.parse(await fs.readFile(resultsPath, "utf8"));
    const result = validateResearchResults(payload);
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
