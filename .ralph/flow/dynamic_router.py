from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum

class TaskComplexity(Enum):
    TRIVIAL = 1    # Простые правки, документация
    SIMPLE = 2     # Одиночный файл
    MODERATE = 3   # Несколько файлов, понятная логика
    COMPLEX = 4    # Крупные системные изменения
    CRITICAL = 5   # Требует эскалации к архитектору

@dataclass
class RoutingDecision:
    skip_stages: List[str]    # Стадии для пропуска
    require_stages: List[str] # Обязательные стадии
    escalate: bool            # Требуется эскалация
    reason: str               # Причина решения

class DynamicRouter:
    """
    Динамически изменяет маршрут шагов выполнения задачи на основе анализа сложности.
    """
    
    COMPLEXITY_THRESHOLDS = {
        TaskComplexity.TRIVIAL: {"max_files": 1, "max_lines": 20},
        TaskComplexity.SIMPLE: {"max_files": 2, "max_lines": 100},
        TaskComplexity.MODERATE: {"max_files": 5, "max_lines": 300},
        TaskComplexity.COMPLEX: {"max_files": 10, "max_lines": 1000},
    }
    
    def __init__(self):
        self.complexity_history: List[Dict] = []
    
    def analyze_complexity(self, task_context: Dict) -> TaskComplexity:
        """
        Анализирует сложность на основе контекста (Researcher output).
        """
        files_count = len(task_context.get("files_affected", []))
        estimated_lines = task_context.get("estimated_lines", 0)
        has_breaking_changes = task_context.get("breaking_changes", False)
        
        if has_breaking_changes or files_count > 10:
            return TaskComplexity.CRITICAL
            
        for complexity in [TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE, TaskComplexity.MODERATE, TaskComplexity.COMPLEX]:
            thresholds = self.COMPLEXITY_THRESHOLDS[complexity]
            if files_count <= thresholds["max_files"] and estimated_lines <= thresholds["max_lines"]:
                return complexity
        
        return TaskComplexity.COMPLEX

    def route(self, task_context: Dict, initial_complexity: Optional[TaskComplexity] = None) -> RoutingDecision:
        current_complexity = self.analyze_complexity(task_context)
        
        # Эскалация, если сложность сильно выросла в процессе исследования
        if initial_complexity and current_complexity.value > initial_complexity.value + 1:
            return RoutingDecision(
                skip_stages=[],
                require_stages=["planning"],
                escalate=True,
                reason=f"Significant complexity growth detected: {initial_complexity.name} -> {current_complexity.name}"
            )
            
        if current_complexity == TaskComplexity.TRIVIAL:
            return RoutingDecision(
                skip_stages=["researching", "reviewing"],
                require_stages=["coding", "testing"],
                escalate=False,
                reason="Trivial task, skipping research and review"
            )
            
        if current_complexity == TaskComplexity.CRITICAL:
            return RoutingDecision(
                skip_stages=[],
                require_stages=["planning", "researching", "coding", "testing", "reviewing"],
                escalate=True,
                reason="Critical task requires full attention and Architect review"
            )
            
        return RoutingDecision(
            skip_stages=[],
            require_stages=["researching", "coding", "testing", "reviewing"],
            escalate=False,
            reason=f"Standard routing for {current_complexity.name} complexity"
        )
