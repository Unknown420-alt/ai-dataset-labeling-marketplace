"""TF-IDF + MultinomialNB training service with in-memory cache."""

import time
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score
import numpy as np

# In-memory cache: dataset_id → (pipeline, timestamp)
_model_cache: dict[int, tuple[Pipeline, float]] = {}
_CACHE_TTL = 300  # 5 minutes

MIN_LABELED_ROWS = 10
MAX_TRAINING_ROWS = 2000


def _extract_text_label(items: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Extract (texts, labels) from DataItem dicts."""
    texts = []
    labels = []
    for item in items:
        content = item.get("content_json") or {}
        final = item.get("final_label") or {}
        text = content.get("text", "")
        label = final.get("label", "")
        if text and label:
            texts.append(str(text))
            labels.append(str(label))
    return texts, labels


def train_model(dataset_id: int, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Train TF-IDF + MultinomialNB on labeled items.

    Returns dict with accuracy, labeled_count, dataset_id.
    Caches the trained pipeline in memory for subsequent predict calls.
    Raises ValueError if fewer than MIN_LABELED_ROWS after filtering.
    """
    texts, labels = _extract_text_label(items)

    if len(texts) < MIN_LABELED_ROWS:
        raise ValueError(
            f"Need at least {MIN_LABELED_ROWS} labeled rows, got {len(texts)}"
        )

    # Cap training rows
    if len(texts) > MAX_TRAINING_ROWS:
        texts = texts[:MAX_TRAINING_ROWS]
        labels = labels[:MAX_TRAINING_ROWS]

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
        ("clf", MultinomialNB()),
    ])

    # Cross-validation accuracy (min 3 folds, or fewer if small dataset)
    n_samples = len(texts)
    n_folds = min(5, n_samples)
    scores = cross_val_score(pipeline, texts, labels, cv=n_folds, scoring="accuracy")
    accuracy = float(np.mean(scores))

    # Fit on full data for prediction
    pipeline.fit(texts, labels)

    # Cache the model
    _model_cache[dataset_id] = (pipeline, time.time())

    return {
        "accuracy": round(accuracy, 4),
        "labeled_count": len(texts),
        "dataset_id": dataset_id,
    }


def predict_with_model(
    dataset_id: int, text: str
) -> dict[str, Any]:
    """Predict label for text using cached model.

    Returns dict with label, confidence, dataset_id.
    Raises KeyError if no cached model for this dataset.
    Raises ValueError if text is empty.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    if dataset_id not in _model_cache:
        raise KeyError(f"No trained model for dataset {dataset_id}. Train first.")

    pipeline, ts = _model_cache[dataset_id]

    # Check TTL
    if time.time() - ts > _CACHE_TTL:
        del _model_cache[dataset_id]
        raise KeyError(f"Model for dataset {dataset_id} expired. Train again.")

    label = pipeline.predict([text])[0]
    proba = pipeline.predict_proba([text])[0]
    confidence = float(np.max(proba))

    return {
        "label": label,
        "confidence": round(confidence, 4),
        "dataset_id": dataset_id,
    }
