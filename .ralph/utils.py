import os
import shutil
import hashlib
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

# --- Paths ---
RALPH_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(RALPH_DIR)
BACKUP_DIR = os.path.join(RALPH_DIR, "backups")
CONFIG_FILE = os.path.join(RALPH_DIR, "ralph_config.json")
STATE_DIR = os.path.join(RALPH_DIR, "state")
LOGS_DIR = os.path.join(RALPH_DIR, "logs")
LOG_FILE = os.path.join(RALPH_DIR, "LOG.md")
ERROR_HISTORY_FILE = os.path.join(STATE_DIR, "error_history.json")

def load_config() -> Dict[str, Any]:
    """Загружает конфигурацию из JSON файла."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception as e:
            log_local(f"❌ Failed to load config: {e}", "red")
            return {}

def log_local(message: str, color: str = "white") -> None:
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
    }
    reset = "\033[0m"
    print(f"{colors.get(color, colors['white'])}[RALPH] {message}{reset}")

def backup_file(path: str) -> None:
    """Создает бэкап файла в директории .ralph/backups."""
    if not os.path.exists(path):
        return
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = os.path.basename(path)
        backup_path = os.path.join(BACKUP_DIR, f"{name}.{ts}.bak")
        shutil.copy2(path, backup_path)
        
        # Ротация: оставляем только последние 10 бэкапов для этого файла
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.startswith(name)],
            key=lambda x: os.path.getmtime(os.path.join(BACKUP_DIR, x))
        )
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                os.remove(os.path.join(BACKUP_DIR, old_backup))
    except Exception as e:
        log_local(f"⚠️ Backup failed for {path}: {e}", "yellow")

def restore_file(path: str, backup_index: int = 0) -> bool:
    """
    Восстанавливает файл из бэкапа.
    backup_index=0 — последний бэкап, 1 — предпоследний и т.д.
    """
    name = os.path.basename(path)
    if not os.path.exists(BACKUP_DIR):
        log_local(f"❌ Backup directory not found", "red")
        return False

    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith(name)],
        key=lambda x: os.path.getmtime(os.path.join(BACKUP_DIR, x)),
        reverse=True
    )
    
    if backup_index >= len(backups):
        log_local(f"❌ Backup #{backup_index} not found for {name}", "red")
        return False
    
    backup_path = os.path.join(BACKUP_DIR, backups[backup_index])
    shutil.copy2(backup_path, path)
    log_local(f"✅ Restored {name} from {backups[backup_index]}", "green")
    return True

def validate_write(path: str, content: str) -> Tuple[bool, str]:
    """Проверяет безопасность записи в файл."""
    config = load_config()
    rel_path = os.path.relpath(path, PROJECT_ROOT).replace("\\", "/")
    
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            old_content = f.read()
        
        old_lines = len(old_content.splitlines())
        new_lines = len(content.splitlines())
        
        # 1. Проверка на резкое сокращение файла
        if old_lines > 10 and new_lines < old_lines * 0.5 and "#TRUNCATE" not in content[:200]:
            return False, f"File would shrink by >50% ({old_lines} -> {new_lines} lines). Use #TRUNCATE to confirm."
            
        # 2. Проверка защищенных файлов
        protected_files = config.get('protection', {}).get('files', [])
        if rel_path in protected_files:
            if new_lines < old_lines * 0.7:
                return False, f"Protected file {rel_path}: deletion of >30% lines blocked."
            
            critical_patterns = config.get('protection', {}).get('critical_patterns', {}).get(rel_path, [])
            for p in critical_patterns:
                if p in old_content and p not in content:
                    return False, f"Protected file {rel_path}: missing critical pattern '{p}'"
    
    return True, ""

def safe_write(path: str, content: str) -> Tuple[bool, str]:
    """Безопасная запись с бэкапом и валидацией."""
    is_safe, error = validate_write(path, content)
    if not is_safe:
        return False, error
        
    backup_file(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True, "OK"

def generate_task_hash(task_index: int, task_text: str) -> str:
    """Генерирует уникальный хэш задачи."""
    return hashlib.md5(f"{task_index}:{task_text}".encode()).hexdigest()[:8]
