"""
Flow Manager для управления зависимостями между задачами
"""

import os
import sys
import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils


from .task_stage import TaskStage
from .handoff_manager import HandoffManager, HandoffResult
from .refinement_cycle import RefinementCycle
from .dynamic_router import DynamicRouter, TaskComplexity
from agents.roles import AgentRole


@dataclass
class Task:
    """Представление задачи из PRD.md"""
    index: int  # Индекс строки в файле
    task_id: Optional[int]  # ID задачи (#1, #2, etc.)
    text: str  # Текст задачи
    status: str  # 'pending' ([ ]), 'done' ([x]), 'in_progress' ([/])
    depends_on: List[int] = field(default_factory=list)  # Список ID задач-зависимостей
    parallel_with: List[int] = field(default_factory=list)  # Список ID параллельных задач
    
    # DAG Flow Manager fields
    stage: TaskStage = TaskStage.PENDING
    current_role: Optional[AgentRole] = None
    complexity: Optional[TaskComplexity] = None
    refinement_count: int = 0
    rollback_history: List[TaskStage] = field(default_factory=list)
    
    def is_done(self) -> bool:
        return self.status == 'done' or self.stage == TaskStage.DONE
    
    def is_pending(self) -> bool:
        """Задача считается доступной, если она не завершена и не заблокирована."""
        return self.status in ['pending', 'in_progress'] and self.stage not in [TaskStage.DONE, TaskStage.BLOCKED]


class FlowManager:
    """
    Управляет зависимостями между задачами и определяет порядок выполнения.
    Теперь поддерживает DAG-архитектуру с передачей эстафеты (Handoff).
    """
    
    def __init__(self, prd_file: str):
        self.prd_file = prd_file
        self.tasks: Dict[int, Task] = {}
        self.task_by_index: Dict[int, Task] = {}
        
        # DAG components
        self.handoff = HandoffManager()
        self.refinement = RefinementCycle()
        self.router = DynamicRouter()
        
        if os.path.exists(prd_file):
            self._parse_prd()
    
    def _parse_prd(self):
        """Парсит PRD.md и извлекает задачи с зависимостями"""
        with open(self.prd_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Паттерны для парсинга
        # Поддержка #1 Задача (depends: #2) и стадий (stage: coding)
        task_pattern = r'^(\s*)-\s*\[([ x/])\]\s+(?:#(\d+)\s+)?(.+)$'
        depends_pattern = r'\(depends:\s*#?([\d,\s]+)\)'
        parallel_pattern = r'\(parallel:\s*#?([\d,\s]+)\)'
        stage_pattern = r'\(stage:\s*(\w+)\)'
        
        for line_index, line in enumerate(lines):
            match = re.match(task_pattern, line)
            if not match:
                continue
            
            indent, status_char, task_id_str, task_text = match.groups()
            
            # Определяем статус
            status_map = {' ': 'pending', 'x': 'done', '/': 'in_progress'}
            status = status_map.get(status_char, 'pending')
            
            # Извлекаем ID задачи
            task_id = int(task_id_str) if task_id_str else None
            
            # Извлекаем зависимости
            depends_on = []
            parallel_with = []
            
            depends_match = re.search(depends_pattern, task_text)
            if depends_match:
                dep_ids = [int(x.strip().replace('#', '')) for x in depends_match.group(1).split(',')]
                depends_on = dep_ids
                task_text = re.sub(depends_pattern, '', task_text).strip()
            
            parallel_match = re.search(parallel_pattern, task_text)
            if parallel_match:
                par_ids = [int(x.strip().replace('#', '')) for x in parallel_match.group(1).split(',')]
                parallel_with = par_ids
                task_text = re.sub(parallel_pattern, '', task_text).strip()

            # Извлекаем стадию, если она есть в тексте (для персистентности)
            stage = TaskStage.PENDING
            if status == 'done':
                stage = TaskStage.DONE
            
            stage_match = re.search(stage_pattern, task_text)
            if stage_match:
                try:
                    stage = TaskStage(stage_match.group(1).lower())
                    task_text = re.sub(stage_pattern, '', task_text).strip()
                except ValueError:
                    pass
            
            # Создаем объект задачи
            task = Task(
                index=line_index,
                task_id=task_id,
                text=task_text,
                status=status,
                depends_on=depends_on,
                parallel_with=parallel_with,
                stage=stage,
                current_role=HandoffManager.get_role_for_stage(stage)
            )
            
            if task_id is not None:
                self.tasks[task_id] = task
            
            self.task_by_index[line_index] = task
    
    def get_next_task(self) -> Optional[Tuple[int, str]]:
        """
        Возвращает следующую задачу для выполнения.
        Учитывает зависимости и текущую стадию DAG.
        """
        for task in self.task_by_index.values():
            if task.is_pending() and self.dependencies_met(task):
                # Если задача только началась, инициализируем её стадию в DAG
                if task.stage == TaskStage.PENDING:
                    handoff = self.handoff.handoff(TaskStage.PENDING, "start", {})
                    task.stage = handoff.next_stage
                    task.current_role = handoff.next_role
                
                # Защита: если роль почему-то не задана, восстанавливаем её по стадии
                if task.current_role is None and task.stage != TaskStage.DONE:
                    task.current_role = HandoffManager.get_role_for_stage(task.stage)
                
                return task.index, task.text
        
        return None, None

    def process_stage_result(self, line_index: int, success: bool, context: Dict = None) -> HandoffResult:
        """
        Обрабатывает результат текущей стадии задачи и переводит её на следующую.
        """
        task = self.task_by_index.get(line_index)
        if not task:
            return HandoffResult(False, None, TaskStage.BLOCKED, {"error": "Task not found"})

        # Логика триггеров
        trigger = "success" if success else "failure"
        
        # Специальная обработка для Reviewer
        if task.stage == TaskStage.REVIEWING:
            review_res = self.refinement.review(context or {}, [], task.refinement_count)
            if review_res.verdict.value == "approve":
                trigger = "approve"
            else:
                trigger = "reject"
                task.refinement_count += 1
        
        # Передача эстафеты (Handoff)
        handoff_res = self.handoff.handoff(task.stage, trigger, context or {})
        
        if handoff_res.success:
            task.stage = handoff_res.next_stage
            task.current_role = handoff_res.next_role
            if handoff_res.rollback_to:
                task.rollback_history.append(handoff_res.rollback_to)
            
            if task.stage == TaskStage.DONE:
                task.status = 'done'
                
            self.save_prd()
                
        return handoff_res
    
    def save_prd(self):
        """Сохраняет текущее состояние стадий задач обратно в PRD.md"""
        if not os.path.exists(self.prd_file):
            return
            
        with open(self.prd_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for index, task in self.task_by_index.items():
            if index >= len(lines):
                continue
                
            line = lines[index]
            # Обновляем статус [ ] -> [x] или [/]
            status_char = 'x' if task.status == 'done' else '/' if task.stage != TaskStage.PENDING and task.stage != TaskStage.DONE else ' '
            line = re.sub(r'\[[ x/]\]', f'[{status_char}]', line, count=1)
            
            # Обновляем тег стадии (stage: ...)
            stage_tag = f"(stage: {task.stage.value})"
            if "(stage:" in line:
                line = re.sub(r'\(stage:\s*\w+\)', stage_tag, line)
            elif task.stage != TaskStage.PENDING:
                # Добавляем тег в конец текста перед новой строкой
                line = line.rstrip() + " " + stage_tag + "\n"
            
            lines[index] = line
            
        with open(self.prd_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    def dependencies_met(self, task: Task) -> bool:
        """Проверяет, выполнены ли все зависимости задачи."""
        if not task.depends_on:
            return True
        for dep_id in task.depends_on:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or not dep_task.is_done():
                return False
        return True
    
    def check_circular_dependencies(self) -> Optional[List[int]]:
        """Проверяет наличие циклических зависимостей."""
        visited = set()
        rec_stack = set()
        def has_cycle(task_id: int, path: List[int]) -> Optional[List[int]]:
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)
            task = self.tasks.get(task_id)
            if not task:
                rec_stack.remove(task_id)
                return None
            for dep_id in task.depends_on:
                if dep_id not in visited:
                    cycle = has_cycle(dep_id, path[:])
                    if cycle: return cycle
                elif dep_id in rec_stack:
                    cycle_start = path.index(dep_id)
                    return path[cycle_start:] + [dep_id]
            rec_stack.remove(task_id)
            return None
        for task_id in self.tasks.keys():
            if task_id not in visited:
                cycle = has_cycle(task_id, [])
                if cycle: return cycle
        return None
    
    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        return self.tasks.get(task_id)
    
    def get_task_by_index(self, line_index: int) -> Optional[Task]:
        return self.task_by_index.get(line_index)
    
    def get_execution_order(self) -> List[int]:
        """Возвращает оптимальный порядок выполнения задач (алгоритм Кана)."""
        cycle = self.check_circular_dependencies()
        if cycle:
            return []
        in_degree = {task_id: len(task.depends_on) for task_id, task in self.tasks.items()}
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []
        while queue:
            current = queue.pop(0)
            result.append(current)
            for task_id, task in self.tasks.items():
                if current in task.depends_on:
                    in_degree[task_id] -= 1
                    if in_degree[task_id] == 0:
                        queue.append(task_id)
        return result
    
    def reload(self):
        """Перезагружает PRD.md"""
        self.tasks.clear()
        self.task_by_index.clear()
        if os.path.exists(self.prd_file):
            self._parse_prd()
