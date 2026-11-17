"""Local dense embeddings for slide chunks — no downloads, no API, no pickles.

Default backend: LSA (TF-IDF over the course tokenizer -> truncated SVD -> L2-normalised
vectors). It is small (137 chunks), deterministic (fixed random_state), and built in well
under a second at startup, so nothing is persisted that could break across scikit-learn
versions (the v0.6 joblib problem).

Optional backend: sentence-transformers MiniLM, enabled with TROJANTUTOR_ENABLE_DENSE=1 and
`pip install sentence-transformers` (downloads a model on first use).

Both expose the same interface:  index.search(text, eligible_ids) -> ids ranked by cosine.
"""
from functools import lru_cache
import os

from .retrieval import CHUNKS, tokenize

LSA_DIM = 96


class _LSA:
    name = 'lsa'

    def __init__(self, chunks):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        import numpy as np
        self.np = np
        docs = [f"{c['title']} {c['title']} {c['text']}" for c in chunks]
        self.vec = TfidfVectorizer(analyzer=tokenize, sublinear_tf=True, min_df=1)
        X = self.vec.fit_transform(docs)
        k = max(2, min(LSA_DIM, X.shape[0] - 1, X.shape[1] - 1))
        self.svd = TruncatedSVD(n_components=k, random_state=425)
        M = self.svd.fit_transform(X)
        self.M = M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-12)

    def encode(self, text):
        v = self.svd.transform(self.vec.transform([text]))[0]
        n = self.np.linalg.norm(v)
        return v / n if n > 0 else v

    def scores(self, text):
        return self.M @ self.encode(text)


class _MiniLM:
    name = 'minilm'

    def __init__(self, chunks):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.M = self.model.encode([f"{c['title']}\n{c['text']}" for c in chunks],
                                   normalize_embeddings=True, show_progress_bar=False)

    def scores(self, text):
        return self.M @ self.model.encode([text], normalize_embeddings=True)[0]


@lru_cache(maxsize=1)
def get_index():
    """Return the best available dense index, or None if none can be built."""
    if os.getenv('TROJANTUTOR_ENABLE_DENSE', '0') == '1':
        try:
            return _MiniLM(CHUNKS)
        except (ImportError, OSError, RuntimeError, ValueError):
            pass
    if os.getenv('TROJANTUTOR_DISABLE_LSA', '0') == '1':
        return None
    try:
        return _LSA(CHUNKS)
    except (ImportError, ValueError):
        return None


def dense_rank(text, eligible, min_score=0.05):
    """Rank eligible chunk ids by cosine similarity; drop near-zero matches."""
    idx = get_index()
    if idx is None or not eligible:
        return None, []
    s = idx.scores(text)
    ranked = sorted(eligible, key=lambda i: (-float(s[i]), i))
    return idx.name, [i for i in ranked if float(s[i]) >= min_score]
