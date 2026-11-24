"""Spam detection model: training, persistence, prediction and explanations."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).parent
DEFAULT_DATA = BASE_DIR / "data" / "emails.csv"
MODEL_PATH = BASE_DIR / "models" / "spam_model.joblib"
METRICS_PATH = BASE_DIR / "models" / "metrics.json"

URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
URGENCY_WORDS = {
    "urgent", "immediately", "act now", "final notice", "limited time", "expires", "last chance",
    "right away", "today only", "don't miss", "hurry", "asap",
}
MONEY_RE = re.compile(r"[$€£₹]\s?\d|\d+\s?(?:usd|dollars|rupees)|\bfree\b|\bcash\b|\bprize\b|\bwinner\b", re.I)
SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd")
RISKY_TLDS = (".xyz", ".top", ".biz", ".click", ".loan", ".win", ".work")


# ----------------------------------------------------------------- data ----
def clean_text(text: str) -> str:
    """Normalise text so the model sees consistent tokens."""
    text = text or ""
    text = URL_RE.sub(" urltoken ", text)
    text = re.sub(r"\d{6,}", " longnumber ", text)
    text = re.sub(r"\$", " dollarsign ", text)
    return text.lower()


def combine(subject: str, body: str) -> str:
    return clean_text(f"{subject or ''} . {body or ''}")


def load_dataset(path: str | Path) -> pd.DataFrame:
    """Load a CSV and return a frame with columns: label (0/1), text.

    Supported layouts:
      * label,subject,text   (this project's format)
      * label,text
      * v1,v2                (Kaggle "SMS Spam Collection" spam.csv)
      * Category,Message
    """
    path = Path(path)
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1")

    cols = {c.lower().strip(): c for c in df.columns}
    label_col = next((cols[c] for c in ("label", "v1", "category", "class", "spam") if c in cols), None)
    text_col = next((cols[c] for c in ("text", "v2", "message", "body", "email") if c in cols), None)
    if label_col is None or text_col is None:
        raise ValueError(
            f"Could not find label/text columns in {path.name}. Found columns: {list(df.columns)}"
        )
    subject_col = cols.get("subject")

    labels = df[label_col].astype(str).str.strip().str.lower().map(
        {"spam": 1, "1": 1, "ham": 0, "0": 0, "not spam": 0}
    )
    subjects = df[subject_col].fillna("") if subject_col else ""
    out = pd.DataFrame({
        "label": labels,
        "text": [combine(s, b) for s, b in zip(
            subjects if subject_col else [""] * len(df), df[text_col].fillna("")
        )],
    }).dropna(subset=["label"])
    out["label"] = out["label"].astype(int)
    out = out[out["text"].str.strip() != ""].drop_duplicates()
    if out["label"].nunique() < 2:
        raise ValueError("Dataset must contain both spam and ham examples.")
    return out.reset_index(drop=True)


# ------------------------------------------------------------- training ----
def build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2), min_df=2, sublinear_tf=True, strip_accents="unicode",
            token_pattern=r"(?u)\b\w[\w']*\b",
        )),
        ("clf", LogisticRegression(C=4.0, max_iter=1000, class_weight="balanced")),
    ])


def train(data_path: str | Path = DEFAULT_DATA, test_size: float = 0.2, seed: int = 42) -> dict:
    df = load_dataset(data_path)
    x_train, x_test, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=test_size, random_state=seed, stratify=df["label"]
    )
    pipe = build_pipeline().fit(x_train, y_train)
    pred = pipe.predict(x_test)
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, pred, average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_test, pred, labels=[0, 1]).ravel()

    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": Path(data_path).name,
        "samples": int(len(df)),
        "spam_samples": int(df["label"].sum()),
        "ham_samples": int((df["label"] == 0).sum()),
        "test_samples": int(len(y_test)),
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "confusion_matrix": {"true_negative": int(tn), "false_positive": int(fp),
                             "false_negative": int(fn), "true_positive": int(tp)},
        "algorithm": "TF-IDF (1-2 grams) + Logistic Regression",
    }

    # Refit on all data for the shipped model; metrics above come from the held-out split.
    final = build_pipeline().fit(df["text"], df["label"])
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    return metrics


# ------------------------------------------------------------ inference ----
def _host(url: str) -> str:
    """Return the lower-case host part of a URL, without scheme, path or punctuation."""
    url = re.sub(r"^https?://", "", url.strip().lower())
    return re.split(r"[/?#]", url, maxsplit=1)[0].rstrip(".,!;:)")


def heuristic_signals(subject: str, body: str) -> list[dict]:
    """Human-readable red flags, independent of the ML score."""
    full = f"{subject} {body}"
    lower = full.lower()
    urls = URL_RE.findall(full)
    signals = []

    if urls:
        signals.append({"name": "Links", "detail": f"{len(urls)} link(s) in the message", "level": "info"})
    if any(s in u.lower() for u in urls for s in SHORTENERS):
        signals.append({"name": "Shortened link", "detail": "Hides the real destination", "level": "warn"})
    if any(_host(u).endswith(RISKY_TLDS) for u in urls):
        signals.append({"name": "Unusual domain", "detail": "Link uses a domain ending often seen in spam", "level": "warn"})

    letters = [c for c in full if c.isalpha()]
    if len(letters) > 20 and sum(c.isupper() for c in letters) / len(letters) > 0.4:
        signals.append({"name": "Shouting", "detail": "Large share of capital letters", "level": "warn"})
    if full.count("!") >= 3:
        signals.append({"name": "Exclamation marks", "detail": f"{full.count('!')} in the message", "level": "warn"})

    hits = sorted(w for w in URGENCY_WORDS if w in lower)
    if hits:
        signals.append({"name": "Urgency", "detail": "Pressure phrases: " + ", ".join(hits[:3]), "level": "warn"})
    if MONEY_RE.search(full):
        signals.append({"name": "Money or prizes", "detail": "Mentions cash, prizes or free offers", "level": "warn"})
    if re.search(r"password|verify your|confirm your|bank details|account (?:has been )?(?:suspended|limited|blocked)", lower):
        signals.append({"name": "Credential request", "detail": "Asks you to verify an account or share details", "level": "danger"})
    return signals


class SpamDetector:
    def __init__(self, model_path: Path = MODEL_PATH):
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"No trained model at {model_path}. Run: python train.py"
            )
        self.pipeline: Pipeline = joblib.load(model_path)
        self.vectorizer: TfidfVectorizer = self.pipeline.named_steps["tfidf"]
        self.clf: LogisticRegression = self.pipeline.named_steps["clf"]
        self.features = np.array(self.vectorizer.get_feature_names_out())

    def predict(self, subject: str = "", body: str = "", top_n: int = 8) -> dict:
        text = combine(subject, body)
        vec = self.vectorizer.transform([text])
        prob = float(self.clf.predict_proba(vec)[0][1])

        contrib = vec.multiply(self.clf.coef_[0]).tocsr()
        idx = contrib.indices
        vals = contrib.data
        order = np.argsort(-np.abs(vals))[:top_n]
        words = [
            {"word": str(self.features[idx[i]]).replace("urltoken", "[link]").replace("dollarsign", "$"),
             "weight": round(float(vals[i]), 4),
             "direction": "spam" if vals[i] > 0 else "ham"}
            for i in order
        ]

        is_spam = prob >= 0.5
        risk = "high" if prob >= 0.85 else "medium" if prob >= 0.3 else "low"
        return {
            "label": "spam" if is_spam else "ham",
            "spam_probability": round(prob, 4),
            "confidence": round(max(prob, 1 - prob), 4),
            "risk": risk,
            "top_words": words,
            "signals": heuristic_signals(subject or "", body or ""),
        }


def load_metrics() -> dict | None:
    if METRICS_PATH.exists():
        return json.loads(METRICS_PATH.read_text())
    return None
