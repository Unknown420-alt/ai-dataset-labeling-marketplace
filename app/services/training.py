"""Text classification without heavy dependencies.

TF-IDF + Multinomial Naive Bayes implemented on the standard library so
the serverless bundle stays small (no numpy/scipy/scikit-learn).
Single-label and multi-label (one binary NB per label) are supported.

Models persist to disk (data/models/) so they survive restarts — the
in-memory cache is just a fast path. No TTL expiry: a model stays valid
until retrained.
"""

import math
import os
import re
import tempfile
import time
from collections import Counter
from typing import Any

import joblib

MODEL_DIR = (
    os.path.join(tempfile.gettempdir(), "labeling_models")
    if os.environ.get("VERCEL") == "1"
    else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "models")
)

_memory_cache: dict[int, tuple[dict, float]] = {}

MIN_LABELED_ROWS = 10
MAX_TRAINING_ROWS = 20000
MAX_FEATURES = 5000

_TOKEN_RE = re.compile(r"[a-z0-9']+")


def _tokens(text: str) -> list[str]:
    words = _TOKEN_RE.findall(text.lower())
    grams = list(words)
    grams.extend(f"{a} {b}" for a, b in zip(words, words[1:]))
    return grams


class Tfidf:
    """Fitted vocabulary + idf weights. Must stay module-level for pickling."""

    def __init__(self) -> None:
        self.vocab: dict[str, int] = {}
        self.idf: list[float] = []

    def fit(self, docs: list[list[str]]) -> "Tfidf":
        df: Counter = Counter()
        for tokens in docs:
            for term in set(tokens):
                df[term] += 1
        ranked = sorted(df.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_FEATURES]
        self.vocab = {term: i for i, (term, _) in enumerate(ranked)}
        n = max(len(docs), 1)
        self.idf = [math.log((n + 1) / (freq + 1)) + 1.0 for _, freq in ranked]
        return self

    def vector(self, tokens: list[str]) -> dict[int, float]:
        counts: Counter = Counter(t for t in tokens if t in self.vocab)
        total = sum(counts.values()) or 1
        return {
            self.vocab[t]: (c / total) * self.idf[self.vocab[t]]
            for t, c in counts.items()
        }


class NaiveBayes:
    """Multinomial NB over TF-IDF vectors. Module-level for pickling."""

    def __init__(self) -> None:
        self.classes: list[str] = []
        self.log_prior: dict[str, float] = {}
        self.log_prob: dict[str, dict[int, float]] = {}
        self.default_log_prob: dict[str, float] = {}

    def fit(self, vectors: list[dict[int, float]], labels: list[str]) -> "NaiveBayes":
        self.classes = sorted(set(labels))
        totals: Counter = Counter()
        feat: dict[str, Counter] = {c: Counter() for c in self.classes}
        for vec, label in zip(vectors, labels):
            totals[label] += 1
            feat[label].update(vec)
        n = len(labels)
        vocab_size = max((max(v.keys()) + 1 for v in vectors if v), default=0)
        for cls in self.classes:
            self.log_prior[cls] = math.log(totals[cls] / n)
            denom = sum(feat[cls].values()) + vocab_size
            self.log_prob[cls] = {
                f: math.log((feat[cls][f] + 1.0) / denom) for f in range(vocab_size)
            }
            self.default_log_prob[cls] = math.log(1.0 / denom)
        return self

    def scores(self, vec: dict[int, float]) -> dict[str, float]:
        out: dict[str, float] = {}
        for cls in self.classes:
            lp = self.log_prob[cls]
            default = self.default_log_prob[cls]
            out[cls] = self.log_prior[cls] + sum(
                w * lp.get(f, default) for f, w in vec.items()
            )
        return out

    def predict_proba(self, vec: dict[int, float]) -> dict[str, float]:
        scores = self.scores(vec)
        if not scores:
            return {}
        best = max(scores.values())
        exps = {c: math.exp(s - best) for c, s in scores.items()}
        total = sum(exps.values()) or 1.0
        return {c: v / total for c, v in exps.items()}


def _model_path(dataset_id: int) -> str:
    os.makedirs(MODEL_DIR, exist_ok=True)
    return os.path.join(MODEL_DIR, f"dataset_{dataset_id}.pkl")


def _save(dataset_id: int, bundle: dict) -> None:
    bundle["trained_at"] = time.time()
    joblib.dump(bundle, _model_path(dataset_id))
    _memory_cache[dataset_id] = (bundle, bundle["trained_at"])


def _load(dataset_id: int) -> dict | None:
    hit = _memory_cache.get(dataset_id)
    if hit:
        return hit[0]
    path = _model_path(dataset_id)
    if not os.path.exists(path):
        return None
    bundle = joblib.load(path)
    _memory_cache[dataset_id] = (bundle, bundle.get("trained_at", 0.0))
    return bundle


def _extract(items: list[dict[str, Any]]) -> tuple[list[str], list[Any], bool]:
    """Extract (texts, targets, is_multilabel) from DataItem dicts."""
    raw: list[tuple[str, Any, bool]] = []
    for item in items:
        content = item.get("content_json") or {}
        final = item.get("final_label") or {}
        text = str(content.get("text", "")).strip()
        if not text:
            continue
        if isinstance(final.get("labels"), list) and final["labels"]:
            raw.append((text, sorted(set(str(l) for l in final["labels"])), True))
        elif final.get("label"):
            raw.append((text, str(final["label"]), False))
    multi = any(is_multi for _, _, is_multi in raw)
    texts: list[str] = []
    targets: list[Any] = []
    for text, target, _ in raw:
        # Mixed datasets: a lone label still counts as one vote in multilabel mode.
        if multi and not isinstance(target, list):
            target = [target]
        texts.append(text)
        targets.append(target)
    return texts, targets, multi


def _split(
    texts: list[str], targets: list, seed: int = 42
) -> tuple[list[int], list[int]]:
    """Deterministic 80/20 split. Falls back to plain split when a class is tiny."""
    import random

    rng = random.Random(seed)
    by_class: dict[Any, list[int]] = {}
    key_of = lambda t: tuple(t) if isinstance(t, list) else t
    for i, t in enumerate(targets):
        by_class.setdefault(key_of(t), []).append(i)
    train: list[int] = []
    test: list[int] = []
    for idxs in by_class.values():
        idxs = idxs[:]
        rng.shuffle(idxs)
        n_test = max(1 if len(idxs) >= 5 else 0, int(len(idxs) * 0.2))
        test.extend(idxs[:n_test])
        train.extend(idxs[n_test:])
    if not test or not train:
        idxs = list(range(len(texts)))
        rng.shuffle(idxs)
        cut = max(1, int(len(idxs) * 0.8))
        return idxs[:cut], idxs[cut:]
    return train, test


def _fit_single(texts: list[str], targets: list[str]) -> tuple[Tfidf, NaiveBayes]:
    tfidf = Tfidf().fit([_tokens(t) for t in texts])
    nb = NaiveBayes().fit([tfidf.vector(_tokens(t)) for t in texts], targets)
    return tfidf, nb


def _single_accuracy(
    texts: list[str], targets: list[str]
) -> tuple[float, str, Tfidf, NaiveBayes]:
    if len(texts) >= 20:
        tr, te = _split(texts, targets)
        tfidf, nb = _fit_single([texts[i] for i in tr], [targets[i] for i in tr])
        hits = sum(
            1
            for i in te
            if max(nb.scores(tfidf.vector(_tokens(texts[i]))), key=nb.scores(tfidf.vector(_tokens(texts[i]))).get)
            == targets[i]
        )
        acc = hits / len(te)
        tfidf, nb = _fit_single(texts, targets)
        return acc, "held-out 20%", tfidf, nb
    n_folds = min(5, len(texts))
    folds: list[list[int]] = [[] for _ in range(n_folds)]
    for rank, i in enumerate(sorted(range(len(texts)), key=lambda k: (targets[k], k))):
        folds[rank % n_folds].append(i)
    hits = total = 0
    for f in range(n_folds):
        te = folds[f]
        tr = [i for g, fold in enumerate(folds) if g != f for i in fold]
        if not tr or not te:
            continue
        tfidf, nb = _fit_single([texts[i] for i in tr], [targets[i] for i in tr])
        for i in te:
            vec = tfidf.vector(_tokens(texts[i]))
            scores = nb.scores(vec)
            if scores and max(scores, key=scores.get) == targets[i]:
                hits += 1
            total += 1
    tfidf, nb = _fit_single(texts, targets)
    return (hits / total) if total else 0.0, f"{n_folds}-fold CV (small sample)", tfidf, nb


def _fit_multi(
    texts: list[str], targets: list[list[str]]
) -> tuple[Tfidf, dict[str, NaiveBayes], list[str]]:
    tfidf = Tfidf().fit([_tokens(t) for t in texts])
    vecs = [tfidf.vector(_tokens(t)) for t in texts]
    classes = sorted({l for ts in targets for l in ts})
    models = {}
    for cls in classes:
        binary = ["yes" if cls in ts else "no" for ts in targets]
        models[cls] = NaiveBayes().fit(vecs, binary)
    return tfidf, models, classes


def train_model(dataset_id: int, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Train on labeled items. Returns accuracy, labeled_count, task_type."""
    texts, targets, multi = _extract(items)

    if len(texts) < MIN_LABELED_ROWS:
        raise ValueError(
            f"Need at least {MIN_LABELED_ROWS} labeled rows, got {len(texts)}"
        )

    if len(texts) > MAX_TRAINING_ROWS:
        texts = texts[:MAX_TRAINING_ROWS]
        targets = targets[:MAX_TRAINING_ROWS]

    if multi:
        tfidf, models, classes = _fit_multi(texts, targets)
        tr, te = _split(texts, targets)
        hits = 0
        for i in te:
            vec = tfidf.vector(_tokens(texts[i]))
            pred = {c for c, m in models.items() if m.scores(vec).get("yes", float("-inf")) >= m.scores(vec).get("no", float("-inf"))}
            if pred == set(targets[i]):
                hits += 1
        accuracy = hits / len(te) if te else 0.0
        _save(dataset_id, {
            "kind": "multilabel", "tfidf": tfidf, "models": models, "classes": classes,
        })
        eval_note = "subset accuracy, held-out split (multilabel)"
    else:
        accuracy, eval_note, tfidf, nb = _single_accuracy(texts, targets)
        _save(dataset_id, {"kind": "single", "tfidf": tfidf, "model": nb})

    return {
        "accuracy": round(accuracy, 4),
        "labeled_count": len(texts),
        "dataset_id": dataset_id,
        "task_type": "multilabel" if multi else "single",
        "evaluation": eval_note,
    }


def predict_with_model(dataset_id: int, text: str) -> dict[str, Any]:
    """Predict label(s) for text using the persisted model.

    Returns label (top single label, always present), confidence,
    plus labels list for multilabel models.
    Raises KeyError if no model exists, ValueError if text is empty.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    bundle = _load(dataset_id)
    if bundle is None:
        raise KeyError(f"No trained model for dataset {dataset_id}. Train first.")

    tfidf = bundle["tfidf"]
    vec = tfidf.vector(_tokens(text))
    if bundle.get("kind") == "multilabel":
        conf = {}
        for cls in bundle["classes"]:
            probs = bundle["models"][cls].predict_proba(vec)
            conf[cls] = round(probs.get("yes", 0.0), 4)
        picked = [c for c, p in conf.items() if p >= 0.5] or [
            max(conf, key=conf.get)
        ]
        top = max(conf, key=conf.get)
        return {
            "label": top,
            "confidence": conf[top],
            "labels": picked,
            "confidences": conf,
            "dataset_id": dataset_id,
        }

    probs = bundle["model"].predict_proba(vec)
    if not probs:
        raise ValueError("Model has no classes")
    top = max(probs, key=probs.get)
    return {
        "label": top,
        "confidence": round(probs[top], 4),
        "dataset_id": dataset_id,
    }


def clear_cache() -> None:
    """Drop the in-memory cache (disk models stay). Used by tests."""
    _memory_cache.clear()
