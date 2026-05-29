from dataclasses import dataclass
import random


@dataclass
class SyntheticDocument:
    doc_id: str
    title: str
    content: str
    tenant_id: str


class DocumentCorpusGenerator:
    """Generate synthetic knowledge documents."""

    TEMPLATES = {
        "policy": "Policy: {topic}\n\n{content}",
        "faq": "Q: {question}\nA: {answer}",
        "procedure": "Procedure: {title}\n\nSteps:\n{steps}",
    }

    TOPICS = [
        "refund policy", "data privacy", "security guidelines",
        "expense reimbursement", "remote work policy",
        "code of conduct", "IT support procedures",
    ]

    def generate(self, tenant_id: str, count: int) -> list[SyntheticDocument]:
        documents = []
        for i in range(count):
            topic = random.choice(self.TOPICS)
            doc_type = random.choice(list(self.TEMPLATES.keys()))
            documents.append(SyntheticDocument(
                doc_id=f"doc_{tenant_id}_{i:04d}",
                title=f"{topic.title()} - {i}",
                content=self._generate_content(doc_type, topic),
                tenant_id=tenant_id,
            ))
        return documents

    def _generate_content(self, doc_type: str, topic: str) -> str:
        template = self.TEMPLATES[doc_type]
        return template.format(
            topic=topic,
            content=f"Detailed content about {topic}...",
            question=f"What is the {topic}?",
            answer=f"The {topic} states that...",
            title=topic,
            steps="1. First step\n2. Second step",
        )
