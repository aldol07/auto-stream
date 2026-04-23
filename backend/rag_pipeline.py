"""
RAG Pipeline for AutoStream Agent
Loads knowledge base, creates embeddings, and retrieves relevant context.
Uses FAISS for vector storage and sentence-transformers for embeddings.
"""

import os
import re
from pathlib import Path

# ─────────────────────────────────────────────
# KNOWLEDGE BASE LOADER
# ─────────────────────────────────────────────

def load_knowledge_base(filepath: str = None) -> str:
    """Load the markdown knowledge base file."""
    if filepath is None:
        filepath = Path(__file__).parent / "knowledge_base.md"
    
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    """
    Split text into overlapping chunks for better retrieval.
    Splits on section boundaries first, then by size.
    """
    # Split by markdown headers first
    sections = re.split(r'\n(?=#{1,3} )', text)
    
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        # If section fits in one chunk, keep it whole
        if len(section) <= chunk_size:
            chunks.append(section)
        else:
            # Sliding window chunking
            words = section.split()
            current_chunk = []
            current_len = 0
            
            for word in words:
                current_chunk.append(word)
                current_len += len(word) + 1
                
                if current_len >= chunk_size:
                    chunks.append(" ".join(current_chunk))
                    # Keep last overlap characters
                    overlap_words = []
                    overlap_len = 0
                    for w in reversed(current_chunk):
                        overlap_len += len(w) + 1
                        overlap_words.insert(0, w)
                        if overlap_len >= overlap:
                            break
                    current_chunk = overlap_words
                    current_len = overlap_len
            
            if current_chunk:
                chunks.append(" ".join(current_chunk))
    
    return [c for c in chunks if len(c.strip()) > 20]


# ─────────────────────────────────────────────
# VECTOR STORE (FAISS)
# ─────────────────────────────────────────────

_vector_store = None
_chunks = None


def _build_vector_store():
    """Build FAISS index from knowledge base chunks."""
    global _vector_store, _chunks
    
    if _vector_store is not None:
        return _vector_store, _chunks
    
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_core.documents import Document

        print("📚 Loading knowledge base...")
        kb_text = load_knowledge_base()
        raw_chunks = chunk_text(kb_text)
        
        _chunks = raw_chunks
        docs = [Document(page_content=chunk, metadata={"index": i}) 
                for i, chunk in enumerate(raw_chunks)]
        
        print("🔢 Building embeddings (first run may take ~30 seconds)...")
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        
        _vector_store = FAISS.from_documents(docs, embeddings)
        print("✅ Knowledge base ready!")
        return _vector_store, _chunks
    
    except ImportError:
        print("⚠️  FAISS/HuggingFace not available, using keyword search fallback.")
        kb_text = load_knowledge_base()
        _chunks = chunk_text(kb_text)
        return None, _chunks


def _keyword_search(query: str, chunks: list[str], top_k: int = 3) -> list[str]:
    """Simple keyword-based search fallback."""
    query_words = set(query.lower().split())
    
    scored = []
    for chunk in chunks:
        chunk_words = set(chunk.lower().split())
        score = len(query_words & chunk_words)
        scored.append((score, chunk))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k] if _ > 0]


# ─────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────

def retrieve_context(query: str, top_k: int = 3) -> str:
    """
    Retrieve the most relevant chunks from the knowledge base.
    
    Args:
        query: User's question
        top_k: Number of chunks to retrieve
    
    Returns:
        Concatenated relevant context string
    """
    vector_store, chunks = _build_vector_store()
    
    if vector_store is not None:
        # Use FAISS semantic search
        results = vector_store.similarity_search(query, k=top_k)
        retrieved = [doc.page_content for doc in results]
    else:
        # Fallback to keyword search
        retrieved = _keyword_search(query, chunks, top_k)
    
    if not retrieved:
        return load_knowledge_base()  # Return full KB as last resort
    
    return "\n\n---\n\n".join(retrieved)


# ─────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    test_queries = [
        "What is the price of the Pro plan?",
        "Does AutoStream support 4K video?",
        "What is your refund policy?",
        "Is 24/7 support available on Basic plan?"
    ]
    
    for q in test_queries:
        print(f"\nQuery: {q}")
        ctx = retrieve_context(q)
        print(f"Context:\n{ctx[:300]}...")
        print("-" * 50)
