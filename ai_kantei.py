import streamlit as st
import google.generativeai as genai
import datetime
import time  # リトライ機能用
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib.chart import Chart
from flatlib import const
from flatlib import aspects

# ==========================================
# 1. アプリ設定 & 定義データ
# ==========================================
st.set_page_config(page_title="AI古典占星術鑑定", layout="wide", page_icon="my_icon.png")

# --- サイドバーでの入力処理 ---
with st.sidebar:
    st.header("1. 設定")
    api_key = None
    
    # 1. まずStreamlitの金庫（Secrets）を探す
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("🔑 APIキーを読み込み済み")
    except:
        pass # 金庫がなくても気にしない

    # 2. 金庫になければ、手入力欄を出す
    if not api_key:
        api_key = st.text_input("Gemini APIキー", type="password")
        if not api_key:
            st.warning("⚠️ キーを入力してください")

    # 3. キー設定
    if api_key:
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            st.error(f"キー設定エラー: {e}")

# ==========================================
# 2. 定義データ (古典占星術)
# ==========================================
JP_NAMES = {
    'Sun': '太陽', 'Moon': '月', 'Mercury': '水星', 'Venus': '金星', 
    'Mars': '火星', 'Jupiter': '木星', 'Saturn': '土星', 
    'Uranus': '天王星', 'Neptune': '海王星', 'Pluto': '冥王星',
    'North Node': 'ノースノード', 'South Node': 'サウスノード',
    'Part of Fortune': 'パート・オブ・フォーチュン(POF)', # ★追加
    'Aries': '牡羊座', 'Taurus': '牡牛座', 'Gemini': '双子座',
    'Cancer': '蟹座', 'Leo': '獅子座', 'Virgo': '乙女座',
    'Libra': '天秤座', 'Scorpio': '蠍座', 'Sagittarius': '射手座',
    'Capricorn': '山羊座', 'Aquarius': '水瓶座', 'Pisces': '魚座'
}

# サインのリスト（POF計算用）
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

SIGN_ELEMENTS = {'Aries': 'Fire', 'Leo': 'Fire', 'Sagittarius': 'Fire', 'Taurus': 'Earth', 'Virgo': 'Earth', 'Capricorn': 'Earth', 'Gemini': 'Air', 'Libra': 'Air', 'Aquarius': 'Air', 'Cancer': 'Water', 'Scorpio': 'Water', 'Pisces': 'Water'}
DOROTHEUS_TRIPLICITY = {'Fire': {'Day': ['Sun', 'Jupiter', 'Saturn'], 'Night': ['Jupiter', 'Sun', 'Saturn']}, 'Earth': {'Day': ['Venus', 'Moon', 'Mars'], 'Night': ['Moon', 'Venus', 'Mars']}, 'Air': {'Day': ['Saturn', 'Mercury', 'Jupiter'], 'Night': ['Mercury', 'Saturn', 'Jupiter']}, 'Water': {'Day': ['Venus', 'Mars', 'Moon'], 'Night': ['Mars', 'Venus', 'Moon']}}
FACES = {'Aries': ['Mars', 'Sun', 'Venus'], 'Taurus': ['Mercury', 'Moon', 'Saturn'], 'Gemini': ['Jupiter', 'Mars', 'Sun'], 'Cancer': ['Venus', 'Mercury', 'Moon'], 'Leo': ['Saturn', 'Jupiter', 'Mars'], 'Virgo': ['Sun', 'Venus', 'Mercury'], 'Libra': ['Moon', 'Saturn', 'Jupiter'], 'Scorpio': ['Mars', 'Sun', 'Venus'], 'Sagittarius': ['Mercury', 'Moon', 'Saturn'], 'Capricorn': ['Jupiter', 'Mars', 'Sun'], 'Aquarius': ['Venus', 'Mercury', 'Moon'], 'Pisces': ['Saturn', 'Jupiter', 'Mars']}
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

# ==========================================
# 4. メイン画面レイアウト
# ==========================================
col_icon, col_title = st.columns([2, 10])

with col_icon:
    st.image("my_icon.png", width=100)

with col_title:
    st.title("AI古典占星術 鑑定システム")

with st.sidebar:
    st.markdown("---")
    st.header("2. 対象者データ")
    name = st.sidebar.text_input("お名前", "ゲスト")
    input_date = st.date_input("生年月日", datetime.date(1974, 4, 23))
    input_time = st.time_input("出生時間", datetime.time(9, 22), step=60)
    st.header("3. 場所設定")
    input_lat = st.text_input("緯度", "36.6953")
    input_lon = st.text_input("経度", "137.2113")
    st.markdown("---")
    calc_btn = st.button("① チャート計算を実行", type="primary")

if 'result_txt' not in st.session_state:
    st.session_state['result_txt'] = ""

# ==========================================
# 5. 計算ロジック（ホールサイン・POF対応）
# ==========================================
if calc_btn:
    try:
        date_str = input_date.strftime("%Y/%m/%d")
        time_str = input_time.strftime("%H:%M")
        date = Datetime(date_str, time_str, '+09:00')
        pos = GeoPos(float(input_lat), float(input_lon))
        
        all_p = [const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS, const.JUPITER, const.SATURN, const.URANUS, const.NEPTUNE, const.PLUTO, const.NORTH_NODE]
        trad_p = [const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS, const.JUPITER, const.SATURN]

        # ★ 修正: 常にホールサイン(Whole Sign)で計算
        chart_whole = Chart(date, pos, hsys=const.HOUSES_WHOLE_SIGN, IDs=all_p)

        # --- 昼夜（Sect）の判定 (ホールサイン基準) ---
        # 太陽が地平線(Asc-Dsc軸)より上にあるか下にあるか
        # 太陽のハウス(1-6:夜 / 7-12:昼)で判定するが、FlatlibのHouseオブジェクトから取得
        sun_obj = chart_whole.get(const.SUN)
        # FlatlibのHouseオブジェクトは通常 Placidus等がデフォルトになりがちなので
        # ホールサインでのハウス番号を手動で確実に計算する
        asc_obj = chart_whole.get(const.ASC)
        asc_sign_idx = SIGN_LIST.index(asc_obj.sign) # 牡羊座=0 ...
        sun_sign_idx = SIGN_LIST.index(sun_obj.sign)
        
        # 太陽のハウス = (太陽サイン - Ascサイン) + 1
        sun_house_num = (sun_sign_idx - asc_sign_idx) + 1
        if sun_house_num <= 0: sun_house_num += 12
        
        is_day = (7 <= sun_house_num <= 12) # 7〜12ハウスなら昼
        sect_str = "昼チャート (Day)" if is_day else "夜チャート (Night)"

        # --- ★ POF (Part of Fortune) の計算 ---
        asc_lon = asc_obj.lon # 絶対経度(0-360)
        sun_lon = sun_obj.lon
        moon_lon = chart_whole.get(const.MOON).lon
        
        if is_day:
            # 昼: ASC + 月 - 太陽
            pof_lon = (asc_lon + moon_lon - sun_lon) % 360
        else:
            # 夜: ASC + 太陽 - 月
            pof_lon = (asc_lon + sun_lon - moon_lon) % 360
            
        # POFのサインと度数を算出
        pof_sign_idx = int(pof_lon // 30)
        pof_deg = pof_lon % 30
        pof_sign = SIGN_LIST[pof_sign_idx]
        
        # POFのハウス (ホールサイン)
        pof_house_num = (pof_sign_idx - asc_sign_idx) + 1
        if pof_house_num <= 0: pof_house_num += 12

        # ----------------------------------------
        # 結果テキスト作成
        # ----------------------------------------
        lines = []
        def log(t): lines.append(t)

        log(f"【AI鑑定用 詳細データ】")
        log(f"生年月日: {date_str} {time_str}\nチャート区分: {sect_str}")
        log("-" * 60)
        
        log("【データ1: 天体位置・アングル】")
        for p_id in all_p:
            obj = chart_whole.get(p_id)
            d, m = int(obj.signlon), int((obj.signlon - int(obj.signlon)) * 60)
            retro = " (R)" if obj.isRetrograde() else ""
            log(f"{JP_NAMES.get(p_id):<6}: {JP_NAMES.get(obj.sign)} {d:02}度{m:02}分{retro} 【360度:{format_360(obj.sign, d, m)}】")
        
        asc, mc = chart_whole.get(const.ASC), chart_whole.get(const.MC)
        log(f"{'ASC':<6}: {JP_NAMES.get(asc.sign)} {int(asc.signlon):02}度 【360度:{format_360(asc.sign, int(asc.signlon), 0)}】")
        log(f"{'MC':<6}: {JP_NAMES.get(mc.sign)} {int(mc.signlon):02}度 【360度:{format_360(mc.sign, int(mc.signlon), 0)}】")
        
        # ★ POF出力
        log(f"{'POF':<6}: {JP_NAMES.get(pof_sign)} {int(pof_deg):02}度 (第{pof_house_num}ハウス)")
        log("-" * 60)

        log("\n【データ2: ディグニティ(惑星の強さ)】")
        scores, planet_score_map = [], {}
        for p_id in trad_p:
            obj = chart_whole.get(p_id)
            score, detail = calculate_dignity_score(p_id, obj.sign, obj.signlon, is_day)
            scores.append({'name': JP_NAMES.get(p_id), 'sign': JP_NAMES.get(obj.sign), 'deg': int(obj.signlon), 'score': score, 'detail': detail})
            planet_score_map[p_id] = score
        
        scores.sort(key=lambda x: x['score'], reverse=True)
        for i, s in enumerate(scores, 1):
            log(f"{i:<2}| {s['name']:<6}| {s['sign'][0]} {s['deg']:02}度 | {s['score']:+d} | {s['detail']}")
        log("-" * 60)

        log("\n【データ3: ハウス・ストレングス (Whole Sign)】")
        for i in range(1, 13):
            # ホールサインのハウスオブジェクトを取得
            h_obj = chart_whole.get(f'House{i}')
            ruler_en = RULERS.get(h_obj.sign)
            ruler_score = planet_score_map.get(ruler_en, 0)
            rank = "S" if ruler_score >= 7 else "A" if ruler_score >= 4 else "B" if ruler_score >= 0 else "C" if ruler_score >= -4 else "D"
            log(f"House{i:<2}: {HOUSE_THEMES[i-1]:<10} (支配星:{JP_NAMES.get(ruler_en)}) -> {rank}")
        log("-" * 60)

        log("\n【■ 主要アスペクト】")
        asp_names = {const.CONJUNCTION:'合(0度)', const.SEXTILE:'60度', const.SQUARE:'90度', const.TRINE:'120度', const.OPPOSITION:'180度'}
        check_list = all_p + [const.ASC, const.MC]
        for i, id1 in enumerate(check_list):
            for id2 in check_list[i+1:]:
                asp = aspects.getAspect(chart_whole.get(id1), chart_whole.get(id2), const.MAJOR_ASPECTS)
                if asp.exists() and asp.orb <= 5:
                    log(f"{JP_NAMES.get(id1,id1)} x {JP_NAMES.get(id2,id2)} : {asp_names.get(asp.type)} (誤差{asp.orb:.1f})")

        st.session_state['result_txt'] = "\n".join(lines)
        st.success("計算完了 (ホールサイン・POF対応)")
    except Exception as e: st.error(f"エラー: {e}")

# ==========================================
# 6. AI鑑定実行
# ==========================================
if 'result_txt' in st.session_state and st.session_state['result_txt']:
    
    col1, col2 = st.columns([1, 1.2])
    
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

                with st.status("🌌 星々と交信中...", expanded=True) as status:
                    max_retries = 3
                    
                    for attempt in range(max_retries):
                        try:
                            if attempt > 0:
                                st.write(f"⏳ 混雑中... ({attempt}/{max_retries})")
                                time.sleep(5 * attempt)

                            st.write(f"📡 宇宙（Gemini 2.0）に接続中... (試行: {attempt + 1}回目)")
                            
                            # =========================================================
                            # ★ 改良版プロンプト：激辛・ガチ古典モード
                            # =========================================================
                            prompt = f"""
                            あなたは「甘さを一切排除した厳格な古典占星術師」です。
                            相談者を慰めるのではなく、冷徹なまでに客観的な「運命の事実」のみを告げてください。
                            専門用語（セクト、エグザルテーション、ペレグリン等）を駆使し、吉凶をはっきりと断じてください。

                            以下の計算データを元に、マークダウン形式で出力してください。

                            【鑑定のポイント】
                            1. **惑星の品位（ディグニティ）とセクト**:
                               - 「セクト外」や「ペレグリン」「デトリメント・フォール」の惑星があれば、それがもたらす**「具体的な害悪・リスク・損失」**を容赦なく指摘してください。
                               - 逆に高品位な惑星があれば、それがもたらす**「圧倒的な才能」**を称えてください。

                            2. **パート・オブ・フォーチュン (POF)**:
                               - データにあるPOFのハウス位置から、この人が「現世的利益・幸運」を得られる具体的な場所を教えてください。

                            3. **性格と行動**:
                               - アセンダントと月星座、及びその支配星の状態から、本質的な性格を鋭く分析してください。
                               - 矛盾があれば「二面性」として指摘してください。

                            4. **ハウスの状況**:
                               - ハウスルーラーの強さ（S〜Dランク）に基づき、人生で「成功する分野」と「苦労する分野」を明確に分けてください。

                            5. **結論（激辛アドバイス）**:
                               - 最後に、このチャートの持ち主が人生を棒に振らないための、**厳しくも現実的な警告**を与えてください。

                            【計算データ】
                            {st.session_state['result_txt']}
                            """
                            # =========================================================

                            model = genai.GenerativeModel(target_model)
                            response = model.generate_content(prompt)
                            
                            if response.text:
                                result_text = response.text
                                status.update(label="✅ 鑑定完了！", state="complete", expanded=False)
                                success = True
                                break 

                        except Exception as e:
                            error_msg = str(e)
                            if "429" in error_msg or "Resource" in error_msg:
                                continue 
                            else:
                                status.update(label="❌ 予期せぬエラー", state="error")
                                st.error(f"詳細エラー: {error_msg}")
                                break
                    
                    if not success and not result_text:
                        status.update(label="❌ 混雑のため中断", state="error")
                        st.error("星々の回線が混み合っています。")

                if result_text:
                    st.markdown("### 🔮 鑑定結果")
                    st.markdown(result_text)
