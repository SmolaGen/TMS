"""
Инструменты для выполнения команд в песочнице
"""

import os
import sys
import subprocess
from typing import Dict, Any

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.base import Tool
import utils


class ExecCommandTool(Tool):
    """Инструмент для выполнения команд в Docker песочнице"""
    
    name = "exec_command"
    description = "Выполняет команду в Docker контейнере с валидацией безопасности"
    parameters_schema = {
        'required': ['command'],
        'properties': {
            'command': {
                'type': 'string',
                'description': 'Команда для выполнения (будет проверена whitelist)'
            }
        }
    }
    
    def execute(self, command: str) -> Dict[str, Any]:
        """Выполняет команду через ralph.run_command()"""
        # Импортируем здесь, чтобы избежать циклических зависимостей
        import ralph
        
        return_code, output = ralph.run_command(command)
        
        return {
            'success': return_code == 0,
            'result': {
                'return_code': return_code,
                'output': output
            },
            'message': f"Command executed (exit code: {return_code})"
        }


class RunTestsTool(Tool):
    """Специализированный инструмент для запуска тестов"""
    
    name = "run_tests"
    description = "Запускает pytest с указанными параметрами"
    parameters_schema = {
        'properties': {
            'path': {
                'type': 'string',
                'description': 'Путь к тестам (по умолчанию tests/)'
            },
            'verbose': {
                'type': 'boolean',
                'description': 'Включить подробный вывод'
            },
            'markers': {
                'type': 'string',
                'description': 'Pytest markers для фильтрации тестов'
            }
        }
    }
    
    def execute(self, path: str = "tests/", verbose: bool = True, markers: str = None) -> Dict[str, Any]:
        """Запускает pytest"""
        import ralph
        
        cmd_parts = ["pytest", path]
        if verbose:
            cmd_parts.append("-v")
        if markers:
            cmd_parts.extend(["-m", markers])
        
        command = " ".join(cmd_parts)
        return_code, output = ralph.run_command(command)
        
        # Парсим вывод pytest для подсчета тестов
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        
        return {
            'success': return_code == 0,
            'result': {
                'return_code': return_code,
                'output': output,
                'passed': passed,
                'failed': failed
            },
            'message': f"Tests: {passed} passed, {failed} failed"
        }


class GitCommitTool(Tool):
    """Инструмент для автоматического git commit"""
    
    name = "git_commit"
    description = "Создает git commit с детальным описанием изменений"
    parameters_schema = {
        'required': ['message'],
        'properties': {
            'message': {
                'type': 'string',
                'description': 'Сообщение коммита (должно быть детальным)'
            },
            'add_all': {
                'type': 'boolean',
                'description': 'Добавить все изменения (git add .)'
            }
        }
    }
    
    def execute(self, message: str, add_all: bool = True) -> Dict[str, Any]:
        """Создает git commit"""
        import ralph
        
        if add_all:
            ralph.run_command("git add .")
        
        # Экранируем кавычки в сообщении
        safe_message = message.replace('"', '\\"')
        return_code, output = ralph.run_command(f'git commit -m "{safe_message}"')
        
        return {
            'success': return_code == 0,
            'result': {
                'return_code': return_code,
                'output': output
            },
            'message': "Commit created" if return_code == 0 else "Commit failed"
        }
