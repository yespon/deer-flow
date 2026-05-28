"""Configuration models for Corporate Knowledge Base.

Provides configuration for vector store, chunking, embedding, and retrieval.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class VectorStoreConfig(BaseModel):
    """Configuration for vector store backend.

    Attributes:
        provider: Vector store provider (chroma, weaviate, pgvector)
        connection_string: Connection string for the vector store
        collection_name: Base collection name (tenant namespace will be appended)
    """

    provider: Literal["chroma", "weaviate", "pgvector", "milvus"] = Field(
        default="chroma",
        description="Vector store provider",
    )
    connection_string: str | None = Field(
        default=None,
        description="Connection string (provider-specific)",
    )
    collection_name: str = Field(
        default="deerflow_kb",
        description="Base collection name",
    )

    @field_validator("connection_string")
    @classmethod
    def validate_connection(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            return None
        return v


class EmbeddingConfig(BaseModel):
    """Configuration for text embedding.

    Attributes:
        provider: Embedding provider (openai, local, huggingface)
        model: Model name for embeddings
        dimensions: Embedding dimensions
        batch_size: Batch size for embedding requests
    """

    provider: Literal["openai", "local", "huggingface"] = Field(
        default="openai",
        description="Embedding provider",
    )
    model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name",
    )
    dimensions: int = Field(
        default=1536,
        ge=1,
        description="Embedding dimensions",
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Batch size for embedding requests",
    )


class ChunkingConfig(BaseModel):
    """Configuration for document chunking.

    Attributes:
        strategy: Chunking strategy (fixed_size, paragraphs, sentences)
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks in characters
        sentences_per_chunk: Number of sentences per chunk (for sentence strategy)
    """

    strategy: Literal["fixed_size", "paragraphs", "sentences"] = Field(
        default="fixed_size",
        description="Chunking strategy",
    )
    chunk_size: int = Field(
        default=500,
        ge=100,
        le=10000,
        description="Maximum chunk size in characters",
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        description="Overlap between chunks in characters",
    )
    sentences_per_chunk: int = Field(
        default=5,
        ge=1,
        description="Sentences per chunk (for sentence strategy)",
    )


class RetrievalConfig(BaseModel):
    """Configuration for knowledge retrieval.

    Attributes:
        top_k: Number of results to retrieve
        similarity_threshold: Minimum similarity score (0-1)
        hybrid_search: Whether to use hybrid search (keyword + vector)
        rerank: Whether to rerank results
        rerank_top_k: Number of results to rerank
    """

    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of results to retrieve",
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score",
    )
    hybrid_search: bool = Field(
        default=True,
        description="Use hybrid search (keyword + vector)",
    )
    rerank: bool = Field(
        default=True,
        description="Rerank results",
    )
    rerank_top_k: int = Field(
        default=20,
        ge=1,
        description="Number of results to rerank",
    )


class KnowledgeBaseConfig(BaseModel):
    """Top-level configuration for Corporate Knowledge Base.

    Attributes:
        enabled: Whether knowledge base is enabled
        vector_store: Vector store configuration
        embedding: Embedding configuration
        chunking: Chunking configuration
        retrieval: Retrieval configuration
    """

    enabled: bool = Field(
        default=False,
        description="Enable knowledge base",
    )
    vector_store: VectorStoreConfig = Field(
        default_factory=VectorStoreConfig,
        description="Vector store configuration",
    )
    embedding: EmbeddingConfig = Field(
        default_factory=EmbeddingConfig,
        description="Embedding configuration",
    )
    chunking: ChunkingConfig = Field(
        default_factory=ChunkingConfig,
        description="Chunking configuration",
    )
    retrieval: RetrievalConfig = Field(
        default_factory=RetrievalConfig,
        description="Retrieval configuration",
    )
