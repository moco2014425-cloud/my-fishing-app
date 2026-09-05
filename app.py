import datetime
import math
import ephem
import numpy as np
import plotly.graph_objects as go
from ipywidgets import interact, widgets
from IPython.display import display, HTML

# --- スタイリング用のCSS（ダークモード風・京都の海をイメージしたディープブルー） ---
CSS_STYLE = """
<style>
    .fishing-card {
        background: linear-gradient(135deg, #0f172a 0%, #020617 100%);
        color: #f8fafc;
        padding: 25px;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        font-family: 'Helvetica Neue', Arial, sans-serif;
        max-width: 600px;
        margin: 10px 0;
        border: 1px solid #1e293b;
    }
    .card-title { font-size: 20px; font-weight: bold; color: #38bdf8; margin-bottom: 5px; letter-spacing: 1px; }
    .card-subtitle { font-size: 13px; color: #94a3b8; margin-bottom: 15px; }
    .metric-container { display: flex; justify-content: space-between; margin-bottom: 15px; }
    .metric-box { background: rgba(255,255,255,0.03); padding: 12px; border-radius: 8px; width: 48%; text-align: center; border: 1px solid #334155; }
    .metric-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px; }
    .metric-value { font-size: 18px; font-weight: bold; color: #f1f5f9; }
    .chance-box { background: linear-gradient(90deg, #0369a1 0%, #0284c7 100%); padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #0ea5e9; }
    .stars { font-size: 24px; color: #f59e0b; margin-top: 5px; text-shadow: 0 0 10px rgba(245,158,11,0.6); }
</style>
"""

# --- 日本海側（経ヶ岬）のリアルな潮位データをシミュレートする関数 ---
def get_kyogamisaki_tide(tide_type):
    # 日本海側は潮位の変化が非常に小さい（大潮でも最大30cm程度、小潮だと数cm）
    amplitude_map = {"大潮": 15, "中潮": 10, "小潮": 5, "長潮": 3, "若潮": 5}
    amp = amplitude_map.get(tide_type, 10)
    
    times = np.linspace(0, 24, 100)
    # 平均潮位を約35cmとし、日本海特有の小さななだらかな波を再現
    tide_levels = 35 + amp * np.sin(2 * np.pi * times / 12.42) + 4 * np.sin(2 * np.pi * times / 24)
    return times, tide_levels

# --- 月のビジュアル（絵文字）を取得する関数 ---
def get_moon_phase_emoji(age):
    if age < 1.8 or age >= 28.2: return "🌑 新月"
    elif age < 5.5: return "🌘 三日月"
    elif age < 9.2: return "🌓 上弦の月"
    elif age < 12.9: return "🌔 満月前"
    elif age < 16.6: return "🌕 満月"
    elif age < 20.3: return "🌖 満月後"
    elif age < 24.0: return "🌗 下弦の月"
    else: return "🌘 晦日"

# --- 月齢と潮回りを計算する関数 ---
def calculate_moon_and_tide(target_date):
    date_ephem = ephem.Date(target_date)
    prev_new_moon = ephem.previous_new_moon(date_ephem)
    moon_age = (date_ephem - prev_new_moon) % 29.53
    
    rounded_age = int(math.floor(moon_age)) % 30
    
    oo_shio = [0, 1, 2, 14, 15, 16, 17, 28, 29]
    naka_shio = [3, 4, 5, 6, 12, 13, 18, 19, 20, 21, 27]
    ko_shio = [7, 8, 11, 22, 23, 26]
    naga_shio = [9, 24]
    
    if rounded_age in oo_shio:
        tide_type = "大潮"
        chance_score = 5
        explanation = "🌊 経ヶ岬の大潮！わずかな潮の動きでも魚が動き出す大チャンス日です。"
    elif rounded_age in naka_shio:
        tide_type = "中潮"
        chance_score = 4
        explanation = "🎣 潮が程よく動き、青物からアオリイカまで最も安定して狙える好条件！"
    elif rounded_age in ko_shio:
        tide_type = "小潮"
        chance_score = 3
        explanation = "🐟 潮が緩い日は根魚（ロックフィッシュ）を足元でじっくり狙うのがオススメ。"
    elif rounded_age in naga_shio:
        tide_type = "長潮"
        chance_score = 2
        explanation = "⏰ 潮が止まりやすい日。マズメ時や、急な風の変化に集中しましょう。"
    else:
        tide_type = "若潮"
        chance_score = 3
        explanation = "🌀 『潮が若返る』タイミング。これからジワジワと状況が好転します！"
        
    return moon_age, tide_type, chance_score, explanation

# --- メインの描画関数 ---
def update_app(日付):
    target_date = datetime.datetime.combine(日付, datetime.time(12, 0))
    moon_age, tide_type, score, explanation = calculate_moon_and_tide(target_date)
    moon_emoji = get_moon_phase_emoji(moon_age)
    
    times, levels = get_kyogamisaki_tide(tide_type)
    stars_html = "★" * score + "☆" * (5 - score)
    
    # --- HTMLパネル表示 ---
    html_content = f"""
    {CSS_STYLE}
    <div class="fishing-card">
        <div class="card-title">⚓ KYOGAMISAKI NAVI</div>
        <div class="card-subtitle">京都府 京丹後市 経ヶ岬沖・磯エリア</div>
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
            <div class="metric-label" style="color: #cbd5e1;">🎯 釣りチャンス度</div>
            <div class="stars">{stars_html}</div>
            <div style="font-size: 13px; margin-top: 8px; color: #e0f2fe;">{explanation}</div>
        </div>
    </div>
    """
    display(HTML(html_content))
    
    # --- グラフ表示 ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=levels,
        mode='lines+markers',
        marker=dict(size=4),
        line=dict(color='#0ea5e9', width=3),
        fill='tozeroy',
        fillcolor='rgba(14, 165, 233, 0.05)',
        name='潮位'
    ))
    
    # マズメ時ハイライト
    fig.add_vrect(x0=5, x1=7, fillcolor="rgba(251, 146, 60, 0.12)", layer="below", line_width=0, annotation_text="朝マズメ", annotation_position="top left", annotation_font=dict(color="#fb923c"))
    fig.add_vrect(x0=17, x1=19, fillcolor="rgba(129, 140, 248, 0.12)", layer="below", line_width=0, annotation_text="夕マズメ", annotation_position="top left", annotation_font=dict(color="#818cf8"))

    fig.update_layout(
        title=dict(text=f"📊 経ヶ岬 予測タイドグラフ ({日付.strftime('%Y/%m/%d')})", font=dict(color='#f8fafc', size=15)),
        template="plotly_dark",
        paper_bgcolor='rgba(2, 6, 23, 1)',
        plot_bgcolor='rgba(15, 23, 42, 0.6)',
        xaxis=dict(title="時間 (Hour)", tickmode='linear', tick0=0, dtick=2, range=[0, 24], gridcolor='#1e293b'),
        yaxis=dict(title="潮位 (cm)", gridcolor='#1e293b', range=[0, 80]), # 日本海用に縦軸を0〜80cmに最適化
        margin=dict(l=40, r=40, t=50, b=40),
        height=340,
        showlegend=False
    )
    fig.show()

# --- ウィジェット起動 ---
today = datetime.date.today()
interact(update_app, 日付=widgets.DatePicker(value=today, description='日付を選択:'))
