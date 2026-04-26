**[English](./README.md)** | **日本語**

# ga4-remote-mcp

Google 公式の GA4 MCP（[google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp)）を**リモート MCP（HTTP）化**した、**非公式**プロジェクトです。

## このツールでできること

GA4 のデータを使った **AI チャットボットや自動レポート** を、Dify・n8n・Slack などと組み合わせて作れます。


| できること               | 例                                                  |
| ------------------- | -------------------------------------------------- |
| チームで共有              | サーバー 1 台を立てれば、メンバー全員が同じ AI 分析環境を使える。PC ごとのインストール不要 |
| **定期レポートの自動化**      | 「週末に先週との変化をAIがレポート作って Slack に投稿」するワークフローを作る        |
| **GA4 の権限がない人でも分析** | Slack ボットや社内チャットから自然言語で聞けるので、GA4 にログインできなくても使える。見せたくないデータはシステムプロンプトでマスクすることも可能 |
| **自然言語で GA4 に質問**   | 「流入元別の分析をして」や「季節変動を除いた過去半年の分析をして」と聞くだけで回答が返る       |


### 公式 MCP との違い


|       | Google 公式 GA4 MCP | ga4-remote-mcp（このプロジェクト）                |
| ----- | ----------------- | --------------------------------------- |
| 接続方式  | ローカル（stdio）       | リモート（HTTP）                              |
| 利用場所  | インストールした PC で動く   | Dify・n8n・Slack ボットなど、HTTP が届く場所ならどこからでも |
| チーム利用 | 各自がインストール         | サーバー 1 台でチーム共有可能                        |
| 自動化   | インストールしたPC内で可能    | クラウドから実行可能なので、n8n や Dify のワークフローで利用できる  |


---

## この README の読み方

**あなたの役割によって、読むべきセクションが違います。**


| あなたの役割                                                   | 読むところ                                                                                        |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **利用者**（マーケター・ディレクターなど） URL とトークンをもらって Dify / n8n を設定する人 | [利用者ガイド](#利用者ガイド) → [Dify での設定](#dify-での設定) or [n8n での設定](#n8n-での設定) → [よくあるつまずき](#よくあるつまずき) |
| **管理者**（エンジニア） サーバーを立てて URL とトークンを発行する人                  | [管理者ガイド](#管理者ガイドサーバー構築) → 利用者にも目を通す                                                          |


---

## 利用者ガイド

> **管理者（エンジニア）にサーバーを立ててもらうと、以下の情報がもらえます。設定手順は複雑に見えるかもしれませんが、AI（ChatGPT・Gemini など）に手順を見せながら聞けば、一つずつ進められます。**

### 事前に準備するもの


| 準備するもの             | 説明                                                                                | 誰が用意するか                                                      |
| ------------------ | --------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **MCP サーバーの URL**  | Dify / n8n に入力する接続先。                                                              | 管理者からもらう                                                     |
| **Bearer トークン**    | 認証用の文字列 （パスワードのようなもの）                                                             | 管理者からもらう                                                     |
| **GA4 プロパティ ID**   | 分析対象のプロパティの数値。                                                                    | GA4を見て確認                                                     |
| **AI モデルの API キー** | MCPから取得データを分析するための AIをAPIから利用できるにする必要があります。GeminiやClaude、GPTなど、利用しやすいものを準備してください。 | 自分で契約・取得するか、管理者に相談してください。無料APIは、学習利用されることがあるので業務用としては非推奨です。 |


---

## Dify で使う場合の例

Dify の **Tools → MCP → Add MCP Server (HTTP)** から登録します。  
（日本語 UI では「ツール → MCP → MCP サーバーを追加」）

![Dify の MCP サーバー追加画面](./docs/images/dify-add-mcp-server.png)

### 手順

1. **DIfyの Tools → MCP** → **Add MCP Server (HTTP)** を選ぶ
2. **Server URL** に、管理者からもらった URL を入力する
3. **Name** と **Server ID** を入力する（名前は自由に設定できますが、Server ID は一度決めたら変更しないこと）
4. **認証→ヘッダーを選択**して、以下を設定する
  - 名前: `Authorization`
  - 値: `Bearer ＜トークン＞`（トークンの値の前に`Bearer` という文字列と半角スペース 1 つ入ります）
5. 保存して、ツール一覧が表示されることを確認する
6. チャットまたはワークフローからツールを呼べるか試してください

### エージェントのシステムプロンプト（推奨）

AI の精度を上げるため、**システムプロンプト**を設定することをおすすめします。

- システムプロンプトの例: [docs/dify-system-prompt-ga4-mcp-tools.md](./docs/dify-system-prompt-ga4-mcp-tools.md)
- 自由に設定できますが、例を参考にしてください。
- プロパティ固有、組織固有の質問に答えられるような情報を追記することをおすすめします。

### Dify でよくあるエラー

#### 「Failed to discover OAuth metadata from server」

1. `Authorization` の値が `Bearer ＜トークン＞` になっているか確認

#### Bearer が 403 になる

- `Authorization` の値が `Bearer ＜トークン＞` になっているか確認
- 行末に `%` が入っていたら、コピーミスです。行末の%はトークンの一部ではありません
- 末尾 `=` はトークンの一部なので削らないこと

---

## n8n で使う場合の例

![n8n AI Agent + MCP Client の構成例](./docs/images/n8n-ai-agent-mcp-client.png)

※ノード名や設定名は日々変わるので、最新の情報を確認してください。

### 手順

1. Credentials で Bearer を選びトークンを入力する。
2. Credentials で API利用するAIの接続設定をする。 
3. **AIエージェントノードにMCP Client** 、AIモデル(会話モデル)の2つのノードを接続してワークフローに配置する
4. **MCP Client** に手順1のCredentialsを設定し、**Server URL** に管理者からもらった URL を入力。
5. AIモデル(会話モデル)に手順2のCredentialsを設定。
6. **AIエージェントノードにユーザープロンプトとシステムプロンプトを設定する。**
   システムプロンプトの例: [docs/dify-system-prompt-ga4-mcp-tools.md](./docs/dify-system-prompt-ga4-mcp-tools.md)
7. 必要な他のノードを設定(Slackから入力を受ける等)してテストしてください。



---

---

## 管理者ガイド（サーバー構築）

> このセクションはサーバーを構築・運用するエンジニア向けです。

### 認証の全体像


| 何の認証か                     | どこに設定するか       | 方法                                                                                                |
| ------------------------- | -------------- | ------------------------------------------------------------------------------------------------- |
| **MCP サーバー → GA4**        | MCP サーバーの環境変数  | `GOOGLE_APPLICATION_CREDENTIALS` にサービスアカウント JSON のパスを指定。 Cloud Run なら Workload Identity / ADC 推奨  |
| **Dify / n8n → MCP サーバー** | サーバーとクライアントの両方 | サーバー: `GA4MCP_AUTH_MODE=bearer` + `GA4MCP_BEARER_TOKEN`。クライアント: `Authorization: Bearer ＜同じトークン＞`。 |
| **AI モデル（LLM）**           | Dify / n8n 側   | Dify の「モデルプロバイダー」や n8n の LLM ノードで API キーを設定                                                       |


### サーバー起動前の準備

1. **サーバーを起動**し、HTTPS（推奨）または HTTP でアクセスできるようにする
2. **環境変数を設定**する。
  - `GA4MCP_BEARER_TOKEN`: `./scripts/generate-bearer-token.sh` で生成（`bearer` モードで空だと起動しない）
  - `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403`: Dify 連携時に推奨
  - `GA4MCP_ALLOWED_PROPERTY_IDS`: 許可するプロパティ ID（カンマ区切り）
3. **本番環境では `GA4MCP_ALLOWED_HOSTS`** を設定する（DNS リバインディング対策。未設定だと接続がすべて失敗することがある）

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

### Cloud Run で動かす例

詳細: [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md) / [scripts/deploy-cloud-run.sh](./scripts/deploy-cloud-run.sh)


| 区分             | 必要なもの                                                                                                                                                               |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **GCP**        | デプロイ先プロジェクト、請求の有効化、API（Cloud Run、Cloud Build、Artifact Registry、Secret Manager）                                                                                      |
| **ランタイム SA**   | Cloud Run に紐づけるサービスアカウント。GA4 プロパティに閲覧権限、必要に応じて Analytics Admin API が使えること。JSON 鍵よりも Workload Identity / ADC 推奨                                                      |
| **環境変数**       | `GA4MCP_ENV=production`、`GA4MCP_ALLOWED_PROPERTY_IDS`、本番では `GA4MCP_ALLOWED_HOSTS`                                                                                   |
| **Bearer（推奨）** | `GA4MCP_AUTH_MODE=bearer` + Secret Manager にトークン格納。Dify 連携では `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403` 推奨                                                             |
| **デプロイ操作**     | `./scripts/deploy-cloud-run.sh` を実行。`GCP_PROJECT_ID`、`GA4MCP_ALLOWED_PROPERTY_IDS`、`CLOUD_RUN_SERVICE_ACCOUNT`（推奨）、Bearer 利用時は `GA4MCP_BEARER_SECRET_NAME` を export |


デプロイ後、`gcloud run services describe` で公開 URL を確認し、`https://＜ホスト＞/mcp` を利用者に共有します。

---

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