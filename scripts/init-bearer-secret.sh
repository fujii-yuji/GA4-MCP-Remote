#!/usr/bin/env bash
# Secret Manager に Bearer 用ランダムトークンを格納し、Cloud Run 実行 SA に accessor を付与する。
# トークン本文は標準出力に出さない。取得は:
#   gcloud secrets versions access latest --secret=＜名前＞ --project=＜プロジェクト＞
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?GCP_PROJECT_ID をセットしてください}"
SECRET="${GA4MCP_BEARER_SECRET_NAME:-ga4-remote-mcp-bearer}"
SA="${CLOUD_RUN_SERVICE_ACCOUNT:?CLOUD_RUN_SERVICE_ACCOUNT をセットしてください}"

gcloud config set project "$PROJECT_ID"
gcloud services enable secretmanager.googleapis.com --project "$PROJECT_ID"

TOKEN="$(openssl rand -base64 32)"
if gcloud secrets describe "$SECRET" --project "$PROJECT_ID" &>/dev/null; then
  echo -n "$TOKEN" | gcloud secrets versions add "$SECRET" --data-file=- --project "$PROJECT_ID"
  echo "Secret '$SECRET': 新しいバージョンを追加しました（直前のバージョンは無効化されていません）。"
else
  echo -n "$TOKEN" | gcloud secrets create "$SECRET" --data-file=- --replication-policy=automatic --project "$PROJECT_ID"
  echo "Secret '$SECRET': 新規作成しました。"
fi

gcloud secrets add-iam-policy-binding "$SECRET" \
  --project "$PROJECT_ID" \
  --member="serviceAccount:${SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet

echo ""
echo "Dify / n8n に設定するトークンを表示するコマンド（出力はパスワード同様に扱い、リポジトリに書かないでください）:"
echo "  gcloud secrets versions access latest --secret=${SECRET} --project=${PROJECT_ID}"
