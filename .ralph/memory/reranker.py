"""
Модуль реранкинга для Ralph на основе FlashRank.
"""

from flashrank import Ranker, RerankRequest
from typing import List, Dict, Any

class ReRanker:
    def __init__(self, model_name: str = "ms-marco-TinyBERT-L-2-v2"):
        # TinyBERT — быстрая и легковесная модель для реранкинга
        self.ranker = Ranker(model_name=model_name, cache_dir="/tmp/flashrank_models")

    def rerank(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Переранжирует документы на основе релевантности запросу.
        """
        if not documents:
            return []
            
        rerank_request = RerankRequest(query=query, passages=documents)
        results = self.ranker.rerank(rerank_request)
        return results
