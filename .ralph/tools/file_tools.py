"""
Инструменты для работы с файлами
"""

import os
import sys
from typing import Dict, Any

# Добавляем родительскую директорию в путь для импорта utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.base import Tool
import utils


class WriteFileTool(Tool):
    """Инструмент для записи содержимого в файл с валидацией"""
    
    name = "write_file"
    description = "Записывает содержимое в файл с автоматическим бэкапом и валидацией безопасности"
    parameters_schema = {
        'required': ['path', 'content'],
        'properties': {
            'path': {
                'type': 'string',
                'description': 'Относительный путь к файлу от корня проекта'
            },
            'content': {
                'type': 'string',
                'description': 'Содержимое файла для записи'
            }
        }
    }
    
    def execute(self, path: str, content: str) -> Dict[str, Any]:
        """Записывает файл через utils.safe_write()"""
        full_path = os.path.join(utils.PROJECT_ROOT, path)
        success, message = utils.safe_write(full_path, content)
        
        return {
            'success': success,
            'result': {'path': path, 'size': len(content)},
            'message': message if not success else f"File written: {path}"
        }


class ReadFileTool(Tool):
    """Инструмент для чтения файла с ограничением размера"""
    
    name = "read_file"
    description = "Читает содержимое файла с ограничением размера"
    parameters_schema = {
        'required': ['path'],
        'properties': {
            'path': {
                'type': 'string',
                'description': 'Относительный путь к файлу от корня проекта'
            },
            'max_size_kb': {
                'type': 'integer',
                'description': 'Максимальный размер файла в КБ (по умолчанию 500)'
            }
        }
    }
    
    def execute(self, path: str, max_size_kb: int = 500) -> Dict[str, Any]:
        """Читает файл с проверкой размера"""
        full_path = os.path.join(utils.PROJECT_ROOT, path)
        
        if not os.path.exists(full_path):
            return {
                'success': False,
                'result': None,
                'message': f"File not found: {path}"
            }
        
        file_size = os.path.getsize(full_path)
        max_size = max_size_kb * 1024
        
        if file_size > max_size:
            return {
                'success': False,
                'result': None,
                'message': f"File too large: {file_size} bytes (max {max_size} bytes)"
            }
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                'success': True,
                'result': {'content': content, 'size': file_size},
                'message': f"File read: {path} ({file_size} bytes)"
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'message': f"Error reading file: {str(e)}"
            }


class BackupFileTool(Tool):
    """Инструмент для создания бэкапа файла"""
    
    name = "backup_file"
    description = "Создает бэкап файла в директории .ralph/backups"
    parameters_schema = {
        'required': ['path'],
        'properties': {
            'path': {
                'type': 'string',
                'description': 'Относительный путь к файлу от корня проекта'
            }
        }
    }
    
    def execute(self, path: str) -> Dict[str, Any]:
        """Создает бэкап через utils.backup_file()"""
        full_path = os.path.join(utils.PROJECT_ROOT, path)
        
        if not os.path.exists(full_path):
            return {
                'success': False,
                'result': None,
                'message': f"File not found: {path}"
            }
        
        try:
            utils.backup_file(full_path)
            return {
                'success': True,
                'result': {'path': path},
                'message': f"Backup created for: {path}"
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'message': f"Backup failed: {str(e)}"
            }


class RestoreFileTool(Tool):
    """Инструмент для восстановления файла из бэкапа"""
    
    name = "restore_file"
    description = "Восстанавливает файл из бэкапа (0 = последний, 1 = предпоследний и т.д.)"
    parameters_schema = {
        'required': ['path'],
        'properties': {
            'path': {
                'type': 'string',
                'description': 'Относительный путь к файлу от корня проекта'
            },
            'backup_index': {
                'type': 'integer',
                'description': 'Индекс бэкапа (0 = последний, 1 = предпоследний)'
            }
        }
    }
    
    def execute(self, path: str, backup_index: int = 0) -> Dict[str, Any]:
        """Восстанавливает файл через utils.restore_file()"""
        full_path = os.path.join(utils.PROJECT_ROOT, path)
        
        success = utils.restore_file(full_path, backup_index)
        
        return {
            'success': success,
            'result': {'path': path, 'backup_index': backup_index},
            'message': f"File restored from backup #{backup_index}" if success else "Restore failed"
        }
