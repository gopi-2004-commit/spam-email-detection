"""API tests. Run from the backend folder:  python -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as app_module  # noqa: E402


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_module.app.config["TESTING"] = True
        cls.client = app_module.app.test_client()

    def test_health(self):
        self.assertEqual(self.client.get("/api/health").get_json()["status"], "ok")

    def test_spam_is_flagged(self):
        r = self.client.post("/api/predict", json={
            "subject": "You WON!!!",
            "body": "Congratulations! Claim your $5000 prize now at http://bit.ly/x9Fq2 and act now!!!",
        })
        data = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(data["label"], "spam")
        self.assertGreater(data["spam_probability"], 0.8)
        self.assertTrue(data["signals"])

    def test_ham_is_not_flagged(self):
        data = self.client.post("/api/predict", json={
            "subject": "Meeting tomorrow",
            "body": "Hi Priya, are we still meeting at 3:30 PM to go over the project report?",
        }).get_json()
        self.assertEqual(data["label"], "ham")
        self.assertLess(data["spam_probability"], 0.3)

    def test_rejects_empty(self):
        r = self.client.post("/api/predict", json={"subject": "", "body": "  "})
        self.assertEqual(r.status_code, 400)

    def test_rejects_non_json(self):
        self.assertEqual(self.client.post("/api/predict", data="hello").status_code, 400)

    def test_rejects_wrong_types(self):
        r = self.client.post("/api/predict", json={"subject": 5, "body": ["x"]})
        self.assertEqual(r.status_code, 400)

    def test_batch(self):
        data = self.client.post("/api/predict/batch", json={"emails": [
            {"subject": "Free gift", "body": "Click http://claim-reward.top/abc to win cash now!!!"},
            {"subject": "Lunch?", "body": "Want to grab lunch on Friday?"},
        ]}).get_json()
        self.assertEqual(data["summary"]["total"], 2)
        self.assertEqual(data["results"][0]["label"], "spam")

    def test_batch_limit(self):
        emails = [{"subject": "hi", "body": "hello"}] * 101
        self.assertEqual(self.client.post("/api/predict/batch", json={"emails": emails}).status_code, 400)

    def test_model_info(self):
        self.assertGreater(self.client.get("/api/model-info").get_json()["accuracy"], 0.9)

    def test_frontend_served(self):
        for path in ("/", "/style.css", "/app.js"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_unknown_api_route(self):
        self.assertEqual(self.client.get("/api/nope").status_code, 404)


if __name__ == "__main__":
    unittest.main()
