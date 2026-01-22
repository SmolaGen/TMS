from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from .task_stage import TaskStage
from agents.roles import AgentRole

@dataclass
class HandoffResult:
    success: bool
    next_role: Optional[AgentRole]
    next_stage: TaskStage
    context: Dict  # Контекст для передачи следующему агенту
    rollback_to: Optional[TaskStage] = None

class HandoffManager:
    """
    Управляет передачей задач между ролями по DAG (Directed Acyclic Graph).
    """
    
    # Граф переходов (DAG): (current_stage, trigger) -> (next_stage, next_role)
    TRANSITIONS = {
        (TaskStage.PENDING, "start"): (TaskStage.PLANNING, AgentRole.ARCHITECT),
        
        # Architect transitions
        (TaskStage.PLANNING, "success"): (TaskStage.RESEARCHING, AgentRole.RESEARCHER),
        (TaskStage.PLANNING, "simple"): (TaskStage.CODING, AgentRole.DEVELOPER),
        (TaskStage.PLANNING, "failure"): (TaskStage.BLOCKED, None),
        
        # Researcher transitions
        (TaskStage.RESEARCHING, "success"): (TaskStage.CODING, AgentRole.DEVELOPER),
        (TaskStage.RESEARCHING, "escalate"): (TaskStage.PLANNING, AgentRole.ARCHITECT),
        (TaskStage.RESEARCHING, "failure"): (TaskStage.PLANNING, AgentRole.ARCHITECT),
        
        # Developer transitions
        (TaskStage.CODING, "success"): (TaskStage.TESTING, AgentRole.TESTER),
        (TaskStage.CODING, "failure"): (TaskStage.RESEARCHING, AgentRole.RESEARCHER),
        
        # Tester transitions
        (TaskStage.TESTING, "success"): (TaskStage.REVIEWING, AgentRole.REVIEWER),
        (TaskStage.TESTING, "failure"): (TaskStage.CODING, AgentRole.DEVELOPER),
        
        # Reviewer transitions
        (TaskStage.REVIEWING, "approve"): (TaskStage.DONE, None),
        (TaskStage.REVIEWING, "reject"): (TaskStage.CODING, AgentRole.DEVELOPER),
    }
    
    def handoff(self, current_stage: TaskStage, trigger: str, context: Dict) -> HandoffResult:
        """
        Выполняет переход к следующей стадии на основе текущего состояния и триггера.
        """
        key = (current_stage, trigger)
        
        if key not in self.TRANSITIONS:
            return HandoffResult(
                success=False,
                next_role=None,
                next_stage=TaskStage.BLOCKED,
                context={"error": f"No transition defined for stage={current_stage.value}, trigger={trigger}"}
            )
        
        next_stage, next_role = self.TRANSITIONS[key]
        
        is_rollback = trigger in ["failure", "reject"]
        rollback_to = current_stage if is_rollback else None
        
        return HandoffResult(
            success=True,
            next_role=next_role,
            next_stage=next_stage,
            context=context,
            rollback_to=rollback_to
        )

    @staticmethod
    def get_role_for_stage(stage: TaskStage) -> Optional[AgentRole]:
        """Возвращает роль по умолчанию для заданной стадии."""
        return {
            TaskStage.PLANNING: AgentRole.ARCHITECT,
            TaskStage.RESEARCHING: AgentRole.RESEARCHER,
            TaskStage.CODING: AgentRole.DEVELOPER,
            TaskStage.TESTING: AgentRole.TESTER,
            TaskStage.REVIEWING: AgentRole.REVIEWER,
        }.get(stage)
