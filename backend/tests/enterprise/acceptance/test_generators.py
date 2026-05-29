import pytest
from .data_generators.tenant_generator import SyntheticTenantGenerator
from .data_generators.document_generator import DocumentCorpusGenerator, SyntheticDocument
from .data_generators.qa_generator import QAGenerator


def test_tenant_generator_creates_valid_tenants():
    generator = SyntheticTenantGenerator()
    tenants = generator.generate(count=5)

    assert len(tenants) == 5
    assert all(t.id.startswith("tenant_") for t in tenants)
    assert all(t.plan in ["free", "pro", "enterprise"] for t in tenants)


def test_document_generator_creates_valid_documents():
    generator = DocumentCorpusGenerator()
    documents = generator.generate(tenant_id="tenant_001", count=10)

    assert len(documents) == 10
    assert all(d.tenant_id == "tenant_001" for d in documents)
    assert all(d.doc_id.startswith("doc_tenant_001_") for d in documents)


def test_qa_generator_creates_valid_qa_pairs():
    doc = SyntheticDocument(
        doc_id="doc_001",
        title="Test Document",
        content="This is test content for the document.",
        tenant_id="tenant_001",
    )

    generator = QAGenerator()
    qa_pairs = generator.generate([doc])

    assert len(qa_pairs) == 1
    assert qa_pairs[0].relevant_doc_ids == ["doc_001"]
    assert "Test Document" in qa_pairs[0].question
