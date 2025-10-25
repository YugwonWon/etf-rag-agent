"""
Gradio Web UI for ETF RAG Agent
채팅 인터페이스로 ETF 정보를 질의할 수 있는 웹 UI
"""

import os
import gradio as gr
import requests
from typing import List, Tuple

# API 서버 설정
# Render 배포 URL로 변경 필요!
API_BASE_URL = os.getenv("API_BASE_URL", "https://etf-rag-agent.onrender.com")  # 로컬 기본값

# 스타일링을 위한 CSS
custom_css = """
.chatbot {
    height: 600px !important;
}
.message {
    padding: 10px;
    border-radius: 10px;
}
footer {
    display: none !important;
}
"""


def format_sources(sources: List[dict]) -> str:
    """참고 문서 포맷팅"""
    if not sources:
        return ""
    
    formatted = "\n\n📚 **참고 문서**:\n"
    for i, source in enumerate(sources[:3], 1):
        etf_name = source.get("etf_name", "N/A")
        etf_code = source.get("etf_code", "")
        source_type = source.get("source", "N/A")
        relevance = source.get("relevance", 0)
        
        formatted += f"\n{i}. **{etf_name}** ({etf_code})\n"
        formatted += f"   - 출처: {source_type}\n"
        formatted += f"   - 관련도: {relevance:.3f}\n"
    
    return formatted


def query_etf(message: str, history: List[Tuple[str, str]], top_k: int = 3) -> Tuple[List[Tuple[str, str]], str]:
    """
    ETF 정보 질의
    
    Args:
        message: 사용자 질문
        history: 대화 히스토리
        top_k: 검색할 문서 수
    
    Returns:
        (업데이트된 히스토리, 빈 문자열)
    """
    if not message.strip():
        return history, ""
    
    try:
        # API 호출
        response = requests.post(
            f"{API_BASE_URL}/api/query",
            json={"question": message, "top_k": top_k},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "답변을 생성하지 못했습니다.")
            sources = data.get("sources", [])
            
            # 답변에 참고 문서 추가
            full_answer = answer
            if sources:
                full_answer += format_sources(sources)
            
            # 히스토리에 추가
            history.append((message, full_answer))
        else:
            error_msg = f"❌ API 오류 (상태 코드: {response.status_code})\n\n서버 응답:\n{response.text}"
            history.append((message, error_msg))
    
    except requests.exceptions.ConnectionError:
        error_msg = f"❌ 서버에 연결할 수 없습니다.\n\nAPI 서버가 실행 중인지 확인해주세요.\n- URL: {API_BASE_URL}\n- 로컬: `./server.sh start`"
        history.append((message, error_msg))
    except requests.exceptions.Timeout:
        error_msg = "⏱️ 요청 시간 초과 (60초)\n\n서버가 응답하지 않습니다. 잠시 후 다시 시도해주세요."
        history.append((message, error_msg))
    except Exception as e:
        error_msg = f"❌ 오류가 발생했습니다:\n\n```\n{str(e)}\n```"
        history.append((message, error_msg))
    
    return history, ""


def check_server_status() -> str:
    """서버 상태 확인"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return f"✅ 서버 정상 작동 중\n\n- 상태: {data.get('status', 'OK')}\n- 시간: {data.get('timestamp', 'N/A')}"
        else:
            return f"⚠️ 서버 응답 오류\n\n상태 코드: {response.status_code}"
    except requests.exceptions.ConnectionError:
        return f"❌ 서버 연결 실패\n\n- API URL: {API_BASE_URL}\n- 서버를 시작해주세요: `./server.sh start`"
    except Exception as e:
        return f"❌ 오류 발생\n\n{str(e)}"


def get_stats() -> str:
    """통계 정보 조회"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            stats_text = "📊 **ETF RAG Agent 통계**\n\n"
            stats_text += f"- **총 문서 수**: {data.get('total_documents', 0):,}개\n"
            stats_text += f"- **Vector DB**: {data.get('vector_db', 'N/A')}\n"
            stats_text += f"- **LLM 모델**: {data.get('llm_model', 'N/A')}\n"
            stats_text += f"- **Embedding 모델**: {data.get('embedding_model', 'N/A')}\n"
            
            sources = data.get("sources", {})
            if sources:
                stats_text += "\n**소스별 문서 수**:\n"
                for source, count in sources.items():
                    stats_text += f"- {source}: {count}개\n"
            
            return stats_text
        else:
            return f"⚠️ 통계 조회 실패 (상태 코드: {response.status_code})"
    except Exception as e:
        return f"❌ 통계 조회 중 오류: {str(e)}"


def create_examples() -> List[List[str]]:
    """예시 질문 목록"""
    return [
        ["KODEX 200 ETF에 대해 자세히 설명해줘"],
        ["미국 S&P 500 ETF 추천해줘"],
        ["KODEX 레버리지 ETF의 특징은 뭐야?"],
        ["금 ETF에 투자하고 싶은데 추천해줘"],
        ["배당 ETF 중에서 좋은 것 있어?"],
    ]


# Gradio UI 구성
with gr.Blocks(css=custom_css, title="ETF RAG Agent", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🤖 ETF RAG Agent
        
        **장기투자를 위한 국내외 ETF 정보 AI 어시스턴트**
        
        국내 ETF (네이버, DART)와 해외 ETF (yfinance) 정보를 기반으로 질문에 답변합니다.
        """
    )
    
    with gr.Tabs():
        # 메인 채팅 탭
        with gr.Tab("💬 채팅"):
            with gr.Row():
                with gr.Column(scale=4):
                    chatbot = gr.Chatbot(
                        value=[],
                        label="ETF 정보 채팅",
                        height=600,
                        show_copy_button=True,
                        type="tuples",  # 명시적으로 타입 지정
                    )
                    
                    with gr.Row():
                        msg = gr.Textbox(
                            label="질문을 입력하세요",
                            placeholder="예: KODEX 200 ETF에 대해 설명해줘",
                            lines=2,
                            scale=5
                        )
                        submit_btn = gr.Button("전송", variant="primary", scale=1)
                    
                    with gr.Row():
                        clear_btn = gr.Button("대화 초기화", variant="secondary")
                        top_k_slider = gr.Slider(
                            minimum=1,
                            maximum=10,
                            value=3,
                            step=1,
                            label="검색할 문서 수 (top_k)",
                            scale=2
                        )
                
                with gr.Column(scale=1):
                    gr.Markdown("### 📝 예시 질문")
                    examples = gr.Examples(
                        examples=create_examples(),
                        inputs=msg,
                        label="클릭하여 질문 입력"
                    )
                    
                    gr.Markdown("---")
                    gr.Markdown("### 💡 사용 팁")
                    gr.Markdown(
                        """
                        - ETF 이름이나 코드로 질문
                        - 투자 전략이나 특징 질문
                        - 여러 ETF 비교 요청
                        - 상세한 질문일수록 정확한 답변
                        """
                    )
            
            # 이벤트 핸들러
            submit_btn.click(
                query_etf,
                inputs=[msg, chatbot, top_k_slider],
                outputs=[chatbot, msg]
            )
            msg.submit(
                query_etf,
                inputs=[msg, chatbot, top_k_slider],
                outputs=[chatbot, msg]
            )
            clear_btn.click(lambda: ([], ""), outputs=[chatbot, msg])
        
        # 통계 탭
        with gr.Tab("📊 통계"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 시스템 상태 및 통계")
                    
                    with gr.Row():
                        status_btn = gr.Button("🔄 서버 상태 확인", variant="primary")
                        stats_btn = gr.Button("📈 통계 조회", variant="primary")
                    
                    status_output = gr.Markdown(label="서버 상태")
                    stats_output = gr.Markdown(label="통계 정보")
                    
                    status_btn.click(
                        check_server_status,
                        outputs=status_output
                    )
                    stats_btn.click(
                        get_stats,
                        outputs=stats_output
                    )
                    
                    # 초기 로드 시 자동 확인
                    demo.load(
                        check_server_status,
                        outputs=status_output
                    )
                    demo.load(
                        get_stats,
                        outputs=stats_output
                    )
        
        # 정보 탭
        with gr.Tab("ℹ️ 정보"):
            gr.Markdown(
                """
                ## 📖 ETF RAG Agent 소개
                
                이 시스템은 Retrieval-Augmented Generation (RAG) 기술을 사용하여 
                ETF 관련 질문에 답변하는 AI 어시스턴트입니다.
                
                ### 🎯 주요 기능
                
                1. **국내 ETF 정보**: 네이버 금융과 DART 공시 문서 기반
                2. **해외 ETF 정보**: yfinance API를 통한 실시간 정보
                3. **AI 답변 생성**: LLM을 활용한 자연스러운 답변
                4. **소스 제공**: 답변의 근거가 되는 문서 출처 표시
                
                ### 🔧 기술 스택
                
                - **Vector DB**: Weaviate
                - **LLM**: Ollama (qwen2.5:3b) / OpenAI GPT-4
                - **Embedding**: sentence-transformers (all-MiniLM-L6-v2)
                - **Framework**: FastAPI + Gradio
                - **데이터**: 네이버 금융, DART, yfinance
                
                ### 📚 데이터 소스
                
                - **네이버 금융**: 국내 ETF 기본 정보
                - **DART**: 공시 문서 (자산운용보고서 등)
                - **yfinance**: 미국 주요 ETF 정보
                
                ### 🔗 링크
                
                - [GitHub Repository](https://github.com/YugwonWon/etf-rag-agent)
                - [API Documentation](http://localhost:8000/docs)
                
                ### ⚠️ 면책 조항
                
                이 시스템은 정보 제공 목적으로만 사용되며, 투자 권유나 자문이 아닙니다.
                실제 투자 결정 시에는 반드시 전문가의 조언을 받으시기 바랍니다.
                
                ---
                
                **© 2025 ETF RAG Agent. All rights reserved.**
                """
            )
    
    gr.Markdown(
        """
        ---
        <div style="text-align: center; color: #666;">
            💡 서버가 실행 중이어야 합니다 | 문제가 있다면 <a href="https://github.com/YugwonWon/etf-rag-agent/issues">Issue</a>를 남겨주세요
        </div>
        """
    )


# Gradio 앱 실행
if __name__ == "__main__":
    # 로컬 실행
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_api=False
    )
