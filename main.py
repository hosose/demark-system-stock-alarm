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
    'TSLA': '테슬라' # 필요하면 주석 해제
}

def send_telegram(msg):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("텔레그램 토큰이 설정되지 않아 메시지를 보낼 수 없습니다.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {'chat_id': chat_id, 'text': msg}
    
    try:
        requests.post(url, data=data)
        print("텔레그램 전송 완료")
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def check_demark(ticker, name):
    print(f"[{name}] 데이터 분석 중...")
    df = yf.download(ticker, period='3mo', progress=False)
    
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
    
    # 최근 데이터 순회
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

    # 오늘의 종가
    current_price = int(df['Close'].iloc[-1]) # 보기 좋게 정수로 변환
    
    # 알림 로직 (9 카운트 이상일 때만 알림)
    msg = ""
    if buy_setup >= 3:
        msg = f"🔥 [매수 신호] {name} ({ticker})\n- 종가: {current_price:,}원\n- 디마크: Buy Setup {buy_setup}일차\n- 반등 가능성이 높습니다!"
    elif sell_setup >= 3:
        msg = f"⚠️ [매도 신호] {name} ({ticker})\n- 종가: {current_price:,}원\n- 디마크: Sell Setup {sell_setup}일차\n- 조정 가능성이 높습니다!"
    
    # 메시지가 있으면(신호가 떴으면) 텔레그램 발송
    if msg:
        print(f"알림 발송: {msg}")
        send_telegram(msg)
    else:
        print(f"특이사항 없음 (Buy:{buy_setup}, Sell:{sell_setup})")

if __name__ == "__main__":
    print(f"--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 분석 시작 ---")
    
    # 혹시 모르니 시작했다는 알림을 한번 보내고 싶으면 아래 주석 해제
    # send_telegram("📈 주식 디마크 분석을 시작합니다.") 
    
    for t, n in tickers.items():
        try:
            check_demark(t, n)
        except Exception as e:
            print(f"에러 발생: {e}")