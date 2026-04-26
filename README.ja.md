**[English](./README.md)** | **日本語**

# ga4-remote-mcp

Google 公式の GA4 MCP（[google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp)）を**リモート MCP（HTTP）化**した、**非公式**プロジェクトです。

## このツールでできること

GA4 のデータを使った **AI チャットボットや自動レポート** を、Dify・n8n・Slack などと組み合わせて作れます。

| やりたいこと | 例 |
|---|---|
| **自然言語で GA4 に質問** | Dify のチャットボットに「先週のセッション数は？」「流入元の内訳を教えて」と聞くだけで回答が返る |
| **定期レポートの自動化** | n8n で「毎週月曜に先週の主要指標を Slack に投稿」するワークフローを作る |
| **GA4 の権限がない人でも分析** | Slack ボットや社内チャットから自然言語で聞けるので、GA4 にログインできなくても使える |
| **チーム共有** | サーバー 1 台を立てれば、メンバー全員が同じ AI 分析環境を使える。PC ごとのインストール不要 |

### 公式 MCP との違い

| | Google 公式 GA4 MCP | ga4-remote-mcp（このプロジェクト） |
|---|---|---|
| 接続方式 | ローカル（stdio） | リモート（HTTP） |
| 利用場所 | インストールした PC のみ | Dify・n8n・Slack ボットなど、HTTP が届く場所ならどこからでも |
| チーム利用 | 各自がインストール | サーバー 1 台でチーム共有可能 |
| 自動化 | 難しい | n8n や Dify のワークフローで定期実行できる |

> **stdio（標準入出力）での接続には対応していません。** HTTP 接続専用です。

---

## この README の読み方

**あなたの役割によって、読むべきセクションが違います。**

| あなたの役割 | 読むところ |
|---|---|
| **利用者**（マーケター・ディレクターなど）<br>URL とトークンをもらって Dify / n8n を設定する人 | [利用者ガイド](#利用者ガイド) → [Dify での設定](#dify-での設定) or [n8n での設定](#n8n-での設定) → [よくあるつまずき](#よくあるつまずき) |
| **管理者**（エンジニア）<br>サーバーを立てて URL とトークンを発行する人 | [管理者ガイド](#管理者ガイドサーバー構築) → 利用者にも目を通す |

---

## 利用者ガイド

> **管理者（エンジニア）にサーバーを立ててもらうと、以下の情報がもらえます。設定手順は複雑に見えるかもしれませんが、AI（ChatGPT・Gemini など）に手順を見せながら聞けば、一つずつ進められます。**

### 事前に準備するもの

| 準備するもの | 説明 | 誰が用意するか |
|---|---|---|
| **MCP サーバーの URL** | Dify / n8n に入力する接続先。例: `https://analytics-mcp.example.com/mcp` | 管理者からもらう |
| **Bearer トークン** | 認証用の文字列（パスワードのようなもの） | 管理者からもらう |
| **GA4 プロパティ ID** | 分析対象のプロパティの数値。例: `123456789` | 管理者からもらう |
| **AI モデルの API キー** | Dify / n8n のチャットボットが考えるための AI。OpenAI（GPT）、Google（Gemini）、Anthropic（Claude）などから選ぶ | 自分で契約・取得する（または管理者に相談） |

上の 4 つがそろえば、Dify / n8n の設定に進めます。

> **AI モデルの API** は、Dify なら「モデルプロバイダー」、n8n なら LLM ノードで設定します。AI モデルが「どのツールを呼ぶか」「結果をどう説明するか」を判断します。

---

## Dify での設定

Dify の **Tools → MCP → Add MCP Server (HTTP)** から登録します。（日本語 UI では「ツール → MCP → MCP サーバーを追加」）

> Dify は HTTP トランスポートの MCP のみに対応しています。このサーバーはその前提と一致します。
> 参照: [Using MCP Tools（Dify 公式）](https://docs.dify.ai/en/use-dify/build/mcp)

![Dify の MCP サーバー追加画面](./docs/images/dify-add-mcp-server.png)

### 手順

1. **Tools → MCP** で **Add MCP Server (HTTP)** を選ぶ
2. **Server URL** に、管理者からもらった URL を入力する
   - 例: `https://analytics-mcp.example.com/mcp`
   - 末尾の `/mcp` を忘れずに
3. **Name** と **Server ID** を入力する（Server ID は一度決めたら変更しない）
4. **Bearer 認証のヘッダーを設定する**（管理者からトークンをもらっている場合）
   - 名前: `Authorization`
   - 値: `Bearer ＜トークン＞`（`Bearer` の後に半角スペース 1 つ、続けてトークン）
   - ヘッダー設定欄が見当たらない場合は Dify のバージョンが古い可能性があります。[2025年9月にマージ](https://github.com/langgenius/dify/pull/24760)された機能のため、アップデートを検討してください
5. 保存して、ツール一覧が表示されることを確認する
6. エージェント / ワークフローからツールを呼べるか試す

### エージェントのシステムプロンプト（推奨）

AI の精度を上げるため、**システムプロンプト**を設定することをおすすめします。

- コピー用プロンプト: [docs/dify-system-prompt-ga4-mcp-tools.md](./docs/dify-system-prompt-ga4-mcp-tools.md)
- ツール名・引数の形式・ガードレールが含まれており、AI の取り違いや余計な推測を減らせます
- プロパティ ID や組織固有の言い回しは Dify 側で追記・差し替えしてください

### Dify でよくあるエラー

#### 「Failed to discover OAuth metadata from server」

Dify が Bearer の不一致で HTTP 401 を受け取ると、OAuth メタデータを探しに行きます。このサーバーは OAuth ではなく Bearer のみなので、このエラーになります。

**多くの場合、トークンが正しく届いていないことが原因です。**

1. `Authorization` の値が `Bearer ＜トークン＞` になっているか確認（`Bearer` の後に半角スペース 1 つ）
2. 管理者に `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403` の設定を依頼すると、このエラーが出にくくなります

#### Bearer が 403 になる

- 値の形式: `Bearer ` + 半角スペース 1 つ + トークン（`Bearer` だけ、トークンだけでは不可）
- ターミナルからコピーしたとき、行末の `%` は zsh の表示であってトークンの一部ではありません
- Base64 の末尾 `=` はトークンの一部です（削らないこと）

---

## n8n での設定

n8n では **AI Agent ノード**に **AI モデル（Chat Model）** と **MCP Client** を接続して使います。

![n8n AI Agent + MCP Client の構成例](./docs/images/n8n-ai-agent-mcp-client.png)

- **MCP Client ノード** — ワークフローのステップとしてツールを実行
- **MCP Client Tool ノード** — AI エージェントにツールとして渡す

参照: [MCP Client node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcpClient/) / [MCP Client Tool node](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp/)

### 手順

1. **MCP Client** または **MCP Client Tool** をワークフローに配置する
2. **Server URL** に管理者からもらった URL を入力する
   - 例: `https://analytics-mcp.example.com/mcp`
3. **Bearer 認証**を設定する（Credentials で Bearer を選びトークンを入力、またはヘッダー認証で `Authorization: Bearer ＜トークン＞`）
4. ツール一覧が取得でき、エージェントから GA4 ツールが呼べることを確認する
5. 失敗時はノード出力の HTTP ステータスコードとメッセージを管理者に共有する

### 補足

- 接続エラーが続く場合は **n8n のバージョンを最新にする**ことで解消することがあります（MCP の Streamable HTTP 対応が進んでいるため）
- **HTTP Request ノード**で MCP の JSON-RPC を手動で組むのは非推奨です。**MCP Client（Tool）ノード**を使ってください
- エージェントで AI を使う場合、MCP とは別に **AI モデルの API 設定**（OpenAI・Vertex AI 等）が必要です

---

## よくあるつまずき

| 現象 | 確認すること |
|---|---|
| **401 Unauthorized** | Bearer トークンがサーバーと一致しているか。`Authorization: Bearer ＜トークン＞` の形式か |
| **403** | トークンの形式ミス（余計な改行・`%`）。上の [Dify でよくあるエラー](#dify-でよくあるエラー) を参照 |
| **Dify: Failed to discover OAuth metadata** | Bearer が届いていない。上の [Dify でよくあるエラー](#dify-でよくあるエラー) を参照 |
| **421 や接続できない** | `GA4MCP_ALLOWED_HOSTS` の設定ミス → 管理者に確認 |
| **ツールは出るがプロパティで拒否される** | プロパティ ID がサーバーの許可リストに入っているか → 管理者に確認 |
| **ready は成功だが GA4 が取れない** | Google 認証・API の有効化・サービスアカウント権限 → 管理者に確認 |
| **n8n + Gemini: `zod_to_gemini_parameters` エラー** | n8n と サーバーを最新版に更新する。`property_id` は `"123456789"` のように文字列で渡す |

---

## 管理者ガイド（サーバー構築）

> このセクションはサーバーを構築・運用するエンジニア向けです。

### 認証の全体像

| 何の認証か | どこに設定するか | 方法 |
|---|---|---|
| **MCP サーバー → GA4** | MCP サーバーの環境変数 | `GOOGLE_APPLICATION_CREDENTIALS` にサービスアカウント JSON のパスを指定。Cloud Run なら Workload Identity / ADC 推奨 |
| **Dify / n8n → MCP サーバー** | サーバーとクライアントの両方 | サーバー: `GA4MCP_AUTH_MODE=bearer` + `GA4MCP_BEARER_TOKEN`。クライアント: `Authorization: Bearer ＜同じトークン＞`。信頼できる経路のみ `GA4MCP_AUTH_MODE=none` も可 |
| **AI モデル（LLM）** | Dify / n8n 側 | Dify の「モデルプロバイダー」や n8n の LLM ノードで API キーを設定（このサーバーとは独立） |

### サーバー起動前の準備

1. **サーバーを起動**し、HTTPS（推奨）または HTTP でアクセスできるようにする
2. **環境変数を設定**する。[.env.example](./.env.example) を `cp .env.example .env` でコピーし、値を埋める
   - `GA4MCP_BEARER_TOKEN`: `./scripts/generate-bearer-token.sh` で生成（`bearer` モードで空だと起動しない）
   - `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403`: Dify 連携時に推奨
   - `GA4MCP_ALLOWED_PROPERTY_IDS`: 許可するプロパティ ID（カンマ区切り）
3. **本番環境では `GA4MCP_ALLOWED_HOSTS`** を設定する（DNS リバインディング対策。未設定だと接続がすべて失敗することがある）

### ヘルスチェック

- `GET /health` → サーバーが生きていれば成功
- `GET /ready` → 設定読み込みの確認のみ（GA4 API への到達性は初回ツール実行まで不明）

### Docker で動かす

```bash
docker build -t ga4-remote-mcp .
docker run --rm -p 8080:8080 \
  -e GA4MCP_ENV=production \
  -e GA4MCP_AUTH_MODE=bearer \
  -e GA4MCP_BEARER_TOKEN=＜./scripts/generate-bearer-token.sh の出力＞ \
  -e GA4MCP_BEARER_FAILURE_HTTP_STATUS=403 \
  -e GA4MCP_ALLOWED_HOSTS=＜クライアントが送る Host と同じ値＞ \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/sa.json \
  -v /path/to/sa.json:/secrets/sa.json:ro \
  ga4-remote-mcp
```

### Cloud Run にデプロイ

詳細: [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md) / [scripts/deploy-cloud-run.sh](./scripts/deploy-cloud-run.sh)

| 区分 | 必要なもの |
|---|---|
| **GCP** | デプロイ先プロジェクト、請求の有効化、API（Cloud Run、Cloud Build、Artifact Registry、Secret Manager） |
| **ランタイム SA** | Cloud Run に紐づけるサービスアカウント。GA4 プロパティに閲覧権限、必要に応じて Analytics Admin API が使えること。JSON 鍵よりも Workload Identity / ADC 推奨 |
| **環境変数** | `GA4MCP_ENV=production`、`GA4MCP_ALLOWED_PROPERTY_IDS`、本番では `GA4MCP_ALLOWED_HOSTS` |
| **Bearer（推奨）** | `GA4MCP_AUTH_MODE=bearer` + Secret Manager にトークン格納。Dify 連携では `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403` 推奨 |
| **デプロイ操作** | `./scripts/deploy-cloud-run.sh` を実行。`GCP_PROJECT_ID`、`GA4MCP_ALLOWED_PROPERTY_IDS`、`CLOUD_RUN_SERVICE_ACCOUNT`（推奨）、Bearer 利用時は `GA4MCP_BEARER_SECRET_NAME` を export |

デプロイ後、`gcloud run services describe` で公開 URL を確認し、`https://＜ホスト＞/mcp` を利用者に共有します。

---

## 公式ドキュメントとの対応

| 項目 | 内容 |
|---|---|
| **Dify のメニュー** | **Tools → MCP → Add MCP Server (HTTP)**。この README の手順と一致 |
| **Dify と HTTP** | Dify は HTTP トランスポートの MCP のみ対応。このサーバーは HTTP のみのため整合 |
| **Dify と Bearer** | カスタム HTTP ヘッダー機能は 2025年9月に本家マージ済み。古い Dify ではヘッダー欄がない場合あり → アップデート推奨 |
| **n8n のノード** | MCP Client / MCP Client Tool が公式ドキュメントに掲載。Bearer・ヘッダー・OAuth2 認証に対応 |
| **n8n とトランスポート** | Streamable HTTP 対応は n8n のバージョンアップに伴い進行中。接続できない場合はバージョンを確認 |

---

## ライセンス・開発者向け情報

- **ライセンス**: Apache License 2.0（[LICENSE](./LICENSE)）。Google 公式 [google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp) 由来部分は [NOTICE](./NOTICE)
- **Cloud Run デプロイ**: [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md) / [scripts/deploy-cloud-run.sh](./scripts/deploy-cloud-run.sh)
- **ローカル開発**: Python 3.10+。`pip install -e ".[dev]"` で依存をインストール、`pytest` / `ruff` で検証（`pyproject.toml` 参照）

### 運用メモ

- **グレースフルシャットダウン**: Uvicorn に `timeout_graceful_shutdown=30` 秒を指定。Kubernetes では `terminationGracePeriodSeconds` を 45〜60 程度に設定
- **ログと個人関連データ**: 構造化ログに接続元 IP が含まれることがあります。保持期間・アクセス制御・GDPR 等はデプロイ・運用側の責務です

---

*Issue や Pull Request での改善提案を歓迎します。*
