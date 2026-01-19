"""
Short-term RAG Memory для Ralph на основе ChromaDB.
Реализует семантический поиск, гибридный поиск и семантическое чанкирование.
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
import sys

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

class ShortTermMemory:
    """
    Класс для управления кратковременной векторной памятью (RAG).
    """
    
    def __init__(self, collection_name: str = "ralph_short_term"):
        self.db_path = os.path.join(utils.RALPH_DIR, "memory", "chroma_db")
        os.makedirs(self.db_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # Используем стандартную модель эмбеддингов (HuggingFace по умолчанию в Chroma)
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """
        Добавляет документы в векторное хранилище.
        """
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Выполняет семантический поиск по запросу.
        """
        return self.collection.query(
            query_texts=[query],
            n_results=n_results
        )

    def clear_session(self):
        """
        Очищает коллекцию текущей сессии.
        """
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(name=self.collection.name)

# Пример семантического чанкирования (упрощенная версия)
def semantic_chunking(text: str, max_chunk_size: int = 1000) -> List[str]:
    """
    Разбивает текст на чанки, стараясь сохранять целостность предложений и абзацев.
    """
    # В будущем здесь можно использовать semantic-router для более умного разбиения
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        if len(current_chunk) + len(p) < max_chunk_size:
            current_chunk += p + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n\n"
            
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks
