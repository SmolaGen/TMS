"""
Центральный реестр инструментов с автоматической регистрацией
"""

import os
import sys
from typing import Dict, Optional, List

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.base import Tool
from tools.file_tools import WriteFileTool, ReadFileTool, BackupFileTool, RestoreFileTool
from tools.exec_tools import ExecCommandTool, RunTestsTool, GitCommitTool
from tools.search_tools import GrepTool, FindFileTool, AnalyzeImportsTool


class ToolRegistry:
    """
    Singleton реестр всех доступных инструментов.
    Автоматически регистрирует инструменты и предоставляет API для работы с ними.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._tools: Dict[str, Tool] = {}
        self._register_default_tools()
        self._initialized = True
    
    def _register_default_tools(self):
        """Регистрирует все встроенные инструменты"""
        default_tools = [
            # File tools
            WriteFileTool(),
            ReadFileTool(),
            BackupFileTool(),
            RestoreFileTool(),
            
            # Exec tools
            ExecCommandTool(),
            RunTestsTool(),
            GitCommitTool(),
            
            # Search tools
            GrepTool(),
            FindFileTool(),
            AnalyzeImportsTool(),
        ]
        
        for tool in default_tools:
            self.register(tool)
    
    def register(self, tool: Tool) -> None:
        """
        Регистрирует новый инструмент в реестре.
        
        Args:
            tool: Экземпляр инструмента (наследник Tool)
        """
        if not isinstance(tool, Tool):
            raise TypeError(f"Tool must be instance of Tool class, got {type(tool)}")
        
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """
        Получает инструмент по имени.
        
        Args:
            name: Имя инструмента
            
        Returns:
            Экземпляр инструмента или None если не найден
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """Возвращает список имен всех зарегистрированных инструментов"""
        return list(self._tools.keys())
    
    def get_documentation(self) -> str:
        """
        Генерирует документацию для всех инструментов (для промпта).
        
        Returns:
            Markdown-форматированная документация
        """
        doc = "# Available Tools\n\n"
        doc += "You can use the following tools by creating code blocks with format:\n"
        doc += "```tool:tool_name\n"
        doc += "{\n"
        doc += '  "param1": "value1",\n'
        doc += '  "param2": "value2"\n'
        doc += "}\n"
        doc += "```\n\n"
        doc += "---\n\n"
        
        # Группируем инструменты по категориям
        categories = {
            'File Operations': ['write_file', 'read_file', 'backup_file', 'restore_file'],
            'Command Execution': ['exec_command', 'run_tests', 'git_commit'],
            'Code Search & Analysis': ['grep_search', 'find_file', 'analyze_imports'],
        }
        
        for category, tool_names in categories.items():
            doc += f"## {category}\n\n"
            for tool_name in tool_names:
                tool = self._tools.get(tool_name)
                if tool:
                    doc += tool.get_documentation() + "\n"
            doc += "---\n\n"
        
        return doc
    
    def execute_tool(self, name: str, params: Dict) -> Dict:
        """
        Выполняет инструмент по имени с параметрами.
        
        Args:
            name: Имя инструмента
            params: Словарь параметров
            
        Returns:
            Результат выполнения инструмента
        """
        tool = self.get_tool(name)
        if not tool:
            return {
                'success': False,
                'result': None,
                'message': f"Tool not found: {name}"
            }
        
        return tool(**params)
