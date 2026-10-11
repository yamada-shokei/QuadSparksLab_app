-- ============================================================
-- 品質管理データベース（Quality Case DB）
-- 添付の20項目仕様に完全準拠
-- CSV（quality_data_261006.csv）をそのまま取り込める構造
-- ============================================================

-- 1. 品質事例テーブル（cases）
CREATE TABLE IF NOT EXISTS cases (
    case_id INTEGER PRIMARY KEY AUTOINCREMENT,   -- 1: 事例ID（自動採番）
    part_no               TEXT,                    -- 2: 品番
    product_name          TEXT,                    -- 3: 製品名
    mount_area            TEXT,                    -- 4: 実装面
    item_group            TEXT,                    -- 5: 品目分類
    product_structure     TEXT,                    -- 6: 製品構成
    material              TEXT,                    -- 7: 材料グレード
    customer              TEXT,                    -- 8: 顧客名
    lot_no                TEXT,                    -- 9: ロット番号
    manufactured_at       DATETIME,                -- 10: 製造日時
    plant                 TEXT,                    -- 11: 製造工場
    mold_no               TEXT,                    -- 12: 金型番号
    cavity_no             TEXT,                    -- 13: キャビティ番号
    found_on              DATE,                    -- 14: 発見日
    occurred_on           DATE,                    -- 15: 発生日
    found_at              TEXT,                    -- 16: 発見場所
    occurred_process      TEXT,                    -- 17: 発生工程
    occurrence_unit       TEXT,                    -- 18: 発生ユニット
    defect_class          TEXT,                     -- 19: 不具合分類
    defect_type           TEXT,                    -- 20: 不具合現象
    defect_type_note      TEXT,                    -- 21: 不具合現象補足
    defect_detail         TEXT,                    -- 22: 現象の詳細
    defect_qty            INTEGER,                 -- 23: 不具合数量
    cause_category        TEXT,                    -- 24: 原因分類
    cause_origin          TEXT,                    -- 25: 原因起点
    cause                 TEXT,                    -- 26: 原因
    outflow_cause         TEXT,                    -- 27: 流出原因
    temp_action           TEXT,                    -- 28: 暫定対策
    containment_scope     TEXT,                    -- 29: 封じ込め範囲
    perm_action           TEXT,                    -- 30: 恒久対策
    effect_check          TEXT,                    -- 31: 効果確認
    horizontal_deploy     TEXT,                    -- 32: 横断展開
    standardization       TEXT,                    -- 33: 標準化
    customer_response     TEXT,                    -- 34: 顧客対応
    lesson                TEXT,                    -- 35: 教訓
    outcome               TEXT,                    -- 36: 結果
    outcome_status        TEXT,                    -- 37: 結果ステータス
    recurrence_of         TEXT,                    -- 38: 再発の有無
    status_id             TEXT,                    -- 39: ステータス
    report_file           TEXT,                    -- 40: 報告書ファイル
    registered_by         TEXT,                    -- 41: 登録者
    registered_on         DATE,                    -- 42: 登録日
    updated_by            TEXT,                    -- 43: 更新者    
    updated_at            DATE,                    -- 44: 更新日
    search_text           TEXT,                    -- 45: 検索用文章（自動生成）
    symptom_text          TEXT,                     -- 46: 現象文章（自動生成）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. TF-IDF 用キーワードテーブル
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    tf_score REAL DEFAULT 0.0,
    tfidf_score REAL DEFAULT 0.0,
    FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
);

-- 3. 検索ログ
CREATE TABLE IF NOT EXISTS search_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    result_count INTEGER,
    user_id TEXT,
    searched_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. インデックス（検索高速化）
CREATE INDEX IF NOT EXISTS idx_defect_type ON cases(defect_type);
CREATE INDEX IF NOT EXISTS idx_defect_detail ON cases(defect_detail);
CREATE INDEX IF NOT EXISTS idx_cause_category ON cases(cause_category);
CREATE INDEX IF NOT EXISTS idx_search_text ON cases(search_text);
CREATE INDEX IF NOT EXISTS idx_keyword ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_case_id ON keywords(case_id);
