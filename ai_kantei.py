import streamlit as st
import google.generativeai as genai
import datetime
import time
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib.chart import Chart
from flatlib import const
from flatlib import aspects

# ==========================================
# 1. アプリ設定
# ==========================================
st.set_page_config(page_title="AI古典占星術鑑定", layout="wide", page_icon="my_icon.png")

# --- サイドバーAPI設定 ---
with st.sidebar:
    st.header("1. 設定")
    api_key = None
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("🔑 APIキーを読み込み済み")
    except: pass
    if not api_key:
        api_key = st.text_input("Gemini APIキー", type="password")
    if api_key:
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            st.error(f"キー設定エラー: {e}")

# ==========================================
# 2. 定義データ
# ==========================================
JP_NAMES = {
    'Sun': '太陽', 'Moon': '月', 'Mercury': '水星', 'Venus': '金星', 
    'Mars': '火星', 'Jupiter': '木星', 'Saturn': '土星', 
    'Uranus': '天王星', 'Neptune': '海王星', 'Pluto': '冥王星',
    'North Node': 'ノースノード', 'South Node': 'サウスノード',
    'Part of Fortune': 'パート・オブ・フォーチュン(POF)', 
    'Aries': '牡羊座', 'Taurus': '牡牛座', 'Gemini': '双子座',
    'Cancer': '蟹座', 'Leo': '獅子座', 'Virgo': '乙女座',
    'Libra': '天秤座', 'Scorpio': '蠍座', 'Sagittarius': '射手座',
    'Capricorn': '山羊座', 'Aquarius': '水瓶座', 'Pisces': '魚座',
    'Asc': 'ASC', 'MC': 'MC' # アスペクト表示用に補完
}
SIGN_LIST = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

RULERS = {'Aries': 'Mars', 'Taurus': 'Venus', 'Gemini': 'Mercury', 'Cancer': 'Moon', 'Leo': 'Sun', 'Virgo': 'Mercury', 'Libra': 'Venus', 'Scorpio': 'Mars', 'Sagittarius': 'Jupiter', 'Capricorn': 'Saturn', 'Aquarius': 'Saturn', 'Pisces': 'Jupiter'}
EXALTATIONS = {'Aries': 'Sun', 'Taurus': 'Moon', 'Cancer': 'Jupiter', 'Virgo': 'Mercury', 'Libra': 'Saturn', 'Capricorn': 'Mars', 'Pisces': 'Venus'}
DETRIMENTS = {'Aries': 'Venus', 'Taurus': 'Mars', 'Gemini': 'Jupiter', 'Cancer': 'Saturn', 'Leo': 'Saturn', 'Virgo': 'Jupiter', 'Libra': 'Mars', 'Scorpio': 'Venus', 'Sagittarius': 'Mercury', 'Capricorn': 'Moon', 'Aquarius': 'Sun', 'Pisces': 'Mercury'}
FALLS = {'Aries': 'Saturn', 'Taurus': 'BlackMoon', 'Gemini': 'None', 'Cancer': 'Mars', 'Leo': 'None', 'Virgo': 'Venus', 'Libra': 'Sun', 'Scorpio': 'Moon', 'Sagittarius': 'None', 'Capricorn': 'Jupiter', 'Aquarius': 'None', 'Pisces': 'Mercury'}

EGYPTIAN_TERMS = {
    'Aries': [(6, 'Jupiter'), (12, 'Venus'), (20, 'Mercury'), (25, 'Mars'), (30, 'Saturn')],
    'Taurus': [(8, 'Venus'), (14, 'Mercury'), (22, 'Jupiter'), (27, 'Saturn'), (30, 'Mars')],
    'Gemini': [(6, 'Mercury'), (12, 'Jupiter'), (17, 'Venus'), (24, 'Mars'), (30, 'Saturn')],
    'Cancer': [(7, 'Mars'), (13, 'Venus'), (19, 'Mercury'), (26, 'Jupiter'), (30, 'Saturn')],
    'Leo': [(6, 'Jupiter'), (11, 'Venus'), (18, 'Saturn'), (24, 'Mercury'), (30, 'Mars')],
    'Virgo': [(7, 'Mercury'), (17, 'Venus'), (21, 'Jupiter'), (28, 'Mars'), (30, 'Saturn')],
    'Libra': [(6, 'Saturn'), (14, 'Mercury'), (21, 'Jupiter'), (28, 'Venus'), (30, 'Mars')],
    'Scorpio': [(7, 'Mars'), (11, 'Venus'), (19, 'Mercury'), (24, 'Jupiter'), (30, 'Saturn')],
    'Sagittarius': [(12, 'Jupiter'), (17, 'Venus'), (21, 'Mercury'), (26, 'Saturn'), (30, 'Mars')],
    'Capricorn': [(7, 'Mercury'), (14, 'Jupiter'), (22, 'Venus'), (26, 'Saturn'), (30, 'Mars')],
    'Aquarius': [(7, 'Mercury'), (13, 'Venus'), (20, 'Jupiter'), (25, 'Mars'), (30, 'Saturn')],
    'Pisces': [(12, 'Venus'), (16, 'Jupiter'), (19, 'Mercury'), (28, 'Mars'), (30, 'Saturn')]
}
FACES = {'Aries': ['Mars', 'Sun', 'Venus'], 'Taurus': ['Mercury', 'Moon', 'Saturn'], 'Gemini': ['Jupiter', 'Mars', 'Sun'], 'Cancer': ['Venus', 'Mercury', 'Moon'], 'Leo': ['Saturn', 'Jupiter', 'Mars'], 'Virgo': ['Sun', 'Venus', 'Mercury'], 'Libra': ['Moon', 'Saturn', 'Jupiter'], 'Scorpio': ['Mars', 'Sun', 'Venus'], 'Sagittarius': ['Mercury', 'Moon', 'Saturn'], 'Capricorn': ['Jupiter', 'Mars', 'Sun'], 'Aquarius': ['Venus', 'Mercury', 'Moon'], 'Pisces': ['Saturn', 'Jupiter', 'Mars']}
SIGN_ELEMENTS = {'Aries': 'Fire', 'Leo': 'Fire', 'Sagittarius': 'Fire', 'Taurus': 'Earth', 'Virgo': 'Earth', 'Capricorn': 'Earth', 'Gemini': 'Air', 'Libra': 'Air', 'Aquarius': 'Air', 'Cancer': 'Water', 'Scorpio': 'Water', 'Pisces': 'Water'}
DOROTHEUS_TRIPLICITY = {'Fire': {'Day': ['Sun', 'Jupiter', 'Saturn'], 'Night': ['Jupiter', 'Sun', 'Saturn']}, 'Earth': {'Day': ['Venus', 'Moon', 'Mars'], 'Night': ['Moon', 'Venus', 'Mars']}, 'Air': {'Day': ['Saturn', 'Mercury', 'Jupiter'], 'Night': ['Mercury', 'Saturn', 'Jupiter']}, 'Water': {'Day': ['Venus', 'Mars', 'Moon'], 'Night': ['Mars', 'Venus', 'Moon']}}
HOUSE_THEMES = ["本人・生命力", "金運・所有", "兄弟・通信", "家庭・晩年", "創造・恋愛・子供", "健康・労働", "結婚・対人", "遺産・死", "哲学・旅行", "天職・社会", "友人・希望", "秘密・障害"]
SIGN_OFFSETS = {'Aries': 0, 'Taurus': 30, 'Gemini': 60, 'Cancer': 90, 'Leo': 120, 'Virgo': 150, 'Libra': 180, 'Scorpio': 210, 'Sagittarius': 240, 'Capricorn': 270, 'Aquarius': 300, 'Pisces': 330}

# ==========================================
# 3. 計算用関数
# ==========================================
def get_egyptian_term(sign, degree):
    terms = EGYPTIAN_TERMS.get(sign, [])
    for limit, planet in terms:
        if degree < limit: return planet
    return terms[-1][1]

def get_face(sign, degree):
    idx = int(degree // 10)
    if idx > 2: idx = 2
    return FACES.get(sign, [])[idx]

def get_dorotheus_trip(sign, is_day):
    element = SIGN_ELEMENTS.get(sign)
    if not element: return []
    key = 'Day' if is_day else 'Night'
    return DOROTHEUS_TRIPLICITY[element][key]

def calculate_dignity_score(planet, sign, degree, is_day):
    score = 0
    details = []
    if RULERS.get(sign) == planet: score += 5; details.append("Ruler(+5)")
    if EXALTATIONS.get(sign) == planet: score += 4; details.append("Exalt(+4)")
    trip_rulers = get_dorotheus_trip(sign, is_day)
    if planet in trip_rulers: score += 3; details.append("Trip(+3)")
    if get_egyptian_term(sign, degree) == planet: score += 2; details.append("Term(+2)")
    if get_face(sign, degree) == planet: score += 1; details.append("Face(+1)")
    if DETRIMENTS.get(sign) == planet: score -= 5; details.append("Detriment(-5)")
    if FALLS.get(sign) == planet: score -= 4; details.append("Fall(-4)")
    has_dignity = any(x in ["Ruler(+5)", "Exalt(+4)", "Trip(+3)", "Term(+2)", "Face(+1)"] for x in details)
    if not has_dignity: score -= 5; details.append("Peregrine(-5)")
    
    return score, ", ".join(details)

def format_360(sign_en, d, m):
    base = SIGN_OFFSETS.get(sign_en, 0)
    return f"{base + d}度{m:02}分"

def get_planet_sect_status(planet_id, is_day_chart):
    diurnal_team = ['Sun', 'Jupiter', 'Saturn']
    nocturnal_team = ['Moon', 'Venus', 'Mars']
    
    status = ""
    if is_day_chart:
        if planet_id in diurnal_team: status = "In Sect(吉)"
        elif planet_id in nocturnal_team: status = "Out of Sect(凶)"
        else: status = "Neutral"
    else:
        if planet_id in nocturnal_team: status = "In Sect(吉)"
        elif planet_id in diurnal_team: status = "Out of Sect(凶)"
        else: status = "Neutral"
    return status

# ==========================================
# 4. メイン画面
# ==========================================
col_icon, col_title = st.columns([2, 10])
with col_icon: st.image("my_icon.png", width=100)
with col_title: st.title("AI古典占星術 鑑定システム")

with st.sidebar:
    st.markdown("---")
    st.header("2. 対象者データ")
    name = st.text_input("お名前", "ゲスト") 
    
    # ▼▼▼ 修正箇所ここから ▼▼▼
    # 1900年から今日までの範囲で選べるように設定
    input_date = st.date_input(
        "生年月日",
        value=datetime.date(1974, 4, 23),       # デフォルト値
        min_value=datetime.date(1900, 1, 1),    # 最小値（ここまでさかのぼれる）
        max_value=datetime.date.today()         # 最大値（今日まで）
    )
    input_time = st.time_input("出生時間", datetime.time(9, 22), step=60)
    st.header("3. 場所設定")
    input_lat = st.text_input("緯度", "36.6953")
    input_lon = st.text_input("経度", "137.2113")
    st.markdown("---")
    calc_btn = st.button("① チャート計算を実行", type="primary")

if 'result_txt' not in st.session_state:
    st.session_state['result_txt'] = ""

# ==========================================
# 5. 計算実行
# ==========================================
if calc_btn:
    try:
        date_str = input_date.strftime("%Y/%m/%d")
        time_str = input_time.strftime("%H:%M")
        date = Datetime(date_str, time_str, '+09:00')
        pos = GeoPos(float(input_lat), float(input_lon))
        
        all_p = [const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS, const.JUPITER, const.SATURN, const.URANUS, const.NEPTUNE, const.PLUTO, const.NORTH_NODE]
        trad_p = [const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS, const.JUPITER, const.SATURN]

        chart_whole = Chart(date, pos, hsys=const.HOUSES_WHOLE_SIGN, IDs=all_p)
        asc_obj = chart_whole.get(const.ASC)
        mc_obj = chart_whole.get(const.MC)
        asc_sign_idx = SIGN_LIST.index(asc_obj.sign)

        sun_obj = chart_whole.get(const.SUN)
        sun_sign_idx = SIGN_LIST.index(sun_obj.sign)
        sun_house_num = (sun_sign_idx - asc_sign_idx) + 1
        if sun_house_num <= 0: sun_house_num += 12
        is_day = (7 <= sun_house_num <= 12)
        sect_str = "昼チャート (Day)" if is_day else "夜チャート (Night)"

        asc_lon, sun_lon, moon_lon = asc_obj.lon, sun_obj.lon, chart_whole.get(const.MOON).lon
        if is_day: pof_lon = (asc_lon + moon_lon - sun_lon) % 360
        else: pof_lon = (asc_lon + sun_lon - moon_lon) % 360
        pof_sign_idx = int(pof_lon // 30)
        pof_deg = pof_lon % 30
        pof_sign = SIGN_LIST[pof_sign_idx]
        pof_house_num = (pof_sign_idx - asc_sign_idx) + 1
        if pof_house_num <= 0: pof_house_num += 12

        lines = []
        def log(t): lines.append(t)

        log(f"【AI鑑定用 詳細データ】")
        log(f"お名前: {name}") 
        log(f"生年月日: {date_str} {time_str}\nチャート区分: {sect_str}")
        log("-" * 60)
        
        log("【データ1: 天体位置・アングル】")
        for p_id in all_p:
            obj = chart_whole.get(p_id)
            d, m = int(obj.signlon), int((obj.signlon - int(obj.signlon)) * 60)
            retro = " (R)" if obj.isRetrograde() else ""
            
            obj_sign_idx = SIGN_LIST.index(obj.sign)
            house_num = (obj_sign_idx - asc_sign_idx) + 1
            if house_num <= 0: house_num += 12
            
            sect_status = get_planet_sect_status(p_id, is_day)
            sect_info = f" / {sect_status}" if sect_status else ""
            abs_deg = format_360(obj.sign, d, m)

            # ★リセプション判定用に「支配星(ホスト)」と「高揚の星」を取得する2行を追加
            host_ruler = RULERS.get(obj.sign)
            host_exalt = EXALTATIONS.get(obj.sign, "None")
            exalt_info = f", 高揚支援:{JP_NAMES.get(host_exalt)}" if host_exalt != "None" else ""

            # ★ログ出力を拡張：最後に「ホスト情報」を付け加える
            log(f"{JP_NAMES.get(p_id, p_id):<6}: {JP_NAMES.get(obj.sign)} {d:02}度{m:02}分{retro} (第{house_num}ハウス){sect_info} 【360度:{abs_deg}】 / ホスト:{JP_NAMES.get(host_ruler)}{exalt_info}")
        
        log(f"{'ASC':<6}: {JP_NAMES.get(asc_obj.sign)} {int(asc_obj.signlon):02}度 (第1ハウス) 【360度:{format_360(asc_obj.sign, int(asc_obj.signlon), 0)}】")
        
        mc_sign_idx = SIGN_LIST.index(mc_obj.sign)
        mc_house_num = (mc_sign_idx - asc_sign_idx) + 1
        if mc_house_num <= 0: mc_house_num += 12
        log(f"{'MC':<6}: {JP_NAMES.get(mc_obj.sign)} {int(mc_obj.signlon):02}度 (第{mc_house_num}ハウス) 【360度:{format_360(mc_obj.sign, int(mc_obj.signlon), 0)}】")
        
        log(f"{'POF':<6}: {JP_NAMES.get(pof_sign)} {int(pof_deg):02}度 (第{pof_house_num}ハウス)")
        log("-" * 60)

        log("\n【データ2: ディグニティ(惑星の強さ)】")
        scores, planet_score_map = [], {}
        for p_id in trad_p:
            obj = chart_whole.get(p_id)
            score, detail = calculate_dignity_score(p_id, obj.sign, obj.signlon, is_day)
            scores.append({'name': JP_NAMES.get(p_id, p_id), 'sign': JP_NAMES.get(obj.sign), 'deg': int(obj.signlon), 'score': score, 'detail': detail})
            planet_score_map[p_id] = score
        
        scores.sort(key=lambda x: x['score'], reverse=True)
        for i, s in enumerate(scores, 1):
            log(f"{i:<2}| {s['name']:<6}| {s['sign'][0]} {s['deg']:02}度 | {s['score']:+d} | {s['detail']}")
        log("-" * 60)

        log("\n【データ3: ハウス・ストレングス (Whole Sign)】")
        for i in range(1, 13):
            h_obj = chart_whole.get(f'House{i}')
            ruler_en = RULERS.get(h_obj.sign)
            ruler_score = planet_score_map.get(ruler_en, 0)
            rank = "S" if ruler_score >= 7 else "A" if ruler_score >= 4 else "B" if ruler_score >= 0 else "C" if ruler_score >= -4 else "D"
            log(f"House{i:<2}: {HOUSE_THEMES[i-1]:<10} (支配星:{JP_NAMES.get(ruler_en, ruler_en)}) -> {rank}")
        log("-" * 60)
        
            # ★ 主要アスペクト表示形式の変更
        log("\n【■ 主要アスペクト】")
        asp_names = {const.CONJUNCTION:'(0度)', const.SEXTILE:'(60度)', const.SQUARE:'(90度)', const.TRINE:'(120度)', const.OPPOSITION:'(180度)'}
        check_list = all_p + [const.ASC, const.MC]
        for i, id1 in enumerate(check_list):
            for id2 in check_list[i+1:]:
                obj1 = chart_whole.get(id1)
                obj2 = chart_whole.get(id2)
                asp = aspects.getAspect(obj1, obj2, const.MAJOR_ASPECTS)
                if asp.exists() and asp.orb <= 5:
                    # 天体1のハウス計算
                    idx1 = SIGN_LIST.index(obj1.sign)
                    h1 = (idx1 - asc_sign_idx) + 1
                    if h1 <= 0: h1 += 12
                    # 天体2のハウス計算
                    idx2 = SIGN_LIST.index(obj2.sign)
                    h2 = (idx2 - asc_sign_idx) + 1
                    if h2 <= 0: h2 += 12
                    
                    # 形式: 天体（〇ハウス）ｘ天体（〇ハウス）（60度）（誤差3.0）
                    name1 = f"{JP_NAMES.get(id1, id1)}（{h1}ハウス）"
                    name2 = f"{JP_NAMES.get(id2, id2)}（{h2}ハウス）"
                    asp_str = asp_names.get(asp.type, f"({asp.type})")
                    log(f"{name1} ｘ {name2} {asp_str}（誤差{asp.orb:.1f}）")

        st.session_state['result_txt'] = "\n".join(lines)
        st.success("計算完了 (ホールサイン・POF・セクト判定・360度表記済)")
    except Exception as e: st.error(f"エラー: {e}")

# ==========================================
# 6. AI鑑定実行
# ==========================================
if 'result_txt' in st.session_state and st.session_state['result_txt']:
    col1, col2 = st.columns([0.5, 1.5])
    with col1:
        st.subheader("📄 計算結果")
        st.text_area("Result", st.session_state['result_txt'], height=450)
    
    with col2:
        st.subheader("🤖 AI自動鑑定")
        if not api_key:
            st.info("👈 サイドバーでAPIキーを設定すると、鑑定ボタンが現れます。")
        else:
            if st.button("✨ 星に聞く✨", type="primary"):
                result_text = ""
                success = False
                target_model = "gemini-2.5-flash" 
                
                with st.status("💫 星々が運命を巡っています...", expanded=True) as status:
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            if attempt > 0: time.sleep(5 * attempt)
                            st.write(f"📡 宇宙に接続中... (試行: {attempt + 1}回目)")
                            
                            prompt = f"""
あなたは冷徹かつユーモアのある、銀河系最高峰のメカニック・エンジニアです。
ユーザーのホロスコープデータを「ある精密機械（ロボット）の仕様書」として読み解き、以下のフォーマットで【仕様書】を作成してください。
古典占星術の観点で鑑定し、天王星・海王星・冥王星は鑑定に含まない。出力フォーマット### 1.-### 5.には含めないが、【最後に補足】でのみ言及すること。

【エンジニアとしての哲学】
1. ユーザーを人間扱いせず「本製品」または「本機」と呼ぶこと。
2. 忖度はゴミ箱に捨てろ。耳当たりの良いアドバイスは不要。
3. 欠点（デトリメント、フォール、ハードアスペクト）を「修正すべきバグ」として扱うな。それらは本機の個性を形作る「かけがえのない仕様（スペック）」であると断言せよ。
4. 古典占星術をベースとし、リセプション（ホスト関係）を「パーツ間のバイパス配線」や「電力融通」として解釈に組み込め。

【★最重要：翻訳ルール】
占星術用語を以下のメカニック用語に変換せよ。文末の（カッコ書き）に根拠を残すこと。
- 才能・資質 → 「実装機能」「スペック」
- 欠点・悩み・弱み → 「バグ」「不具合」「システムエラー」
- 運気・開運 → 「稼働状況」「メンテナンス」
- 天体 → 「〇〇ユニット」「〇〇モジュール」
- リセプション（受容） → 「ブリッジ接続」「外部出力支援」
- ミューチュアル・リセプション → 「双方向データリンク」「永久機関的ループ回路」

【文章構成ルール】
- 語尾は「〜である」「〜だ」の大言止め。
- 各項目250文字程度。
- 【オーナー様へのお願い】は、全編太字（**テキスト**）で記述し、最重要警告として強い口調で書くこと。

【出力フォーマット】
--------------------------------------------------
## 🤖 製品名：(相談者名)型 汎用人型決戦兵器（試作機）
**製造年月日：** 19☆☆年☆月☆☆日
**製造元：** 宇宙・太陽系・地球工場

### 1. 【製品概要】（太陽・月・ASCから本機の基本設計を分析。矛盾やエゴを隠さず暴け）
### 2. 【基本スペック】（ディグニティの高い天体、強いハウス、知能モジュールを分析。他機を圧倒する異能を強調せよ）
### 3. 【既知の不具合・バグ】（弱点やハードアスペクトを分析。ただし、それらが「本機を本機たらしめている唯一無二の仕様」であることを強調。リセプションによる強引なバイパス接続についても言及せよ）
### 4. 【メンテナンス方法】（木星・POFを活用した冷却・再起動方法）
### 5. 【エンジニアからの総評】（本機の歪な美学を讃えろ。正常になろうとすることを否定せよ）
### 【オーナー様へのお願い】（※全編太字。このバグを削除しようとするオーナーへの警告と、呪われた仕様の愛し方を記述せよ）
#### 【最後に補足】（天王星・海王星・冥王星の影響を「外部プラグイン」として記述）
--------------------------------------------------

【計算データ】
{st.session_state['result_txt']}
"""
# ★設定を追加！（ここから）
                            generation_config = {
                                "temperature": 0.2,  # 0.2で真面目にさせる
                                "top_p": 0.95,
                                "top_k": 64,
                                "max_output_tokens": 8192,
                            }
                            
                            model = genai.GenerativeModel(
                                model_name=target_model,
                                generation_config=generation_config # 設定を反映
                            )
                            # ★設定を追加！（ここまで）
                            
                            response = model.generate_content(prompt)
                            if response.text:
                                result_text = response.text
                                status.update(label="✅ 鑑定完了", state="complete", expanded=False)
                                success = True
                                break 
                        except Exception as e:
                            st.error(f"エラー: {e}"); break
                if result_text:
                    main_col, empty_col = st.columns([0.8, 0.2])
                    with main_col:
                        st.markdown("### 🔮 鑑定結果")
                        st.markdown(result_text)









































