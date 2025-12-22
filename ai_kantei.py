import streamlit as st
import google.generativeai as genai
import datetime
import time  # ★リトライ機能用
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib.chart import Chart
from flatlib import const
from flatlib import aspects

# ==========================================
# 1. アプリ設定 & 定義データ
# ==========================================
# ↓↓↓ さっきの「金庫の鍵」コードはこのすぐ下に書きます ↓↓↓
try:
    my_api_key = st.secrets["GEMINI_API_KEY"]
except FileNotFoundError:
    st.error("APIキーが見つかりません。")
    st.stop()

genai.configure(api_key=my_api_key)

# ... 他のimport ...

# --- サイドバーでの入力処理 ---
with st.sidebar:
    
    # ★ここが改良版のキー読み込みロジックです
    api_key = None
    
    # 1. まずStreamlitの金庫（Secrets）を探す
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
    except:
        pass # 金庫がなくても気にしない（手入力を待つ）

    # 2. 金庫になければ、手入力欄を出す
    if not api_key:
        api_key = st.text_input("Gemini APIキー", type="password")
        if not api_key:
            st.warning("⚠️ キーを入力してください")

    # 3. キーが見つかったら設定する
    if api_key:
        try:
            genai.configure(api_key=api_key)
        except Exception as e:
            st.error(f"キー設定エラー: {e}")

    # --- この下に「対象者データ」などの入力欄が続きます ---
    # st.subheader("2. 対象者データ") ...

# ==========================================
# 1. 定義データ (古典占星術)
# ==========================================
JP_NAMES = {
    'Sun': '太陽', 'Moon': '月', 'Mercury': '水星', 'Venus': '金星', 
    'Mars': '火星', 'Jupiter': '木星', 'Saturn': '土星', 
    'Uranus': '天王星', 'Neptune': '海王星', 'Pluto': '冥王星',
    'North Node': 'ノースノード', 'South Node': 'サウスノード',
    'Aries': '牡羊座', 'Taurus': '牡牛座', 'Gemini': '双子座',
    'Cancer': '蟹座', 'Leo': '獅子座', 'Virgo': '乙女座',
    'Libra': '天秤座', 'Scorpio': '蠍座', 'Sagittarius': '射手座',
    'Capricorn': '山羊座', 'Aquarius': '水瓶座', 'Pisces': '魚座'
}

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
# 2. 計算用関数
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
# 3. アプリ本体
# ==========================================
st.set_page_config(page_title="AI古典占星術鑑定", layout="wide", page_icon="my_icon.png")

# --- タイトル部分のレイアウト変更 ---
# 画面上で画像とタイトルを横に並べるために、列（カラム）を作ります
# [1, 10] は「画像の幅 : タイトルの幅」の比率です（アイコンの大きさに合わせて数字を変えてOK）
col_icon, col_title = st.columns([2, 10])

with col_icon:
    # ここでアイコン画像を表示（widthで大きさを調整）
    st.image("my_icon.png", width=100)

with col_title:
    # ここは文字だけを表示
    st.title("AI古典占星術 鑑定システム")

with st.sidebar:
    st.header("1. 設定")
    api_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            st.success("🔑 APIキーを読み込み済み")
    except: pass
    if not api_key:
        api_key = st.text_input("Gemini APIキー", type="password")

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

if calc_btn:
    try:
        date_str = input_date.strftime("%Y/%m/%d")
        time_str = input_time.strftime("%H:%M")
        date = Datetime(date_str, time_str, '+09:00')
        pos = GeoPos(float(input_lat), float(input_lon))
        
        all_p = [const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS, const.JUPITER, const.SATURN, const.URANUS, const.NEPTUNE, const.PLUTO, const.NORTH_NODE]
        trad_p = [const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS, const.JUPITER, const.SATURN]

        chart_whole = Chart(date, pos, hsys=const.HOUSES_WHOLE_SIGN, IDs=all_p)
        chart_placidus = Chart(date, pos, hsys=const.HOUSES_PLACIDUS, IDs=all_p)

        sun_obj = chart_placidus.get(const.SUN)
        sun_lon = sun_obj.lon
        sun_house = 1
        for i in range(1, 13):
            h = chart_placidus.get(f'House{i}')
            start, end = h.lon, (h.lon + h.size) % 360
            if start < end:
                if start <= sun_lon < end: sun_house = i; break
            else:
                if start <= sun_lon or sun_lon < end: sun_house = i; break
        
        is_day = (7 <= sun_house <= 12)
        sect_str = "昼チャート (Day)" if is_day else "夜チャート (Night)"

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

        log("\n【データ3: ハウス・ストレングス】")
        for i in range(1, 13):
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
        st.success("計算完了")
    except Exception as e: st.error(f"エラー: {e}")

# --- AI鑑定ボタン ---
# --- メイン画面の最後の方 ---

# (計算結果の表示エリアなど...)
if 'result_txt' in st.session_state and st.session_state['result_txt']:
    
    # 画面を左右に分割（左：計算結果、右：AI鑑定）
    col1, col2 = st.columns([1.2, 1])
    
    with col1:
        st.subheader("📄 計算結果")
        st.text_area("Result", st.session_state['result_txt'], height=450)
    
# ------------------------------------------------------------------
    # ▼ ここから右側エリア（AI鑑定）の完全版コード ▼
    # ------------------------------------------------------------------
    with col2:
        st.subheader("🤖 AI自動鑑定")
        
        # キーがない時はボタンを押させない
        if not api_key:
            st.info("👈 サイドバーでAPIキーを設定すると、鑑定ボタンが現れます。")
        else:
            # ★鑑定ボタン
            if st.button("✨ 星に聞く✨", type="primary"):
                
                # 変数の初期化
                result_text = ""
                success = False
                target_model = "gemini-2.5-flash"  # ★最新モデル指定

                # ★魔法の演出（st.statusを使うと途中経過が見えて安心です）
                with st.status("🌌 星々と交信中... (星の配置を読み解いています)", expanded=True) as status:
                    
                    max_retries = 3
                    
                    for attempt in range(max_retries):
                        try:
                            # 2回目以降は少し待つ（API制限対策）
                            if attempt > 0:
                                st.write(f"⏳ 混雑中... 星の導きを待っています ({attempt}/{max_retries})")
                                time.sleep(5 * attempt)

                            st.write(f"📡 宇宙（Gemini 2.0）に接続中... (試行: {attempt + 1}回目)")
                            
                            # =========================================================
                            # ★最強プロンプト（ここを変えるだけで占いの質が変わります）
                            # =========================================================
                            prompt = f"""
                            あなたは厳しくも愛のある古典占星術師です。専門用語も交えて「生まれ持った資質・才能・運命」について深く鑑定してください。
                            以下の計算データを元に、マークダウン形式で見やすく出力してください。

                            【鑑定のポイント】
                            1. **惑星の強弱（ディグニティ）**:
                               - スコアが高い(+3点以上)惑星を特定し、それが示す「最強の武器・才能」を具体的に解説してください。
                               - スコアが低い(マイナス点)惑星について、それをどう乗り越えるかのアドバイスを提示してください。
                               - チャートの王様（アルムテン）となる惑星があれば、その意味を伝えてください。

                            2. **性格と行動**:
                               - アセンダントや月星座と、上記の強い惑星を組み合わせて、本質的な性格を読み解いてください。

                            3. **適職・キャリア**:
                               - 才能のある惑星やハウス配置から、向いている仕事や働き方を提案してください。

                            4. **ハウスの強弱・アスペクト**:
                               - データにある「アスペクト」や「ハウス配置」に基づいた根拠のあるアドバイスをしてください。
                               - 特に「吉角（トライン・セクスタイル・合）」と「凶角（スクエア・オポジション）」のバランスを見て、注意点とチャンスの両方を伝えてください。

                            5. **まとめ**:
                               - 最後に「全体的なアドバイス」と「今すぐできるラッキーアクション」をまとめてください。

                            【計算データ】
                            {st.session_state['result_txt']}
                            """
                            # =========================================================

                            # AIを呼び出す
                            model = genai.GenerativeModel(target_model)
                            response = model.generate_content(prompt)
                            
                            if response.text:
                                result_text = response.text
                                # 成功したらステータスを完了にしてループを抜ける
                                status.update(label="✅ 鑑定完了！ 星からの手紙が届きました", state="complete", expanded=False)
                                success = True
                                break 

                        except Exception as e:
                            error_msg = str(e)
                            # 429エラー（混雑）なら再挑戦、それ以外はエラー終了
                            if "429" in error_msg or "Resource" in error_msg:
                                continue 
                            else:
                                status.update(label="❌ 予期せぬエラー", state="error")
                                st.error(f"詳細エラー: {error_msg}")
                                break
                    
                    # 3回やってもダメだった場合のメッセージ
                    if not success and not result_text:
                        status.update(label="❌ 混雑のため中断", state="error")
                        st.error("星々の回線が混み合っています。少し時間を置いて再挑戦してください。")

                # 結果表示
                if result_text:
                    st.markdown("### 🔮 鑑定結果")
                    st.markdown(result_text)













