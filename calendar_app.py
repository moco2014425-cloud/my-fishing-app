import datetime
import calendar
import math
import ephem
import pandas as pd
import streamlit as st

# --- ページ設定（スマホ対応） ---
st.set_page_config(page_title="経ヶ岬沖 月間オフショアナビ", page_icon="⚓", layout="centered")

st.title("⚓ 経ヶ岬沖 月間カレンダー")
st.caption("何年先でも一気見可能！オフショア釣行最適日予測ツール")

# --- サイドバー（年・月・モードの選択） ---
st.sidebar.header("⚙️ 釣行スケジュール設定")
today = datetime.date.today()

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
    
    oo_shio = [0, 1, 2, 14, 15, 16, 17, 27, 28, 29]
    naka_shio = [3, 4, 5, 11, 12, 13, 18, 19, 20, 25, 26]
    ko_shio = [6, 7, 8, 21, 22, 23]
    naga_shio = [9, 24]
    
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

def get_simple_moon_emoji(age):
    if age < 1.8 or age >= 28.2: return "🌑"
    elif age < 12.9: return "🌓"
    elif age < 16.6: return "🌕"
    else: return "🌗"

# --- カレンダーデータの作成（文字化け絶対しない版） ---
cal = calendar.Calendar(firstweekday=6) # 日曜から開始
month_days = cal.monthdayscalendar(year, month)

st.subheader(f"📊 {year}年 {month}月 の釣行おすすめ度")
st.write(f"現在のモード: **{mode}**")

# データフレームを使って綺麗な表を作る
weeks_list = []
for week in month_days:
    week_data = {}
    week_days_names = ["日", "月", "火", "水", "木", "金", "土"]
    
    for idx, day in enumerate(week):
        w_name = week_days_names[idx]
        if day == 0:
            week_data[w_name] = ""
        else:
            this_date = datetime.date(year, month, day)
            target_datetime = datetime.datetime.combine(this_date, datetime.time(12, 0))
            moon_age, tide_type = calculate_moon_and_tide(target_datetime)
            score = get_chance_score(tide_type, moon_age, mode)
            
            stars = "★" * score
            moon_emoji = get_simple_moon_emoji(moon_age)
            
            # 1つのマスの中に「日・潮・星・月」を表示
            week_data[w_name] = f"【{day}日】\n{tide_type}\n{stars}\n{moon_emoji} (齢{moon_age:.1f})"
            
    weeks_list.append(week_data)

# 表（データフレーム）に変換してStreamlitの標準機能でドーンと表示
df = pd.DataFrame(weeks_list)
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("""
💡 **見方**：マスの中の星（★）が多いほど、選んだモードに適した大チャンス日です！サイドバーから年や月、釣り方を変えてみてください。
""")
