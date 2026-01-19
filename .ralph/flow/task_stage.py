from enum import Enum
from dataclasses import dataclass
from typing import Optional

class TaskStage(Enum):
    PENDING = "pending"        # Ожидает выполнения
    PLANNING = "planning"      # Architect работает
    RESEARCHING = "researching"# Researcher собирает контекст
    CODING = "coding"          # Developer пишет код
    TESTING = "testing"        # Tester валидирует
    REVIEWING = "reviewing"    # Reviewer проверяет
    DONE = "done"              # Завершена
    BLOCKED = "blocked"        # Заблокирована
    ESCALATED = "escalated"    # Требует эскалации

@dataclass
class StageTransition:
    from_stage: TaskStage
    to_stage: TaskStage
    trigger: str  # "success", "failure", "escalate", "rollback"
    role: Optional["AgentRole"]
