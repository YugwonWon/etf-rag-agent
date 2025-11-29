#!/bin/bash
# Cloud Run 배포만 실행 (이미지 빌드 스킵)

set -e

PROJECT_ID="etf-rag-agent"
SERVICE_NAME="etf-rag-agent"
REGION="asia-northeast3"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "☁️  Cloud Run에 배포 중..."

gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --timeout 300s \
    --max-instances 10 \
    --min-instances 0 \
    --concurrency 80 \
    --port 8080 \
    --set-env-vars "\
LLM_PROVIDER=openai,\
OPENAI_API_KEY=$(grep '^OPENAI_API_KEY=' .env | cut -d'=' -f2),\
OPENAI_MODEL=$(grep '^OPENAI_MODEL=' .env | cut -d'=' -f2),\
OPENAI_EMBEDDING_MODEL=$(grep '^OPENAI_EMBEDDING_MODEL=' .env | cut -d'=' -f2),\
OPENAI_TIMEOUT=$(grep '^OPENAI_TIMEOUT=' .env | cut -d'=' -f2),\
VECTOR_DB_TYPE=chroma,\
CHROMA_PERSIST_DIRECTORY=/app/data/chroma,\
CHROMA_COLLECTION_NAME=ETFDocument,\
DART_API_KEY=$(grep '^DART_API_KEY=' .env | cut -d'=' -f2),\
ENABLE_SCHEDULER=false,\
RUN_INITIAL_COLLECTION=false,\
ENVIRONMENT=production"

echo "✅ 배포 완료!"

SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')
echo ""
echo "🌐 서비스 URL: ${SERVICE_URL}"
echo "📊 헬스체크: ${SERVICE_URL}/api/health"
