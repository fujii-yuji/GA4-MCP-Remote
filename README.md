# ga4-remote-mcp

※本MCPは、Google公式のGA4 MCP([google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp))をフォークした、**非公式**のリモート MCP（HTTP）**です。

Google公式のGA4 MCPは、自然言語による柔軟な分析ができるツール郡になっていて、単にAIエージェントにAPI権限を渡して叩せるのとは違って適切なツールが呼ばるようになっています(とても便利です)。この便利なMCPをサーバー間や外部ツール間でも利用するためにリモートMCP化しているのが本プロジェクトです。

リモートMCPとして機能することで、Google公式MCPでは対応できない「Difyやn8nなどのAIワークフローツールからGA4 MCPを扱う」や「自社アプリから呼び出してSlackに通知する」など各種サーバー間でも使えるようになっています。

> **stdio（標準入出力）での接続には対応していません。** ブラウザやクラウドから届く HTTP 接続だけを想定しています。



## リモートMCPだと何がいいの？

**リモートMCPにすることで、Google AnalyticsのAI分析をシステム間での利用がしやすく、複数人でのチーム利用がしやすくなります。**

Google公式のGA4 MCPはローカルMCPなので、基本的にはPCにインストールしないといけないため、他のシステムから呼び出したりする用途には向いていません。

毎週月曜日に自動でAI分析の結果をSlackに送るとか、プロパティの権限をもっていない「偉い人」がSlackから自然言語で「最近の傾向は？」って聞いたりする用途で活躍すると思います。





---



## 準備が必要なこと

**このMCP ツールは、リモートMCP(外部から呼び出せるMCPサーバー)です。**  
**そのため、MCPサーバーのホスティング(実行環境)と、各種の認証情報を準備する必要があります**。  

### MCP サーバーの URL

Dify / n8n から**アクセス可能なサーバーを準備して、そこでMCPサーバーを起動し**、Dify / n8n から叩くURLを決めます。


| やること           | 内容                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------ |
| 1. 実行環境        | 社内サーバー、クラウドのコンテナ（Cloud Runがおすすめ）、など。 **クラウド上の Dify / n8n から**アクセス可能なURLを用意する。              |
| 2. 実行環境にデプロイする | ソースから起動するか、[Dockerfile](./Dockerfile) でイメージをビルドして実行する。 詳細は [サーバー側でやること](#サーバー側でやること管理者向け)。 |
| 3. URL を組み立てる  | `https://＜ホスト名＞/mcp` 上記の形式が基本。                                                             |


### 認証はどこに書くか

Dify/n8n がMCP サーバーに接続する権限、MCPサーバーからGA4の接続権限がそれぞれ設定必要です。  
その他にAIモデル(例: **gemini-3.1-pro-preview**)をDify/n8n で動かせるようにする権限設定も必要になります。


| 何のための認証か                        | どこに設定するか                                | 代表例                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **MCPサーバーからGA4へ**               | **MCP サーバー**                            | 環境変数 `GOOGLE_APPLICATION_CREDENTIALS` にサービスアカウント JSON のパス。 参考: `[.env.example](./.env.example)`。                                                                                                                                                                                                                                                               |
| **Dify / n8n など外部から MCP サーバーへ** | **サーバー側**と**クライアント側の両方**で **同じトークン**を使う | **サーバー**: `GA4MCP_AUTH_MODE=bearer` と `GA4MCP_BEARER_TOKEN`（環境変数または `.env`。**Git にコミットしない**）。 **Dify**: MCP 登録画面の **HTTP Header**に `Authorization` / `Bearer ＜トークン＞`（[手順](#dify-での設定)）。 **n8n**: MCP Client Tool ノードの **Credentials** で **HTTP Header** として設定する（[手順](#n8n-での設定)）。基本的に Bearer を推奨。**信頼できる経路のみ** `GA4MCP_AUTH_MODE=none` にすると Bearer は不要。 |


---

## 目次

1. [準備が必要なこと（URL と認証の整理）](#準備が必要なこと)
2. [事前にそろえるもの](#事前にそろえるもの)（[エージェント用 LLM API](#agent-llm-api) を含む）
3. [サーバー側でやること（管理者向け）](#サーバー側でやること管理者向け)（[Cloud Run で必要なもの](#cloud-run-deploy-prereqs)）
4. [Dify での設定](#dify-での設定)（[システムプロンプト例](#dify-system-prompt-ga4)）
5. [n8n での設定](#n8n-での設定)
6. [公式ドキュメントとの対応](#公式ドキュメントとの対応)
7. [よくあるつまずき](#よくあるつまずき)
8. [ライセンス・開発者向け情報](#ライセンス開発者向け情報)

---

## 事前にそろえるもの

**URL をまだ持っていない**場合は、先に [準備が必要なこと](#準備が必要なこと) の「MCP サーバーの URL」を読んでください。


| 項目                    | 内容                                                                                      |
| --------------------- | --------------------------------------------------------------------------------------- |
| **この MCP サーバーの URL**  | 例: `https://analytics-mcp.example.com/mcp`（**末尾は `/mcp` のまま**にしてください）。                  |
| **Google 側の認証**       | GA4 と Google Analytics Admin API にアクセスできる**サービスアカウント**（またはクラウド上の同等の認証）。サーバー起動環境で有効であること |
| **GA4 のプロパティ ID**     | 分析対象の数値（例: `123456789`）。サーバー管理者が「許可リスト」に登録する値と一致させます                                    |
| **Bearer トークン**       | Dify/n8nとMCP**サーバー間で**必要になります。 サーバーで「Bearer 認証」を無効にすることも可能ですが、基本的には設定必要です。              |
| **エージェント用 LLM の API** | **Dify / n8n 上でチャットやエージェントが使う推論 API**（OpenAI、Vertex AI、Anthropic 等）。                    |


**Allowlist（許可リスト）**  
プロパティ ID がサーバーの許可リストに入っていないと、レポート系のツールは実行されません。一覧取得だけ許したい場合も、管理者に「使うプロパティ ID」を伝えてください。

### エージェント用の LLM API（Dify / n8n 側）

**AI** エージェントが **どのツールをいつ呼ぶか・結果をどう説明するか**は、**Dify や n8n が接続している LLM**が担います。

- **LLM 用**: Dify の「モデルプロバイダー」や n8n の LLM ノードで指定する **API キー / Vertex の認証 / エンドポイント** … **推論・プランニング**向け。
- 利用するクラウドの組み合わせ（例: **Vertex AI で Dify のモデルを動かし、別 GCP プロジェクトの Cloud Run に本 MCP を置く**）はよくある構成です。**請求・IAM はプロバイダーごとのドキュメント**で確認してください。

---

## サーバー側でやること（管理者向け）

利用者が Dify / n8n から接続する**前に**、次ができている必要があります。

1. **サーバーを起動**し、インターネットまたは社内ネットワークから **HTTPS（推奨）または HTTP** で届くようにする。
2. **環境変数**で Google 認証・許可リスト・**Bearer（本番・公開前は推奨）**を設定する。具体例は [.env.example](./.env.example)。変数の意味は同ファイルと `src/ga4_remote_mcp/config/settings.py` を参照。トークン生成は `./scripts/generate-bearer-token.sh`。初回は `cp .env.example .env` のうえ **`GA4MCP_BEARER_TOKEN` を必ず埋める**（`bearer` のとき空では起動しません）。**Dify 連携では `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403` を推奨**（`deploy-cloud-run.sh` が Bearer 利用時に既定で付与）。
3. **本番で DNS リバインディング対策をオンにする場合**は、`Host` ヘッダーと一致する **`GA4MCP_ALLOWED_HOSTS`** を必ず設定する。未設定だと接続がすべて失敗することがあります。

**動作確認（任意）**

- `GET https://＜ホスト＞/health` → サーバーが生きていれば成功応答  
- `GET https://＜ホスト＞/ready` → **設定ファイルの読み込みが問題ないこと**のみを表します。**GA4 API まで届いている保証ではありません**（初回のツール実行で初めて分かることがあります）

**Docker で動かす例**（詳細は従来どおり `Dockerfile` を参照）

```bash
docker build -t ga4-remote-mcp .
docker run --rm -p 8080:8080 \
  -e GA4MCP_ENV=production \
  -e GA4MCP_AUTH_MODE=bearer \
  -e GA4MCP_BEARER_TOKEN=＜./scripts/generate-bearer-token.sh の出力＞ \
  -e GA4MCP_BEARER_FAILURE_HTTP_STATUS=403 \
  -e GA4MCP_ALLOWED_HOSTS=＜クライアントが送るHostと同じ値＞ \
  -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/sa.json \
  -v /path/to/sa.json:/secrets/sa.json:ro \
  ga4-remote-mcp
```

### Cloud Runの例: デプロイする場合に必要なもの

**手順の詳細**は [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md) と [scripts/deploy-cloud-run.sh](./scripts/deploy-cloud-run.sh) を正とします。ここでは **最低限そろえたいもの**だけ列挙します。


| 区分                 | 必要なもの                                                                                                                                                                                                                                                                   |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **GCP**            | デプロイ先 **プロジェクト**、**請求**の有効化、API（例: **Cloud Run**、**Cloud Build**（`gcloud run deploy --source` 利用時）、**Artifact Registry**、**Secret Manager**（Bearer をシークレットで載せる場合））。                                                                                                     |
| **実行身份（ランタイム SA）** | Cloud Run サービスに紐づける **サービスアカウント**。**GA4 プロパティに閲覧権限**、必要に応じて **Analytics Admin API** が使えること。JSON 鍵をコンテナに直置きせず **Workload Identity / デフォルト認証**で済ませるのが望ましい（上記 deploy ドキュメント参照）。                                                                                            |
| **環境変数（代表）**       | `GA4MCP_ENV=production`、`GA4MCP_ALLOWED_PROPERTY_IDS`（カンマ区切り）、本番で DNS 保護をオンにするなら **`GA4MCP_ALLOWED_HOSTS`**（クライアントが送る `Host` と一致）。詳細は [.env.example](./.env.example)。                                                                                                         |
| **Bearer（推奨）**     | `GA4MCP_AUTH_MODE=bearer` とトークン。**Secret Manager** に格納し Cloud Run から参照する流れが [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md) にあります。スクリプト利用時は `GA4MCP_BEARER_SECRET_NAME` を指定。**Dify 連携では `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403` を推奨**（当スクリプトが Bearer 利用時に既定で付与）。 |
| **デプロイ操作**         | `gcloud` ログイン済み端末から `./scripts/deploy-cloud-run.sh` を実行する場合、少なくとも **`GCP_PROJECT_ID`**、**`GA4MCP_ALLOWED_PROPERTY_IDS`**、**`CLOUD_RUN_SERVICE_ACCOUNT`**（推奨）、Bearer 利用時は **`GA4MCP_BEARER_SECRET_NAME`** を export（スクリプト先頭のコメント参照）。                                      |


デプロイ後、コンソールまたは `gcloud run services describe` で **公開 URL** を確認し、**`https://＜ホスト＞/mcp`** を Dify / n8n の MCP Server URL に設定します。

---

## Dify での設定

Dify 公式ドキュメントでは、ワークスペースで **Tools → MCP** を開き、**Add MCP Server (HTTP)**（HTTP で MCP サーバーを追加）から登録する流れになっています。日本語 UI では「ツール」「MCP」「MCP サーバーを追加」など、同じ意味のメニュー名になります。

> Dify は現時点で **HTTP トランスポートの MCP サーバー**のみ接続対象です。本サーバーはその前提と一致します。  
> 参照: [Using MCP Tools（Dify 公式）](https://docs.dify.ai/en/use-dify/build/mcp)

### エージェントのシステムプロンプト（GA4 分析向け）

Dify の **エージェント / アプリ**に、この MCP の **ツール名・引数（snake_case）・ガードレール**を踏まえた指示を載せると、取り違いや余計な推測が減ります。

- **コピー用プロンプト（Markdown）**: [docs/dify-system-prompt-ga4-mcp-tools.md](./docs/dify-system-prompt-ga4-mcp-tools.md)  
  - 役割、共通ルール、ツールの選び方、取得後の分析のしかた、Dify 向けの注意などを **システムプロンプトとして貼れる形**でまとめています。  
  - 利用中の **プロパティ ID や組織固有の言い回し**は、Dify 側で追記・差し替えしてください。

**LLM プロバイダー（Vertex AI 等）の設定**は Dify のモデル管理にあります。[事前にそろえるもの](#agent-llm-api) の「エージェント用 LLM API」とあわせて確認してください。

### 手順

1. **Tools → MCP** で **Add MCP Server (HTTP)** を選ぶ。
2. **Server URL** に次の形式で入力する。
  `https://＜あなたのドメイン＞/mcp`  
   公式の例も `https://api.notion.com/mcp` のように **パスが `/mcp` で終わる URL** です。末尾スラッシュの要否は Dify やリバースプロキシの設定で差が出ることがあるため、うまくいかないときは管理者に相談してください。
3. **Name**、**Server ID**（一度決めたら変更しない／公式も同趣旨）など、画面の指示どおり入力する。
4. サーバーで **Bearer 認証**（`GA4MCP_AUTH_MODE=bearer`）を使っている場合、Dify 側で **カスタム HTTP ヘッダー**を追加する。
  - 名前: `Authorization`  
  - 値: `Bearer ＜サーバー管理者から共有されたトークン＞`  
   （先頭の `Bearer` のあとに **半角スペース 1 つ**、そのあとトークン）  
   **ヘッダーを MCP 登録画面で設定する機能**は、Dify 本家リポジトリに **2025年9月頃**マージされています（[該当プルリクエスト](https://github.com/langgenius/dify/pull/24760)）。画面にヘッダー欄が無い場合は、**Dify のバージョンが古い**可能性が高いのでアップデートを検討してください。
5. 保存後、ツール一覧が取得できるか、エージェント／ワークフローから呼べるか試す。
6. エラー時は [よくあるつまずき](#よくあるつまずき) と、Dify のエラーメッセージを管理者に共有する。

### 補足

- エージェントで GA4 を触らせる場合、そのアプリで **この MCP のツールが有効**か確認してください。
- **401** のときは Bearer の誤り、`Bearer`  の欠けが多いです。
- OAuth 連携が必要な MCP（例: 一部の SaaS）とは異なり、本サーバーは **共有トークン（Bearer）または認証なし**の想定です。

### 「Failed to discover OAuth metadata from server」が出るとき（Dify）

Dify（本家実装）は、MCP への接続で **HTTP 401** を受け取ると **OAuth のメタデータ（`/.well-known/...`）を取りに行く**動きになります。本サーバーは **OAuth ではなく共有 Bearer だけ**なので、メタデータは存在せず、このエラーになりやすいです。

**多くの場合、根本原因は「Bearer がサーバーに届いていない／一致していない」**です（トークン誤り、ヘッダー値の末尾スペース、`Authorization` の書き方など）。次を確認してください。

1. **ヘッダー**で `Authorization` の値が **`Bearer ` + トークン**（`Bearer` の直後に半角スペース 1 つ。前後に余計な空白なし）か。
2. **認証**タブの **動的クライアント登録を OFF** にできるなら OFF（UI で戻る場合は [Dify 側の不具合の可能性](https://github.com/langgenius/dify/issues) もあります）。
3. サーバー側で **Bearer 不一致時の HTTP ステータスを 403 にする**と、Dify が OAuth ルートに入りにくくなり、メッセージが紛らわしくなくなることがあります。環境変数 **`GA4MCP_BEARER_FAILURE_HTTP_STATUS=403`**（デフォルトは `401`）。Cloud Run ならデプロイ後にコンソールで環境変数を追加するか、`deploy-cloud-run.sh` 用の env に同キーを足してください。

**正しい Bearer で接続できていれば 401/403 は返らない**ため、このエラー自体は出ません。

### Bearer が 403 になるとき（Dify・クライアント側の見落とし）

- 値は **`Bearer ` + 半角スペース 1 つ + トークン**（`Bearer` だけ・トークンだけは不可）。
- ターミナルからコピーしたとき、行末の **`%` は zsh の表示でトークンではない**（余計に貼らない）。base64 の末尾 **`=` はトークンの一部**。
- トークンは `gcloud secrets versions access ... | tr -d '\n\r'` のように **改行なし**で取り直すと安全。
- `curl` で試すときは **`Accept: application/json, text/event-stream`** も付ける（無いと **406** になり、Bearer 成否とは別問題に見えることがある）。

---

## n8n での設定

n8n 公式ドキュメントでは、次のノードが外部 MCP サーバーのツールを使うためのエントリです。

- **MCP Client ノード** … ワークフローの通常ステップとしてツールを実行  
- **MCP Client Tool ノード** … AI エージェントにツールとして渡す

いずれも **Credentials** で **Bearer**、**Generic Header**、**OAuth2** などの認証方式に対応している、と記載されています。  
参照: [MCP Client node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcpClient/) / [MCP Client Tool node](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp/)

### 手順

1. 上記の **MCP Client** または **MCP Client Tool** をワークフローに配置する。
2. **サーバー URL**（または同等の項目）に次を設定する。
  `https://＜あなたのドメイン＞/mcp`
3. サーバーで **Bearer 認証**を使っている場合、**Credentials** で Bearer を選びトークンだけを入れるか、ヘッダー認証で `Authorization` に `Bearer ＜トークン＞` を指定する（ノード・バージョンで画面が異なります）。
4. 実行してツール一覧が取得できるか、エージェントから GA4 系ツールが呼べるか確認する。
5. 失敗時はノード出力の **HTTP ステータスコード**とメッセージを管理者に渡す。

### 補足

- 本サーバーは MCP の **HTTP 上のトランスポート**（いわゆる Streamable HTTP）で `/mcp` に応答します。MCP の仕様では従来の SSE 方式からの移行が進んでおり、**n8n もバージョンアップに伴い接続まわりが更新されています**。接続エラーが続く場合は **n8n を可能な範囲で新しめの安定版**にしてから再試行してください。
- **HTTP Request ノードだけ**で MCP の JSON-RPC 手順を真似するのは手間と不整合が出やすいので、**MCP Client（Tool）ノードの利用を推奨**します。
- **エージェントが LLM を使う構成**の場合、**MCP とは別に**チャットモデル用の **Credentials / API**（OpenAI、Azure、Vertex 等）が必要です。[事前にそろえるもの](#agent-llm-api) を参照。GA4 向けの指示文は [Dify 用と同じプロンプト例](./docs/dify-system-prompt-ga4-mcp-tools.md) を流用・調整できます。

---

## 公式ドキュメントとの対応

次表は、公開ドキュメントに基づく対応関係の例です。製品の UI はアップデートで変わるため、**最終的には各公式ドキュメントを優先**してください。


| 項目                | 内容                                                                                                                                                 |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Dify のメニュー**    | 公式: **Tools → MCP** → **Add MCP Server (HTTP)**。README の手順と一致。                                                                                     |
| **Dify の URL 例**  | 公式例は `https://api.notion.com/mcp` の形式。**`/mcp` パス**でよい、という README の書き方は妥当。                                                                         |
| **Dify と HTTP**   | 公式に「現時点では HTTP トランスポートの MCP のみ」とある。本サーバーは HTTP のみのため整合。                                                                                            |
| **Dify と Bearer** | カスタム **HTTP ヘッダー**を MCP プロバイダーに付けられる変更が **2025年9月に本家へマージ**済み。それ以前の Dify ではヘッダー欄が無く、Bearer 設定が難しい可能性がある → **アップデート推奨**。                             |
| **n8n のノード名**     | 公式ドキュメントに **MCP Client** / **MCP Client Tool** が掲載。Bearer・ヘッダー・OAuth2 の認証に対応、とある。README と一致。                                                       |
| **n8n とトランスポート**  | 公式のノード説明だけでは SSE と Streamable HTTP の表の違いまでは細かく書かれていないが、コミュニティ・開発側の議論では **Streamable HTTP への対応**が進行中。接続できない場合は **n8n のバージョン**を疑う、という README の注意は妥当。 |


---

## よくあるつまずき


| 現象                                                                                        | 確認すること                                                                                                                                                                                                                                                   |
| ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **401 Unauthorized**                                                                      | Bearer をサーバーと同じにしたか。`Authorization: Bearer` の形式か。                                                                                                                                                                                                        |
| **403（Dify など）**                                                                          | `Authorization: Bearer …` の形式・トークン一致・余計な文字（改行・`%`）。Dify 節の「Bearer が 403 になるとき」を参照。                                                                                                                                                                       |
| **Dify: Failed to discover OAuth metadata**                                               | [Dify での設定](#dify-での設定) の「OAuth metadata」小見出しを参照。多くは Bearer 不達／不一致。必要なら `GA4MCP_BEARER_FAILURE_HTTP_STATUS=403`。                                                                                                                                         |
| **421 や接続できない（本番のみ多い）**                                                                   | サーバーの `GA4MCP_ALLOWED_HOSTS` と、ブラウザ／クライアントが送る **Host** が一致しているか（管理者向け）。                                                                                                                                                                                  |
| **ツールは出るがプロパティで拒否される**                                                                    | そのプロパティ ID がサーバーの **許可リスト**に入っているか。                                                                                                                                                                                                                      |
| **ready は成功だが GA4 が取れない**                                                                 | Google の認証・API の有効化・サービスアカウントの GA4 権限はサーバー側の問題です。`/ready` はそれらをチェックしません。                                                                                                                                                                                 |
| **n8n + Vertex（Gemini）: `zod_to_gemini_parameters` / `anyOf` / `discriminatedUnion` エラー** | MCP ツールの JSON Schema が **整数と文字列の共用体**になると Gemini 側の変換に失敗することがあります。本リポジトリでは **`property_id` を文字列型のみ**にそろえてあります。**最新のサーバーに更新**し、`property_id` は `"123456789"` のように **JSON 文字列**で渡す。まだ出るツールがある場合は MCP Client Tool の **Tools to Include** で当該ツールを一時除外して切り分け。 |


---

## ライセンス・開発者向け情報

- **ライセンス**: Apache License 2.0（[LICENSE](./LICENSE)）。Google 公式 [google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp) 由来部分は [NOTICE](./NOTICE)。
- **Google Cloud Run へのデプロイ**: [docs/deploy-cloud-run.md](./docs/deploy-cloud-run.md) と [scripts/deploy-cloud-run.sh](./scripts/deploy-cloud-run.sh)
- **ローカル開発**: Python 3.10 以上。`pip install -e ".[dev]"` のうえ `pytest` / `ruff` を利用（`pyproject.toml` 参照）。

### 運用メモ（シャットダウン・ログ）

- **グレースフルシャットダウン**: 本サーバーの起動（`ga4_remote_mcp.cli:main`）では Uvicorn に **`timeout_graceful_shutdown=30`**（秒）を指定しています。進行中のリクエスト完了待ちに最大 30 秒かかります。Kubernetes では Pod の **`terminationGracePeriodSeconds`** を **少なくとも 45〜60** 程度にし、PreStop などとあわせてコンテナ停止に余裕を持たせてください。
- **ログと個人関連データ**: `/mcp` 経路の構造化ログに **接続元 IP**（または信頼できるプロキシ経由の `X-Forwarded-For` 先頭）が含まれることがあります。**保持期間・アクセス制御・GDPR 等はデプロイ・運用側の責務**です。必要に応じてログ基盤でのマスキングや保存期間ポリシーを設定してください。

---

*README の改善案は Issue や Pull Request で歓迎します。*