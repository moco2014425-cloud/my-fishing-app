import datetime
import calendar
import math
import ephem
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# --- ページ設定（スマホ対応） ---
st.set_page_config(page_title="経ヶ岬沖 月間オフショアナビ", page_icon="⚓", layout="centered")

# --- ダークモード風・サイバーカスタムCSS ---
st.markdown("""
<style>
    .stApp { background-color: #020617; color: #f8fafc; }
    .fishing-card {
        background: linear-gradient(135deg, #0f172a 0%, #020617 100%);
        padding: 20px;
        border-radius: 14px;
        border: 1px solid #1e293b;
        margin-bottom: 15px;
    }
    .card-title { font-size: 20px; font-weight: bold; color: #38bdf8; text-align: center; letter-spacing: 1px; }
    
    /* カレンダー全体のスタイリング */
    .cal-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-family: sans-serif; }
    .cal-th { text-align: center; padding: 8px; color: #94a3b8; font-size: 12px; font-weight: bold; text-transform: uppercase; border-bottom: 2px solid #1e293b; }
    .cal-td { width: 14.2%; height: 85px; vertical-align: top; padding: 6px; border: 1px solid #1e293b; border-radius: 4px; transition: all 0.2s; }
    
    /* 日付ごとのチャンス度背景色 */
    .bg-star5 { background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 100%); border: 1px solid #3b82f6 !important; } /* 激アツ */
    .bg-star4 { background: rgba(3, 105, 161, 0.4); } /* チャンス */
    .bg-star3 { background: rgba(15, 23, 42, 0.6); }  /* 普通 */
    .bg-star2 { background: rgba(30, 41, 59, 0.3); }  /* 渋め */
    .bg-star1 { background: rgba(2, 6, 23, 0.9); opacity: 0.5; }     /* 激渋 */
    
    .cal-day-num { font-size: 14px; font-weight: bold; color: #f1f5f9; }
    .cal-tide-text { font-size: 11px; font-weight: bold; margin-top: 2px; }
    .cal-stars { font-size: 12px; color: #f59e0b; margin-top: 2px; }
    .cal-moon { font-size: 11px; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

st.title("⚓ 経ヶ岬沖 月間ナビ")
st.caption("何年先でも一気見可能！オフショア釣行最適日カレンダー")

# --- サイドバー（年・月・モードの選択） ---
st.sidebar.header("⚙️ 釣行スケジュール設定")
today = datetime.date.today()

# 何年後でも選べるように前後10年を選択可能に
year = st.sidebar.selectbox("年を選択", list(range(today.year - 1, today.year + 10)), index=1)
month = st.sidebar.selectbox("月を選択", list(range(1, 13)), index=today.month - 1)
mode = st.sidebar.selectbox("ターゲット（釣り方）", ["青物ジギング", "タイラバ・根魚", "イカメタル（白イカ）"])

# --- 月齢と潮回りを計算する関数 ---
def calculate_moon_and_tide(target_date):
    date_str = target_date.strftime("%Y/%m/%d %H:%M:%S")
    date_ephem = ephem.Date(date_str)
    prev_new_moon = ephem.previous_new_moon(date_ephem)
    moon_age = (date_ephem - prev_new_moon) % 29.53
    
    rounded_age = int(math.floor(moon_age)) % 30
    
    oo_shio = [0, 1, 2, 14, 15, 16, 27, 28, 29]
    naka_shio = [3, 4, 5, 12, 13, 17, 18, 25, 26]
    ko_shio = [6, 7, 8, 19, 20, 21]
    naga_shio = [9, 22]
    
    if rounded_age in oo_shio: return moon_age, "大潮"
    elif rounded_age in naka_shio: return moon_age, "中潮"
    elif rounded_age in ko_shio: return moon_age, "小潮"
    elif rounded_age in naga_shio: return moon_age, "長潮"
    else: return moon_age, "若潮"

# --- モード別のチャンス度判定 ---
def get_chance_score(tide_type, moon_age, mode):
    if mode == "青物ジギング":
        score_map = {"大潮": 5, "中潮": 4, "若潮": 3, "小潮": 2, "長潮": 1}
        return score_map.get(tide_type, 3)
    elif mode == "タイラバ・根魚":
        score_map = {"中潮": 5, "若潮": 4, "小潮": 4, "大潮": 3, "長潮": 2}
        return score_map.get(tide_type, 3)
    else:  # イカメタル
        is_dark_night = (moon_age < 5 or moon_age > 24)
        if is_dark_night:
            return 5 if tide_type in ["中潮", "小潮", "若潮"] else 4
        else:
            return 2 if (11 <= moon_age <= 18) else 3

# --- 月の絵文字簡略版 ---
def get_simple_moon_emoji(age):
    if age < 1.8 or age >= 28.2: return "🌑"
    elif age < 12.9: return "🌓"
    elif age < 16.6: return "🌕"
    else: return "🌗"

# --- 潮回りの文字色指定 ---
def get_tide_color(tide_type):
    color_map = {"大潮": "#ef4444", "中潮": "#38bdf8", "小潮": "#34d399", "長潮": "#a1a1aa", "若潮": "#f43f5e"}
    return color_map.get(tide_type, "#f1f5f9")

# --- メイン画面表示 ---
st.markdown(f"""
<div class="fishing-card">
    <div class="card-title">⚓ {year}年 {month}月 作戦カレンダー</div>
    <div style="text-align: center; font-size: 13px; color: #94a3b8; margin-top: 5px;">
        モード: <b style="color: #38bdf8;">{mode}</b> | 濃い青色の日は<b>最高（⭐⭐⭐⭐⭐）</b>の潮回りです！
    </div>
</div>
""", unsafe_allow_html=True)

# カレンダーのデータ作成
cal = calendar.Calendar(firstweekday=6) # 日曜日から開始
month_days = cal.monthdayscalendar(year, month)

# HTMLカレンダーの組み立て
html_cal = '<table class="cal-table">'
html_cal += '<tr><th class="cal-th" style="color:#ef4444;">日</th><th class="cal-th">月</th><th class="cal-th">火</th><th class="cal-th">水</th><th class="cal-th">木</th><th class="cal-th">金</th><th class="cal-th" style="color:#38bdf8;">土</th></tr>'

for week in month_days:
    html_cal += '<tr>'
    for day in week:
        if day == 0:
            # 今月ではない空欄のマス
            html_cal += '<td class="cal-td" style="background: rgba(0,0,0,0.2); opacity: 0.2;"></td>'
        else:
            # 日付があるマス
            this_date = datetime.date(year, month, day)
            target_datetime = datetime.datetime.combine(this_date, datetime.time(12, 0))
            moon_age, tide_type = calculate_moon_and_tide(target_datetime)
            score = get_chance_score(tide_type, moon_age, mode)
            
            # 星マークと絵文字
            stars = "★" * score
            moon_emoji = get_simple_moon_emoji(moon_age)
            tide_color = get_tide_color(tide_type)
            
            # チャンス度に応じた背景クラス
            bg_class = f"bg-star{score}"
            
            html_cal += f"""
            <td class="cal-td {bg_class}">
                <div class="cal-day-num">{day}</div>
                <div class="cal-tide-text" style="color: {tide_color};">{tide_type}</div>
                <div class="cal-stars">{stars}</div>
                <div class="cal-moon">{moon_emoji} <span style="font-size:9px; color:#94a3b8;">{moon_age:.0e}</span></div>
            </td>
            """
    html_cal += '</tr>'
html_cal += '</table>'

st.markdown(html_cal, unsafe_allow_html=True)

# 凡例表示
st.markdown("""
<div style="margin-top: 15px; display: flex; justify-content: center; gap: 10px; font-size: 11px; color: #94a3b8;">
    <span><span style="color:#ef4444;">■</span> 大潮</span>
    <span><span style="color:#38bdf8;">■</span> 中潮</span>
    <span><span style="color:#34d399;">■</span> 小潮</span>
    <span><span style="color:#f43f5e;">■</span> 若潮</span>
    <span><span style="color:#a1a1aa;">■</span> 長潮</span>
</div>
""", unsafe_allow_html=True)
