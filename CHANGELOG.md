# 更新履歴

読み取りツールの基準は、公式 [google-analytics-mcp 1.1.0](https://github.com/googleanalytics/google-analytics-mcp/releases/tag/1.1.0)（2026-11-06）です。1.1.0 はこのリポジトリのパッケージ版ではありません。パッケージ版は `pyproject.toml` の `0.1.0` です。

同じ 1.1.0 にあって、こちらに含めていないもの:

- 書き込みツール（公式の `--allow-write`）
- `run_conversions_report`
- 公式の OAuth。接続は HTTP のみで、stdio はありません

---

## 2026-11-15

- n8n のように、ワークフローが有効なあいだ `GET /mcp` を送り続けるクライアントがある。このサーバーは GET にすぐ 405 を返し、結果を返したあとの SSE は開かない。有効化したあとも、実行していない時間にサーバーが動き続けていないか確認する。README にその注意を書いた。

## 2026-11-14

公式 1.1.0 の読み取り側に合わせた。

### 追加したツール

- `run_funnel_report`（Data API の alpha）。`date_ranges` は必須で、幅は `run_report` と同じ。`funnel_next_action.limit` を付けたときだけ行数上限を適用する。省略時は API の既定のまま。
- `list_key_events`。キーイベントの定義一覧。発生回数と金額は返さない。それらは `run_report`。
- `run_realtime_report` の任意引数 `minute_ranges`。省略、または空のリストは、フィールドを付けない（直近 30 分）。3 件以上は拒否する。

### 依存

- `google-analytics-data` 0.23.3
- `google-analytics-admin` 0.30.2
- `google-auth` `~=2.62`
- MCP Python SDK は 2.3 の low-level handler（`mcp>=2.3.0,<3`）

### ツールのスキーマ

- 公開しているツールは読み取り専用（`readOnlyHint` が true）。`property_id` は文字列。`additionalProperties` が bool でないときは bool に揃える。

### このサーバー側の制限

- `get_account_summaries` は `GA4MCP_ALLOWED_PROPERTY_IDS` にあるプロパティだけを返す。残るプロパティが無いアカウントは落とす。許可リストが空で、全件許可でもないときは空の一覧を返し、Google を呼ばない。
- 日付幅と行数上限は、相対日付のときと、`limit` を省略したときにも適用する。
- ステートレスな `GET /mcp` はすぐ 405 を返す。セッション ID（`Mcp-Session-Id`）は出さない。

---

# Changelog

Read-only tools follow official [google-analytics-mcp 1.1.0](https://github.com/googleanalytics/google-analytics-mcp/releases/tag/1.1.0) (2026-11-06). That release number is not this repository's package version. The package version in `pyproject.toml` is `0.1.0`.

Present in official 1.1.0 and not included here:

- Write tools (the official `--allow-write` path)
- `run_conversions_report`
- The official OAuth transport. This server is HTTP-only and does not offer stdio

---

## 2026-11-15

- Some clients, including n8n, keep sending `GET /mcp` while a workflow is enabled. This server returns 405 immediately and does not open an SSE stream after the result. After you enable a workflow, check that the server is not kept running while nothing is executing. The README now says so.

## 2026-11-14

Aligned the read-only surface with official 1.1.0.

### Tools added

- `run_funnel_report` (Data API alpha). `date_ranges` is required, with the same date span as `run_report`. The row cap applies only when `funnel_next_action.limit` is set. When it is omitted, the API default is left as-is.
- `list_key_events`. Lists key event definitions. It does not return occurrence counts or revenue. Use `run_report` for those.
- Optional `minute_ranges` on `run_realtime_report`. Omitting it, or passing an empty list, leaves the field unset (the last 30 minutes). Three or more ranges are rejected.

### Dependencies

- `google-analytics-data` 0.23.3
- `google-analytics-admin` 0.30.2
- `google-auth` `~=2.62`
- MCP Python SDK 2.3 low-level handlers (`mcp>=2.3.0,<3`)

### Tool schema

- Published tools are marked read-only (`readOnlyHint` true). `property_id` is a string. A non-boolean `additionalProperties` is coerced to a boolean.

### Limits on this server

- `get_account_summaries` returns only properties in `GA4MCP_ALLOWED_PROPERTY_IDS`. Accounts with no remaining allowed properties are dropped. An empty allowlist, when allow-all is also off, returns an empty list and does not call Google.
- The date span and row cap also apply when dates are relative, and when `limit` is omitted.
- A stateless `GET /mcp` returns 405 immediately. The server does not issue a session id (`Mcp-Session-Id`).
