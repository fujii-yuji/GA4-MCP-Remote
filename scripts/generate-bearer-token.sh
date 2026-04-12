#!/usr/bin/env bash
# ランダムな Bearer 用トークンを標準出力に出す（パイプやクリップボード用）。
# リポジトリやチャットに貼らず、.env と Dify のみに使うこと。
set -euo pipefail
openssl rand -hex 32
