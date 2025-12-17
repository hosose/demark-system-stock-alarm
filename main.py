import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

# 종목 리스트
tickers = {
    '^KS11': '코스피',
    '^KQ11': '코스닥',
    '005930.KS': '삼성전자',
    'TSLA': '테슬라',
    'NVDA': '엔비디아', # 테스트용 미국 주식 추가
    'AAPL': '애플'
}

def send_telegram(msg):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ 설정 오류: 텔레그램 토큰이나 채팅 ID가 없습니다.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {'chat_id': chat_id, 'text': msg}
    
    try:
        response = requests.post(url, data=data)
        res_json = response.json()
        
        if response.status_code == 200 and res_json.get('ok'):
            print("✅ 텔레그램 메시지 발송 성공!")
        else:
            print(f"❌ 텔레그램 발송 실패! (HTTP {response.status_code})")
            print(f"🔻 에러 이유: {res_json.get('description')}")
            
    except Exception as e:
        print(f"❌ 연결 에러 발생: {e}")

def check_demark(ticker, name):
    print(f"[{name}] 데이터 분석 중...")
    try:
        df = yf.download(ticker, period='3mo', progress=False)
    except Exception as e:
        print(f"다운로드 에러: {e}")
        return
    
    if df.empty:
        return

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 디마크 계산
    df['Close_4'] = df['Close'].shift(4)
    close_vals = df['Close'].values
    close_4_vals = df['Close_4'].values
    
    buy_setup = 0
    sell_setup = 0
    
    for i in range(len(df)-15, len(df)):
        if close_vals[i] > close_4_vals[i]:
            sell_setup += 1
            buy_setup = 0
        elif close_vals[i] < close_4_vals[i]:
            buy_setup += 1
            sell_setup = 0
        else:
            buy_setup = 0
            sell_setup = 0

    # --- [수정된 부분] 화폐 단위 구분 로직 ---
    last_close = df['Close'].iloc[-1]
    
    # 한국 주식 특징: .KS(코스피), .KQ(코스닥), ^K(한국지수)
    if ticker.endswith('.KS') or ticker.endswith('.KQ') or ticker.startswith('^K'):
        price_str = f"{int(last_close):,}원"  # 한국: 정수 + 원
    else:
        price_str = f"${last_close:,.2f}"    # 미국: 소수점 + $

    # 알림 로직
    msg = ""
    if buy_setup >= 9:
        msg = f"🔥 [매수 신호] {name} ({ticker})\n- 종가: {price_str}\n- 디마크: Buy Setup {buy_setup}일차\n- 반등 가능성이 높습니다!"
    elif sell_setup >= 9:
        msg = f"⚠️ [매도 신호] {name} ({ticker})\n- 종가: {price_str}\n- 디마크: Sell Setup {sell_setup}일차\n- 조정 가능성이 높습니다!"
    
    if msg:
        print(f"알림 발송: {msg}")
        send_telegram(msg)
    else:
        print(f"특이사항 없음 (종가: {price_str}, Buy:{buy_setup}, Sell:{sell_setup})")

if __name__ == "__main__":
    print(f"--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 분석 시작 ---")
    
    for t, n in tickers.items():
        try:
            check_demark(t, n)
        except Exception as e:
            print(f"[{n}] 처리 중 에러 발생: {e}")