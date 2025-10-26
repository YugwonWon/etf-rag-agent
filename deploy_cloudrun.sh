#!/bin/bash

# Google Cloud Run 배포 스크립트
# 사용법: ./deploy_cloudrun.sh

set -e  # 에러 시 중단
export CLOUDSDK_CORE_DISABLE_PROMPTS=1

echo "========================================"
echo "🚀 Google Cloud Run 배포 시작"
echo "========================================"

# 환경변수 설정
PROJECT_ID="etf-rag-agent"
SERVICE_NAME="etf-rag-agent"
REGION="asia-northeast3"  # 서울 리전
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
KEY_FILE="gcp-key.json"

# 인증 확인
echo ""
echo "🔐 Step 0: 인증 확인..."
if [ ! -f "${KEY_FILE}" ]; then
    echo "❌ 에러: ${KEY_FILE} 파일이 없습니다!"
    echo ""
    echo "다음 중 하나를 실행하세요:"
    echo "  1. ./setup_gcloud.sh  (자동 설정)"
    echo "  2. gcloud auth login  (수동 로그인)"
    echo ""
    exit 1
fi

# 서비스 계정으로 인증
gcloud auth activate-service-account --key-file=${KEY_FILE}
echo "✅ 인증 완료"

# 1. 프로젝트 설정
echo ""
echo "📝 Step 1: GCP 프로젝트 설정..."
gcloud config set project ${PROJECT_ID}

# 2. API 활성화
echo ""
echo "🔌 Step 2: 필요한 API 활성화..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
echo "✅ API 활성화 완료"

# 3. 환경변수 파일 확인
echo ""
echo "📄 Step 3: 환경변수 확인..."
if [ ! -f ".env" ]; then
    echo "❌ .env 파일이 없습니다!"
    exit 1
fi

# .env 파일에서 환경변수 추출
echo "✅ 환경변수 로드 완료"

# 4. Docker 이미지 빌드 및 푸시
echo ""
echo "🐳 Step 4: Docker 이미지 빌드 중..."
echo "   (이 단계는 5-10분 소요될 수 있습니다...)"
gcloud builds submit --tag "${IMAGE_NAME}" --timeout=20m
echo "✅ 이미지 빌드 완료"

# 5. Cloud Run 배포
echo ""
echo "☁️  Step 5: Cloud Run에 배포 중..."
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
    --set-env-vars "LLM_PROVIDER=openai,OPENAI_API_KEY=$(grep '^OPENAI_API_KEY=' .env | cut -d'=' -f2),OPENAI_MODEL=$(grep '^OPENAI_MODEL=' .env | cut -d'=' -f2),OPENAI_EMBEDDING_MODEL=$(grep '^OPENAI_EMBEDDING_MODEL=' .env | cut -d'=' -f2),OPENAI_TIMEOUT=$(grep '^OPENAI_TIMEOUT=' .env | cut -d'=' -f2),WEAVIATE_URL=$(grep '^WEAVIATE_URL=' .env | cut -d'=' -f2),WEAVIATE_API_KEY=$(grep '^WEAVIATE_API_KEY=' .env | cut -d'=' -f2),WEAVIATE_CLASS_NAME=$(grep '^WEAVIATE_CLASS_NAME=' .env | cut -d'=' -f2),DART_API_KEY=$(grep '^DART_API_KEY=' .env | cut -d'=' -f2),ENABLE_SCHEDULER=false,RUN_INITIAL_COLLECTION=false,ENVIRONMENT=production"MODEL=$(grep OPENAI_MODEL .env.production | cut -d'=' -f2),OPENAI_EMBEDDING_MODEL=$(grep OPENAI_EMBEDDING_MODEL .env.production | cut -d'=' -f2),OPENAI_TIMEOUT=$(grep OPENAI_TIMEOUT .env.production | cut -d'=' -f2),WEAVIATE_URL=$(grep WEAVIATE_URL .env.production | cut -d'=' -f2),WEAVIATE_API_KEY=$(grep WEAVIATE_API_KEY .env.production | cut -d'=' -f2),WEAVIATE_CLASS_NAME=$(grep WEAVIATE_CLASS_NAME .env.production | cut -d'=' -f2),DART_API_KEY=$(grep DART_API_KEY .env.production | cut -d'=' -f2),ENABLE_SCHEDULER=false,RUN_INITIAL_COLLECTION=false,ENVIRONMENT=production"

echo "✅ 배포 완료"

# 6. 배포 완료
echo ""
echo "========================================"
echo "✅ 배포 성공!"
echo "========================================"
echo ""
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')
echo "🌐 서비스 URL:"
echo "   ${SERVICE_URL}"
echo ""
echo "📊 주요 엔드포인트:"
echo "   ${SERVICE_URL}/"
echo "   ${SERVICE_URL}/api/health"
echo "   ${SERVICE_URL}/api/query"
echo "   ${SERVICE_URL}/docs"
echo ""
echo "📝 로그 확인:"
echo "   gcloud run services logs read ${SERVICE_NAME} --region ${REGION} --limit 50"
echo ""
echo "🔄 업데이트 방법:"
echo "   코드 수정 후 ./deploy_cloudrun.sh 재실행"
echo ""
echo "🗑️  서비스 삭제:"
echo "   gcloud run services delete ${SERVICE_NAME} --region ${REGION}"
echo ""
