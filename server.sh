#!/bin/bash

# ETF RAG Agent 서버 관리 통합 스크립트
# 사용법: ./server.sh [start|stop|restart|status|logs] [options]

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
LOG_FILE="$PROJECT_DIR/server.log"
PID_FILE="$PROJECT_DIR/server.pid"
HOST="0.0.0.0"
PORT="8000"

# 도움말 출력
show_help() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}          ${GREEN}ETF RAG Agent 서버 관리 스크립트${NC}                   ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}사용법:${NC}"
    echo -e "  ${GREEN}./server.sh${NC} ${CYAN}<command>${NC} [options]"
    echo ""
    echo -e "${YELLOW}명령어:${NC}"
    echo -e "  ${GREEN}start${NC}           서버 시작 (백그라운드)"
    echo -e "  ${GREEN}stop${NC}            서버 중지"
    echo -e "  ${GREEN}restart${NC}         서버 재시작"
    echo -e "  ${GREEN}status${NC}          서버 상태 확인 (상세)"
    echo -e "  ${GREEN}logs${NC}            로그 실시간 확인 (tail -f)"
    echo -e "  ${GREEN}logs -n${NC} ${CYAN}<N>${NC}      마지막 N줄 로그 확인"
    echo -e "  ${GREEN}help${NC}            이 도움말 표시"
    echo ""
    echo -e "${YELLOW}옵션:${NC}"
    echo -e "  ${CYAN}--port${NC} ${CYAN}<PORT>${NC}     포트 번호 지정 (기본: 8000)"
    echo -e "  ${CYAN}--host${NC} ${CYAN}<HOST>${NC}     호스트 지정 (기본: 0.0.0.0)"
    echo -e "  ${CYAN}-h, --help${NC}      도움말 표시"
    echo ""
    echo -e "${YELLOW}예시:${NC}"
    echo -e "  ${GREEN}./server.sh start${NC}              # 서버 시작"
    echo -e "  ${GREEN}./server.sh stop${NC}               # 서버 중지"
    echo -e "  ${GREEN}./server.sh restart${NC}            # 서버 재시작"
    echo -e "  ${GREEN}./server.sh status${NC}             # 상태 확인"
    echo -e "  ${GREEN}./server.sh logs${NC}               # 로그 실시간 확인"
    echo -e "  ${GREEN}./server.sh logs -n 50${NC}         # 마지막 50줄 로그"
    echo -e "  ${GREEN}./server.sh start --port 8080${NC}  # 포트 8080으로 시작"
    echo ""
    echo -e "${YELLOW}통합 CLI 도구:${NC}"
    echo -e "  ${GREEN}python cli.py query${NC} ${CYAN}\"질문\"${NC}    # ETF 정보 질의"
    echo -e "  ${GREEN}python cli.py health${NC}          # 서버 Health Check"
    echo -e "  ${GREEN}python cli.py stats${NC}           # 통계 정보 조회"
    echo -e "  ${GREEN}python cli.py collect${NC}         # 데이터 수집 실행"
    echo ""
}

# 서버 시작
start_server() {
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}   ETF RAG Agent 서버 시작${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    
    # 이미 실행 중인지 확인
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if ps -p "$OLD_PID" > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠  서버가 이미 실행 중입니다 (PID: $OLD_PID)${NC}"
            echo -e "   중지하려면: ${GREEN}./server.sh stop${NC}"
            return 1
        else
            echo -e "${YELLOW}⚠  PID 파일이 존재하지만 프로세스가 없습니다. 정리 중...${NC}"
            rm -f "$PID_FILE"
        fi
    fi
    
    # 가상환경 확인
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${RED}✗ 가상환경을 찾을 수 없습니다: $VENV_DIR${NC}"
        echo -e "  먼저 가상환경을 생성해주세요:"
        echo -e "  ${GREEN}python -m venv venv${NC}"
        return 1
    fi
    
    # 서버 시작
    cd "$PROJECT_DIR"
    echo -e "${CYAN}▶  서버를 시작합니다...${NC}"
    echo -e "   호스트: ${YELLOW}$HOST${NC}"
    echo -e "   포트: ${YELLOW}$PORT${NC}"
    echo -e "   로그: ${YELLOW}$LOG_FILE${NC}"
    echo ""
    
    # nohup으로 백그라운드 실행
    source "$VENV_DIR/bin/activate"
    nohup python -m uvicorn app.main:app --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
    
    # PID 저장
    echo $! > "$PID_FILE"
    PID=$(cat "$PID_FILE")
    
    # 서버 시작 대기
    echo -e "${YELLOW}⏳ 서버 시작 중... (최대 10초 대기)${NC}"
    sleep 3
    
    # Health check
    for i in {1..7}; do
        if curl -s "http://localhost:$PORT/api/health" > /dev/null 2>&1; then
            echo ""
            echo -e "${GREEN}✓ 서버가 정상적으로 시작되었습니다!${NC}"
            echo -e "  ${CYAN}PID:${NC}      ${YELLOW}$PID${NC}"
            echo -e "  ${CYAN}URL:${NC}      ${YELLOW}http://localhost:$PORT${NC}"
            echo -e "  ${CYAN}Docs:${NC}     ${YELLOW}http://localhost:$PORT/docs${NC}"
            echo -e "  ${CYAN}로그:${NC}     ${GREEN}./server.sh logs${NC}"
            echo -e "  ${CYAN}상태:${NC}     ${GREEN}./server.sh status${NC}"
            echo -e "  ${CYAN}쿼리:${NC}     ${GREEN}python cli.py query \"질문\"${NC}"
            return 0
        fi
        sleep 1
    done
    
    # 시작 실패
    echo ""
    echo -e "${RED}✗ 서버 시작에 실패했습니다.${NC}"
    echo -e "  로그를 확인해주세요: ${YELLOW}./server.sh logs -n 50${NC}"
    rm -f "$PID_FILE"
    return 1
}

# 서버 중지
stop_server() {
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}   ETF RAG Agent 서버 중지${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    
    # PID 파일 확인
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${YELLOW}⚠  PID 파일을 찾을 수 없습니다.${NC}"
        echo -e "   uvicorn 프로세스를 모두 종료합니다..."
        pkill -f "uvicorn app.main:app"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ 서버를 중지했습니다.${NC}"
        else
            echo -e "${YELLOW}⚠  실행 중인 서버를 찾을 수 없습니다.${NC}"
        fi
        return 0
    fi
    
    # PID 읽기
    PID=$(cat "$PID_FILE")
    
    # 프로세스 확인 및 종료
    if ps -p "$PID" > /dev/null 2>&1; then
        echo -e "${CYAN}▶  서버를 중지합니다... (PID: ${YELLOW}$PID${NC}${CYAN})${NC}"
        kill "$PID"
        
        # 종료 대기 (최대 5초)
        for i in {1..5}; do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                echo -e "${GREEN}✓ 서버가 정상적으로 중지되었습니다.${NC}"
                rm -f "$PID_FILE"
                return 0
            fi
            sleep 1
        done
        
        # 강제 종료
        echo -e "${YELLOW}⚠  서버가 응답하지 않습니다. 강제 종료합니다...${NC}"
        kill -9 "$PID" 2>/dev/null
        rm -f "$PID_FILE"
        echo -e "${GREEN}✓ 서버를 강제 종료했습니다.${NC}"
    else
        echo -e "${YELLOW}⚠  프로세스가 이미 종료되었습니다 (PID: $PID)${NC}"
        rm -f "$PID_FILE"
    fi
    
    # 혹시 남아있을 수 있는 uvicorn 프로세스 정리
    pkill -f "uvicorn app.main:app" 2>/dev/null
    echo -e "${GREEN}✓ 서버 중지 완료${NC}"
}

# 서버 재시작
restart_server() {
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}   ETF RAG Agent 서버 재시작${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    
    # 서버 중지
    stop_server
    
    # 잠시 대기
    echo ""
    sleep 2
    
    # 서버 시작
    start_server
}

# 서버 상태 확인
check_status() {
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}   ETF RAG Agent 서버 상태${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    
    # 서버 프로세스 상태
    echo -e "${BLUE}📊 서버 프로세스${NC}"
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓ 실행 중${NC}"
            echo -e "    PID:      ${YELLOW}$PID${NC}"
            echo -e "    메모리:   ${YELLOW}$(ps -o rss= -p $PID | awk '{printf "%.1f MB", $1/1024}')${NC}"
            echo -e "    CPU:      ${YELLOW}$(ps -o %cpu= -p $PID)%${NC}"
            echo -e "    실행시간: ${YELLOW}$(ps -o etime= -p $PID | xargs)${NC}"
        else
            echo -e "  ${RED}✗ 중지됨${NC} (PID 파일은 존재하지만 프로세스 없음)"
        fi
    else
        echo -e "  ${RED}✗ 중지됨${NC} (PID 파일 없음)"
    fi
    
    echo ""
    
    # API Health Check
    echo -e "${BLUE}🏥 API Health Check${NC}"
    HEALTH_RESPONSE=$(curl -s "http://localhost:$PORT/api/health" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓ 응답 정상${NC}"
        echo -e "    URL: ${YELLOW}http://localhost:$PORT${NC}"
        echo -e "    상태: ${YELLOW}$(echo "$HEALTH_RESPONSE" | jq -r '.status' 2>/dev/null || echo "OK")${NC}"
    else
        echo -e "  ${RED}✗ 응답 없음${NC}"
        echo -e "    서버가 시작되지 않았거나 포트 $PORT이 사용 중입니다."
    fi
    
    echo ""
    
    # Docker (Weaviate)
    echo -e "${BLUE}🐳 Docker 컨테이너 (Weaviate)${NC}"
    if docker ps 2>/dev/null | grep -q weaviate; then
        echo -e "  ${GREEN}✓ 실행 중${NC}"
        WEAVIATE_PORT=$(docker ps | grep weaviate | sed -n 's/.*0.0.0.0:\([0-9]*\)->8080.*/\1/p')
        if [ -n "$WEAVIATE_PORT" ]; then
            echo -e "    포트: ${YELLOW}$WEAVIATE_PORT${NC}"
        fi
    else
        echo -e "  ${RED}✗ 중지됨${NC}"
        echo -e "    시작: ${YELLOW}docker-compose -f docker/docker-compose.yml up -d${NC}"
    fi
    
    echo ""
    
    # Ollama
    echo -e "${BLUE}🤖 Ollama LLM${NC}"
    OLLAMA_RESPONSE=$(curl -s http://localhost:11434/api/tags 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓ 실행 중${NC}"
        MODELS=$(echo "$OLLAMA_RESPONSE" | jq -r '.models[].name' 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
        if [ -n "$MODELS" ]; then
            echo -e "    모델: ${YELLOW}$MODELS${NC}"
        fi
    else
        echo -e "  ${RED}✗ 중지됨${NC}"
        echo -e "    시작: ${YELLOW}ollama serve${NC}"
    fi
    
    echo ""
    
    # 로그 파일
    echo -e "${BLUE}📄 로그 파일${NC}"
    if [ -f "$LOG_FILE" ]; then
        LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
        LOG_LINES=$(wc -l < "$LOG_FILE")
        echo -e "  ${GREEN}✓ 존재${NC}"
        echo -e "    경로: ${YELLOW}$LOG_FILE${NC}"
        echo -e "    크기: ${YELLOW}$LOG_SIZE${NC} (${LOG_LINES} 줄)"
        
        # 최근 에러 확인
        ERROR_COUNT=$(grep -i "error\|exception\|failed" "$LOG_FILE" 2>/dev/null | tail -10 | wc -l)
        if [ "$ERROR_COUNT" -gt 0 ]; then
            echo -e "    ${RED}⚠ 최근 에러 $ERROR_COUNT건${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ 없음${NC}"
    fi
    
    echo ""
    
    # 관리 명령어
    echo -e "${BLUE}⚙️  관리 명령어${NC}"
    echo -e "  시작:     ${GREEN}./server.sh start${NC}"
    echo -e "  중지:     ${GREEN}./server.sh stop${NC}"
    echo -e "  재시작:   ${GREEN}./server.sh restart${NC}"
    echo -e "  로그:     ${GREEN}./server.sh logs${NC}"
    echo -e "  쿼리:     ${GREEN}python cli.py query \"질문\"${NC}"
}

# 로그 확인
show_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo -e "${RED}✗ 로그 파일을 찾을 수 없습니다: $LOG_FILE${NC}"
        return 1
    fi
    
    # 옵션 파싱
    if [ "$1" = "-n" ] && [ -n "$2" ]; then
        echo -e "${CYAN}마지막 $2줄의 로그:${NC}"
        echo -e "${YELLOW}─────────────────────────────────────────────────${NC}"
        tail -n "$2" "$LOG_FILE"
    elif [ "$1" = "-f" ] || [ -z "$1" ]; then
        echo -e "${CYAN}실시간 로그 (Ctrl+C로 종료):${NC}"
        echo -e "${YELLOW}─────────────────────────────────────────────────${NC}"
        tail -f "$LOG_FILE"
    else
        echo -e "${YELLOW}기본 로그 (마지막 30줄):${NC}"
        echo -e "${YELLOW}─────────────────────────────────────────────────${NC}"
        tail -n 30 "$LOG_FILE"
    fi
}

# 메인 로직
main() {
    # 인자가 없으면 help 표시
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    # 명령어 파싱
    COMMAND="$1"
    shift
    
    # 옵션 파싱
    while [ $# -gt 0 ]; do
        case "$1" in
            --port)
                PORT="$2"
                shift 2
                ;;
            --host)
                HOST="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                # 로그 명령어의 옵션들
                break
                ;;
        esac
    done
    
    # 명령어 실행
    case "$COMMAND" in
        start)
            start_server
            ;;
        stop)
            stop_server
            ;;
        restart)
            restart_server
            ;;
        status)
            check_status
            ;;
        logs)
            show_logs "$@"
            ;;
        help|-h|--help)
            show_help
            ;;
        *)
            echo -e "${RED}✗ 알 수 없는 명령어: $COMMAND${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"
