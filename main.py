import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime

# 종목 리스트
tickers = {
    # --- 암호화폐  ---
    'BTC-USD': '비트코인',
    'ETH-USD': '이더리움',
    
    # --- 한국 지수 ---
    '^KS11': '코스피',
    '^KQ11': '코스닥',
    '161510.KS': 'PLUS 고배당주 (ETF)',
    

    # --- 미국 지수 (새로 추가됨) ---
    'SPY': 'S&P 500 (ETF)',   # 가장 거래량 많은 S&P500 ETF
    'QQQ': '나스닥 100 (ETF)', # 기술주 중심 (애플, 엔비디아 등 포함)
    'SOXX': '반도체 ETF',      # 필라델피아 반도체 지수 추종

    # --- 한국 개별 종목 ---
    '005930.KS': '삼성전자',
    '222800.KQ': '심텍 ',
    '103590.KS': '일진전기',
    '195870.KS': '해성디에스',

    # --- 미국 개별 종목 ---
    'TSLA': '테슬라',
    'NVDA': '엔비디아',
    'AAPL': '애플',
}

def send_telegram(msg):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ 설정 오류: 토큰 없음")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {'chat_id': chat_id, 'text': msg}
    
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"전송 실패: {e}")

# --- 지표 계산 함수 ---
def add_indicators(df):
    # 1. 20일 지수이동평균 (EMA) - 추세 생명선
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    
    # 2. MACD (12, 26, 9)
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # 3. MACD 오실레이터 (막대그래프)
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']
    
    return df

def check_market(ticker, name):
    print(f"[{name}] 데이터 분석 중...")
    try:
        # 데이터 기간을 6개월(6mo)로 늘림 (이동평균선 계산 안정성 확보)
        df = yf.download(ticker, period='6mo', progress=False)
    except:
        return
    
    if df.empty: return
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

    # 지표 추가
    df = add_indicators(df)

    # 디마크 계산
    df['Close_4'] = df['Close'].shift(4)
    close_vals = df['Close'].values
    close_4_vals = df['Close_4'].values
    
    buy_setup = 0
    sell_setup = 0
    
    # 최근 20일만 순회하며 디마크 카운트
    for i in range(len(df)-20, len(df)):
        if close_vals[i] > close_4_vals[i]:
            sell_setup += 1
            buy_setup = 0
        elif close_vals[i] < close_4_vals[i]:
            buy_setup += 1
            sell_setup = 0
        else:
            buy_setup = 0
            sell_setup = 0

    # --- 최종 분석 데이터 ---
    last_close = df['Close'].iloc[-1]
    last_ema20 = df['EMA_20'].iloc[-1]
    last_macd_hist = df['MACD_Hist'].iloc[-1]
    
    # 추세 판단
    trend_msg = ""
    is_uptrend = False
    
    if last_close > last_ema20:
        is_uptrend = True
        trend_msg = "상승 추세 (20일선 위 📈)"
    else:
        trend_msg = "하락 추세 (20일선 아래 📉)"
        
    if last_macd_hist > 0:
        trend_msg += " + MACD 강세"
    else:
        trend_msg += " + MACD 약세"

    # 화폐 단위
    if ticker.endswith('.KS') or ticker.endswith('.KQ') or ticker.startswith('^K'):
        price_str = f"{int(last_close):,}원"
    else:
        price_str = f"${last_close:,.2f}"

    # --- 알림 로직 (조건부 알림) ---
    msg = ""
    
# --- [수정] 자산별 맞춤형 기준 설정 ---
    # 기본값은 9 (엄격함)
    buy_threshold = 9 
    sell_threshold = 9

    # 1. 암호화폐 (변동성 큼 -> 매우 엄격하게 9 유지)
    if ticker in ['BTC-USD', 'ETH-USD']:
        buy_threshold = 9
    
    # 2. 개별 주식 (변동성 중간 -> 조금 공격적으로 6~7 정도도 허용)
    # 삼성전자나 테슬라 같은 경우 6~7일 연속 하락하면 기술적 반등이 꽤 잘 나옵니다.
    elif ticker in ['005930.KS', 'TSLA', 'AAPL', 'NVDA']:
        buy_threshold = 4  # 6일 연속 하락하면 알림
        
    # 3. 지수/ETF (변동성 작음 -> 9 유지 권장)
    # 지수가 9일 연속 하락하는 건 정말 드물어서 신뢰도가 높음
    else:
        buy_threshold = 4

    # 1. 최고의 매수 기회: 상승 추세인데 + 디마크로 과하게 떨어졌을 때 (눌림목)
    if buy_setup >= buy_threshold and is_uptrend:
        msg = f"💎 [강력 매수 기회] {name}\n- 가격: {price_str}\n- 상태: {trend_msg}\n- 이유: 상승 추세 중 단기 조정(눌림목) 발생! (Buy Setup 9)"
        
    # 2. 일반 매수/매도 신호 (기존)
    elif buy_setup >= buy_threshold:
        msg = f"🔥 [매수 신호] {name}\n- 가격: {price_str}\n- 상태: {trend_msg}\n- 디마크: Buy Setup {buy_setup}일차"
    elif sell_setup >= sell_threshold:
        msg = f"⚠️ [매도 신호] {name}\n- 가격: {price_str}\n- 상태: {trend_msg}\n- 디마크: Sell Setup {sell_setup}일차"

    if msg:
        print(f"알림 발송: {msg}")
        send_telegram(msg)
    else:
        print(f"특이사항 없음 ({name}: {trend_msg}, Buy:{buy_setup}, Sell:{sell_setup})")

if __name__ == "__main__":
    print(f"--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 분석 시작 ---")
    for t, n in tickers.items():
        try:
            check_market(t, n)
        except Exception as e:
            print(f"[{n}] 에러: {e}")