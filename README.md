# ETF RAG Agent 🚀

**국내외 ETF 정보 기반 RAG(Retrieval-Augmented Generation) 시스템**

장기투자를 위한 정확하고 최신의 ETF 정보를 RAG 방식으로 제공하는 AI 기반 질의응답 시스템입니다.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![Weaviate](https://img.shields.io/badge/Weaviate-4.4-orange.svg)](https://weaviate.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 목차

- [주요 기능](#-주요-기능)
- [시스템 아키텍처](#-시스템-아키텍처)
- [설치 방법](#-설치-방법)
- [환경 설정](#-환경-설정)
- [사용 방법](#-사용-방법)
- [API 문서](#-api-문서)
- [데이터 소스](#-데이터-소스)
- [프로젝트 구조](#-프로젝트-구조)
- [개발 로드맵](#-개발-로드맵)

---

## ✨ 주요 기능

### 🎯 핵심 기능
- **RAG 기반 질의응답**: 최신 ETF 정보를 바탕으로 정확한 답변 제공
- **🖥️ Gradio 웹 UI**: 채팅 인터페이스로 쉽게 ETF 정보 질의 (로컬 & 클라우드)
- **멀티소스 데이터 수집**:
  - 🇰🇷 국내 ETF (네이버 금융)
  - 🇺🇸 해외 ETF (yfinance)
  - 📄 공시 문서 (DART API)
- **완전 무료 운영 가능**: 로컬 임베딩 모델로 OpenAI API 없이 사용 가능
- **LLM 선택 옵션**: Ollama (qwen2.5:3b) 또는 OpenAI GPT (선택)
- **자동 스케줄링**: 매일 자동으로 최신 ETF 정보 수집
- **벡터 DB 관리**: 중복 제거 및 버전 관리로 효율적 저장
- **☁️ 클라우드 배포**: Hugging Face Spaces 무료 배포 지원

### 🔧 기술 스택
- **Backend**: FastAPI, gRPC (ConnectRPC)
- **Frontend**: Gradio (Python 웹 UI)
- **Vector DB**: Weaviate
- **LLM**: Ollama (qwen2.5:3b) / OpenAI GPT-4
- **Embedding**: sentence-transformers (all-MiniLM-L6-v2)
- **Crawling**: BeautifulSoup4, yfinance, DART API
- **Scheduler**: APScheduler
- **Deployment**: Hugging Face Spaces + GitHub Actions

---

## 🏗️ 시스템 아키텍처

```
┌────────────────────────────────────────────┐
│               User Interface               │
│          (REST API / gRPC Client)          │
└────────────────────┬───────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐       ┌───────▼────────┐
│  FastAPI REST  │       │  gRPC Server   │
│    Server      │       │  (ConnectRPC)  │
└───────┬────────┘       └───────┬────────┘
        │                        │
        └────────┬───────────────┘
                 │
        ┌────────▼────────┐
        │  RAG Handler    │
        │  (Query Engine) │
        └────────┬────────┘
                 │
        ┌────────▼────────────────────┐
        │                             │
┌───────▼────────┐          ┌─────────▼────────┐
│  Weaviate      │          │   LLM Model      │
│  Vector Store  │          │ (OpenAI/Local)   │
└───────▲────────┘          └──────────────────┘
        │
        │
┌───────┴─────────────────────────────────────┐
│              Data Collectors                │
├──────────────┬──────────────┬───────────────┤
│ Naver Crawler│ yfinance API │  DART API     │
│  (국내 ETF)   │  (해외 ETF)   │  (공시문서)      │
└──────────────┴──────────────┴───────────────┘
        ▲
        │
┌───────┴────────┐
│   Scheduler    │
│  (Daily Cron)  │
└────────────────┘
```

---

## 🚀 설치 방법

### 1. 사전 요구사항

- Python 3.10 이상
- Docker (Weaviate 실행용)
- Git

### 2. 저장소 클론

```bash
git clone https://github.com/YugwonWon/etf-rag-agent.git
cd etf-rag-agent
```

### 3. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 4. 의존성 설치

```bash
pip install -r requirements.txt
```

### 5. Weaviate 실행 (Docker)

```bash
# 프로젝트 디렉토리에서 실행
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

> 💾 **데이터 저장 위치**: `./data/weaviate/` (프로젝트 내 로컬 디렉토리)

---

## ⚙️ 환경 설정

### 1. 환경 변수 파일 생성

```bash
cp .env.example .env
```

### 2. `.env` 파일 수정

**기본 설정**:

```bash
# LLM Provider 선택
LLM_PROVIDER=local  # 로컬 모델 사용

# Weaviate 설정
WEAVIATE_URL=http://localhost:8081

# 스케줄러 설정
ENABLE_SCHEDULER=true
CRAWL_TIME_HOUR=9
CRAWL_TIME_MINUTE=0
```

**선택 사항**:

```bash
# OpenAI API Key (유료, LLM_PROVIDER=openai 사용 시에만)
# OPENAI_API_KEY=your-openai-api-key-here

# DART API Key
# DART_API_KEY=your-dart-api-key-here
```

### 3. DART API 키 발급 (선택)

DART 공시 문서를 수집하려면:
1. [DART 오픈 API](https://opendart.fss.or.kr/) 접속
2. 회원가입 및 인증키 발급
3. `.env` 파일에 키 입력

---

## 💻 사용 방법

### 🚀 빠른 시작 (통합 관리 스크립트)

#### 1. 서버 관리

```bash
# 도움말 확인
./server.sh --help

# 서버 시작
./server.sh start

# 서버 상태 확인
./server.sh status

# 로그 실시간 확인
./server.sh logs

# 로그 마지막 50줄 확인
./server.sh logs -n 50

# 서버 중지
./server.sh stop

# 서버 재시작
./server.sh restart

# 포트 변경 (기본: 8000)
./server.sh start --port 8080
```

#### 2. Gradio 웹 UI 사용 (권장)

```bash
# Gradio 의존성 설치
pip install gradio

# Gradio UI 실행
python gradio_app.py

# 브라우저에서 접속
# http://localhost:7860
```

**Gradio UI 주요 기능:**
- 💬 채팅 인터페이스로 ETF 질의
- 📊 실시간 통계 확인
- 📚 참고 문서 출처 표시
- 🔍 검색 문서 수 조정 (top_k)

#### 3. CLI 클라이언트 사용

```bash
# 도움말
python cli.py --help

# 서버 상태 확인
python cli.py health

# ETF 질의 (기본)
python cli.py query "KODEX 200 ETF에 대해 설명해줘"

# 상세 정보 포함
python cli.py query "미국 S&P 500 ETF 추천해줘" --top-k 5 --verbose

# 통계 정보 조회
python cli.py stats

# 데이터 수집 실행
python cli.py collect
```

### 📖 전통적인 방법

#### 1. gRPC Proto 파일 생성 (선택)

```bash
python -m grpc_tools.protoc \
  -I./protos \
  --python_out=./protos/__generated__ \
  --grpc_python_out=./protos/__generated__ \
  ./protos/etf_query.proto
```

#### 2. 서버 직접 실행

**FastAPI REST 서버**:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

서버 실행 후: http://localhost:8000/docs

**gRPC 서버** (선택):
```bash
python -m app.connect_rpc
```

#### 3. 초기 데이터 수집

**방법 1: CLI 사용 (권장)**
```bash
python cli.py collect
```

**방법 2: API 호출**
```bash
curl -X POST "http://localhost:8000/api/collect"
```

**방법 3: Python 스크립트**
```python
from app.crawler.collector import ETFDataCollector
from app.vector_store.weaviate_handler import WeaviateHandler

handler = WeaviateHandler()
collector = ETFDataCollector(vector_handler=handler)
results = collector.collect_all(insert_to_db=True)
print(f'Total collected: {results["total"]}')
```

#### 4. 질의응답 예시

**CLI 사용 (권장)**:
```bash
python cli.py query "KODEX 200 ETF의 장단점은?" --verbose
```

**REST API**:
```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "KODEX 미국S&P500 ETF에 대해 알려줘",
    "top_k": 3
  }'
```

**Python 클라이언트**:
```python
from app.retriever.query_handler import RAGQueryHandler

handler = RAGQueryHandler()
response = handler.query(
    question="TIGER 금선물 ETF의 총 보수는 얼마인가요?"
)

print(f"답변: {response['answer']}")
print(f"참고 문서: {response['num_sources']}개")
```

---

## 📚 API 문서

### REST API Endpoints

#### 1. 질의응답
```http
POST /api/query
Content-Type: application/json

{
  "question": "string",
  "model_type": "openai",  // or "local"
  "etf_type": "domestic",  // optional: "domestic", "foreign"
  "top_k": 5,
  "temperature": 0.7
}
```

#### 2. ETF 정보 조회
```http
GET /api/etf/{etf_code}
```

#### 3. 데이터 수집 트리거
```http
POST /api/collection/trigger
Content-Type: application/json

{
  "domestic": true,
  "foreign": true,
  "dart": true,
  "domestic_max": 100  // optional
}
```

#### 4. 헬스 체크
```http
GET /api/health
```

#### 5. 수집 상태 확인
```http
GET /api/collection/status
```

### gRPC API

프로토 정의: `protos/etf_query.proto`

Services:
- `AskQuestion`: 질의응답
- `GetETFSummary`: ETF 요약 정보
- `TriggerCollection`: 데이터 수집 트리거
- `HealthCheck`: 헬스 체크

---

## 🗄️ 데이터 소스

### 1. 국내 ETF (네이버 금융)
- **소스**: https://finance.naver.com/sise/etf.naver
- **수집 항목**: ETF명, 코드, 가격, NAV, 설명, 분류 등

### 2. 해외 ETF (yfinance)
- **소스**: Yahoo Finance API
- **대상**: 주요 미국 ETF (SPY, QQQ, ARKK 등)
- **수집 항목**: 가격, 보수율, 자산규모, 배당수익률 등

### 3. 공시 문서 (DART)
- **소스**: https://opendart.fss.or.kr/
- **수집 항목**: ETF 투자설명서, 운용보고서 등

---

## 📁 프로젝트 구조

```
etf-rag-agent/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI REST 서버
│   ├── connect_rpc.py          # gRPC 서버
│   ├── config.py               # 환경설정
│   ├── scheduler.py            # 스케줄러
│   ├── model/
│   │   ├── __init__.py
│   │   ├── openai_model.py     # OpenAI 모델 핸들러
│   │   ├── local_model.py      # 로컬 LLM 핸들러
│   │   └── model_factory.py    # 모델 팩토리
│   ├── crawler/
│   │   ├── __init__.py
│   │   ├── naver_kr.py         # 네이버 크롤러
│   │   ├── yfinance_us.py      # yfinance 크롤러
│   │   ├── dart_api.py         # DART API 크롤러
│   │   └── collector.py        # 통합 수집기
│   ├── vector_store/
│   │   ├── __init__.py
│   │   └── weaviate_handler.py # Weaviate 핸들러
│   └── retriever/
│       ├── __init__.py
│       └── query_handler.py    # RAG 쿼리 핸들러
├── protos/
│   ├── __init__.py
│   ├── etf_query.proto         # gRPC proto 정의
│   └── __generated__/          # 생성된 proto 코드
├── data/
│   ├── raw/                    # 원시 데이터
│   └── metadata.json           # 메타데이터
├── .env.example                # 환경변수 예시
├── .gitignore
├── requirements.txt
├── LICENSE
└── README.md
```

## 🔧 개발 & 테스트

### 개별 컴포넌트 테스트

```bash
# Config 테스트
python -m app.config

# 네이버 크롤러 테스트
python -m app.crawler.naver_kr

# yfinance 크롤러 테스트
python -m app.crawler.yfinance_us

# Weaviate 핸들러 테스트
python -m app.vector_store.weaviate_handler

# RAG 쿼리 핸들러 테스트
python -m app.retriever.query_handler
```

### 로그 확인

```bash
# 서버 로그
./server.sh logs

# Gradio 로그
tail -f gradio.log

# 애플리케이션 로그
tail -f logs/etf-rag-agent.log
```

---

## ☁️ 클라우드 배포

### Hugging Face Spaces 무료 배포

Gradio UI를 Hugging Face Spaces에 무료로 배포할 수 있습니다!

**배포 단계:**

1. **Hugging Face 계정 생성** ([가입하기](https://huggingface.co))
2. **Access Token 생성** (Write 권한)
3. **GitHub Secrets 설정**:
   - `HF_TOKEN`: Hugging Face Access Token
   - `HF_SPACE`: Space ID (예: `username/etf-rag-agent`)
4. **코드 푸시**:
   ```bash
   git add spaces/
   git commit -m "Deploy to Hugging Face Spaces"
   git push origin main
   ```
5. **자동 배포**: GitHub Actions가 자동으로 배포 실행

**상세 가이드**: [DEPLOYMENT.md](DEPLOYMENT.md) 참조

**데모 URL 예시**: `https://huggingface.co/spaces/[username]/etf-rag-agent`

**무료 옵션:**
- ✅ Hugging Face Spaces (CPU basic)
- ✅ Railway/Render/Fly.io 무료 플랜
- ✅ GitHub Actions (월 2,000분 무료)


---

## 🤝 기여하기

기여는 언제나 환영합니다!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## 👤 작성자

**Yugwon Won**

- GitHub: [@YugwonWon](https://github.com/YugwonWon)

---

## 🙏 감사의 말

이 프로젝트는 다음 오픈소스 프로젝트들을 사용합니다:

- [FastAPI](https://fastapi.tiangolo.com/)
- [Weaviate](https://weaviate.io/)
- [OpenAI](https://openai.com/)
- [yfinance](https://github.com/ranaroussi/yfinance)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)

---

## 📧 문의

프로젝트에 대한 질문이나 제안사항이 있으시면 이슈를 생성해주세요.

---

**⭐ 이 프로젝트가 유용하다면 Star를 눌러주세요!**
ETF-focused RAG system with daily crawling, vectorized document storage (Weaviate), OpenAI/sLLM support, and flexible server deployment with REST &amp; ConnectRPC APIs. Ideal for long-term investment Q&amp;A services.
