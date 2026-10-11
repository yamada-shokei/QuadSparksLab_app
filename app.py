# =============================================================
# app.py — フロント（画面）：検索／一覧／取り込み
# 役割：入力を受け取り、絞り込み、検索（ranking.py）を呼び、結果を見せる。DBと検索の中身は持たない
# 検索は対応の段階で深くなる：①初動（品番か現象）→ ②調査（ロット・工場など）→ ③恒久対策（原因分類・起因）
# 登録フォームはない。事例を足す入口は、承認済みの報告書（様式 v0.1）を crawler.py で取り込む経路だけ
#
# 同じフォルダに database.py・ranking.py・schema.sql・CSV が必要。ライブラリは requirements.txt を参照
# ほかのファイルとの接点（app.py がどう呼ぶか）：
#   database.py：init_db()、get_all_pages() -> list[dict]、migrate_from_csv() を呼ぶ（項目表 v0.2 の列名で読む）
#                get_all_parts() -> list[dict]（品番マスタ）はあれば使う。なければ製品の情報は事例の行から拾う
#   ranking.py ：rebuild_index(事例リスト) と get_engine().search(現象) を呼ぶ。事例の symptom_text・search_text を読む
#   crawler.py ：「取り込み」ボタンで、同じフォルダの crawler.py を `python crawler.py` として実行する
#                （関数は呼ばない・引数も渡さない）。実行前後の件数と、print された出力を画面に出す
# =============================================================
import os
import subprocess
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)  # どこから起動しても、app.py のある場所を基準に DB・schema.sql・CSV を探す

import pandas as pd
import streamlit as st

import database as _db
from database import get_all_pages, init_db, migrate_from_csv

# 品番マスタは、database.py になくても動くようにする
get_all_parts = getattr(_db, "get_all_parts", None)
PART_COLUMNS = ["part_no", "product_name", "mount_area", "item_group", "product_structure", "material", "customer"]

# ---- 選択肢と表示名（項目表 v0.2 の「選択肢」シートと同じ値。変えない） ----
CHOICES = {
    "mount_area": ["内装", "シート", "外装", "ボディ・ドア機構", "シャシー・足回り", "エンジン", "トランスミッション",
                   "吸排気", "冷却", "燃料", "電装", "空調（HVAC）", "灯火・視界", "安全・ADAS", "e-Axle",
                   "バッテリー（充電口を含む）", "その他"],
    "item_group": ["クリップ・ファスナー", "クランプ（ホース・ハーネス）", "グロメット・プラグ", "リテーナー・スペーサー",
                   "ヒンジ・ラッチ", "配管（パイプ・チューブ）", "クイックコネクタ・ジョイント", "ダクト・ホース",
                   "タンク・リザーバー", "ブラケット・ホルダー", "カバー・キャップ", "ハウジング・ケース",
                   "プロテクター・ガイド", "シール・ダンパー（樹脂）", "トリム・パネル・ガーニッシュ", "ベゼル・レンズ・グリル",
                   "ノブ・レバー・ハンドル", "収納（カップホルダー・ポケット）", "エアベント・ルーバー", "バルブ", "フィルター",
                   "ギア・カム", "ファン・インペラ", "コネクタ（電気）", "その他"],
    "product_structure": ["単品", "複合品"],
    "material": ["PC", "PC 難燃", "ABS", "PC/ABS", "PP", "PP TD20", "PA6", "PA66", "PA66 GF30", "POM", "PBT GF15", "PPS GF40"],
    "customer": ["朝霧自動車", "翠峰自動車", "碧浜自動車", "蒼嶺工業", "白樺電装工業"],  # 架空の社名
    "plant": ["第1工場", "第2工場", "第3工場"],
    "found_at": ["工程内", "出荷検査", "顧客受入"],
    "occurred_process": ["受入（材料・購入部品）", "成形", "二次加工・組立", "検査", "梱包", "保管・輸送", "顧客（開封後）", "不明"],
    "occurrence_unit": ["部品単体", "組立後"],
    "defect_class": ["外観", "寸法", "機能", "強度"],
    "defect_type": ["ショート", "ボイド（気泡）", "真空ボイド", "ウェルド", "フローマーク", "バリ", "Eピンバリ", "ヒゲバリ",
                    "反り", "ヒケ", "寸法不良", "グイチ", "嵌合不良・干渉", "ガタ・異音", "白化", "変色", "ガス焼け",
                    "シルバーストリーク", "黒点", "キズ", "クラック", "異物混入", "漏れ・シール不良", "欠品・誤組付け", "その他"],
    "cause_category": ["製品設計", "金型", "成形機・設備", "成形条件", "材料", "作業", "購入部品", "不明"],
    "cause_origin": ["設計起因", "変化点起因", "劣化・摩耗", "不明"],
    "outcome_status": ["再発なし", "再発あり", "経過観察中", "未評価"],
    "status_id": ["受付", "調査中", "完了"],
}

# 画面の表示名（カラム名 → 日本語名）
LABELS = {
    "score": "類似度", "part_no": "品番", "product_name": "製品名", "mount_area": "搭載領域", "item_group": "アイテム群",
    "product_structure": "製品構成", "material": "材料グレード", "lot_no": "ロット", "manufactured_at": "製造日時（ロット代表）",
    "plant": "製造工場", "mold_no": "金型番号", "occurred_on": "発生日", "found_at": "発見場所",
    "customer": "顧客", "cavity_no": "キャビティ番号", "found_on": "発見日", "defect_type_note": "その他の内容",
    "outcome_status": "予後区分", "recurrence_of": "再発元の事例ID", "status_id": "対応状況", "updated_by": "更新者",
    "updated_at": "更新日時", "case_id": "事例ID",
    "occurred_process": "発生工程", "occurrence_unit": "発生単位", "defect_class": "不具合区分",
    "defect_type": "不具合現象", "defect_detail": "現象の詳細", "cause_category": "原因分類", "cause_origin": "起因",
    "cause": "原因", "temp_action": "暫定対策", "perm_action": "恒久対策", "customer_response": "顧客への回答",
    "lesson": "教訓", "outcome": "予後", "report_file": "報告書ファイル", "registered_by": "登録者",
    "registered_on": "登録日",
    "defect_qty": "不良数量", "outflow_cause": "流出原因", "containment_scope": "暫定処置の対象範囲・解除",
    "effect_check": "効果確認の方法", "horizontal_deploy": "水平展開", "standardization": "標準化",
    "search_text": "検索用文章", "symptom_text": "初動用の検索文章",
}

# ---- 検索：ranking.py（W4 の SearchEngine）を呼ぶ ------------------
from ranking import get_engine, rebuild_index

def rank_cases(symptom: str, rows: list[dict]) -> list[dict]:
    """絞り込み済みの rows を並べる。現象があれば似ている順（score は 0〜1）、なければ発見日の新しい順"""
    if not symptom.strip():
        return sorted(rows, key=lambda c: c.get("found_on") or "", reverse=True)
    ids = {c["case_id"] for c in rows}
    out = []
    for h in get_engine().search(symptom, top_n=100000):  # ranking.py が全事例を似ている順に返す
        if h["case_id"] in ids:  # そのうち、絞り込みに残った事例だけ
            h["score"] = h["base_score"] / 100  # ranking.py は 0〜100 で返すので 0〜1 にする
            out.append(h)
    return out

# 検索結果の表：初動で使う列（回答・教訓・予後）を原因・対策より前に出す
RESULT_COLUMNS = ["score", "case_id", "status_id", "defect_type", "defect_detail", "defect_qty", "customer_response",
                  "lesson", "outcome_status", "outcome", "recurrence_of", "cause_category", "cause_origin", "cause",
                  "outflow_cause", "temp_action", "containment_scope", "perm_action", "effect_check",
                  "horizontal_deploy", "standardization", "occurred_process", "found_at", "found_on", "lot_no",
                  "plant", "mold_no", "cavity_no", "customer", "part_no", "product_name", "mount_area", "item_group",
                  "report_file"]
# 詳細条件（空欄は絞り込まない）。不具合現象・搭載領域・アイテム群は①に置く
STAGE2_FILTERS = ["plant", "found_at", "occurred_process", "occurrence_unit", "defect_class", "customer", "status_id"]
STAGE3_FILTERS = ["cause_category", "cause_origin", "outcome_status"]

st.set_page_config(page_title="Q-Cevo", page_icon="🔍", layout="wide")

# ---- DB 準備：空なら CSV から作る（Cloud は再起動で DB が消えるため） ----
init_db()
db_note = ""
if not get_all_pages():
    try:
        migrate_from_csv()
    except Exception as e:  # CSV がない・読めないときも画面は開く（事例0件）
        db_note = f"CSV から事例を入れられませんでした（{e}）。事例0件のまま開きます。"

st.title("🔍 Q-Cevo")
st.caption("品質トラブルの一報を受けたとき、品番と現象から、過去の類似事例と当時の対応を引く")
if db_note:
    st.warning(db_note)

cases = get_all_pages()
# ranking.py は title / description / full_text を読む作りなので、事例の列を当てはめて渡す
# symptom_text が空（取り込んだ事例）は、CSV と同じ「不具合現象＋現象の詳細」で補う
rebuild_index([dict(c, title="", description=c.get("symptom_text") or f"{c.get('defect_type') or ''} {c.get('defect_detail') or ''}".strip(), full_text=c.get("search_text") or "") for c in cases])
if get_all_parts:
    parts = {p["part_no"]: p for p in get_all_parts()}  # 品番 → 製品情報（品番マスタが正）
else:  # 品番マスタがない database.py のときは、事例の行から製品の情報を拾う
    parts = {}
    for c in cases:
        if c.get("part_no"):
            p = parts.setdefault(c["part_no"], {k: None for k in PART_COLUMNS})
            for k in PART_COLUMNS:
                if not p[k] and c.get(k):
                    p[k] = c[k]


def filter_cases(rows: list[dict], conds: dict) -> list[dict]:
    """選ばれた条件で絞り込む（空の条件は絞り込まない）"""
    out = rows
    for col, val in conds.items():
        if not val:
            continue
        if isinstance(val, list):
            out = [r for r in out if r.get(col) in val]
        else:
            out = [r for r in out if (r.get(col) or "") == val]
    return out


def blank_nulls(df: pd.DataFrame) -> pd.DataFrame:
    """文字の列の空欄（NULL）を、None ではなく空で見せる（数の列はそのまま）"""
    for c in df.columns:
        if df[c].dtype == object or pd.api.types.is_string_dtype(df[c]):
            df[c] = df[c].map(lambda v: "" if v is None or v != v else str(v)).astype(object)
    return df


def to_table(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if "score" not in df:
        df["score"] = None
    return blank_nulls(df[[c for c in RESULT_COLUMNS if c in df.columns]].rename(columns=LABELS))

def show_results(results: list[dict], symptom: str, widened: bool) -> None:
    st.markdown(f"**検索結果：{len(results)}件**" + ("（似た製品の事例を含む）" if widened else ""))
    if not results:
        st.warning("該当する事例がありません。条件を減らしてください。")
        return
    lessons = []
    for r in results:
        if r.get("lesson") and r["lesson"] not in lessons:
            lessons.append(r["lesson"])
        if len(lessons) == 3:
            break
    if lessons:
        st.markdown("**まず確認すること（上位の事例の教訓）**")
        for l in lessons:
            st.markdown(f"- {l}")
    top = results[0]
    if top.get("customer_response"):
        st.markdown(f"**当時の顧客への回答（最上位の事例）**：{top['customer_response']}")
    st.dataframe(to_table(results), width="stretch", hide_index=True,
                 column_config={"類似度": st.column_config.ProgressColumn(
                     "類似度", min_value=0.0, max_value=1.0, format="%.2f")} if symptom else None)


tabs = st.tabs(["検索", "一覧", "取り込み"])
tab_search, tab_list = tabs[0], tabs[1]

# ---- 検索タブ ------------------------------------------------
with tab_search:
    st.subheader("① 初動：品番か現象を入れる")
    st.caption("品番・現象・不具合現象のどれか1つで検索できる。ほかの条件は、入れるほど絞れる")
    r1, r2, r3 = st.columns(3)
    part_no = r1.text_input("品番（分かれば）", placeholder="例：QS-1067").strip().upper()
    area = r2.multiselect(LABELS["mount_area"], CHOICES["mount_area"], placeholder="品番が分からなければ")
    group = r3.multiselect(LABELS["item_group"], CHOICES["item_group"], placeholder="品番が分からなければ")
    s1, s2 = st.columns([2, 1])
    symptom = s1.text_input("現象（見つけた人の言葉のままでOK）", placeholder="例：先端まで樹脂が回っていない")
    dtypes = s2.multiselect(LABELS["defect_type"], CHOICES["defect_type"], placeholder="選択（複数可）")

    p = parts.get(part_no) if part_no else None
    if part_no and not p:
        st.warning(f"品番「{part_no}」は品番マスタにありません。品番を確かめてください（この品番の事例があれば表示します）。")
    elif p:
        info = [f"{part_no}　{p.get('product_name') or ''}".strip()]
        for col, name in [("customer", "顧客"), ("mount_area", "搭載領域"), ("item_group", "アイテム群"),
                          ("product_structure", "製品構成"), ("material", "材料グレード"), ("bought_parts", "主な購入部品")]:
            if p.get(col):  # 空（None・空文字）の欄は出さない
                info.append(f"{name}：{p[col]}")
        if p.get("note"):
            info.append(p["note"])
        st.caption("　／　".join(info))

    with st.expander("② 調査が進んだら：ロット・工場・発生工程などで絞る"):
        lot = st.text_input("ロット")
        cols = st.columns(3)
        stage2 = {col: cols[i % 3].multiselect(LABELS[col], CHOICES[col], placeholder="選択（複数可）") for i, col in enumerate(STAGE2_FILTERS)}
    with st.expander("③ 原因が見えてきたら：原因分類・起因で絞る"):
        cols = st.columns(3)
        stage3 = {col: cols[i].multiselect(LABELS[col], CHOICES[col], placeholder="選択（複数可）") for i, col in enumerate(STAGE3_FILTERS)}
    widen = st.checkbox("同じ搭載領域×アイテム群の、他の品番の事例も含める（似た製品で引く）",
                        disabled=not part_no, help="品番を入れたときに使える。品番なしの検索は、もともと全品番が対象")

    conds = {"lot_no": lot.strip(), "mount_area": area, "item_group": group, "defect_type": dtypes, **stage2, **stage3}

    if not (part_no or symptom.strip() or dtypes):
        st.info("品番・現象・不具合現象のどれか1つを入れると検索します。")
    else:
        hits = filter_cases(cases, conds)  # ① 条件で絞る
        widened = False
        if part_no:
            results = rank_cases(symptom, [c for c in hits if c.get("part_no") == part_no])  # ② 似ている順に並べる
            if p and p.get("mount_area") and p.get("item_group") and (widen or not results):
                # 似た製品（同じ搭載領域×アイテム群の他の品番）の事例を足す。品番マスタにある品番のときだけ
                similar = [q for q, v in parts.items() if q != part_no and v.get("mount_area") == p.get("mount_area")
                           and v.get("item_group") == p.get("item_group")]
                others = rank_cases(symptom, [c for c in hits if c.get("part_no") in similar])
                widened = bool(others)
                if not results and others:
                    if any(c.get("part_no") == part_no for c in cases):
                        st.warning("この品番の事例はありますが、条件に合う事例はありませんでした。"
                                   f"似た製品（{p.get('mount_area')}×{p.get('item_group')}）の事例を表示します。")
                    else:
                        st.warning(f"この品番の事例はまだありません。似た製品（{p.get('mount_area')}×{p.get('item_group')}）の事例を表示します。")
                results = results + others
        else:
            results = rank_cases(symptom, hits)  # 品番なし：全品番が対象
        show_results(results, symptom, widened)

# ---- 一覧タブ ------------------------------------------------
with tab_list:
    st.subheader(f"登録済み事例（{len(cases)}件）")
    df_all = pd.DataFrame(cases).drop(columns=["search_text", "symptom_text", "created_at", "keywords"], errors="ignore")
    st.dataframe(blank_nulls(df_all.rename(columns=LABELS)), width="stretch", hide_index=True)

# ---- 取り込みタブ-------------------------------
with tabs[2]:
    st.subheader("承認済みの報告書を取り込む")
    st.caption("承認済みフォルダの報告書を crawler.py が読み、事例として登録する")
    st.write(f"いま登録されている事例：**{len(cases)}件**")
    if st.button("承認済みの報告書を取り込む", type="primary"):
        script = Path(__file__).resolve().parent / "crawler.py"
        before = len(cases)
        if not script.exists():
            st.session_state["crawl_result"] = {"error": "crawler.py が見つかりません（app.py と同じ場所に置いてください）"}
        else:
            try:
                with st.spinner("取り込み中…"):
                    proc = subprocess.run(
                        [sys.executable, str(script)], cwd=str(script.parent), capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=300,
                        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
                st.session_state["crawl_result"] = {
                    "code": proc.returncode, "out": proc.stdout, "err": proc.stderr,
                    "before": before, "after": len(get_all_pages())}
            except subprocess.TimeoutExpired:
                st.session_state["crawl_result"] = {"error": "5分たっても終わらなかったので止めました。"}
        st.rerun()  # 一覧の件数も新しくする
    res = st.session_state.get("crawl_result")
    if res:
        if res.get("error"):
            st.error(res["error"])
        else:
            added = res["after"] - res["before"]
            if res["code"] == 0 and added > 0:
                st.success(f"{added}件を登録しました（{res['before']}件 → {res['after']}件）")
            elif res["code"] == 0:
                st.info(f"新しく登録された事例はありません（{res['after']}件のまま）。"
                        "対象の報告書がないか、すべて登録済みです。詳しくは下の出力を見てください。")
            else:
                st.error(f"取り込みでエラーがありました（{res['before']}件 → {res['after']}件）。下の出力を見てください。")
            if res["out"].strip():
                st.text_area("crawler.py の出力", res["out"], height=200)
            if res["err"].strip():
                st.text_area("エラー出力", res["err"], height=160)
