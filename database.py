# =============================================================
# Quad_Sparks_Lab/database.py — DB操作の一元管理
# =============================================================
import sqlite3
import csv
from pathlib import Path
from datetime import datetime

# DB ファイルのパス（data/ サブフォルダに保存する）
DB_PATH = Path("data/Quad_search.db")

def get_connection():
    """DB への接続を取得する（data/ フォルダが無ければ自動作成）"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row        # 行データを辞書のように扱う
    return conn

def init_db():
    """schema.sql を読み込んで DB を初期化する"""
    conn = get_connection()
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def _keywords_to_text(keywords) -> str:
    """keywords（リスト or 文字列）を DB 保存用のカンマ区切り文字列にする"""
    if not keywords:
        return ""
    if isinstance(keywords, str):
        return keywords
    return ",".join(keywords)

def insert_case(cases: dict) -> int:
    """品質情報を DB に登録する"""

#　👇追加した部分（始まり）
# search_text（検索用文章）を自動生成
    search_text = " ".join([
        cases.get("defect_detail", ""),
        cases.get("cause", ""),
        cases.get("temp_action", ""),
        cases.get("perm_action", "")
    ]).strip()
#　👆追加した部分（終わり）

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO cases
            (part_no, product_name, mount_area, item_group, product_structure, material, customer, lot_no, manufactured_at, plant, mold_no, cavity_no, found_on, occurred_on, found_at, occurred_process, occurrence_unit, defect_class, defect_type, defect_type_note, defect_detail, defect_qty, cause_category, cause_origin, cause, outflow_cause, temp_action, containment_scope, perm_action, effect_check, horizontal_deploy, standardization, customer_response, lesson, outcome, outcome_status, recurrence_of, status_id, report_file, registered_by, registered_on, updated_by, updated_at, search_text, symptom_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cases["part_no"],
        cases["product_name"],
        cases.get("mount_area", ""),
        cases.get("item_group", ""),
        cases.get("product_structure", ""),
        cases.get("material", ""),
        cases.get("customer", ""),
        cases.get("lot_no", ""),
        cases.get("manufactured_at", ""),
        cases.get("plant", ""),
        cases.get("mold_no", ""),
        cases.get("cavity_no", ""),
        cases.get("found_on", ""),
        cases.get("occurred_on", ""),
        cases.get("found_at", ""),
        cases.get("occurred_process", ""),
        cases.get("occurrence_unit", ""),
        cases.get("defect_class", ""),
        cases.get("defect_type", ""),
        cases.get("defect_type_note", ""),
        cases.get("defect_detail", ""),
        cases.get("defect_qty", 0),
        cases.get("cause_category", ""),
        cases.get("cause_origin", ""),
        cases.get("cause", ""),
        cases.get("outflow_cause", ""),
        cases.get("temp_action", ""),
        cases.get("containment_scope", ""),
        cases.get("perm_action", ""),
        cases.get("effect_check", ""),
        cases.get("horizontal_deploy", ""),
        cases.get("standardization", ""),
        cases.get("customer_response", ""),
        cases.get("lesson", ""),
        cases.get("outcome", ""),
        cases.get("outcome_status", ""),
        cases.get("recurrence_of", ""),
        cases.get("status_id", ""),
        cases.get("report_file", ""),
        cases.get("registered_by", ""),
        cases.get("registered_on", ""),
        cases.get("updated_by", ""),
        cases.get("updated_at", ""),
        search_text,
        cases.get("symptom_text", "")
    ))
    cases_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return cases_id


def get_all_pages() -> list:
    """全ページを登録日時の新しい順で取得する"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    cases = []
    for row in rows:
        c = dict(row)
        # 保存時にカンマ区切りにした keywords をリストに戻す
        c["keywords"] = [k.strip() for k in (c.get("keywords") or "").split(",") if k.strip()]
        cases.append(c)
    return cases

# 👇追加した部分（始まり）
# CSV → DB 移行
def migrate_from_csv(csv_path: str = "QSL_事例テーブル_ダミーデータ150件.csv") -> int:
    """CSV（45項目）を page テーブルへ移行する"""

    conn = get_connection()
    cursor = conn.cursor()

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        insert_case(row)

    return len(rows)

# 👆追加した部分（終わり）

def log_search(query: str, results_count: int, user_id: str = None) -> int:
    """検索ログを記録する（W6 の発展課題で実装予定のスタブ）"""
    pass  # W6 の発展課題で実装します

if __name__ == "__main__":
    init_db()
    count = migrate_from_csv()
    print(f"{count} rows inserted.")
