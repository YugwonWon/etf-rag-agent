# ETF RAG Agent - 설치 가이드

## 시스템 요구사항

- Python 3.12.3+
- Docker (Weaviate 실행용)
- 8GB+ RAM 권장
- CPU 버전으로 실행 가능 (CUDA 선택사항)

## 설치 과정

### 1. 저장소 클론

```bash
git clone https://github.com/YugwonWon/etf-rag-agent.git
cd etf-rag-agent
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

### 3. 의존성 설치

#### CPU 버전 (권장)
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

#### CUDA 버전 (GPU 사용 시)
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

### 4. Weaviate Docker 실행

```bash
# 프로젝트 디렉토리 경로 확인
cd /path/to/etf-rag-agent

# Weaviate 실행 (로컬 볼륨 마운트)
docker run -d --name weaviate \
  -p 8081:8080 \
  -p 50051:50051 \
  -e QUERY_DEFAULTS_LIMIT=25 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  -e DEFAULT_VECTORIZER_MODULE='none' \
  -e ENABLE_MODULES='' \
  -e CLUSTER_HOSTNAME='node1' \
  -v $(pwd)/data/weaviate:/var/lib/weaviate \
  semitechnologies/weaviate:1.32.13
```

**중요**:
- 포트 8081 (HTTP)와 50051 (gRPC) 둘 다 노출 필요
- 데이터는 `./data/weaviate/` 디렉토리에 저장됨
- 컨테이너 삭제해도 데이터는 유지됨

**Weaviate 상태 확인**:
```bash
# 컨테이너 상태 확인
docker ps | grep weaviate

# Weaviate API 테스트
curl http://localhost:8081/v1/meta
```

### 5. 환경 설정

`.env.example`을 `.env`로 복사하고 수정:

```bash
cp .env.example .env
```

`.env` 파일에서 설정:

```bash
# LLM 제공자 선택 (local 또는 openai)
LLM_PROVIDER=local  # 무료 로컬 모델 사용 (권장)

# OpenAI API Key (선택 - openai 사용 시에만 필요)
# OPENAI_API_KEY=your-openai-api-key

# Weaviate 설정
WEAVIATE_URL=http://localhost:8081
WEAVIATE_API_KEY=  # 로컬은 비워두기

# DART API Key (선택 - 공시정보용)
# DART_API_KEY=your-dart-api-key
```

**참고**: 
- `LLM_PROVIDER=local`로 설정하면 **완전 무료**로 사용 가능합니다
- 로컬 임베딩: `sentence-transformers` (all-MiniLM-L6-v2) 사용
- 로컬 LLM: Ollama 설치 필요 (선택사항)

## 설치 검증

### 1. Weaviate 연결 테스트

```bash
python test_weaviate.py
```

예상 출력:
```
✓ Connected to Weaviate at http://localhost:8081
✓ Collection 'ETFDocument' has 0 documents
```

### 2. 임베딩 모델 테스트

```bash
python test_embedding.py
```

예상 출력:
```
✓ Model loaded successfully in X.XX seconds
✓ Encoding test successful!
```

### 3. 빠른 데이터 삽입 테스트

```bash
python test_quick.py
```

예상 출력:
```
✓ Inserted: KODEX 200 (UUID: xxxxxxxx...)
✓ Inserted: SPDR S&P 500 ETF (UUID: xxxxxxxx...)
```

## 문제 해결

### torch 임포트 실패

```bash
# CPU 버전으로 재설치
pip uninstall torch -y
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Weaviate 연결 실패

```bash
# Docker 컨테이너 상태 확인
docker ps | grep weaviate

# Weaviate 재시작
docker restart weaviate

# 포트 확인
curl http://localhost:8081/v1/meta
```

### gRPC 타임아웃

- 포트 50051이 노출되었는지 확인
- Docker run 명령에 `-p 50051:50051` 포함 필수

### 패키지 버전 충돌

```bash
# 가상환경 재생성
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

## 다음 단계

설치가 완료되면:

1. **크롤러 테스트**: `python test_crawler.py`
2. **서버 실행**: `python -m app.main`
3. **API 문서**: http://localhost:8000/docs

자세한 사용법은 `README.md`를 참조하세요.
