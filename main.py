# 파일명: main.py
import yfinance as yf
import pandas as pd
from datetime import datetime

# 종목 리스트 (필요하면 여기에 종목 추가)
tickers = {
    '^KS11': 'KOSPI',
    '^KQ11': 'KOSDAQ',
    '005930.KS': 'Samsung Elec'
}

def check_demark(ticker, name):
    # 데이터 가져오기 (최근 30일치면 충분)
    df = yf.download(ticker, period='3mo', progress=False)
    
    if df.empty:
        print(f"[{name}] 데이터 수집 실패")
        return

    # MultiIndex 컬럼 처리 (yfinance 버그 방지)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 디마크 로직 (간소화 버전)
    df['Close_4'] = df['Close'].shift(4)
    close_vals = df['Close'].values
    close_4_vals = df['Close_4'].values
    
    # 카운트 계산을 위한 변수
    buy_setup = 0
    sell_setup = 0
    
    # 전체를 다 돌 필요 없이, 최근 15일치만 계산해서 오늘의 카운트를 구함
    for i in range(len(df)-15, len(df)):
        # Sell Setup (상승 피로감)
        if close_vals[i] > close_4_vals[i]:
            sell_setup += 1
        else:
            sell_setup = 0
            
        # Buy Setup (하락 피로감 - 반등 가능성)
        if close_vals[i] < close_4_vals[i]:
            buy_setup += 1
        else:
            buy_setup = 0

    # 결과 출력 (GitHub Actions 로그에 찍힘)
    today_date = df.index[-1].strftime('%Y-%m-%d')
    print(f"[{today_date}] {name} ({ticker}) 분석 결과:")
    print(f" - 매수(Buy) 셋업 카운트: {buy_setup}")
    print(f" - 매도(Sell) 셋업 카운트: {sell_setup}")
    
    if buy_setup >= 9:
        print(" 🔥 [매수 신호] 9 카운트 도달! 반등 가능성 있음!")
    if sell_setup >= 9:
        print(" ⚠️ [매도 신호] 9 카운트 도달! 조정 가능성 있음!")
    print("-" * 30)

if __name__ == "__main__":
    print(f"--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 실행 시작 ---")
    for t, n in tickers.items():
        try:
            check_demark(t, n)
        except Exception as e:
            print(f"{n} 처리 중 에러 발생: {e}")