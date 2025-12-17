# 📈 Personal Stock Analyst Bot (DeMark + Trend Following)

매일 아침 9시(KST), **디마크(DeMark) 시스템**과 **추세 추종(Trend Following)** 전략을 기반으로 관심 종목을 분석하여 텔레그램으로 매매 타이밍을 알려주는 개인용 주식 비서입니다.

별도의 서버 구축 없이 **GitHub Actions**를 통해 100% 무료로 24시간 자동화되어 작동합니다.

## ✨ 주요 기능 (Features)

1.  **복합 매매 전략 분석**
    * **DeMark(TD) Sequential:** 추세의 과열(9 카운트)을 감지하여 반전 타이밍 포착
    * **Trend Following:** 20일 이동평균선(EMA)과 MACD를 사용하여 현재 추세 방향(상승/하락) 판별
    * **눌림목(Dip) 감지:** "상승 추세 중 일시적 하락(디마크 매수 신호)" 발생 시 **[💎강력 매수 기회]** 알림 발송
2.  **화폐 단위 자동 인식**
    * 한국 주식(코스피/코스닥)은 `원(KRW)` 단위 표시
    * 미국 주식은 `달러($)` 단위 및 소수점 표시
3.  **텔레그램 실시간 알림**
    * 매수/매도 시그널 발생 시에만 스마트폰으로 메시지 전송
    * GitHub Actions 로그를 통해 상세 분석 내역 확인 가능
4.  **Serverless Automation**
    * GitHub Actions Cron 기능을 사용하여 매일 한국 시간 오전 9시 장 시작 전 자동 실행

## 🛠 기술 스택 (Tech Stack)

* **Language:** Python 3.9+
* **Data Source:** `yfinance` (Yahoo Finance API)
* **Notification:** Telegram Bot API
* **Automation:** GitHub Actions
* **Libraries:** `pandas`, `requests`, `yfinance`

---

## 🚀 시작 가이드 (Getting Started)

### 1. 사전 준비 (Prerequisites)
* **Telegram Bot 생성:**
    1. 텔레그램에서 `@BotFather` 검색 -> `/newbot` 입력 -> 봇 생성.
    2. **API Token** 획득.
    3. 내 봇에게 메시지 보내기 (`Start` 혹은 `hi`).
    4. `@userinfobot`을 통해 본인의 **Chat ID** 획득.

### 2. 설치 및 로컬 실행 (Installation)
로컬 환경에서 테스트해보고 싶다면 아래 명령어를 따르세요.

```bash
# 리포지토리 클론
git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)

# 필수 라이브러리 설치
pip install -r requirements.txt

# 환경변수 설정 (Mac/Linux)
export TELEGRAM_TOKEN="여기에_토큰_입력"
export TELEGRAM_CHAT_ID="여기에_챗ID_입력"

# 실행
python main.py
