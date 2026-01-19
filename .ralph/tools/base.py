"""
Базовый класс для всех инструментов Ralph
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
from datetime import datetime


class Tool(ABC):
    """
    Абстрактный базовый класс для всех инструментов.
    
    Каждый инструмент должен определить:
    - name: уникальное имя инструмента
    - description: описание для промпта
    - parameters_schema: JSON Schema для валидации параметров
    - execute(): метод выполнения
    """
    
    name: str = "base_tool"
    description: str = "Base tool class"
    parameters_schema: Dict[str, Any] = {}
    
    def __init__(self):
        self.last_execution_time: Optional[datetime] = None
        self.execution_count: int = 0
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Выполняет действие инструмента.
        
        Returns:
            Dict с ключами:
            - success: bool
            - result: Any (результат выполнения)
            - message: str (сообщение об ошибке или успехе)
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> tuple[bool, str]:
        """
        Валидирует параметры согласно JSON Schema.
        
        Args:
            params: Словарь параметров для валидации
            
        Returns:
            (is_valid, error_message)
        """
        if not self.parameters_schema:
            return True, ""
        
        required = self.parameters_schema.get('required', [])
        properties = self.parameters_schema.get('properties', {})
        
        # Проверка обязательных параметров
        for req_param in required:
            if req_param not in params:
                return False, f"Missing required parameter: {req_param}"
        
        # Проверка типов параметров
        for param_name, param_value in params.items():
            if param_name not in properties:
                return False, f"Unknown parameter: {param_name}"
            
            expected_type = properties[param_name].get('type')
            if expected_type:
                if not self._check_type(param_value, expected_type):
                    return False, f"Parameter '{param_name}' must be of type {expected_type}"
        
        return True, ""
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Проверяет соответствие типа значения ожидаемому типу из JSON Schema"""
        type_mapping = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict,
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type is None:
            return True  # Неизвестный тип - пропускаем
        
        return isinstance(value, expected_python_type)
    
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """
        Вызов инструмента с валидацией параметров.
        """
        # Валидация
        is_valid, error = self.validate_params(kwargs)
        if not is_valid:
            return {
                'success': False,
                'result': None,
                'message': f"Validation error: {error}"
            }
        
        # Выполнение
        try:
            self.last_execution_time = datetime.now()
            self.execution_count += 1
            result = self.execute(**kwargs)
            return result
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'message': f"Execution error: {str(e)}"
            }
    
    def get_documentation(self) -> str:
        """
        Генерирует документацию для промпта.
        """
        doc = f"**{self.name}**\n"
        doc += f"{self.description}\n\n"
        
        if self.parameters_schema.get('properties'):
            doc += "Parameters:\n"
            for param_name, param_info in self.parameters_schema['properties'].items():
                required = param_name in self.parameters_schema.get('required', [])
                req_marker = " (required)" if required else " (optional)"
                param_type = param_info.get('type', 'any')
                param_desc = param_info.get('description', 'No description')
                doc += f"  - {param_name} ({param_type}){req_marker}: {param_desc}\n"
        
        return doc
