#!/bin/bash

# Cloud Run 배포 확인 스크립트
# 사용법: ./check_deployment.sh

set -e

PROJECT_ID="etf-rag-agent"
SERVICE_NAME="etf-rag-agent"
REGION="asia-northeast3"

echo "========================================"
echo "🔍 Cloud Run 배포 상태 확인"
echo "========================================"

# 서비스 URL 가져오기
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --format 'value(status.url)' 2>/dev/null)

if [ -z "$SERVICE_URL" ]; then
    echo "❌ 서비스를 찾을 수 없습니다."
    echo "   배포를 먼저 실행하세요: ./deploy_cloudrun.sh"
    exit 1
fi

echo ""
echo "🌐 서비스 URL: ${SERVICE_URL}"
echo ""

# 헬스체크
echo "📊 헬스체크 테스트..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/api/health")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 헬스체크 성공 (HTTP ${HTTP_CODE})"
    curl -s "${SERVICE_URL}/api/health" | jq '.'
else
    echo "❌ 헬스체크 실패 (HTTP ${HTTP_CODE})"
fi

echo ""
echo "📝 최근 로그 (마지막 10줄):"
echo "----------------------------------------"
gcloud run services logs read ${SERVICE_NAME} \
    --region ${REGION} \
    --limit 10 \
    --format "table(timestamp,severity,textPayload)"

echo ""
echo "========================================"
echo "🔗 유용한 링크"
echo "========================================"
echo ""
echo "📊 Cloud Run 콘솔:"
echo "   https://console.cloud.google.com/run/detail/${REGION}/${SERVICE_NAME}/metrics?project=${PROJECT_ID}"
echo ""
echo "📝 로그 뷰어:"
echo "   https://console.cloud.google.com/logs/query?project=${PROJECT_ID}"
echo ""
echo "💰 빌링:"
echo "   https://console.cloud.google.com/billing?project=${PROJECT_ID}"
echo ""
