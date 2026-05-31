"""RAG accuracy evaluation tests.

Evaluates RAG system accuracy using curated Q&A pairs.
"""

import json
from pathlib import Path

import pytest

from .metrics import RAGAccuracyEvaluator, RAGMetrics


class TestRAGAccuracy:
    """RAG accuracy evaluation tests."""

    @pytest.fixture
    def qa_pairs(self):
        """Load curated Q&A pairs."""
        dataset_path = Path(__file__).parent / "dataset" / "qa_pairs.json"
        if dataset_path.exists():
            with open(dataset_path) as f:
                return json.load(f)
        # Fallback if file doesn't exist
        return [
            {
                "question": "What is the refund policy?",
                "expected_answer": "Full refund within 30 days",
                "relevant_doc_ids": ["doc_refund_001"],
                "category": "hr_policies",
            },
            {
                "question": "How do I reset my password?",
                "expected_answer": "Go to Settings > Security",
                "relevant_doc_ids": ["doc_it_001"],
                "category": "it_support",
            },
        ]

    @pytest.fixture
    def mock_kb_results(self):
        """Mock knowledge base search results."""
        return {
            "doc_refund_001": [{"doc_id": "doc_refund_001", "score": 0.95}],
            "doc_it_001": [{"doc_id": "doc_it_001", "score": 0.87}],
        }

    def test_hit_rate_at_5_calculation(self):
        """Test Hit Rate @ 5 calculation."""
        evaluator = RAGAccuracyEvaluator()

        # Results where first doc is relevant
        results = [
            [{"doc_id": "doc_001"}, {"doc_id": "doc_002"}],
            [{"doc_id": "doc_003"}, {"doc_id": "doc_004"}],
        ]
        expected = [["doc_001"], ["doc_003"]]

        metrics = evaluator.evaluate(results, expected)

        assert metrics.hit_rate_at_5 == 1.0  # 100% hit rate

    def test_mrr_calculation(self):
        """Test MRR calculation."""
        evaluator = RAGAccuracyEvaluator()

        # Results where relevant doc is at position 2
        results = [
            [{"doc_id": "doc_002"}, {"doc_id": "doc_001"}],
        ]
        expected = [["doc_001"]]

        metrics = evaluator.evaluate(results, expected)

        # MRR should be 1/2 = 0.5
        assert metrics.mrr == 0.5

    def test_rag_metrics_acceptance_criteria(self):
        """Test that metrics correctly evaluate acceptance criteria."""
        # Good metrics
        good_metrics = RAGMetrics(
            hit_rate_at_5=0.90,
            mrr=0.80,
            ndcg_at_10=0.85,
        )
        assert good_metrics.is_acceptable() is True

        # Bad metrics
        bad_metrics = RAGMetrics(
            hit_rate_at_5=0.70,
            mrr=0.60,
            ndcg_at_10=0.70,
        )
        assert bad_metrics.is_acceptable() is False

        # Borderline - hit rate too low
        borderline_metrics = RAGMetrics(
            hit_rate_at_5=0.80,  # Below 85%
            mrr=0.80,
            ndcg_at_10=0.85,
        )
        assert borderline_metrics.is_acceptable() is False

    @pytest.mark.asyncio
    async def test_rag_evaluation_with_mock_kb(self, qa_pairs, mock_kb_results):
        """Test RAG evaluation with mock knowledge base."""
        evaluator = RAGAccuracyEvaluator()

        # Simulate KB search results
        results = []
        expected_ids = []

        for qa in qa_pairs:
            doc_id = qa["relevant_doc_ids"][0]
            # Simulate retrieval - return the relevant doc at position 1
            results.append(
                [
                    {"doc_id": doc_id, "score": 0.9},
                    {"doc_id": "doc_other", "score": 0.7},
                ]
            )
            expected_ids.append(qa["relevant_doc_ids"])

        metrics = evaluator.evaluate(results, expected_ids)

        print(f"\nRAG Metrics: {metrics}")

        # With perfect retrieval, hit rate should be 100%
        assert metrics.hit_rate_at_5 == 1.0
        assert metrics.mrr == 1.0  # First position

    def test_dcg_calculation(self):
        """Test DCG/NDCG calculation."""

        evaluator = RAGAccuracyEvaluator()

        # Perfect ranking
        results = [[{"doc_id": "doc_001"}]]
        expected = [["doc_001"]]

        metrics = evaluator.evaluate(results, expected)

        # NDCG should be 1.0 for perfect ranking
        assert metrics.ndcg_at_10 == 1.0
