import os
import io
import requests
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# 서버(GitHub Actions)에서 GUI 없이 그래프를 그리기 위한 설정
import matplotlib
matplotlib.use('Agg') 

# 종목 리스트
tickers = {
    # --- 암호화폐 ---
    'BTC-USD': '비트코인',
    'ETH-USD': '이더리움',
    
    # --- 한국 지수 & ETF ---
    '^KS11': '코스피',
    '^KQ11': '코스닥',
    '161510.KS': 'PLUS 고배당주 (ETF)',
    
    # --- 미국 ETF ---
    'SPY': 'S&P 500 (ETF)',
    'QQQ': '나스닥 100 (ETF)',
    'SOXX': '반도체 ETF',

    # --- 한국 개별 종목 ---
    '005930.KS': '삼성전자',
    '222800.KQ': '심텍',
    '103590.KS': '일진전기',
    '195870.KS': '해성디에스',

    # --- 미국 개별 종목 ---
    'TSLA': '테슬라',
    'NVDA': '엔비디아',
    'AAPL': '애플',
}

def send_telegram(msg, img_buf=None):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ 설정 오류: 토큰 없음")
        return

    # 이미지가 있으면 sendPhoto, 없으면 sendMessage
    if img_buf:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        # 이미지를 파일 형태로 전송
        img_buf.seek(0)
        files = {'photo': img_buf}
        # 사진과 함께 보낼 텍스트는 'caption' 파라미터 사용
        data = {'chat_id': chat_id, 'caption': msg}
        try:
            requests.post(url, files=files, data=data)
            print("✅ 텔레그램 사진 전송 완료")
        except Exception as e:
            print(f"사진 전송 실패: {e}")
    else:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {'chat_id': chat_id, 'text': msg}
        try:
            requests.post(url, data=data)
            print("✅ 텔레그램 텍스트 전송 완료")
        except Exception as e:
            print(f"텍스트 전송 실패: {e}")

# --- 차트 그리기 함수 (New!) ---
def create_chart(df, ticker, name):
    # 최근 6개월 데이터만 사용
    plot_df = df.iloc[-120:] 

    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # 1. 주가 (캔들 대신 종가 선으로 심플하게)
    ax1.plot(plot_df.index, plot_df['Close'], color='black', label='Price', linewidth=1.5)
    
    # 2. 20일 이평선 & 60일 이평선
    ax1.plot(plot_df.index, plot_df['EMA_20'], color='green', linestyle='--', label='EMA 20', alpha=0.7)
    if 'MA_60' in plot_df.columns:
        ax1.plot(plot_df.index, plot_df['MA_60'], color='orange', linestyle='--', label='MA 60', alpha=0.7)

    # 3. 매수/매도 시점 표시 (마지막 날)
    last_date = plot_df.index[-1]
    last_price = plot_df['Close'].iloc[-1]
    ax1.scatter(last_date, last_price, color='red', s=100, zorder=5) # 현재 위치 점 찍기

    # 꾸미기
    plt.title(f"{name} ({ticker}) Daily Chart", fontsize=15, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # 날짜 포맷
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))

    # 이미지를 메모리 버퍼에 저장 (파일로 저장 안 함)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close(fig) # 메모리 해제
    return buf

# --- 지표 계산 함수 ---
def add_indicators(df):
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['MA_60'] = df['Close'].rolling(window=60).mean() # 60일선 추가
    
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']
    
    return df

def check_market(ticker, name):
    print(f"[{name}] 데이터 분석 중...")
    try:
        # 60일선 계산을 위해 1년치 데이터 가져옴
        df = yf.download(ticker, period='1y', progress=False)
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

    # --- 최종 분석 ---
    last_close = df['Close'].iloc[-1]
    last_ma60 = df['MA_60'].iloc[-1]
    last_ema20 = df['EMA_20'].iloc[-1]
    last_macd_hist = df['MACD_Hist'].iloc[-1]
    
    # 추세 판단
    is_downtrend = False
    trend_msg = ""
    
    if last_close < last_ma60:
        is_downtrend = True
        trend_msg = "📉 하락장 (60일선 아래)"
    else:
        trend_msg = "📈 상승장 (60일선 위)"
        
    if last_macd_hist > 0: trend_msg += " + MACD 강세"
    else: trend_msg += " + MACD 약세"

    # 화폐 단위
    if ticker.endswith('.KS') or ticker.endswith('.KQ') or ticker.startswith('^K'):
        price_str = f"{int(last_close):,}원"
    else:
        price_str = f"${last_close:,.2f}"

    # --- 기준값 설정 ---
    buy_threshold = 9 
    sell_threshold = 9

    if ticker in ['BTC-USD', 'ETH-USD']:
        base_threshold = 9
    elif ticker in ['005930.KS', 'TSLA', 'AAPL', 'NVDA']:
        base_threshold = 4
    else:
        base_threshold = 4
        
    # --- 알림 로직 ---
    msg = ""
    should_send_chart = False # 차트를 보낼지 여부

    # 1. 강력 매수
    if buy_setup >= buy_threshold and not is_downtrend:
        msg = f"💎 [강력 매수 기회] {name}\n- 가격: {price_str}\n- 상태: {trend_msg}\n- 이유: 상승 추세 중 눌림목 (Buy {buy_setup})"
        should_send_chart = True
        
    # 2. 일반 매수
    elif buy_setup >= buy_threshold:
        msg = f"🔥 [매수 신호] {name}\n- 가격: {price_str}\n- 상태: {trend_msg}\n- 디마크: Buy {buy_setup}일차 (기준: {buy_threshold})"
        should_send_chart = True

    # 3. 매도 신호
    elif sell_setup >= sell_threshold:
        msg = f"⚠️ [매도 신호] {name}\n- 가격: {price_str}\n- 상태: {trend_msg}\n- 디마크: Sell {sell_setup}일차"
        should_send_chart = True

    # 알림 발송
    if msg:
        print(f"알림 발송: {msg}")
        
        if should_send_chart:
            # 차트 생성 (메모리에 저장)
            img_buffer = create_chart(df, ticker, name)
            send_telegram(msg, img_buffer)
        else:
            send_telegram(msg)
    else:
        print(f"특이사항 없음 ({name}: {trend_msg}, Buy:{buy_setup}/{buy_threshold})")

if __name__ == "__main__":
    from datetime import timedelta
    kst_now = datetime.now() + timedelta(hours=9)
    print(f"--- {kst_now.strftime('%Y-%m-%d %H:%M:%S')} (KST) 분석 시작 ---")
    
    for t, n in tickers.items():
        try:
            check_market(t, n)
        except Exception as e:
            print(f"[{n}] 에러: {e}")