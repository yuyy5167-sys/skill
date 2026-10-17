# 設定と実行

## 新規作成と既存プロジェクト

`scripts/create_project.py --project PATH --mode new` は空の作業先へテンプレートを作る。既存の `tmp/` は許容する。`--mode existing` は専用のソース・スクリプト・例素材だけを追加し、同名の既存ファイルがあれば書き込む前に停止する。Root、既存の設定、package.json、ロックファイルは書き換えない。

追加先で不足する依存とRemotionの版を確認する。新規プロジェクトは付属のロックファイルで `npm ci`。追加先では既存Remotion関連パッケージの版をそろえ、必要な依存だけ追加する。TypeScriptのJSON読み込みとJSX設定も既存設定に合わせる。`REMOTION_BROWSER_EXECUTABLE` で既存Chrome等の実行パスを指定できる。未指定ならRemotionの標準ブラウザ解決を使う。スキルに個人の絶対パスを埋め込まない。

実行はプロジェクトのルートから行う。独立エントリーは `src/manga-animation/index.tsx`。設定は同フォルダの `manga.config.json`。`node scripts/manga/render.mjs --frames 0-119 --output tmp/sample.mp4` で試作し、範囲指定なしなら全編を出力する。出力先は完成物なら `output/`、確認用なら `tmp/` とする。

## 座標と時刻

全ての `polygon`、`pivot`、`dx`、`dy`、`feather` は **切り出したコマ内の原稿ピクセル**。左上が `[0,0]`。ページ全体や出力画面の座標と混在させない。`size:[幅,高さ]` は切り出したコマの実寸。表示の拡大縮小は描画側が行い、原稿の縦横比を保持する。

時刻 `at` と `seconds` は各コマ開始からの秒。音の `at` だけは動画全体の開始からの秒。`angle` は度。`fps` は `poseHz` の整数倍とし、標準は24/8。視覚の表示開始は次の姿勢更新時刻へ切り上げる（例：8Hzの0.3秒指定→0.375秒）。0.5秒以下も同じ規則で扱う。

## 設定項目

- 全体：`id`、`width`、`height`、`fps`、`poseHz`、`background`、`margin`、`timingMode`、`panels`、任意の `audio`。
- コマ：`id`、`image`（public相対パス）、`size`、`seconds`、`mode`（`mesh` / `layers`）、`parts`、`fixed`、`dialogues`。
- 素材切り出し：任意の `source:{file,crop:[左,上,幅,高さ]}`。`prepare.mjs` がpublic内の原稿から `image` へ切り出す。原稿は上書きしない。
- 動作：`id`、`polygon`、`feather`、`pivot`、`keys:[{at,dx,dy,angle}]`。キーは時刻順。先頭キーは0秒。指定しない移動・角度は0。最後のキー以降は保持する。
- 固定範囲：`polygon` と `feather`。コマ枠は自動で固定。吹き出し全体や背景の直線は必要に応じて追加する。
- セリフ：`id`、`at`、`mask`、`cover:{color}` または `cover:{image}`、`readSeconds` または `text`。`mask` は文字を隠す範囲。色はその範囲が均一な場合だけ使う。画像はコマと同寸法の文字なし画像。
- レイヤー：`baseImage`（動く物の元の位置を除いた画像）と `layers:[{id,image,polygon?,part?}]`。画像はコマと同寸法。配列は奥から手前。`part` は動作ID。同じIDで手と持ち物を一緒に動かせる。静止した前景には `part` を付けない。
- 音：`audio:[{src,at,duration,volume}]`。素材はpublic相対パス。実際に使う音だけ設定し、仮フォーリーを実録音と呼ばない。

`timingMode:"extend"` では `seconds` を最小の尺とし、最後のセリフの読了と動作の終了まで延長する。`"strict"` では不足をエラーにし、姿勢更新間隔で表現できない尺も黙って丸めずエラーにする。総尺は全コマから算出し、90秒などへ固定しない。読む時間を省略した場合の文字数見積もりは仮値なので実再生で調整する。

## 実装上の制限と確認

メッシュは画像寸法に合わせて網目を調整し、16bitの頂点番号の上限を超えない。画像がGPUのテクスチャ上限を超えた場合は理由を表示して停止する。元原稿を保持した別の作業画像へ縮小し、sizeと全座標も同じ比率で変換するか、レイヤー方式を選ぶ。

`validate.mjs` は設定、参照画像の実寸、時刻、読み時間、座標、素材の存在を確認する。`review.mjs` はパーツごとのキーと文字表示前後を抽出し、フレーム保持を圧縮前PNGで確認する。PNG一覧を生成しただけで目視確認済みと扱わない。

本編は24fps等の出力設定で直接レンダリングし、H.264の中間動画を再圧縮しない。書き出し後、Remotion同梱FFmpeg/ffprobe等で映像・音声の尺、解像度、fps、デコードを検査し、動画も実際に再生する。

スキルのテンプレートを変更した場合、`node <このスキル>/scripts/test_runtime.mjs` で時刻、読み時間、座標と高解像度の網目を検査できる。ブラウザ描画の確認は別に実行する。
