"""Corporate Knowledge Base for enterprise RAG.

Provides document storage, chunking, embedding, and retrieval with
tenant namespace isolation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from deerflow.enterprise.knowledge_config import KnowledgeBaseConfig


logger = logging.getLogger(__name__)


@dataclass
class KnowledgeDocument:
    """A document in the knowledge base.

    Attributes:
        doc_id: Unique document identifier
        title: Document title
        content: Full document content
        source_url: Original source URL
        metadata: Additional metadata
    """

    doc_id: str
    title: str
    content: str
    source_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentChunk:
    """A chunk of a document with optional embedding.

    Attributes:
        chunk_id: Unique chunk identifier
        doc_id: Parent document ID
        content: Chunk text content
        embedding: Vector embedding (optional)
        metadata: Chunk metadata (position, etc.)
    """

    chunk_id: str
    doc_id: str
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncResult:
    """Result of a knowledge base sync operation.

    Attributes:
        documents_synced: Number of documents successfully synced
        documents_failed: Number of documents that failed
        chunks_created: Total chunks created
        errors: List of error messages
    """

    documents_synced: int = 0
    documents_failed: int = 0
    chunks_created: int = 0
    errors: list[str] = field(default_factory=list)


class KnowledgeConnector(Protocol):
    """Protocol for knowledge source connectors.

    Implementations connect to external knowledge sources like
    Confluence, Notion, SharePoint, etc.
    """

    async def sync(self, full: bool = False) -> SyncResult:
        """Sync documents from the knowledge source.

        Args:
            full: If True, perform full sync. If False, incremental sync.

        Returns:
            SyncResult with sync statistics.
        """
        ...

    async def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        """Search the knowledge source directly.

        Args:
            query: Search query
            filters: Optional filters
            top_k: Number of results

        Returns:
            List of matching document chunks.
        """
        ...

    async def get_document(self, doc_id: str) -> KnowledgeDocument | None:
        """Get a document by ID.

        Args:
            doc_id: Document identifier

        Returns:
            Document or None if not found.
        """
        ...


class ChunkingStrategy:
    """Strategies for chunking document content."""

    @staticmethod
    def chunk_by_paragraphs(content: str, max_chunk_size: int = 1000) -> list[str]:
        """Chunk content by paragraphs.

        Each paragraph becomes its own chunk (if within size limit).
        Paragraphs exceeding max_chunk_size are split by fixed_size.
        """
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        chunks = []

        for para in paragraphs:
            if len(para) <= max_chunk_size:
                chunks.append(para)
            else:
                # Split large paragraphs
                sub_chunks = ChunkingStrategy.chunk_by_fixed_size(
                    para, chunk_size=max_chunk_size, overlap=0
                )
                chunks.extend(sub_chunks)

        return chunks

    @staticmethod
    def chunk_by_fixed_size(
        content: str,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> list[str]:
        """Chunk content into fixed-size chunks with overlap.

        Args:
            content: Text content to chunk
            chunk_size: Maximum chunk size in characters
            overlap: Number of characters to overlap between chunks
        """
        if not content:
            return []

        chunks = []
        start = 0

        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]

            # Try to break at word boundary
            if end < len(content):
                # Look for space or newline to break
                for i in range(min(len(chunk), 20), 0, -1):
                    if chunk[-i] in " \n":
                        chunk = chunk[:-i]
                        end = start + len(chunk)
                        break

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks

    @staticmethod
    def chunk_by_sentences(content: str, sentences_per_chunk: int = 5) -> list[str]:
        """Chunk content by sentences.

        Uses simple sentence splitting (period + space or newline).
        """
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', content.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current_chunk = []

        for sentence in sentences:
            current_chunk.append(sentence)
            if len(current_chunk) >= sentences_per_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks


class CorporateKnowledgeBase:
    """Enterprise knowledge base with tenant isolation.

    Provides document storage, chunking, embedding, and retrieval
    with per-tenant namespace isolation.
    """

    def __init__(self, config: KnowledgeBaseConfig) -> None:
        """Initialize knowledge base.

        Args:
            config: Knowledge base configuration
        """
        self.config = config
        self._vector_store: Any | None = None
        self._embedder: Any | None = None
        self._connectors: list[KnowledgeConnector] = []

        if config.enabled:
            self._initialize_vector_store()
            self._initialize_embedder()

    def _initialize_vector_store(self) -> None:
        """Initialize vector store connection."""
        # Placeholder - would initialize actual vector store client
        # based on config.vector_store.provider
        logger.info(
            "Initializing vector store: %s",
            self.config.vector_store.provider
        )
        self._vector_store = MockVectorStore()

    def _initialize_embedder(self) -> None:
        """Initialize embedding model."""
        # Placeholder - would initialize actual embedder
        logger.info(
            "Initializing embedder: %s / %s",
            self.config.embedding.provider,
            self.config.embedding.model
        )
        self._embedder = MockEmbedder(
            dimensions=self.config.embedding.dimensions
        )

    def _ensure_enabled(self) -> None:
        """Check if knowledge base is enabled."""
        if not self.config.enabled:
            raise RuntimeError("Knowledge base is disabled")

    def _get_tenant_collection(self, tenant_id: str) -> str:
        """Get collection name for tenant."""
        return f"{self.config.vector_store.collection_name}_{tenant_id}"

    def _ensure_tenant_namespace(self, tenant_id: str) -> None:
        """Ensure tenant namespace exists in vector store."""
        collection_name = self._get_tenant_collection(tenant_id)
        if self._vector_store:
            self._vector_store.create_collection(collection_name)

    def _chunk_document(self, doc: KnowledgeDocument) -> list[DocumentChunk]:
        """Chunk a document based on config strategy."""
        strategy = self.config.chunking.strategy

        if strategy == "paragraphs":
            raw_chunks = ChunkingStrategy.chunk_by_paragraphs(
                doc.content,
                max_chunk_size=self.config.chunking.chunk_size,
            )
        elif strategy == "sentences":
            raw_chunks = ChunkingStrategy.chunk_by_sentences(
                doc.content,
                sentences_per_chunk=self.config.chunking.sentences_per_chunk,
            )
        else:  # fixed_size
            raw_chunks = ChunkingStrategy.chunk_by_fixed_size(
                doc.content,
                chunk_size=self.config.chunking.chunk_size,
                overlap=self.config.chunking.chunk_overlap,
            )

        # Create DocumentChunk objects
        chunks = []
        for i, content in enumerate(raw_chunks):
            chunk = DocumentChunk(
                chunk_id=f"{doc.doc_id}_chunk_{i}",
                doc_id=doc.doc_id,
                content=content,
                metadata={
                    "position": i,
                    "chunk_index": i,
                    "total_chunks": len(raw_chunks),
                },
            )
            chunks.append(chunk)

        return chunks

    async def _embed_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Embed chunks using the configured embedder."""
        if not self._embedder:
            return chunks

        # Process in batches
        batch_size = self.config.embedding.batch_size
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c.content for c in batch]
            embeddings = await self._embedder.embed(texts)

            for chunk, embedding in zip(batch, embeddings):
                chunk.embedding = embedding

        return chunks

    def _process_document(self, doc: KnowledgeDocument) -> list[DocumentChunk]:
        """Process document into chunks."""
        return self._chunk_document(doc)

    async def add_document(
        self,
        doc: KnowledgeDocument,
        tenant_id: str | None = None,
    ) -> list[DocumentChunk]:
        """Add a document to the knowledge base.

        Args:
            doc: Document to add
            tenant_id: Tenant ID for namespace isolation

        Returns:
            List of created chunks.
        """
        self._ensure_enabled()

        if tenant_id is None:
            raise ValueError("tenant_id is required")

        self._ensure_tenant_namespace(tenant_id)

        # Chunk document
        chunks = self._process_document(doc)

        # Embed chunks
        chunks = await self._embed_chunks(chunks)

        # Store in vector store
        collection = self._get_tenant_collection(tenant_id)
        if self._vector_store:
            for chunk in chunks:
                self._vector_store.upsert(
                    collection=collection,
                    chunk_id=chunk.chunk_id,
                    embedding=chunk.embedding,
                    content=chunk.content,
                    metadata={
                        "doc_id": chunk.doc_id,
                        **chunk.metadata,
                    },
                )

        logger.info(
            "Added document %s with %d chunks for tenant %s",
            doc.doc_id, len(chunks), tenant_id
        )

        return chunks

    async def search(
        self,
        query: str,
        tenant_id: str | None = None,
        top_k: int | None = None,
    ) -> list[DocumentChunk]:
        """Search the knowledge base.

        Args:
            query: Search query
            tenant_id: Tenant ID for namespace isolation
            top_k: Number of results (defaults to config)

        Returns:
            List of matching chunks.
        """
        self._ensure_enabled()

        if tenant_id is None:
            raise ValueError("tenant_id is required")

        if top_k is None:
            top_k = self.config.retrieval.top_k

        self._ensure_tenant_namespace(tenant_id)

        # Embed query
        query_embedding = None
        if self._embedder:
            query_embedding = (await self._embedder.embed([query]))[0]

        # Search vector store
        collection = self._get_tenant_collection(tenant_id)
        results = []

        if self._vector_store and query_embedding:
            raw_results = await self._vector_store.search(
                collection=collection,
                query_embedding=query_embedding,
                top_k=top_k,
                threshold=self.config.retrieval.similarity_threshold,
            )

            for result in raw_results:
                chunk = DocumentChunk(
                    chunk_id=result.get("chunk_id", ""),
                    doc_id=result.get("metadata", {}).get("doc_id", ""),
                    content=result.get("content", ""),
                    metadata=result.get("metadata", {}),
                )
                results.append(chunk)

        return results

    def delete_document(self, doc_id: str, tenant_id: str) -> bool:
        """Delete a document and its chunks.

        Args:
            doc_id: Document ID to delete
            tenant_id: Tenant ID

        Returns:
            True if deleted, False otherwise.
        """
        self._ensure_enabled()

        collection = self._get_tenant_collection(tenant_id)
        if self._vector_store:
            # Delete all chunks with matching doc_id
            self._vector_store.delete(
                collection=collection,
                filter={"doc_id": doc_id},
            )
            return True

        return False

    def _format_context(self, chunks: list[DocumentChunk]) -> str:
        """Format chunks into context string for LLM."""
        if not chunks:
            return ""

        parts = []
        for chunk in chunks:
            parts.append(f"## {chunk.chunk_id}\n{chunk.content}")

        return "\n\n".join(parts)

    async def get_context_for_query(
        self,
        query: str,
        tenant_id: str | None = None,
    ) -> str:
        """Get formatted context for a query.

        Args:
            query: User query
            tenant_id: Tenant ID

        Returns:
            Formatted context string.
        """
        chunks = await self.search(query, tenant_id=tenant_id)
        return self._format_context(chunks)


# Mock implementations for development/testing
class MockVectorStore:
    """Mock vector store for development."""

    def __init__(self):
        self._collections: dict[str, dict] = {}

    def create_collection(self, name: str) -> None:
        if name not in self._collections:
            self._collections[name] = {}

    def upsert(
        self,
        collection: str,
        chunk_id: str,
        embedding: list[float] | None,
        content: str,
        metadata: dict,
    ) -> None:
        if collection not in self._collections:
            self._collections[collection] = {}

        self._collections[collection][chunk_id] = {
            "embedding": embedding,
            "content": content,
            "metadata": metadata,
        }

    def search(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int,
        threshold: float,
    ) -> list[dict]:
        if collection not in self._collections:
            return []

        # Mock search - return all items (in production, would do actual similarity)
        results = []
        for chunk_id, data in self._collections[collection].items():
            results.append({
                "chunk_id": chunk_id,
                "content": data["content"],
                "metadata": data["metadata"],
                "score": 0.9,
            })

        return results[:top_k]

    def delete(self, collection: str, filter: dict) -> None:
        if collection not in self._collections:
            return

        doc_id = filter.get("doc_id")
        if doc_id:
            to_delete = [
                cid for cid, data in self._collections[collection].items()
                if data.get("metadata", {}).get("doc_id") == doc_id
            ]
            for cid in to_delete:
                del self._collections[collection][cid]


class MockEmbedder:
    """Mock embedder for development."""

    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return mock embeddings."""
        import random
        random.seed(42)

        return [
            [random.random() for _ in range(self.dimensions)]
            for _ in texts
        ]
