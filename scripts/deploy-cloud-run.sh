#!/usr/bin/env bash
# Cloud Run へソースからビルド・デプロイする例（gcloud がログイン済みであること）
#
# 使い方:
#   export GCP_PROJECT_ID="your-project-id"
#   export GA4MCP_ALLOWED_PROPERTY_IDS="123456789"   # 複数はカンマ区切りで 1 つの値として渡す
#   export CLOUD_RUN_SERVICE_ACCOUNT="xxx@PROJECT.iam.gserviceaccount.com"  # 推奨（GA4 権限付き SA）
#   # Bearer を Secret Manager 経由で渡す場合（推奨）:
#   export GA4MCP_BEARER_SECRET_NAME="ga4-remote-mcp-bearer"
#   ./scripts/deploy-cloud-run.sh
#
# 初回テスト用に GA4MCP_ENABLE_DNS_REBINDING_PROTECTION=false。本番では許可ホスト設定後に true 推奨。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROJECT_ID="${GCP_PROJECT_ID:?環境変数 GCP_PROJECT_ID をセットしてください}"
REGION="${GCP_REGION:-asia-northeast1}"
SERVICE="${CLOUD_RUN_SERVICE:-ga4-remote-mcp}"
ALLOWED="${GA4MCP_ALLOWED_PROPERTY_IDS:?GA4MCP_ALLOWED_PROPERTY_IDS をセット（例: 123456789 または 111,222）}"

ENV_FILE="$(mktemp)"
trap 'rm -f "$ENV_FILE"' EXIT

# --set-env-vars は値にカンマがあると壊れるため YAML ファイルを使う
cat >"$ENV_FILE" <<EOF
GA4MCP_ENV: production
GA4MCP_PORT: "8080"
GA4MCP_ENABLE_DNS_REBINDING_PROTECTION: "false"
GA4MCP_LOG_LEVEL: INFO
GA4MCP_ALLOWED_PROPERTY_IDS: "${ALLOWED}"
GA4MCP_ALLOW_ALL_PROPERTIES: "false"
EOF

# Bearer + Dify 向け: 不一致時はデフォルト 403（401 だと OAuth メタデータ探索に寄りやすい）
if [[ -n "${GA4MCP_BEARER_SECRET_NAME:-}" ]]; then
  echo "GA4MCP_AUTH_MODE: bearer" >>"$ENV_FILE"
  BF_STATUS="${GA4MCP_BEARER_FAILURE_HTTP_STATUS:-403}"
  echo "GA4MCP_BEARER_FAILURE_HTTP_STATUS: \"${BF_STATUS}\"" >>"$ENV_FILE"
fi

echo "Project=$PROJECT_ID Region=$REGION Service=$SERVICE"

gcloud config set project "$PROJECT_ID"

DEPLOY_ARGS=(
  gcloud run deploy "$SERVICE"
  --region="$REGION"
  --source=.
  --platform=managed
  --allow-unauthenticated
  --port=8080
  --memory=512Mi
  --timeout=300
  --max-instances=3
  --env-vars-file="$ENV_FILE"
)
if [[ -n "${CLOUD_RUN_SERVICE_ACCOUNT:-}" ]]; then
  DEPLOY_ARGS+=(--service-account="$CLOUD_RUN_SERVICE_ACCOUNT")
fi

if [[ -n "${GA4MCP_BEARER_SECRET_NAME:-}" ]]; then
  DEPLOY_ARGS+=(
    --update-secrets="GA4MCP_BEARER_TOKEN=${GA4MCP_BEARER_SECRET_NAME}:latest"
  )
fi

"${DEPLOY_ARGS[@]}"

echo "Deployed. Service URL:"
gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)'
