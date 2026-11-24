"""Flask API + static frontend for the spam email detector."""
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from model import MODEL_PATH, SpamDetector, load_metrics, train

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
MAX_FIELD_CHARS = 20_000
MAX_BATCH = 100

app = Flask(__name__, static_folder=None)

_detector: SpamDetector | None = None


def get_detector() -> SpamDetector:
    """Load the model lazily; train automatically on first run if none exists."""
    global _detector
    if _detector is None:
        if not MODEL_PATH.exists():
            train()
        _detector = SpamDetector()
    return _detector


def error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def read_email(payload: dict):
    subject = payload.get("subject", "")
    body = payload.get("body", "")
    if not isinstance(subject, str) or not isinstance(body, str):
        return None, "subject and body must be strings"
    if not (subject.strip() or body.strip()):
        return None, "Enter a subject or message body to analyse"
    if len(subject) > MAX_FIELD_CHARS or len(body) > MAX_FIELD_CHARS:
        return None, f"Each field must be under {MAX_FIELD_CHARS} characters"
    return (subject, body), None


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "model_ready": MODEL_PATH.exists()})


@app.get("/api/model-info")
def model_info():
    get_detector()
    return jsonify(load_metrics() or {})


@app.post("/api/predict")
def predict():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error("Send a JSON body with subject and/or body")
    email, problem = read_email(payload)
    if problem:
        return error(problem)
    return jsonify(get_detector().predict(*email))


@app.post("/api/predict/batch")
def predict_batch():
    payload = request.get_json(silent=True)
    emails = payload.get("emails") if isinstance(payload, dict) else None
    if not isinstance(emails, list) or not emails:
        return error("Send a JSON body like {\"emails\": [{\"subject\": \"...\", \"body\": \"...\"}]}")
    if len(emails) > MAX_BATCH:
        return error(f"At most {MAX_BATCH} emails per request")

    detector = get_detector()
    results = []
    for i, item in enumerate(emails):
        if not isinstance(item, dict):
            return error(f"Item {i + 1} must be an object with subject and/or body")
        email, problem = read_email(item)
        if problem:
            return error(f"Item {i + 1}: {problem}")
        result = detector.predict(*email, top_n=5)
        result["subject"] = email[0]
        results.append(result)
    spam_count = sum(r["label"] == "spam" for r in results)
    return jsonify({"results": results, "summary": {"total": len(results), "spam": spam_count,
                                                     "ham": len(results) - spam_count}})


# ---- frontend -------------------------------------------------------------
@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:filename>")
def assets(filename):
    if filename.startswith("api/"):
        return error("Not found", 404)
    return send_from_directory(FRONTEND_DIR, filename)


if __name__ == "__main__":
    get_detector()
    app.run(host="127.0.0.1", port=5000, debug=False)
