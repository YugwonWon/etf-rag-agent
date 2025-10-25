---
title: ETF RAG Agent
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.0
app_file: gradio_app.py
pinned: false
license: mit
short_description: 장기투자를 위한 국내외 ETF 정보 AI 어시스턴트
---

# ETF RAG Agent

**장기투자를 위한 국내외 ETF 정보 AI 어시스턴트**

이 애플리케이션은 RAG (Retrieval-Augmented Generation) 기술을 사용하여 국내외 ETF 정보를 제공합니다.

## 주요 기능

- 💬 자연어로 ETF 정보 질의
- 📊 국내 ETF (네이버, DART) 정보
- 🌎 해외 ETF (yfinance) 정보
- 🤖 AI 기반 답변 생성
- 📚 출처 제공

## 기술 스택

- Vector DB: Weaviate
- LLM: Ollama (qwen2.5:3b)
- Embedding: sentence-transformers
- Framework: FastAPI + Gradio

## 면책 조항

이 시스템은 정보 제공 목적으로만 사용되며, 투자 권유나 자문이 아닙니다.

## 링크

- [GitHub Repository](https://github.com/YugwonWon/etf-rag-agent)
- [Documentation](https://github.com/YugwonWon/etf-rag-agent#readme)
