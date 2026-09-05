import datetime
import math
import ephem
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# --- ページ設定（スマホ対応） ---
st.set_page_config(page_title="経ヶ岬沖 オフショアナビ", page_icon="⚓", layout="centered")

# --- ダークモード風カスタムCSS ---
st.markdown("""
<style>
    .stApp { background-color: #020617; color: #f8fafc; }
    .fishing-card {
        background: linear-gradient(135deg, #0f172a 0%, #020617 100%);
        padding: 22px;
        border-radius: 14px;
        border: 1px solid #1e293b;
        margin-bottom: 20px;
    }
    .card-title { font-size: 20px; font-weight: bold; color: #38bdf8; margin-bottom: 2px; }
    .card-subtitle { font-size: 12px; color: #94a3b8; margin-bottom: 15px; }
    .metric-container { display: flex; justify-content: space-between; margin-bottom: 15px; }
    .metric-box { background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px; width: 48%; text-align: center; border: 1px solid #334155; }
    .metric-label { font-size: 11px; color: #94a3b8; text-transform: uppercase; }
    .metric-value { font-size: 16px; font-weight: bold; color: #f1f5f9; }
    .chance-box { background: linear-gradient(90deg, #0369a1 0%, #0284c7 100%); padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #0ea5e9; }
    .stars { font-size: 24px; color: #f59e0b; margin-top: 3px; }
</style>
""", unsafe_allow_html=True)

st.title("⚓ 経ヶ岬沖 オフショアナビ")
st.caption("京都府 京丹後市 経ヶ岬沖専用・釣行最適日予測ツール")

# --- サイドバー（設定入力） ---
st.sidebar.header("⚙️ 釣行条件設定")
select_date = st.sidebar.date_input("釣行日を選択", datetime.date.today())
mode = st.sidebar.selectbox("ターゲット（釣り方）", ["青物ジギング", "タイラバ・根魚", "イカメタル（白イカ）"])

# --- 月齢と潮回りを計算する関数 ---
def calculate_moon_and_tide(target_date):
    date_str = target_date.strftime("%Y/%m/%d %H:%M:%S")
    date_ephem = ephem.Date(date_str)
    prev_new_moon = ephem.previous_new_moon(date_ephem)
    moon_age = (date_ephem - prev_new_moon) % 29.53
    
    rounded_age = int(math.floor(moon_age)) % 30
    
    oo_shio = [0, 1, 2, 3, 14, 15, 16, 17, 28, 29]
    naka_shio = [4, 5, 6, 7, 12, 13, 18, 19, 20, 21, 26, 27]
    ko_shio = [8, 9, 11, 22, 23, 25]
    naga_shio = [10, 24]
    
    if rounded_age in oo_shio:
        tide_type = "大潮"
    elif rounded_age in naka_shio:
        tide_type = "中潮"
    elif rounded_age in ko_shio:
        tide_type = "小潮"
    elif rounded_age in naga_shio:
        tide_type = "長潮"
    else:
        tide_type = "若潮"
        
    return moon_age, tide_type

# --- モード別のチャンス度・解説判定 ---
def get_fishing_advice(tide_type, moon_age, mode):
    if mode == "青物ジギング":
        score_map = {"大潮": 5, "中潮": 4, "若潮": 3, "小潮": 2, "長潮": 1}
        score = score_map.get(tide_type, 3)
        explanation = "🌊 青物は潮が命！ジグにしっかり水圧がかかり、ワンピッチジャークに好反応な大チャンス日です。" if score >= 4 else "⏰ 潮が緩めです。早巻きからのストップや、軽めのジグでスローに誘うのが手です。"
        
    elif mode == "タイラバ・根魚":
        score_map = {"中潮": 5, "若潮": 4, "小潮": 4, "大潮": 3, "長潮": 2}
        score = score_map.get(tide_type, 3)
        explanation = "🎣 経ヶ岬沖のディープでも二枚潮になりにくく、タイラバの底取りが非常にしやすい好条件日です！" if score >= 4 else "🌀 潮が動きすぎる（または止まる）時間帯があります。ヘッドの重さをこまめに調整してください。"
        
    else:  # イカメタル（白イカ）
        is_dark_night = (moon_age < 5 or moon_age > 24)
        if is_dark_night:
            score = 5 if tide_type in ["中潮", "小潮", "若潮"] else 4
            explanation = "🦑 【激アツの闇夜！】月明かりがなく船の集魚灯にシロイカが猛烈に集まります。棚を絞って連発を狙えます！"
        else:
            is_full_moon = (11 <= moon_age <= 18)
            if is_full_moon:
                score = 2
                explanation = "🌕 【月が明るい満月周り】集魚灯の効きが弱くイカが散らばりやすい日。オモリグで広範囲を探るのが吉。"
            else:
                score = 3
                explanation = "⏰ 月が半分ほど出ています。潮の速さに合わせて仕掛け（オモリグ・イカメタル）を使い分けましょう。"
                
    return score, explanation

# --- 日本海側（経ヶ岬）のなだらかな潮位を再現 ---
def get_kyogamisaki_tide(tide_type):
    amplitude_map = {"大潮": 15, "中潮": 10, "小潮": 5, "長潮": 3, "若潮": 5}
    amp = amplitude_map.get(tide_type, 10)
    times = np.linspace(0, 24, 100)
    tide_levels = 35 + amp * np.sin(2 * np.pi * times / 12.42) + 4 * np.sin(2 * np.pi * times / 24)
    return times, tide_levels

# --- 月の絵文字 ---
def get_moon_phase_emoji(age):
    if age < 1.8 or age >= 28.2: return "🌑 新月(闇夜)"
    elif age < 5.5: return "🌘 三日月"
    elif age < 9.2: return "🌓 上弦の月"
    elif age < 12.9: return "🌔 満月前"
    elif age < 16.6: return "🌕 満月(大月夜)"
    elif age < 20.3: return "🌖 満月後"
    elif age < 24.0: return "🌗 下弦の月"
    else: return "🌘 晦日"

# --- 計算と表示処理 ---
moon_age, tide_type = calculate_moon_and_tide(select_date)
moon_emoji = get_moon_phase_emoji(moon_age)
score, explanation = get_fishing_advice(tide_type, moon_age, mode)
times, levels = get_kyogamisaki_tide(tide_type)
stars_html = "★" * score + "☆" * (5 - score)

# --- リッチパネルの描画 ---
st.markdown(f"""
<div class="fishing-card">
    <div class="card-title">⚓ KYOGAMISAKI OFFSHORE NAVI</div>
    <div class="card-subtitle">設定モード: <b>{mode}</b></div>
    <div class="metric-container">
        <div class="metric-box">
            <div class="metric-label">🌙 月の状態 (Moon)</div>
            <div class="metric-value">{moon_emoji} (齢 {moon_age:.1f})</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">🌊 潮回り (Tide)</div>
            <div class="metric-value" style="color: #38bdf8;">{tide_type}</div>
        </div>
    </div>
    <div class="chance-box">
        <div class="metric-label" style="color: #cbd5e1;">🎯 オフショア チャンス度</div>
        <div class="stars">{stars_html}</div>
        <div style="font-size: 13px; margin-top: 8px; color: #e0f2fe;">{explanation}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- タイドグラフ描画 ---
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=times, y=levels, mode='lines',
    line=dict(color='#0ea5e9', width=3.5),
    fill='tozeroy', fillcolor='rgba(14, 165, 233, 0.06)'
))

fig.add_vrect(x0=5, x1=7, fillcolor="rgba(251, 146, 60, 0.12)", layer="below", line_width=0, annotation_text="朝マズメ", annotation_position="top left", annotation_font=dict(color="#fb923c"))
fig.add_vrect(x0=17, x1=19, fillcolor="rgba(129, 140, 248, 0.12)", layer="below", line_width=0, annotation_text="夕マズメ", annotation_position="top left", annotation_font=dict(color="#818cf8"))

fig.update_layout(
    title=dict(text=f"📊 {select_date.strftime('%Y/%m/%d')} 予測タイドグラフ", font=dict(color='#f8fafc', size=14)),
    template="plotly_dark",
    paper_bgcolor='rgba(2, 6, 23, 1)', plot_bgcolor='rgba(15, 23, 42, 0.5)',
    xaxis=dict(title="時間 (Hour)", tickmode='linear', tick0=0, dtick=2, range=[0, 24], gridcolor='#1e293b'),
    yaxis=dict(title="潮位 (cm)", gridcolor='#1e293b', range=[0, 80]),
    margin=dict(l=40, r=40, t=40, b=40), height=320, showlegend=False
)
st.plotly_chart(fig, use_container_width=True)
