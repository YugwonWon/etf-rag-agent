# Weaviate 데이터 관리 가이드

## 📁 데이터 저장 위치

Weaviate 데이터는 프로젝트 내 `data/weaviate/` 디렉토리에 저장됩니다:

```
etf-rag-agent/
├── data/
│   ├── weaviate/          # ← Weaviate 데이터 (Docker 볼륨 마운트)
│   │   ├── .gitkeep
│   │   └── README.md
│   ├── raw/               # 원본 크롤링 데이터 (선택)
│   └── metadata.json      # 메타데이터
```

## 🐳 Docker 볼륨 마운트

### 프로젝트 디렉토리에서 실행 (권장)

```bash
cd /path/to/etf-rag-agent

docker run -d --name weaviate \
  -p 8081:8080 \
  -p 50051:50051 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  -v $(pwd)/data/weaviate:/var/lib/weaviate \
  semitechnologies/weaviate:1.32.13
```

### 절대 경로로 실행

```bash
docker run -d --name weaviate \
  -p 8081:8080 \
  -p 50051:50051 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  -v /data3/yugwon/projects/etf-rag-agent/data/weaviate:/var/lib/weaviate \
  semitechnologies/weaviate:1.32.13
```

## 💾 데이터 백업

### 백업 생성

```bash
# 1. Weaviate 중지
docker stop weaviate

# 2. 데이터 압축
tar -czf weaviate-backup-$(date +%Y%m%d).tar.gz data/weaviate/

# 3. Weaviate 재시작
docker start weaviate
```

### 백업 복원

```bash
# 1. Weaviate 중지 및 제거
docker stop weaviate
docker rm weaviate

# 2. 기존 데이터 백업 (안전을 위해)
mv data/weaviate data/weaviate.old

# 3. 백업 파일 압축 해제
tar -xzf weaviate-backup-20251025.tar.gz

# 4. Weaviate 재시작
docker run -d --name weaviate \
  -p 8081:8080 -p 50051:50051 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  -v $(pwd)/data/weaviate:/var/lib/weaviate \
  semitechnologies/weaviate:1.32.13
```

## 🗑️ 데이터 초기화

### 전체 데이터 삭제

```bash
# 1. Weaviate 중지 및 제거
docker stop weaviate
docker rm weaviate

# 2. 데이터 삭제
rm -rf data/weaviate/*

# 3. .gitkeep 복원
touch data/weaviate/.gitkeep

# 4. Weaviate 재시작 (깨끗한 상태)
docker run -d --name weaviate \
  -p 8081:8080 -p 50051:50051 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  -v $(pwd)/data/weaviate:/var/lib/weaviate \
  semitechnologies/weaviate:1.32.13
```

## 📊 데이터 확인

### 디렉토리 크기 확인

```bash
du -sh data/weaviate/
```

### 데이터 파일 목록

```bash
ls -lh data/weaviate/
```

### Weaviate 통계 확인

```bash
# API로 확인
curl http://localhost:8081/v1/meta

# Python 스크립트로 확인
python -c "
from app.vector_store.weaviate_handler import WeaviateHandler
handler = WeaviateHandler()
print(f'Total documents: {handler.get_document_count()}')
handler.close()
"
```

## ⚠️ 주의사항

1. **Git 버전 관리**: `data/weaviate/`는 `.gitignore`에 포함되어 있어 자동으로 제외됩니다.

2. **디스크 공간**: Weaviate 데이터는 ETF 개수와 히스토리에 따라 증가합니다. 주기적으로 확인하세요.

3. **Docker 볼륨 vs 로컬 마운트**: 
   - ❌ Docker 볼륨 (`-v weaviate_data:/var/lib/weaviate`): 시스템 어딘가에 저장, 관리 어려움
   - ✅ 로컬 마운트 (`-v $(pwd)/data/weaviate:/var/lib/weaviate`): 프로젝트 내 저장, 관리 쉬움

4. **권한 문제**: Docker 컨테이너가 디렉토리에 쓸 수 없다면:
   ```bash
   chmod 777 data/weaviate/
   ```

## 🔄 마이그레이션 (기존 Docker 볼륨 → 로컬 디렉토리)

기존에 Docker 볼륨을 사용했다면:

```bash
# 1. 기존 컨테이너에서 데이터 복사
docker cp weaviate:/var/lib/weaviate ./data/weaviate-backup

# 2. 컨테이너 중지 및 제거
docker stop weaviate
docker rm weaviate

# 3. 데이터 이동
rm -rf data/weaviate/*
cp -r data/weaviate-backup/* data/weaviate/

# 4. 새 설정으로 재시작
docker run -d --name weaviate \
  -p 8081:8080 -p 50051:50051 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  -v $(pwd)/data/weaviate:/var/lib/weaviate \
  semitechnologies/weaviate:1.32.13

# 5. 임시 백업 삭제
rm -rf data/weaviate-backup
```
