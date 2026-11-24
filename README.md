# Spam Check: spam email detection

A small full-stack machine-learning project. Paste an email and the app says whether it is spam, how likely that is, which warning signs it found and which words moved the score.

- **Backend:** Python, Flask, scikit-learn (TF-IDF + Logistic Regression)
- **Frontend:** plain HTML, CSS and JavaScript (no build step), served by Flask

## Quick start

Requires Python 3.9 or newer.

```bash
cd spam-detector
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cd backend
python app.py
```

Open <http://127.0.0.1:5000>.

On first run the app trains a model automatically from `backend/data/emails.csv` and saves it to `backend/models/`. To retrain by hand, run `python train.py`.

## Project structure

```
spam-detector/
├── requirements.txt
├── backend/
│   ├── app.py                  Flask API and static file server
│   ├── model.py                data loading, training, prediction, explanations
│   ├── train.py                command-line training script
│   ├── generate_sample_data.py builds the demo dataset
│   ├── data/emails.csv         demo dataset (generated)
│   ├── models/                 trained model and metrics are saved here
│   └── tests/test_api.py       API tests
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Server status |
| GET | `/api/model-info` | Accuracy, precision, recall, F1, confusion matrix |
| POST | `/api/predict` | Check one email |
| POST | `/api/predict/batch` | Check up to 100 emails |

Example:

```bash
curl -X POST http://127.0.0.1:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"subject": "You WON!!!", "body": "Claim your $5000 prize at http://bit.ly/x9Fq2 now!!!"}'
```

Response (shortened):

```json
{
  "label": "spam",
  "spam_probability": 0.98,
  "confidence": 0.98,
  "risk": "high",
  "top_words": [{"word": "free", "weight": 0.45, "direction": "spam"}],
  "signals": [{"name": "Shortened link", "detail": "Hides the real destination", "level": "warn"}]
}
```

Batch requests send `{"emails": [{"subject": "...", "body": "..."}, ...]}` and return `results` plus a `summary` of spam and safe counts.

## Important: the demo dataset is synthetic

`data/emails.csv` is generated from message templates so the project runs without downloads. Because the test split comes from the same templates, the scores are close to 100% and say nothing about real-world accuracy. Before presenting results, train on a real corpus.

### Using a real dataset

1. Download a public dataset, for example the SMS Spam Collection (`spam.csv`) or an email corpus such as Enron-Spam or SpamAssassin, from Kaggle or the UCI repository.
2. Make sure it is a CSV with a label column and a text column. These layouts are detected automatically: `label,subject,text`, `label,text`, `v1,v2` and `Category,Message`. Labels must be `spam` or `ham`.
3. Train and restart the server:

```bash
cd backend
python train.py --data path/to/your_dataset.csv
python app.py
```

The Model tab in the app then shows metrics from your data, computed on a held-out 20% test split.

## Tests

```bash
cd backend
python -m unittest discover -s tests -v
```

## How it works

1. **Cleaning:** subject and body are joined, lower-cased, and links and long numbers are replaced with placeholder tokens so the model learns the presence of a link rather than a specific address.
2. **Features:** TF-IDF over single words and two-word phrases.
3. **Classifier:** logistic regression with balanced class weights. A spam probability of 0.5 or higher is labelled spam.
4. **Explanations:** for each message, each word's TF-IDF value is multiplied by its learned weight, and the largest contributions are shown.
5. **Warning signs:** separate rule checks (shortened links, unusual domains, capital letters, exclamation marks, urgency phrases, credential requests). They are informational and do not change the score.

## Ideas for extending it

- Compare Naive Bayes, SVM and gradient boosting in `model.py`
- Add character n-grams to catch obfuscated words such as `fr33`
- Parse `.eml` files and check sender and header fields
- Add a "wrong verdict" button that stores corrections for retraining
- Deploy with gunicorn behind a reverse proxy

## Limitations

The model only sees text. It does not check sender reputation, SPF/DKIM headers or whether a link is actually malicious, so it should complement a real mail filter, not replace one.
