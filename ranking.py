# =============================================================
# answers/w4/ranking.py — TF-IDF 検索エンジン（W4 完成版）
# ノートブック W4 Step 4 で作った SearchEngine クラス＋シングルトン
# =============================================================
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
from typing import List


class SearchEngine:
    """TF-IDFベースの検索エンジン（ranking.py の本体）"""

    def __init__(self):
        # 日本語は単語の間にスペースが無いため、既定の「単語区切り」では
        # 「営業店DX推進レポート」が丸ごと1語になり、「DX」で検索しても一致しない。
        # そこで analyzer="char_wb"（文字N-gram）を使い、2〜3文字のまとまりを特徴量にする。
        # ※ 本文 Step 1〜3 の手計算デモは、仕組みを追いやすいようスペース区切りで説明している。
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",  # 文字N-gram（日本語のまま扱えるようにする）
            ngram_range=(2, 3),  # 2〜3文字のまとまり
            max_features=5000,
            min_df=1,
            max_df=0.95,
            sublinear_tf=True    # TF の対数スケーリング
        )
        self.tfidf_matrix = None
        self.pages = []
        self.is_fitted = False

#   ranking.py ：search_cases(品番, 現象, 事例リスト) を呼ぶ（形は下の import の所に書いてある）。なければ新しい順に並べる

    def build_index(self, pages: list):
        """全ページの TF-IDF インデックスを構築する"""
        if not pages:
            return

        self.pages = pages
        corpus = []
        for p in pages:
            kw = p.get("keywords", "") or ""
            if isinstance(kw, str):
                kw_list = [k.strip() for k in kw.split(",") if k.strip()]
            else:
                kw_list = kw

            # タイトルは3倍、説明は2倍、キーワードは2倍の重みを付ける
            text = " ".join([
                (p.get("title", "") + " ") * 3,
                ((p.get("description", "") or "") + " ") * 2,
                ((p.get("full_text", "") or "") + " "),
                (" ".join(kw_list) + " ") * 2,
            ])
            corpus.append(text)

        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        self.is_fitted = True

    def search(self, query: str, top_n: int = 20) -> list:
        """TF-IDF ベースの検索を実行する"""
        if not self.is_fitted or not query.strip():
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        results = []
        for idx, base_score in enumerate(similarities):
            if base_score > 0.01:
                page = self.pages[idx].copy()
                final_score = self._calculate_final_score(page, base_score, query)
                page["relevance_score"] = round(float(final_score) * 100, 1)
                page["base_score"] = round(float(base_score) * 100, 1)
                results.append(page)

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_n]

    def _calculate_final_score(self, page: dict, base_score: float, query: str) -> float:
        """タイトルマッチ・新鮮度・文字数を加味した最終スコア"""
        score = base_score
        query_lower = query.lower()

        # 1. タイトルマッチボーナス
        title = (page.get("title", "") or "").lower()
        if query_lower == title:
            score *= 1.8
        elif query_lower in title:
            score *= 1.4

        # 2. キーワードマッチボーナス
        keywords = page.get("keywords", []) or []
        if isinstance(keywords, str):
            keywords = keywords.split(",")
        if query_lower in [k.strip().lower() for k in keywords]:
            score *= 1.3

        # 3. 新鮮度ボーナス（90日以内は最大 +20%）
        crawled_at = page.get("crawled_at", "") or ""
        if crawled_at:
            try:
                crawled = datetime.fromisoformat(crawled_at.replace("Z", "+00:00"))
                days_old = (datetime.now() - crawled.replace(tzinfo=None)).days
                if days_old <= 90:
                    score *= 1 + (0.2 * (90 - days_old) / 90)
            except Exception:
                pass

        # 4. 文字数による調整
        word_count = page.get("word_count", 0) or 0
        if word_count < 50:
            score *= 0.7
        elif word_count > 10000:
            score *= 0.85

        return score


# ── シングルトン（アプリ全体で1つのエンジンを使いまわす） ──
_engine = None


def get_engine() -> SearchEngine:
    """検索エンジンのシングルトンを取得する"""
    global _engine
    if _engine is None:
        _engine = SearchEngine()
    return _engine


def rebuild_index(pages: List[dict]):
    """インデックスを再構築する（ページ追加時に呼び出す）"""
    get_engine().build_index(pages)
