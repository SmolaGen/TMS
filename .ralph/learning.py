"""
Модуль обучения Ralph (Learning System).
Анализирует успешные и неудачные паттерны выполнения задач.
"""

import os
import json
import re
from typing import Dict, List, Optional, Any

class LearningSystem:
    def __init__(self, patterns_file: str = None):
        if patterns_file is None:
            # Находим путь относительно текущего файла
            ralph_dir = os.path.dirname(os.path.abspath(__file__))
            patterns_file = os.path.join(ralph_dir, "memory", "patterns.json")
            
        self.patterns_file = patterns_file
        os.makedirs(os.path.dirname(patterns_file), exist_ok=True)
        self.patterns = self._load()

    def _load(self) -> Dict[str, List[Dict]]:
        if os.path.exists(self.patterns_file):
            try:
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"success": [], "failure": []}

    def _save(self):
        with open(self.patterns_file, 'w', encoding='utf-8') as f:
            json.dump(self.patterns, f, indent=2, ensure_ascii=False)

    def _categorize(self, task_text: str) -> str:
        """Простая категоризация задачи по ключевым словам."""
        text = task_text.lower()
        if any(w in text for w in ["fix", "bug", "error", "исправить", "ошибка"]):
            return "bugfix"
        if any(w in text for w in ["feat", "add", "implement", "добавить", "реализовать"]):
            return "feature"
        if any(w in text for w in ["test", "unittest", "pytest", "тест"]):
            return "testing"
        if any(w in text for w in ["refactor", "clean", "improve", "рефакторинг"]):
            return "refactoring"
        if any(w in text for w in ["doc", "readme", "comment", "документация"]):
            return "doc"
        return "general"

    def record_outcome(self, task_text: str, success: bool, approach: str = None, details: Any = None):
        """Записывает результат выполнения задачи или итерации."""
        category = "success" if success else "failure"
        pattern = {
            "task_type": self._categorize(task_text),
            "task_text": task_text[:100],
            "approach": approach,
            "details": details,
            "timestamp": re.sub(r'\..*', '', str(json.dumps(None))) # dummy timestamp or use datetime
        }
        
        # Ограничиваем количество паттернов для каждой категории
        self.patterns[category].append(pattern)
        if len(self.patterns[category]) > 100:
            self.patterns[category].pop(0)
            
        self._save()

    def suggest_approach(self, task_text: str) -> Optional[str]:
        """Предлагает подход на основе прошлых успешных задач того же типа."""
        task_type = self._categorize(task_text)
        relevant = [p for p in self.patterns['success'] if p['task_type'] == task_type]
        
        if not relevant:
            return None
            
        # Возвращаем последний успешный подход для этого типа
        return relevant[-1].get('approach')

    def get_anti_patterns(self, task_text: str) -> List[str]:
        """Возвращает список подходов, которые привели к неудаче."""
        task_type = self._categorize(task_text)
        failures = [p for p in self.patterns['failure'] if p['task_type'] == task_type]
        
        anti_patterns = []
        for f in failures:
            if f.get('approach') and f['approach'] not in anti_patterns:
                anti_patterns.append(f['approach'])
        return anti_patterns
