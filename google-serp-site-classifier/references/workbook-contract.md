# Excelと結果JSONの契約

## 対象Excel

既定値は `サジュエストワード` シートのA列をキーワード列とする。A～D列は元データとして保持し、E～L列だけをこのスキルの管理対象にする。

| 列 | 項目 |
|---|---|
| E | 調査ID |
| F | 自然検索対象件数 |
| G | 個人件数 |
| H | 企業件数 |
| I | 要確認件数 |
| J | 分類状態 |
| K | 色判定 |
| L | 調査日時 |

スキルが管理する補助シートは `検索結果詳細` と `要確認` のみである。ほかのシートは変更しない。

## 色判定

| 条件 | 値 |
|---|---|
| 要確認件数が1件以上 | 要確認 |
| 個人件数が0件 | 赤 |
| 個人件数が1～2件 | 青 |
| 個人件数が3件以上 | 緑 |

## 結果JSON

`queries` 配列または同等の配列を使う。`serpDetails` は順位順で必須とする。

```json
{
  "queries": [
    {
      "keyword": "スマイルゼミ 口コミ",
      "inspectedCount": 9,
      "personalCount": 2,
      "corporateCount": 7,
      "reviewCount": 0,
      "status": "確定",
      "color": "青",
      "checkedAt": "2026-09-14T10:00:00+09:00",
      "serpDetails": [
        {
          "rank": 1,
          "siteName": "サイト名",
          "domain": "example.jp",
          "classification": "企業",
          "classificationReason": "JPドメイン規則"
        }
      ]
    }
  ]
}
```

## 整合性

各キーワードで次を満たす。

```text
inspectedCount = personalCount + corporateCount + reviewCount
inspectedCount = serpDetails.length
reviewCount = serpDetails内の「要確認」件数
```

`status` は要確認件数が0なら `確定`、1以上なら `要確認` とする。`color` は上記の色判定に一致しなければならない。

同一キーワードの重複した結果JSONは許可しない。Excel内に同一キーワードの複数行がある場合は、同じ観測結果を各行へ反映し、調査IDと詳細行は行ごとに分ける。
