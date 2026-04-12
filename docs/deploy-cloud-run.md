# Cloud Run へのデプロイ

## デプロイ担当者に渡す情報（機密は平文で共有しない）

次を共有すれば作業できます。**パスワード・JSON 鍵・Bearer 文字列はチャットやメールに平文で貼らない**でください。

| 渡してよいもの | 例 |
|----------------|-----|
| **Google Cloud のプロジェクト ID** | `my-company-analytics` |
| **デプロイ先リージョン**（任意） | 未指定なら `asia-northeast1` を想定 |
| **許可する GA4 プロパティ ID** | `123456789`（複数はカンマ区切りで一覧として） |
| **Cloud Run 用ランタイム SA のメール**（推奨） | `ga4-mcp@PROJECT_ID.iam.gserviceaccount.com` |
| **Bearer を使うか** | 使う／使わない（使う場合、**値は Secret Manager に登録**し、名前だけ共有する） |

**平文で共有しないもの**

- サービスアカウント JSON の中身
- `GA4MCP_BEARER_TOKEN` の実値
- `gcloud` ログイン用のパスワード

## Google 側で先に済ませる作業（管理者）

1. **API 有効化**（プロジェクトで）: Cloud Run、Artifact Registry（または Container Registry）、Cloud Build（`gcloud run deploy --source` でビルドする場合）。
2. **ランタイム用サービスアカウント**を作成し、**GA4 プロパティに「閲覧者」等**（Analytics のデータ読取に必要なロール）を付与。
3. Cloud Run に **`--service-account=上記SA`** で紐付けると、**JSON 鍵を環境変数に載せずに** ADC 相当で動かせます。

## リポジトリを公開するときの注意

次の **実プロジェクトの固有値は、README・issue・サンプル `.env`・スクショに載せない**でください（プレースホルダに置き換える）。

- Google Cloud の **プロジェクト ID**
- **GA4 プロパティ ID** の一覧
- **サービスアカウントのメール**（特に実行用）
- Cloud Run の **実 URL**（`*.run.app`）
- **Bearer トークン**や Secret の実体

Bearer を誤って共有した場合は、**Secret Manager で新バージョンを追加**し古い値を使わないようにしてください。

## Bearer 認証のおすすめ（Secret Manager）

**平文で環境変数に `GA4MCP_BEARER_TOKEN` を直書き**すると、コンソール閲覧者に見えやすく、ログに漏れるリスクもあります。**Secret Manager にだけ値を置き**、Cloud Run から **シークレット参照**で注入する方法を推奨します。

1. **シークレット作成と IAM**（ローカルで 1 回。トークン本文はスクリプトが標準出力しません）

   ```bash
   cd /path/to/ga4-remote-mcp   # 本リポジトリのルート
   gcloud auth login   # 期限切れなら再ログイン
   export GCP_PROJECT_ID="YOUR_PROJECT_ID"
   export CLOUD_RUN_SERVICE_ACCOUNT="YOUR_RUN_SA@YOUR_PROJECT_ID.iam.gserviceaccount.com"
   export GA4MCP_BEARER_SECRET_NAME="ga4-remote-mcp-bearer"   # 任意の名前でよい
   chmod +x scripts/init-bearer-secret.sh
   ./scripts/init-bearer-secret.sh
   ```

2. **デプロイ**（同じシークレット名を渡す）

   ```bash
   export GCP_PROJECT_ID="YOUR_PROJECT_ID"
   export GA4MCP_ALLOWED_PROPERTY_IDS="123456789"
   export CLOUD_RUN_SERVICE_ACCOUNT="YOUR_RUN_SA@YOUR_PROJECT_ID.iam.gserviceaccount.com"
   export GA4MCP_BEARER_SECRET_NAME="ga4-remote-mcp-bearer"
   chmod +x scripts/deploy-cloud-run.sh
   ./scripts/deploy-cloud-run.sh
   ```

   デプロイ後、Cloud Run のサービスに `GA4MCP_AUTH_MODE=bearer` と、シークレット由来の `GA4MCP_BEARER_TOKEN` が載ります。

3. **Dify / n8n に渡すトークン**（**リポジトリに書かない**）

   プロジェクト管理者が端末でだけ実行し、表示された文字列をコピーして Dify の MCP ヘッダーまたは n8n の Credentials に貼る:

   ```bash
   gcloud secrets versions access latest --secret=ga4-remote-mcp-bearer --project=YOUR_PROJECT_ID
   ```

   ヘッダーは **`Authorization`**、値は **`Bearer ` のあとに上記トークン（スペース 1 つ）**。

4. **トークンを変えたいとき** … `init-bearer-secret.sh` をもう一度実行すると **新しいバージョン**が追加されます。Dify / n8n 側も同じ値に更新してください。

## ローカルからデプロイする（Bearer なしの最小例）

```bash
cd /path/to/ga4-remote-mcp   # 本リポジトリのルート
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

export GCP_PROJECT_ID="YOUR_PROJECT_ID"
export GA4MCP_ALLOWED_PROPERTY_IDS="123456789"
export CLOUD_RUN_SERVICE_ACCOUNT="ga4-mcp@YOUR_PROJECT_ID.iam.gserviceaccount.com"

chmod +x scripts/deploy-cloud-run.sh
./scripts/deploy-cloud-run.sh
```

出力された **URL** に `/mcp` を付けたものが MCP の Server URL です（例: `https://ga4-remote-mcp-xxxxx-an.a.run.app/mcp`）。

**Bearer あり**のときは上の「Bearer 認証のおすすめ」どおり `init-bearer-secret.sh` のあと、`GA4MCP_BEARER_SECRET_NAME` をセットして `deploy-cloud-run.sh` を実行してください。

## デプロイ後の確認

```bash
curl -sS "https://＜Cloud Run の URL＞/health"
curl -sS "https://＜Cloud Run の URL＞/ready"
```

## 本番で DNS 保護をオンにするとき

1. Cloud Run の **実際の Host**（`xxxx.run.app`）を `GA4MCP_ALLOWED_HOSTS` に設定。
2. `GA4MCP_ENABLE_DNS_REBINDING_PROTECTION=true` に更新。

`gcloud run services update ga4-remote-mcp --region=... --set-env-vars=...` またはコンソールの「変数とシークレット」で変更。

## アプリと Cloud Run の PORT

Cloud Run が注入する **`PORT`** をアプリが参照するようになっています（`cli.py`）。
