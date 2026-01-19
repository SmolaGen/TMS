"""
Инструменты для поиска и анализа кода
"""

import os
import sys
import subprocess
import re
from typing import Dict, Any, List

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.base import Tool
import utils


class GrepTool(Tool):
    """Инструмент для поиска паттернов в файлах"""
    
    name = "grep_search"
    description = "Ищет паттерн в файлах проекта с использованием grep"
    parameters_schema = {
        'required': ['pattern'],
        'properties': {
            'pattern': {
                'type': 'string',
                'description': 'Паттерн для поиска'
            },
            'path': {
                'type': 'string',
                'description': 'Путь для поиска (по умолчанию .)'
            },
            'file_pattern': {
                'type': 'string',
                'description': 'Паттерн для фильтрации файлов (например, *.py)'
            }
        }
    }
    
    def execute(self, pattern: str, path: str = ".", file_pattern: str = None) -> Dict[str, Any]:
        """Выполняет grep поиск"""
        cmd_parts = ["grep", "-r", "-n", pattern, path]
        
        if file_pattern:
            cmd_parts.extend(["--include", file_pattern])
        
        try:
            result = subprocess.run(
                cmd_parts,
                cwd=utils.PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            matches = result.stdout.strip().split('\n') if result.stdout else []
            matches = [m for m in matches if m]  # Убираем пустые строки
            
            return {
                'success': True,
                'result': {
                    'matches': matches,
                    'count': len(matches)
                },
                'message': f"Found {len(matches)} matches"
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'result': None,
                'message': "Search timeout (10s)"
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'message': f"Search error: {str(e)}"
            }


class FindFileTool(Tool):
    """Инструмент для поиска файлов по имени"""
    
    name = "find_file"
    description = "Ищет файлы по имени или расширению"
    parameters_schema = {
        'required': ['name'],
        'properties': {
            'name': {
                'type': 'string',
                'description': 'Имя файла или паттерн (например, *.py)'
            },
            'path': {
                'type': 'string',
                'description': 'Путь для поиска (по умолчанию .)'
            },
            'max_depth': {
                'type': 'integer',
                'description': 'Максимальная глубина поиска'
            }
        }
    }
    
    def execute(self, name: str, path: str = ".", max_depth: int = None) -> Dict[str, Any]:
        """Выполняет find поиск"""
        cmd_parts = ["find", path, "-name", name]
        
        if max_depth is not None:
            cmd_parts.extend(["-maxdepth", str(max_depth)])
        
        try:
            result = subprocess.run(
                cmd_parts,
                cwd=utils.PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            files = result.stdout.strip().split('\n') if result.stdout else []
            files = [f for f in files if f]  # Убираем пустые строки
            
            return {
                'success': True,
                'result': {
                    'files': files,
                    'count': len(files)
                },
                'message': f"Found {len(files)} files"
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'result': None,
                'message': "Search timeout (10s)"
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'message': f"Search error: {str(e)}"
            }


class AnalyzeImportsTool(Tool):
    """Инструмент для анализа импортов в Python файле"""
    
    name = "analyze_imports"
    description = "Анализирует импорты в Python файле для выявления зависимостей"
    parameters_schema = {
        'required': ['path'],
        'properties': {
            'path': {
                'type': 'string',
                'description': 'Путь к Python файлу'
            }
        }
    }
    
    def execute(self, path: str) -> Dict[str, Any]:
        """Анализирует импорты в файле"""
        full_path = os.path.join(utils.PROJECT_ROOT, path)
        
        if not os.path.exists(full_path):
            return {
                'success': False,
                'result': None,
                'message': f"File not found: {path}"
            }
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Регулярные выражения для поиска импортов
            import_pattern = r'^import\s+([^\s]+)'
            from_import_pattern = r'^from\s+([^\s]+)\s+import'
            
            imports = re.findall(import_pattern, content, re.MULTILINE)
            from_imports = re.findall(from_import_pattern, content, re.MULTILINE)
            
            all_imports = list(set(imports + from_imports))
            
            # Разделяем на stdlib и локальные
            stdlib_imports = []
            local_imports = []
            
            for imp in all_imports:
                # Простая эвристика: если начинается с точки или содержит src/tests - локальный
                if imp.startswith('.') or 'src' in imp or 'tests' in imp:
                    local_imports.append(imp)
                else:
                    stdlib_imports.append(imp)
            
            return {
                'success': True,
                'result': {
                    'all_imports': all_imports,
                    'stdlib_imports': stdlib_imports,
                    'local_imports': local_imports,
                    'total_count': len(all_imports)
                },
                'message': f"Found {len(all_imports)} imports ({len(local_imports)} local)"
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'message': f"Analysis error: {str(e)}"
            }
