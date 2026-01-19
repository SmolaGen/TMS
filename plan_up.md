# 🚀 Implementation Plan: Улучшение Ralph на основе CrewAI

**Дата:** 2026-01-19  
**Цель:** Внедрить ключевые архитектурные паттерны из CrewAI

---

## 📋 Контекст

На основе анализа CrewAI выявлены 5 ключевых улучшений:
1. Tool Registry — модульная система инструментов
2. Memory System — многоуровневая память
3. Flow Manager — управление зависимостями задач
4. Specialized Agents — роли Researcher, Tester, Reviewer
5. Learning System — обучаемость

---

## 🎯 Затрагиваемые файлы

### Новые файлы:
- [NEW] [tools/base.py](file:///Users/alsmolentsev/tms_new/.ralph/tools/base.py)
- [NEW] [tools/registry.py](file:///Users/alsmolentsev/tms_new/.ralph/tools/registry.py)
- [NEW] [tools/file_tools.py](file:///Users/alsmolentsev/tms_new/.ralph/tools/file_tools.py)
- [NEW] [memory_manager.py](file:///Users/alsmolentsev/tms_new/.ralph/memory_manager.py)
- [NEW] [flow_manager.py](file:///Users/alsmolentsev/tms_new/.ralph/flow_manager.py)
- [NEW] [learning.py](file:///Users/alsmolentsev/tms_new/.ralph/learning.py)

### Модифицируемые:
- [MODIFY] [ralph.py](file:///Users/alsmolentsev/tms_new/.ralph/ralph.py)
- [MODIFY] [ralph_config.json](file:///Users/alsmolentsev/tms_new/.ralph/ralph_config.json)

---

## 🔨 Фаза 1: Tool Registry

### Шаг 1.1: Базовая инфраструктура
**Файл:** `tools/base.py`

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel

class ToolOutput(BaseModel):
    success: bool
    message: str
    data: dict = None

class Tool(ABC):
    name: str
    description: str
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolOutput:
        pass
```

### Шаг 1.2: Registry
**Файл:** `tools/registry.py`

```python
class ToolRegistry:
    def __init__(self):
        self._tools = {}
    
    def register(self, tool):
        self._tools[tool.name] = tool
    
    def get(self, name):
        return self._tools.get(name)
```

### Шаг 1.3: Конкретные инструменты
**Файл:** `tools/file_tools.py`

```python
from .base import Tool, ToolOutput
import utils

class WriteFileTool(Tool):
    name = "write_file"
    description = "Записывает файл с валидацией"
    
    def execute(self, path, content):
        ok, msg = utils.safe_write(path, content)
        return ToolOutput(success=ok, message=msg)
```

---

## 🔨 Фаза 2: Memory System

### Шаг 2.1: Long-term Memory
**Файл:** `memory_manager.py`

```python
import sqlite3

class LongTermMemory:
    def __init__(self, db_path=".ralph/memory/long_term.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_history (
                id INTEGER PRIMARY KEY,
                task_id TEXT,
                task_text TEXT,
                status TEXT,
                tools_used TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    def store(self, task_id, result):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO task_history (task_id, task_text, status, tools_used) VALUES (?, ?, ?, ?)",
            (task_id, result['text'], result['status'], ','.join(result.get('tools', [])))
        )
        conn.commit()
        conn.close()
```

### Шаг 2.2: Entity Memory
**Файл:** `memory_manager.py` (дополнение)

```python
import networkx as nx
import json

class EntityMemory:
    def __init__(self, graph_path=".ralph/memory/entity_graph.json"):
        self.graph_path = graph_path
        self.graph = nx.DiGraph()
        self._load()
    
    def add_dependency(self, from_file, to_file):
        self.graph.add_edge(from_file, to_file)
        self._save()
    
    def get_dependencies(self, filepath):
        return list(self.graph.successors(filepath))
```

---

## 🔨 Фаза 3: Flow Manager

**Файл:** `flow_manager.py`

```python
import re
from dataclasses import dataclass

@dataclass
class Task:
    id: int
    text: str
    status: str
    depends_on: list
    line_index: int

class FlowManager:
    def __init__(self, prd_file):
        self.prd_file = prd_file
        self.tasks = []
        self._parse_prd()
    
    def get_next_task(self):
        for task in self.tasks:
            if task.status == 'pending' and self._deps_met(task):
                return task
        return None
    
    def _deps_met(self, task):
        for dep_id in task.depends_on:
            dep = next((t for t in self.tasks if t.id == dep_id), None)
            if not dep or dep.status != 'done':
                return False
        return True
```

---

## 🔨 Фаза 4: Learning System

**Файл:** `learning.py`

```python
import json

class LearningSystem:
    def __init__(self, patterns_file=".ralph/memory/patterns.json"):
        self.patterns_file = patterns_file
        self.patterns = self._load()
    
    def record_outcome(self, task, success):
        pattern = {
            'type': self._categorize(task['text']),
            'approach': task.get('approach'),
            'success': success
        }
        category = 'success' if success else 'failure'
        self.patterns[category].append(pattern)
        self._save()
    
    def suggest_approach(self, task_text):
        task_type = self._categorize(task_text)
        relevant = [p for p in self.patterns['success'] if p['type'] == task_type]
        return relevant[0] if relevant else None
```

---

## ✅ Критерии завершения

- [ ] Tool Registry работает с 5+ инструментами
- [ ] LongTermMemory сохраняет историю в SQLite
- [ ] EntityMemory строит граф зависимостей
- [ ] FlowManager управляет порядком задач
- [ ] LearningSystem предлагает подходы

---

## 📊 План внедрения

1. **Неделя 1:** Tool Registry
2. **Неделя 2:** Long-term Memory
3. **Неделя 3:** Entity Memory + Flow Manager
4. **Неделя 4:** Learning System
5. **Неделя 5:** Тестирование и оптимизация
