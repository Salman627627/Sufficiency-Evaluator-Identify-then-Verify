import json
from django.test import TestCase, Client
from . import llm, pipeline
from .models import Run
from .samples import SAMPLES

class SufficiencyAPITests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_get(self):
        res = self.client.get("/api/health/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["llm_mode"], "mock")
        self.assertEqual(data["methods"], pipeline.METHODS)

    def test_health_method_not_allowed(self):
        res = self.client.post("/api/health/")
        self.assertEqual(res.status_code, 405)

    def test_samples_get(self):
        res = self.client.get("/api/samples/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("samples", data)
        self.assertEqual(len(data["samples"]), 3)
        s0 = data["samples"][0]
        for key in ["id", "question", "answer", "gold", "distractors"]:
            self.assertIn(key, s0)

    def test_samples_method_not_allowed(self):
        res = self.client.post("/api/samples/")
        self.assertEqual(res.status_code, 405)

    def test_evaluate_validation_errors(self):
        # 405 on GET
        res = self.client.get("/api/evaluate/")
        self.assertEqual(res.status_code, 405)

        # 400 on empty selection
        res = self.client.post(
            "/api/evaluate/",
            data=json.dumps({"sample_ids": [], "methods": []}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)

        # 400 on invalid JSON
        res = self.client.post(
            "/api/evaluate/",
            data="not valid json",
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)

    def test_evaluate_and_runs_flow(self):
        # Run all 3 built-in samples across all 4 methods
        payload = {
            "sample_ids": [s["id"] for s in SAMPLES],
            "methods": pipeline.METHODS,
        }
        res = self.client.post(
            "/api/evaluate/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("run_id", data)
        self.assertEqual(data["mode"], "mock")
        self.assertIn("summary", data)
        self.assertIn("cases", data)

        # 3 samples * 2 cases (full + ablated) = 6 cases
        cases = data["cases"]
        self.assertEqual(len(cases), 6)
        self.assertEqual(data["summary"]["n_cases"], 6)

        # All 4 methods in summary accuracy
        for m in pipeline.METHODS:
            self.assertIn(m, data["summary"]["accuracy"])
            self.assertIsInstance(data["summary"]["accuracy"][m], (int, float))

        # Check case structure
        for c in cases:
            self.assertIn("sample_id", c)
            self.assertIn("question", c)
            self.assertIn("answer", c)
            self.assertIn("setting", c)
            self.assertIn("gold_label", c)
            self.assertIn("context", c)
            self.assertIn("results", c)
            for m in pipeline.METHODS:
                self.assertIn(m, c["results"])
                r = c["results"][m]
                self.assertIn("pred", r)
                self.assertIn(r["pred"], ["Sufficient", "Insufficient"])
                self.assertIn("correct", r)
                self.assertIsInstance(r["correct"], bool)

        # Verify run persistence in DB
        self.assertEqual(Run.objects.count(), 1)
        run_record = Run.objects.first()
        self.assertEqual(run_record.id, data["run_id"])
        self.assertEqual(run_record.mode, "mock")

        # Test GET /api/runs/
        runs_res = self.client.get("/api/runs/")
        self.assertEqual(runs_res.status_code, 200)
        runs_data = runs_res.json()
        self.assertIn("runs", runs_data)
        self.assertEqual(len(runs_data["runs"]), 1)
        self.assertEqual(runs_data["runs"][0]["id"], run_record.id)

    def test_custom_sample_evaluation(self):
        custom_sample = {
            "id": "custom1",
            "question": "What award did the director of Inception win?",
            "answer": "Academy Award",
            "gold": [
                {"title": "Inception", "text": "Inception was directed by Christopher Nolan."},
                {"title": "Christopher Nolan", "text": "Christopher Nolan is a filmmaker who won an Academy Award."}
            ],
            "distractors": [
                {"title": "Interstellar", "text": "A sci-fi film directed by Christopher Nolan."}
            ]
        }
        payload = {
            "sample_ids": [],
            "custom": [custom_sample],
            "methods": ["autorater", "identify_verify"]
        }
        res = self.client.post(
            "/api/evaluate/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["summary"]["n_cases"], 2)
        self.assertEqual(len(data["cases"]), 2)


class PipelineUnitTests(TestCase):
    def test_fallback_embeddings_and_consensus(self):
        # Even without sentence-transformers, bag-of-words cosine fallback must work
        hyps = [
            "No information is missing.",
            "No information is missing.",
            "No information is missing.",
            "The context lacks the date.",
            "No information is missing."
        ]
        claim, score = pipeline.consensus(hyps)
        self.assertEqual(claim, "No information is missing.")
        self.assertGreaterEqual(score, 0.3)

    def test_consensus_below_threshold(self):
        # Dissimilar hypotheses leading to score < threshold
        hyps = [
            "alpha beta gamma",
            "delta epsilon zeta",
            "eta theta iota",
            "kappa lambda mu",
            "nu xi omicron"
        ]
        claim, score = pipeline.consensus(hyps, thr=0.3)
        self.assertIsNone(claim)
        self.assertLess(score, 0.3)

    def test_mock_autorater(self):
        q = "Where was Shirley Temple born?"
        ctx_full = "Shirley Temple was born in Santa Monica."
        ctx_ablated = "Shirley Temple was an American actress and diplomat."
        ans_full = llm.ask("autorater", q=q, ctx=ctx_full)
        ans_ablated = llm.ask("autorater", q=q, ctx=ctx_ablated)
        self.assertTrue(ans_full.startswith("SUFFICIENT"))
        self.assertTrue(ans_ablated.startswith("INSUFFICIENT"))

    def test_mock_migres(self):
        q = "Where was Shirley Temple born?"
        ctx_full = "Shirley Temple was born in Santa Monica."
        ctx_ablated = "Shirley Temple was an American actress and diplomat."
        ans_full = llm.ask("migres", q=q, ctx=ctx_full)
        ans_ablated = llm.ask("migres", q=q, ctx=ctx_ablated)
        self.assertEqual(ans_full, "Answer found in context.")
        self.assertTrue(ans_ablated.startswith("unanswerable"))

    def test_mock_verify(self):
        ctx = "Kiss and Tell is a 1945 American comedy film in which Shirley Temple portrayed Corliss Archer."
        # Present word -> YES
        self.assertEqual(llm.ask("verify", ctx=ctx, claim="The context does not mention: portrayed"), "YES")
        # Absent word -> NO
        self.assertEqual(llm.ask("verify", ctx=ctx, claim="The context does not mention: protocol"), "NO")
