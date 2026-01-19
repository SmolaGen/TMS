"""
Многоуровневая система памяти для Ralph
"""

import os
import sys
import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils
from memory.short_term_memory import ShortTermMemory, semantic_chunking
from memory.reranker import ReRanker
from learning import LearningSystem


class LongTermMemory:
    """
    Долгосрочная память на основе SQLite.
    Хранит историю задач, итераций и решений между сессиями.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(utils.RALPH_DIR, "memory", "long_term.db")
        
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Инициализирует схему БД"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица задач
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_hash TEXT UNIQUE NOT NULL,
                task_text TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                total_iterations INTEGER DEFAULT 0
            )
        ''')
        
        # Таблица итераций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iterations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                iteration_num INTEGER NOT NULL,
                thoughts TEXT,
                plan TEXT,
                actions TEXT,
                success BOOLEAN NOT NULL,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        ''')
        
        # Таблица решений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                decision_text TEXT NOT NULL,
                context TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_hash ON tasks(task_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_created ON tasks(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_iteration_task ON iterations(task_id)')
        
        conn.commit()
        conn.close()
    
    def store_task(self, task_hash: str, task_text: str, status: str = "pending") -> int:
        """
        Сохраняет новую задачу.
        
        Returns:
            ID созданной задачи
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO tasks (task_hash, task_text, status)
                VALUES (?, ?, ?)
            ''', (task_hash, task_text, status))
            
            task_id = cursor.lastrowid
            conn.commit()
            return task_id
        except sqlite3.IntegrityError:
            # Задача уже существует, получаем её ID
            cursor.execute('SELECT id FROM tasks WHERE task_hash = ?', (task_hash,))
            task_id = cursor.fetchone()[0]
            return task_id
        finally:
            conn.close()
    
    def update_task_status(self, task_hash: str, status: str, completed_at: datetime = None):
        """Обновляет статус задачи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if completed_at:
            cursor.execute('''
                UPDATE tasks 
                SET status = ?, completed_at = ?
                WHERE task_hash = ?
            ''', (status, completed_at, task_hash))
        else:
            cursor.execute('''
                UPDATE tasks 
                SET status = ?
                WHERE task_hash = ?
            ''', (status, task_hash))
        
        conn.commit()
        conn.close()
    
    def get_task_status(self, task_hash: str) -> Optional[str]:
        """Возвращает текущий статус задачи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM tasks WHERE task_hash = ?", (task_hash,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def store_iteration(self, task_hash: str, iteration_num: int, 
                       thoughts: str, plan: str, actions: str, 
                       success: bool, error: str = None):
        """Сохраняет итерацию задачи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем task_id
        cursor.execute('SELECT id FROM tasks WHERE task_hash = ?', (task_hash,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return
        
        task_id = result[0]
        
        cursor.execute('''
            INSERT INTO iterations 
            (task_id, iteration_num, thoughts, plan, actions, success, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (task_id, iteration_num, thoughts, plan, actions, success, error))
        
        # Обновляем счетчик итераций
        cursor.execute('''
            UPDATE tasks 
            SET total_iterations = total_iterations + 1
            WHERE id = ?
        ''', (task_id,))
        
        conn.commit()
        conn.close()
    
    def store_decision(self, task_hash: str, decision_text: str, context: Dict = None):
        """Сохраняет важное решение"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM tasks WHERE task_hash = ?', (task_hash,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return
        
        task_id = result[0]
        context_json = json.dumps(context) if context else None
        
        cursor.execute('''
            INSERT INTO decisions (task_id, decision_text, context)
            VALUES (?, ?, ?)
        ''', (task_id, decision_text, context_json))
        
        conn.commit()
        conn.close()
    
    def get_task_history(self, task_hash: str) -> Optional[Dict]:
        """Получает полную историю задачи"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем задачу
        cursor.execute('SELECT * FROM tasks WHERE task_hash = ?', (task_hash,))
        task_row = cursor.fetchone()
        
        if not task_row:
            conn.close()
            return None
        
        task = dict(task_row)
        task_id = task['id']
        
        # Получаем итерации
        cursor.execute('''
            SELECT * FROM iterations 
            WHERE task_id = ? 
            ORDER BY iteration_num
        ''', (task_id,))
        
        iterations = [dict(row) for row in cursor.fetchall()]
        
        # Получаем решения
        cursor.execute('''
            SELECT * FROM decisions 
            WHERE task_id = ? 
            ORDER BY timestamp
        ''', (task_id,))
        
        decisions = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'task': task,
            'iterations': iterations,
            'decisions': decisions
        }
    
    def search_similar_tasks(self, task_text: str, limit: int = 5) -> List[Dict]:
        """
        Ищет похожие задачи (простой поиск по ключевым словам).
        Для более продвинутого поиска используйте RAG в ShortTermMemory.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Извлекаем ключевые слова (простая эвристика)
        keywords = [w.lower() for w in task_text.split() if len(w) > 3]
        
        # Ищем задачи с похожими словами
        cursor.execute('''
            SELECT * FROM tasks 
            WHERE status = 'done'
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        
        all_tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Простой scoring по совпадению слов
        scored_tasks = []
        for task in all_tasks:
            task_words = set(task['task_text'].lower().split())
            score = sum(1 for kw in keywords if kw in task_words)
            if score > 0:
                scored_tasks.append((score, task))
        
        # Сортируем по score и возвращаем топ
        scored_tasks.sort(reverse=True, key=lambda x: x[0])
        return [task for score, task in scored_tasks[:limit]]


class EntityMemory:
    """
    Граф зависимостей между файлами, функциями и классами.
    Использует простой JSON-граф (для NetworkX нужна установка библиотеки).
    """
    
    def __init__(self, graph_path: str = None):
        if graph_path is None:
            graph_path = os.path.join(utils.RALPH_DIR, "memory", "entity_graph.json")
        
        self.graph_path = graph_path
        os.makedirs(os.path.dirname(graph_path), exist_ok=True)
        
        self.graph = self._load_graph()
    
    def _load_graph(self) -> Dict:
        """Загружает граф из файла"""
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {'nodes': {}, 'edges': []}
    
    def _save_graph(self):
        """Сохраняет граф в файл"""
        with open(self.graph_path, 'w') as f:
            json.dump(self.graph, f, indent=2)
    
    def add_file(self, file_path: str, metadata: Dict = None):
        """Добавляет файл в граф"""
        if file_path not in self.graph['nodes']:
            self.graph['nodes'][file_path] = {
                'type': 'file',
                'metadata': metadata or {},
                'added_at': datetime.now().isoformat()
            }
            self._save_graph()
    
    def add_dependency(self, from_file: str, to_file: str, dep_type: str = "imports"):
        """Добавляет зависимость между файлами"""
        edge = {
            'from': from_file,
            'to': to_file,
            'type': dep_type
        }
        
        if edge not in self.graph['edges']:
            self.graph['edges'].append(edge)
            self._save_graph()
    
    def get_dependencies(self, file_path: str) -> List[str]:
        """Возвращает список файлов, от которых зависит данный файл"""
        return [
            edge['to'] 
            for edge in self.graph['edges'] 
            if edge['from'] == file_path
        ]
    
    def get_dependents(self, file_path: str) -> List[str]:
        """Возвращает список файлов, которые зависят от данного файла"""
        return [
            edge['from'] 
            for edge in self.graph['edges'] 
            if edge['to'] == file_path
        ]
    
    def find_affected_files(self, modified_file: str) -> List[str]:
        """
        Находит файлы, которые могут быть затронуты изменением данного файла.
        Возвращает прямых и косвенных зависимых.
        """
        affected = set()
        to_check = [modified_file]
        checked = set()
        
        while to_check:
            current = to_check.pop()
            if current in checked:
                continue
            
            checked.add(current)
            dependents = self.get_dependents(current)
            
            for dep in dependents:
                if dep not in affected:
                    affected.add(dep)
                    to_check.append(dep)
        
        return list(affected)
    
    def update_from_imports(self, file_path: str, imports: List[str]):
        """Обновляет граф на основе списка импортов"""
        self.add_file(file_path)
        
        # Удаляем старые зависимости этого файла
        self.graph['edges'] = [
            edge for edge in self.graph['edges']
            if edge['from'] != file_path
        ]
        
        # Добавляем новые
        for imp in imports:
            # Простая эвристика: если импорт локальный (содержит src/tests)
            if 'src' in imp or 'tests' in imp or imp.startswith('.'):
                # Преобразуем импорт в путь к файлу
                imp_path = imp.replace('.', '/') + '.py'
                self.add_dependency(file_path, imp_path, "imports")
        
        self._save_graph()


class MemoryManager:
    """
    Фасад для работы с многоуровневой памятью.
    Объединяет Long-term Memory и Entity Memory.
    """
    
    def __init__(self):
        self.long_term = LongTermMemory()
        self.entity = EntityMemory()
        self.short_term = ShortTermMemory()
        self.reranker = ReRanker()
        self.learning = LearningSystem()
    
    def _rrf(self, results_list: List[List[Dict]], k: int = 60) -> List[Dict]:
        """
        Reciprocal Rank Fusion для объединения результатов разных поисков.
        """
        scores = {}
        content_map = {}
        
        for results in results_list:
            for rank, item in enumerate(results):
                content = item.get('content') or item.get('task_text')
                if not content: continue
                
                if content not in scores:
                    scores[content] = 0
                    content_map[content] = item
                
                scores[content] += 1.0 / (k + rank + 1)
        
        # Сортируем по финальному счетчику
        sorted_content = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [content_map[c] for c in sorted_content]

    def remember(self, task_hash: str, task_text: str, iteration_num: int,
                 thoughts: str, plan: str, actions: str, success: bool, 
                 error: str = None, modified_files: List[str] = None):
        """
        Сохраняет результат итерации во все уровни памяти.
        """
        # Сохраняем в Long-term Memory
        if iteration_num == 1:
            self.long_term.store_task(task_hash, task_text, status="in_progress")
        
        self.long_term.store_iteration(
            task_hash, iteration_num, thoughts, plan, actions, success, error
        )
        
        # Записываем опыт в систему обучения
        self.learning.record_outcome(task_text, success, plan, error)
        
        # Сохраняем в Short-term Memory (RAG)
        context_text = f"Task: {task_text}\nThoughts: {thoughts}\nPlan: {plan}\nActions: {actions}"
        if error:
            context_text += f"\nError: {error}"
            
        chunks = semantic_chunking(context_text)
        ids = [f"{task_hash}_{iteration_num}_{i}" for i in range(len(chunks))]
        metadatas = [{"task_hash": task_hash, "iteration": iteration_num, "success": success} for _ in chunks]
        
        self.short_term.add_documents(documents=chunks, metadatas=metadatas, ids=ids)
        
        # Обновляем Entity Memory для измененных файлов
        if modified_files:
            for file_path in modified_files:
                self.entity.add_file(file_path)
    
    def recall(self, task_text: str, max_items: int = 5) -> str:
        """
        Гибридный RAG-поиск по истории задач для получения контекста.
        """
        # 1. Поиск в Long-term (SQLite - Keyword-ish)
        lt_results = self.long_term.search_similar_tasks(task_text, limit=10)
        
        # 2. Поиск в Short-term (ChromaDB - Semantic)
        st_search = self.short_term.search(task_text, n_results=10)
        st_results = []
        if st_search and st_search['documents']:
            for i in range(len(st_search['documents'][0])):
                st_results.append({
                    'content': st_search['documents'][0][i],
                    'metadata': st_search['metadatas'][0][i]
                })
        
        # 3. Объединение через RRF
        combined = self._rrf([lt_results, st_results])
        
        # 4. Реранкинг через FlashRank
        if combined:
            rerank_docs = []
            for item in combined:
                content = item.get('content') or item.get('task_text')
                rerank_docs.append({"id": str(hash(content)), "text": content, "metadata": item.get('metadata', {})})
            
            reranked = self.reranker.rerank(task_text, rerank_docs)
            top_results = reranked[:max_items]
        else:
            top_results = []
        
        if not top_results:
            return "No similar tasks found in memory."
        
        context = "## Relevant Context from Memory (Hybrid RAG)\n\n"
        for i, res in enumerate(top_results, 1):
            context += f"### {i}. Source: {res.get('metadata', {}).get('task_hash', 'Unknown')}\n"
            context += f"{res['text']}\n\n"
        
        # Добавляем советы от системы обучения
        suggestion = self.learning.suggest_approach(task_text)
        if suggestion:
            context += f"### 💡 Suggested Approach from previous successes:\n{suggestion}\n\n"
            
        anti_patterns = self.learning.get_anti_patterns(task_text)
        if anti_patterns:
            context += "### ⚠️ Avoid these patterns (failed before):\n"
            for ap in anti_patterns[:3]:
                context += f"- {ap}\n"
            context += "\n"
            
        return context
    
    def mark_task_complete(self, task_hash: str):
        """Отмечает задачу как выполненную"""
        self.long_term.update_task_status(task_hash, "done", datetime.now())
    
    def mark_task_failed(self, task_hash: str):
        """Отмечает задачу как проваленную"""
        self.long_term.update_task_status(task_hash, "failed", datetime.now())
    
    def get_affected_files(self, modified_file: str) -> List[str]:
        """Возвращает файлы, которые могут быть затронуты изменением"""
        return self.entity.find_affected_files(modified_file)
