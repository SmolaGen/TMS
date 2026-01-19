from enum import Enum

class AgentRole(Enum):
    ARCHITECT = "architect"    # Планирование, декомпозиция
    RESEARCHER = "researcher"  # Сбор контекста, анализ
    DEVELOPER = "developer"    # Реализация кода
    TESTER = "tester"          # Тестирование, валидация
    REVIEWER = "reviewer"      # Code review, критика

class RoleCapabilities:
    CAPABILITIES = {
        AgentRole.ARCHITECT: ["decompose", "plan", "estimate"],
        AgentRole.RESEARCHER: ["search", "analyze", "gather_context"],
        AgentRole.DEVELOPER: ["write_code", "refactor", "fix_bugs"],
        AgentRole.TESTER: ["run_tests", "validate", "benchmark"],
        AgentRole.REVIEWER: ["review", "suggest", "approve"],
    }
