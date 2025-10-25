#!/usr/bin/env python3
"""
ETF RAG Agent CLI Client

사용 예시:
    # 쿼리 실행
    python cli.py query "KODEX 200 ETF에 대해 설명해줘"
    
    # 상세 옵션 포함
    python cli.py query "미국 주식 ETF 추천해줘" --top-k 5 --verbose
    
    # Health check
    python cli.py health
    
    # 데이터 수집 실행
    python cli.py collect
    
    # 통계 조회
    python cli.py stats
"""

import argparse
import json
import sys
from typing import Optional
import requests
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
from rich import print as rprint

console = Console()

# API 서버 설정
BASE_URL = "http://localhost:8000"
API_TIMEOUT = 60  # 초


class ETFRagClient:
    """ETF RAG Agent API 클라이언트"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
    
    def health_check(self) -> bool:
        """서버 상태 확인"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                console.print("[green]✓ 서버 정상 작동 중[/green]")
                console.print(f"  상태: {data.get('status', 'unknown')}")
                console.print(f"  타임스탬프: {data.get('timestamp', 'N/A')}")
                return True
            else:
                console.print(f"[red]✗ 서버 응답 오류: {response.status_code}[/red]")
                return False
        except requests.exceptions.ConnectionError:
            console.print(f"[red]✗ 서버에 연결할 수 없습니다: {self.base_url}[/red]")
            console.print("서버를 먼저 시작해주세요: [yellow]./scripts/start.sh[/yellow]")
            return False
        except Exception as e:
            console.print(f"[red]✗ Health check 실패: {e}[/red]")
            return False
    
    def query(self, question: str, top_k: int = 3, verbose: bool = False) -> Optional[dict]:
        """RAG 쿼리 실행"""
        try:
            console.print(f"\n[cyan]질문:[/cyan] {question}\n")
            
            payload = {
                "question": question,
                "top_k": top_k
            }
            
            with console.status("[bold green]답변 생성 중..."):
                response = requests.post(
                    f"{self.base_url}/api/query",
                    json=payload,
                    timeout=API_TIMEOUT
                )
            
            if response.status_code == 200:
                data = response.json()
                
                # 답변 출력
                answer = data.get("answer", "답변을 생성하지 못했습니다.")
                console.print(Panel(
                    Markdown(answer),
                    title="[bold green]답변[/bold green]",
                    border_style="green"
                ))
                
                # 소스 정보 출력
                if verbose and data.get("sources"):
                    self._print_sources(data["sources"])
                
                # 메타 정보 출력
                if verbose:
                    console.print(f"\n[dim]모델: {data.get('model_type', 'N/A')}[/dim]")
                    console.print(f"[dim]검색된 문서: {data.get('num_sources', 0)}개[/dim]")
                
                return data
            else:
                console.print(f"[red]✗ 쿼리 실패: {response.status_code}[/red]")
                console.print(response.text)
                return None
        
        except requests.exceptions.Timeout:
            console.print("[red]✗ 요청 시간 초과 (60초)[/red]")
            return None
        except Exception as e:
            console.print(f"[red]✗ 쿼리 실행 중 오류: {e}[/red]")
            return None
    
    def _print_sources(self, sources: list):
        """검색된 소스 출력"""
        table = Table(title="\n📚 참고 문서", show_header=True, header_style="bold magenta")
        table.add_column("순위", style="cyan", width=6)
        table.add_column("ETF", style="green", width=20)
        table.add_column("출처", style="yellow", width=15)
        table.add_column("관련도", style="blue", width=10)
        table.add_column("미리보기", style="white", width=50)
        
        for source in sources[:5]:  # 상위 5개만 표시
            rank = source.get("rank", "?")
            etf_name = source.get("etf_name", "N/A")
            etf_code = source.get("etf_code", "")
            source_type = source.get("source", "N/A")
            relevance = source.get("relevance", 0)
            preview = source.get("preview", "")[:100] + "..."
            
            etf_display = f"{etf_name}\n({etf_code})" if etf_code else etf_name
            
            table.add_row(
                str(rank),
                etf_display,
                source_type,
                f"{relevance:.3f}",
                preview
            )
        
        console.print(table)
    
    def collect_data(self) -> bool:
        """데이터 수집 실행"""
        try:
            console.print("[cyan]데이터 수집을 시작합니다...[/cyan]")
            
            with console.status("[bold green]데이터 수집 중... (시간이 걸릴 수 있습니다)"):
                response = requests.post(
                    f"{self.base_url}/api/collect",
                    timeout=300  # 5분
                )
            
            if response.status_code == 200:
                data = response.json()
                console.print(f"[green]✓ 데이터 수집 완료[/green]")
                console.print(f"  Naver: {data.get('naver', 0)}개")
                console.print(f"  DART: {data.get('dart', 0)}개")
                console.print(f"  yfinance: {data.get('yfinance', 0)}개")
                console.print(f"  총합: {data.get('total', 0)}개")
                return True
            else:
                console.print(f"[red]✗ 데이터 수집 실패: {response.status_code}[/red]")
                console.print(response.text)
                return False
        
        except requests.exceptions.Timeout:
            console.print("[red]✗ 데이터 수집 시간 초과 (5분)[/red]")
            return False
        except Exception as e:
            console.print(f"[red]✗ 데이터 수집 중 오류: {e}[/red]")
            return False
    
    def get_stats(self) -> Optional[dict]:
        """통계 정보 조회"""
        try:
            response = requests.get(f"{self.base_url}/api/stats", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 통계 테이블 출력
                table = Table(title="📊 ETF RAG Agent 통계", show_header=True)
                table.add_column("항목", style="cyan", width=30)
                table.add_column("값", style="green", width=20)
                
                table.add_row("총 문서 수", str(data.get("total_documents", 0)))
                table.add_row("Vector DB", data.get("vector_db", "N/A"))
                table.add_row("LLM 모델", data.get("llm_model", "N/A"))
                table.add_row("Embedding 모델", data.get("embedding_model", "N/A"))
                
                # 소스별 문서 수
                sources = data.get("sources", {})
                if sources:
                    table.add_row("", "")  # 구분선
                    for source, count in sources.items():
                        table.add_row(f"  {source}", str(count))
                
                console.print(table)
                return data
            else:
                console.print(f"[red]✗ 통계 조회 실패: {response.status_code}[/red]")
                return None
        
        except Exception as e:
            console.print(f"[red]✗ 통계 조회 중 오류: {e}[/red]")
            return None


def main():
    parser = argparse.ArgumentParser(
        description="ETF RAG Agent CLI Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python cli.py query "KODEX 200 ETF에 대해 설명해줘"
  python cli.py query "미국 주식 ETF 추천해줘" --top-k 5 --verbose
  python cli.py health
  python cli.py collect
  python cli.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="실행할 명령")
    
    # query 명령
    query_parser = subparsers.add_parser("query", help="ETF 관련 질문하기")
    query_parser.add_argument("question", type=str, help="질문 내용")
    query_parser.add_argument("--top-k", type=int, default=3, help="검색할 문서 수 (기본: 3)")
    query_parser.add_argument("--verbose", "-v", action="store_true", help="상세 정보 출력")
    
    # health 명령
    subparsers.add_parser("health", help="서버 상태 확인")
    
    # collect 명령
    subparsers.add_parser("collect", help="ETF 데이터 수집 실행")
    
    # stats 명령
    subparsers.add_parser("stats", help="통계 정보 조회")
    
    # URL 옵션
    parser.add_argument("--url", type=str, default=BASE_URL, help=f"API 서버 URL (기본: {BASE_URL})")
    
    args = parser.parse_args()
    
    # 명령이 없으면 help 출력
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 클라이언트 초기화
    client = ETFRagClient(base_url=args.url)
    
    # 명령 실행
    try:
        if args.command == "health":
            success = client.health_check()
            sys.exit(0 if success else 1)
        
        elif args.command == "query":
            result = client.query(args.question, top_k=args.top_k, verbose=args.verbose)
            sys.exit(0 if result else 1)
        
        elif args.command == "collect":
            success = client.collect_data()
            sys.exit(0 if success else 1)
        
        elif args.command == "stats":
            result = client.get_stats()
            sys.exit(0 if result else 1)
        
        else:
            console.print(f"[red]알 수 없는 명령: {args.command}[/red]")
            parser.print_help()
            sys.exit(1)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]사용자에 의해 중단되었습니다.[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
