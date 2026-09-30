export const CLASSIFICATION = Object.freeze({
  PERSONAL: "個人",
  CORPORATE: "企業",
  REVIEW: "要確認",
});

export const REASON = Object.freeze({
  PERSONAL_PLATFORM: "個人ブログ・投稿プラットフォーム指定",
  JP_DOMAIN: "JPドメイン規則",
  CORPORATE_EVIDENCE: "企業名・著名サービス",
  GENERAL_DOMAIN: "一般ドメイン規則",
  INSUFFICIENT: "判定根拠不足",
});

export const DEFAULT_GENERIC_PERSONAL_TLDS = Object.freeze([
  ".com",
  ".net",
  ".info",
  ".biz",
  ".blog",
  ".site",
  ".xyz",
  ".club",
  ".education",
  ".online",
  ".tech",
  ".space",
  ".life",
  ".me",
]);

function hostnameFrom(value) {
  if (typeof value !== "string" || value.trim() === "") {
    return "";
  }

  const raw = value.trim();
  try {
    const url = raw.includes("://")
      ? new URL(raw)
      : new URL(`https://${raw.replace(/^https?:\/\//, "").split(/[\s›]/)[0]}`);
    if (!["http:", "https:"].includes(url.protocol)) {
      return "";
    }
    return url.hostname.toLowerCase();
  } catch {
    return "";
  }
}

function platformHostFromSiteName(siteName) {
  const normalized = String(siteName ?? "").trim().toLowerCase();
  if (normalized.includes("アメーバブログ") || normalized.includes("ameblo")) {
    return "ameblo.jp";
  }
  if (normalized === "note" || /^note(?:[\s・·｜|:-]|$)/.test(normalized)) {
    return "note.com";
  }
  if (normalized.includes("yahoo!知恵袋") || normalized.includes("ヤフー知恵袋")) {
    return "detail.chiebukuro.yahoo.co.jp";
  }
  return "";
}

export function normalizeHostname({ domain, url, siteName } = {}) {
  return hostnameFrom(domain) || hostnameFrom(url) || platformHostFromSiteName(siteName);
}

function isPersonalPlatform(hostname) {
  return hostname === "ameblo.jp"
    || hostname.endsWith(".ameblo.jp")
    || hostname === "note.com"
    || hostname.endsWith(".note.com")
    || hostname === "chiebukuro.yahoo.co.jp"
    || hostname.endsWith(".chiebukuro.yahoo.co.jp");
}

/**
 * 検索結果に表示された情報だけで運営主体を分類する。
 * corporateEvidence は検索結果の企業名・著名サービス・公式表示を見て呼び出し側が判断する。
 */
export function classifySerpResult({
  domain,
  url,
  siteName = "",
  corporateEvidence = false,
  uncertain = false,
  genericPersonalTlds = DEFAULT_GENERIC_PERSONAL_TLDS,
} = {}) {
  const hostname = normalizeHostname({ domain, url, siteName });

  // ユーザー指定の3プラットフォームは、.jp規則や企業根拠より優先する。
  if (isPersonalPlatform(hostname)) {
    return {
      classification: CLASSIFICATION.PERSONAL,
      classificationReason: REASON.PERSONAL_PLATFORM,
    };
  }

  if (!hostname || uncertain) {
    return {
      classification: CLASSIFICATION.REVIEW,
      classificationReason: REASON.INSUFFICIENT,
    };
  }

  if (hostname.endsWith(".jp")) {
    return {
      classification: CLASSIFICATION.CORPORATE,
      classificationReason: REASON.JP_DOMAIN,
    };
  }

  if (corporateEvidence || String(siteName).includes("公式")) {
    return {
      classification: CLASSIFICATION.CORPORATE,
      classificationReason: REASON.CORPORATE_EVIDENCE,
    };
  }

  const isGenericPersonalDomain = Array.isArray(genericPersonalTlds)
    && genericPersonalTlds.some((tld) => (
      typeof tld === "string"
      && tld.startsWith(".")
      && hostname.endsWith(tld.toLowerCase())
    ));

  if (isGenericPersonalDomain) {
    return {
      classification: CLASSIFICATION.PERSONAL,
      classificationReason: REASON.GENERAL_DOMAIN,
    };
  }

  return {
    classification: CLASSIFICATION.REVIEW,
    classificationReason: REASON.INSUFFICIENT,
  };
}

export function deriveStatus(reviewCount) {
  return Number(reviewCount) > 0 ? "要確認" : "確定";
}

export function deriveColor(personalCount, reviewCount) {
  if (Number(reviewCount) > 0) {
    return "要確認";
  }
  if (Number(personalCount) === 0) {
    return "赤";
  }
  return Number(personalCount) <= 2 ? "青" : "緑";
}
