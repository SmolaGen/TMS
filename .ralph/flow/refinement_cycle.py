from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

class ReviewVerdict(Enum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"

@dataclass
class ReviewResult:
    verdict: ReviewVerdict
    comments: List[str]
    issues_found: List[Dict] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)
    confidence_score: float = 0.0  # 0.0 - 1.0

class RefinementCycle:
    """
    Цикл итеративной доработки с критикой (Review Cycle).
    """
    
    MAX_REFINEMENT_ITERATIONS = 3
    APPROVAL_THRESHOLD = 0.85
    
    def __init__(self, project_standards: Dict = None):
        self.project_standards = project_standards or {}
        self.iteration_count = 0
        self.history: List[ReviewResult] = []
    
    def review(self, task_result: Dict, code_changes: List[str], iteration: int) -> ReviewResult:
        """
        Выполняет ревью результатов задачи.
        """
        self.iteration_count = iteration
        issues = []
        comments = []
        
        # В реальной реализации здесь будет вызов LLM Reviewer-а
        # Пока используем логику на основе входных данных task_result
        
        success = task_result.get("success", False)
        errors = task_result.get("error")
        
        if errors:
            issues.append({"type": "runtime_error", "description": str(errors)})
            comments.append(f"Found runtime errors: {errors}")
        
        confidence = 0.9 if success and not errors else 0.3
        
        if self.iteration_count >= self.MAX_REFINEMENT_ITERATIONS:
            verdict = ReviewVerdict.REJECT
            comments.append("Maximum refinement iterations reached.")
        elif confidence >= self.APPROVAL_THRESHOLD:
            verdict = ReviewVerdict.APPROVE
            comments.append("Code meets standards.")
        else:
            verdict = ReviewVerdict.REQUEST_CHANGES
            comments.append("Changes requested to meet quality standards.")
            
        result = ReviewResult(
            verdict=verdict,
            comments=comments,
            issues_found=issues,
            suggested_fixes=[f"Address: {i['description']}" for i in issues],
            confidence_score=confidence
        )
        
        self.history.append(result)
        return result

    def should_continue(self) -> bool:
        if not self.history:
            return True
        last = self.history[-1]
        return last.verdict == ReviewVerdict.REQUEST_CHANGES and self.iteration_count < self.MAX_REFINEMENT_ITERATIONS
