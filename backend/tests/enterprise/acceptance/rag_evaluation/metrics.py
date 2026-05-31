"""RAG evaluation metrics.

Implements standard RAG evaluation metrics:
- Hit Rate @ K: Is correct doc in top K?
- MRR: Mean Reciprocal Rank
- NDCG: Normalized Discounted Cumulative Gain
"""

from dataclasses import dataclass


@dataclass
class RAGMetrics:
    """RAG evaluation metrics."""

    hit_rate_at_5: float
    mrr: float  # Mean Reciprocal Rank
    ndcg_at_10: float

    def is_acceptable(self) -> bool:
        """Check if metrics meet acceptance criteria.

        Criteria:
        - Hit Rate @ 5 >= 85%
        - MRR >= 0.75
        - NDCG @ 10 >= 0.80
        """
        return self.hit_rate_at_5 >= 0.85 and self.mrr >= 0.75 and self.ndcg_at_10 >= 0.80

    def __str__(self) -> str:
        return f"RAGMetrics(hit_rate@5={self.hit_rate_at_5:.2%}, mrr={self.mrr:.3f}, ndcg@10={self.ndcg_at_10:.3f})"


class RAGAccuracyEvaluator:
    """Evaluate RAG system accuracy using standard metrics."""

    def evaluate(
        self,
        results: list[dict],
        expected_doc_ids: list[list[str]],
    ) -> RAGMetrics:
        """
        Evaluate retrieval results.

        Args:
            results: List of retrieved results per query
            expected_doc_ids: List of expected document IDs per query

        Returns:
            RAGMetrics with hit rate, MRR, and NDCG
        """
        hit_at_5 = []
        reciprocal_ranks = []

        for result, expected in zip(results, expected_doc_ids):
            retrieved_ids = [r.get("doc_id") for r in result[:5]]

            # Hit @ 5
            hit = any(e in retrieved_ids for e in expected)
            hit_at_5.append(hit)

            # MRR
            rr = 0.0
            for i, rid in enumerate(retrieved_ids, 1):
                if rid in expected:
                    rr = 1.0 / i
                    break
            reciprocal_ranks.append(rr)

        return RAGMetrics(
            hit_rate_at_5=sum(hit_at_5) / len(hit_at_5) if hit_at_5 else 0.0,
            mrr=sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
            ndcg_at_10=self._compute_ndcg(results, expected_doc_ids),
        )

    def _compute_ndcg(
        self,
        results: list[dict],
        expected_doc_ids: list[list[str]],
        k: int = 10,
    ) -> float:
        """Compute NDCG @ k.

        NDCG = DCG / IDCG
        DCG = sum((2^rel - 1) / log2(i + 1)) for i in [1, k]
        """
        import math

        ndcg_scores = []

        for result, expected in zip(results, expected_doc_ids):
            retrieved_ids = [r.get("doc_id") for r in result[:k]]

            # Compute DCG
            dcg = 0.0
            for i, rid in enumerate(retrieved_ids, 1):
                if rid in expected:
                    # Binary relevance: 1 if relevant, 0 otherwise
                    rel = 1
                    dcg += (2**rel - 1) / math.log2(i + 1)

            # Compute IDCG (ideal DCG)
            # Ideal case: all relevant docs at top
            idcg = 0.0
            for i in range(1, min(len(expected), k) + 1):
                rel = 1
                idcg += (2**rel - 1) / math.log2(i + 1)

            # NDCG
            if idcg > 0:
                ndcg_scores.append(dcg / idcg)
            else:
                ndcg_scores.append(0.0)

        return sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
