#!/usr/bin/env python3
"""
RAG Knowledge Base — Layer 3
Stores and retrieves historical analysis results via ChromaDB
"""

import os, json, logging
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))
logger = logging.getLogger(__name__)


class RAGKnowledge:
    """Vector knowledge base for historical analysis retrieval"""

    def __init__(self, collection_name: str = "hedge_fund_reviews"):
        import chromadb
        self.client = chromadb.HttpClient(
            host=os.getenv("CHROMA_HOST", "localhost"),
            port=int(os.getenv("CHROMA_PORT", "8000")),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def store_analysis(self, analysis_id: str, text: str, metadata: dict):
        """Store an analysis result into vector DB"""
        try:
            self.collection.upsert(
                ids=[analysis_id],
                documents=[text],
                metadatas=[metadata]
            )
            logger.info(f"Stored to RAG: {analysis_id}")
            return True
        except Exception as e:
            logger.error(f"RAG store failed: {e}")
            return False

    def store_review(self, review_id: str, review_text: str,
                     symbol: str, date: str, correct: bool):
        """Store a review record"""
        return self.store_analysis(review_id, review_text, {
            "type": "review",
            "symbol": symbol,
            "date": date,
            "correct": str(correct),
        })

    def store_daily_report(self, date: str, report_text: str, market: str = "crypto"):
        """Store a daily report"""
        return self.store_analysis(f"report_{date}", report_text, {
            "type": "daily_report",
            "date": date,
            "market": market,
        })

    def search_similar(self, query: str, n_results: int = 5,
                       filter_dict: Optional[dict] = None) -> list[dict]:
        """Search for similar historical analyses"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_dict,
            )
            docs = []
            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    docs.append({
                        "id": doc_id,
                        "text": results["documents"][0][i][:500],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if results.get("distances") else None,
                    })
            return docs
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []

    def search_by_symbol(self, symbol: str, limit: int = 10) -> list[dict]:
        """Search analyses for a specific symbol"""
        try:
            results = self.collection.get(
                where={"symbol": symbol},
                limit=limit,
            )
            return [{"id": results["ids"][i], "text": results["documents"][i][:500],
                     "metadata": results["metadatas"][i]}
                    for i in range(len(results["ids"]))] if results["ids"] else []
        except Exception as e:
            logger.error(f"RAG symbol search failed: {e}")
            return []

    def delete_old(self, before_date: str):
        """Delete records older than date (YYYY-MM-DD)"""
        try:
            self.collection.delete(where={"date": {"$lt": before_date}})
            logger.info(f"Deleted RAG records before {before_date}")
        except Exception as e:
            logger.error(f"RAG delete failed: {e}")
