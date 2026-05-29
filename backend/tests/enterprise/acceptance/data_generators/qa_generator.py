from dataclasses import dataclass


@dataclass
class QAPair:
    question: str
    expected_answer: str
    relevant_doc_ids: list[str]


class QAGenerator:
    """Generate Q&A pairs from documents for RAG evaluation."""

    QUESTION_TEMPLATES = [
        "What is the {topic}?",
        "How do I {action}?",
        "What are the requirements for {topic}?",
        "When can I {action}?",
    ]

    def generate(self, documents: list) -> list[QAPair]:
        qa_pairs = []
        for doc in documents:
            qa_pairs.extend(self._generate_for_document(doc))
        return qa_pairs

    def _generate_for_document(self, doc) -> list[QAPair]:
        # Simple extraction - in production, use LLM
        return [
            QAPair(
                question=f"Tell me about {doc.title}",
                expected_answer=doc.content[:200],
                relevant_doc_ids=[doc.doc_id],
            )
        ]
