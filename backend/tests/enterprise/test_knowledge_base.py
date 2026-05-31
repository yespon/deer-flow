"""Tests for KnowledgeConnector and CorporateKnowledgeBase."""

from unittest.mock import Mock

import pytest

from deerflow.enterprise.knowledge_base import (
    ChunkingStrategy,
    CorporateKnowledgeBase,
    DocumentChunk,
    KnowledgeDocument,
    MockEmbedder,
    MockVectorStore,
    SyncResult,
)
from deerflow.enterprise.knowledge_config import (
    ChunkingConfig,
    KnowledgeBaseConfig,
    RetrievalConfig,
    VectorStoreConfig,
)


class TestKnowledgeDocument:
    def test_document_creation(self):
        doc = KnowledgeDocument(
            doc_id="doc_1",
            title="Test Document",
            content="This is test content",
            source_url="https://example.com/doc1",
            metadata={"author": "Test"},
        )
        assert doc.doc_id == "doc_1"
        assert doc.title == "Test Document"
        assert doc.content == "This is test content"

    def test_document_with_defaults(self):
        doc = KnowledgeDocument(
            doc_id="doc_2",
            title="Simple Doc",
            content="Content",
        )
        assert doc.source_url is None
        assert doc.metadata == {}


class TestDocumentChunk:
    def test_chunk_creation(self):
        chunk = DocumentChunk(
            chunk_id="chunk_1",
            doc_id="doc_1",
            content="Chunk content",
            embedding=[0.1, 0.2, 0.3],
            metadata={"position": 0},
        )
        assert chunk.chunk_id == "chunk_1"
        assert chunk.doc_id == "doc_1"
        assert len(chunk.embedding) == 3

    def test_chunk_without_embedding(self):
        chunk = DocumentChunk(
            chunk_id="chunk_2",
            doc_id="doc_1",
            content="No embedding yet",
        )
        assert chunk.embedding is None


class TestSyncResult:
    def test_sync_result_creation(self):
        result = SyncResult(
            documents_synced=10,
            documents_failed=2,
            chunks_created=50,
            errors=["Error 1", "Error 2"],
        )
        assert result.documents_synced == 10
        assert result.documents_failed == 2
        assert result.chunks_created == 50
        assert len(result.errors) == 2


class TestChunkingStrategy:
    def test_chunk_by_paragraphs(self):
        content = "Para 1.\n\nPara 2.\n\nPara 3."
        chunks = ChunkingStrategy.chunk_by_paragraphs(content, max_chunk_size=100)

        assert len(chunks) == 3
        assert "Para 1" in chunks[0]

    def test_chunk_by_fixed_size(self):
        content = "A" * 200
        chunks = ChunkingStrategy.chunk_by_fixed_size(content, chunk_size=50, overlap=10)

        assert len(chunks) > 1
        # Each chunk should be around 50 chars
        assert len(chunks[0]) <= 50

    def test_chunk_by_fixed_size_caps_overlap_to_avoid_stall(self):
        content = "A" * 200

        chunks = ChunkingStrategy.chunk_by_fixed_size(content, chunk_size=50, overlap=50)

        assert len(chunks) > 1
        assert all(chunk for chunk in chunks)

    def test_chunk_by_sentences(self):
        content = "First sentence. Second sentence. Third sentence."
        chunks = ChunkingStrategy.chunk_by_sentences(content, sentences_per_chunk=2)

        assert len(chunks) == 2
        assert "First" in chunks[0]
        assert "Third" in chunks[1]


class TestCorporateKnowledgeBase:
    @pytest.fixture
    def config(self):
        return KnowledgeBaseConfig(
            enabled=True,
            vector_store=VectorStoreConfig(
                provider="chroma",
                collection_name="test_kb",
            ),
            chunking=ChunkingConfig(
                strategy="fixed_size",
                chunk_size=500,
            ),
            retrieval=RetrievalConfig(
                top_k=5,
                similarity_threshold=0.7,
            ),
        )

    @pytest.fixture
    def mock_kb(self, config):
        kb = CorporateKnowledgeBase(config)
        kb._vector_store = Mock()
        kb._embedder = Mock()
        return kb

    def test_kb_initialization(self, mock_kb, config):
        assert mock_kb.config == config
        assert mock_kb._vector_store is not None

    def test_ensure_tenant_namespace(self, mock_kb):
        mock_kb._ensure_tenant_namespace("tenant_abc")
        # Should create namespace for tenant
        mock_kb._vector_store.create_collection.assert_called_once()

    def test_process_document(self, mock_kb):
        doc = KnowledgeDocument(
            doc_id="doc_1",
            title="Test Doc",
            content="This is a test document with multiple sentences. " * 10,
        )

        chunks = mock_kb._process_document(doc)

        assert len(chunks) > 0
        assert all(c.doc_id == "doc_1" for c in chunks)

    def test_chunk_document_fixed_size(self, mock_kb):
        mock_kb.config.chunking.strategy = "fixed_size"
        mock_kb.config.chunking.chunk_size = 50
        mock_kb.config.chunking.chunk_overlap = 50

        doc = KnowledgeDocument(
            doc_id="doc_1",
            title="Test",
            content="A" * 200,
        )

        chunks = mock_kb._chunk_document(doc)

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.doc_id == "doc_1"
            assert chunk.embedding is None  # Not embedded yet

    def test_search_requires_tenant(self, mock_kb):
        with pytest.raises(ValueError, match="tenant_id is required"):
            import asyncio

            asyncio.run(mock_kb.search("query", tenant_id=None))

    def test_format_context(self, mock_kb):
        chunks = [
            DocumentChunk(chunk_id="c1", doc_id="d1", content="Content 1"),
            DocumentChunk(chunk_id="c2", doc_id="d1", content="Content 2"),
        ]

        context = mock_kb._format_context(chunks)

        assert "Content 1" in context
        assert "Content 2" in context

    def test_kb_disabled(self):
        config = KnowledgeBaseConfig(enabled=False)
        kb = CorporateKnowledgeBase(config)

        with pytest.raises(RuntimeError, match="Knowledge base is disabled"):
            kb._ensure_enabled()

    def test_add_document_requires_tenant(self, mock_kb):
        doc = KnowledgeDocument(doc_id="d1", title="Test", content="Content")

        with pytest.raises(ValueError, match="tenant_id is required"):
            import asyncio

            asyncio.run(mock_kb.add_document(doc, tenant_id=None))

    def test_delete_document(self, mock_kb):
        mock_kb.delete_document("doc_1", tenant_id="tenant_abc")

        mock_kb._vector_store.delete.assert_called_once()


class TestMockVectorStore:
    def test_create_collection(self):
        store = MockVectorStore()
        store.create_collection("test_collection")
        assert "test_collection" in store._collections

    def test_upsert_and_search(self):
        store = MockVectorStore()
        store.create_collection("test")

        store.upsert(
            collection="test",
            chunk_id="c1",
            embedding=[0.1, 0.2, 0.3],
            content="Test content",
            metadata={"doc_id": "d1"},
        )

        results = store.search(
            collection="test",
            query_embedding=[0.1, 0.2, 0.3],
            top_k=5,
            threshold=0.7,
        )

        assert len(results) == 1
        assert results[0]["content"] == "Test content"

    def test_delete_by_doc_id(self):
        store = MockVectorStore()
        store.create_collection("test")

        store.upsert(
            collection="test",
            chunk_id="c1",
            embedding=None,
            content="Content",
            metadata={"doc_id": "doc_1"},
        )

        store.delete("test", filter={"doc_id": "doc_1"})

        assert len(store._collections["test"]) == 0


class TestMockEmbedder:
    @pytest.mark.asyncio
    async def test_embed_returns_embeddings(self):
        embedder = MockEmbedder(dimensions=10)
        texts = ["Text 1", "Text 2"]

        embeddings = await embedder.embed(texts)

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 10
        assert len(embeddings[1]) == 10
