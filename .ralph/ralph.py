#!/usr/bin/env python3
"""
Enterprise Ralph - Autonomous AI Developer Agent

Стабильная версия с защитой от зацикливания.
"""
import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import time
import re
import hashlib
from collections import Counter

# --- CONFIGURATION ---
API_KEY = os.getenv("VIBEPROXY_API_KEY", "sk-vibeproxy-placeholder")
API_URL = os.getenv("VIBEPROXY_URL", "http://127.0.0.1:8317/v1/chat/completions")
MODEL = os.getenv("VIBEPROXY_MODEL", "gemini-2.5-flash")
MAX_ITERATIONS = 20
MAX_SAME_ERROR_COUNT = 3  # Остановиться если та же ошибка повторяется N раз

# Интерактивный режим: по умолчанию ВКЛ, с флагом --auto выключается
INTERACTIVE_MODE = "--auto" not in sys.argv

# Project root (one level up from .ralph)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Files
PRD_FILE = os.path.join(PROJECT_ROOT, "PRD.md")
LOG_FILE = os.path.join(SCRIPT_DIR, "LOG.md")
AGENTS_FILE = os.path.join(PROJECT_ROOT, "AGENTS.md")
STATE_DIR = os.path.join(SCRIPT_DIR, "state")
ERROR_HISTORY_FILE = os.path.join(STATE_DIR, "error_history.json")

# Ensure state directory exists
os.makedirs(STATE_DIR, exist_ok=True)


def log(msg: str, color: str = "blue") -> None:
    """Вывод сообщения с цветом в консоль."""
    colors = {
        "blue": "\033[94m",
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "end": "\033[0m"
    }
    print(f"{colors.get(color, '')}[RALPH] {msg}{colors['end']}")


def ask_continue() -> bool:
    """
    Спрашивает пользователя, продолжить ли работу.
    Возвращает True если продолжить, False если остановить.
    """
    if not INTERACTIVE_MODE:
        return True
    
    print()
    log("━" * 50, "cyan")
    log("Действие выполнено. Что дальше?", "cyan")
    log("  [Enter] - продолжить", "green")
    log("  [q]     - остановить агента", "yellow")
    log("  [s]     - пропустить эту задачу", "yellow")
    log("━" * 50, "cyan")
    
    try:
        response = input("\n👉 Ваш выбор: ").strip().lower()
        if response == 'q':
            log("⛔ Агент остановлен пользователем", "red")
            sys.exit(0)
        elif response == 's':
            log("⏭️ Задача пропущена", "yellow")
            return False  # Сигнал пропустить
        return True
    except (KeyboardInterrupt, EOFError):
        log("\n⛔ Агент остановлен (Ctrl+C)", "red")
        sys.exit(0)


def get_error_hash(error_text: str) -> str:
    """Создаёт хэш ошибки для сравнения."""
    # Извлекаем ключевую часть ошибки (тип и сообщение)
    error_patterns = [
        r"(ImportError:.*?)(?:\n|$)",
        r"(ModuleNotFoundError:.*?)(?:\n|$)",
        r"(SyntaxError:.*?)(?:\n|$)",
        r"(NameError:.*?)(?:\n|$)",
        r"(AttributeError:.*?)(?:\n|$)",
        r"(TypeError:.*?)(?:\n|$)",
    ]
    
    for pattern in error_patterns:
        match = re.search(pattern, error_text, re.IGNORECASE)
        if match:
            error_key = match.group(1).strip()
            return hashlib.md5(error_key.encode()).hexdigest()[:12]
    
    # Fallback: хэш всего stderr
    return hashlib.md5(error_text.encode()).hexdigest()[:12]


def load_error_history() -> dict:
    """Загружает историю ошибок."""
    if os.path.exists(ERROR_HISTORY_FILE):
        try:
            with open(ERROR_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"errors": [], "task_hash": None}
    return {"errors": [], "task_hash": None}


def save_error_history(history: dict) -> None:
    """Сохраняет историю ошибок."""
    with open(ERROR_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def check_error_loop(error_output: str, task_hash: str) -> tuple[bool, int]:
    """
    Проверяет, не зацикливается ли агент на одной ошибке.
    Возвращает (is_looping, error_count).
    """
    history = load_error_history()
    
    # Сбросить историю если задача изменилась
    if history.get("task_hash") != task_hash:
        history = {"errors": [], "task_hash": task_hash}
    
    error_hash = get_error_hash(error_output)
    history["errors"].append(error_hash)
    
    # Оставляем только последние 10 ошибок
    history["errors"] = history["errors"][-10:]
    save_error_history(history)
    
    # Считаем повторения последней ошибки
    error_counts = Counter(history["errors"])
    current_count = error_counts.get(error_hash, 0)
    
    is_looping = current_count >= MAX_SAME_ERROR_COUNT
    return is_looping, current_count


def clear_error_history() -> None:
    """Очищает историю ошибок (при успешном завершении)."""
    if os.path.exists(ERROR_HISTORY_FILE):
        os.remove(ERROR_HISTORY_FILE)


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Вызов LLM API с retry логикой."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 8192
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers
    )
    
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                return json.load(response)["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                wait_time = 10 * attempt
                log(f"Rate limit hit, waiting {wait_time}s...", "yellow")
                time.sleep(wait_time)
            else:
                log(f"API Error {e.code}: {e.reason}", "red")
                sys.exit(1)
        except Exception as e:
            log(f"Error: {e}", "red")
            if attempt == 3:
                sys.exit(1)
            time.sleep(10)
    
    return ""


def read_file(path: str) -> str:
    """Читает файл и возвращает содержимое."""
    if os.path.exists(path):
        return open(path, 'r', encoding='utf-8', errors='ignore').read()
    return ""


def write_file(path: str, content: str) -> None:
    """Записывает контент в файл."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def run_command(cmd: str) -> tuple[int, str]:
    """Выполняет команду и возвращает результат."""
    log(f"Exec: {cmd}", "cyan")
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT
    )
    output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nRETURN CODE: {result.returncode}"
    
    with open(LOG_FILE, 'a') as f:
        f.write(f"\n=== CMD: {cmd} ===\n{output}\n")
    
    return result.returncode, output


def get_first_unchecked_task() -> tuple[int | None, str | None]:
    """Извлекает первую невыполненную задачу из PRD.md."""
    if not os.path.exists(PRD_FILE):
        return None, None
    
    prd_content = read_file(PRD_FILE)
    lines = prd_content.splitlines()
    
    for i, line in enumerate(lines):
        if re.search(r'^\s*-\s*\[\s*\]\s+', line):
            task_text = re.sub(r'^\s*-\s*\[\s*\]\s+', '', line).strip()
            return i, task_text
    
    return None, None


def mark_task_complete(task_line_index: int) -> None:
    """Отмечает задачу как выполненную в PRD.md."""
    if not os.path.exists(PRD_FILE):
        return
    
    prd_content = read_file(PRD_FILE)
    lines = prd_content.splitlines()
    
    if task_line_index < len(lines):
        lines[task_line_index] = re.sub(r'^\s*-\s*\[\s*\]', '- [x]', lines[task_line_index])
        write_file(PRD_FILE, '\n'.join(lines) + '\n')
        log(f"✅ Marked task #{task_line_index + 1} as complete", "green")


def get_project_context() -> str:
    """Получает контекст проекта для LLM."""
    cmd = (
        "find . -maxdepth 3 -type f "
        "-not -path '*/.*' "
        "-not -path '*venv*' "
        "-not -path '*node_modules*' "
        "-not -path '*__pycache__*' "
        "-name '*.py' | head -n 30"
    )
    structure = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT
    ).stdout.strip()
    
    key_files = ""
    for fname in ["requirements.txt", "src/main.py", "src/config.py", "pytest.ini", "src/api/routes.py"]:
        fpath = os.path.join(PROJECT_ROOT, fname)
        if os.path.exists(fpath):
            content = read_file(fpath)
            key_files += f"\n--- {fname} (first 30 lines) ---\n"
            key_files += "\n".join(content.splitlines()[:30]) + "\n"
    
    agents_guide = ""
    if os.path.exists(AGENTS_FILE):
        agents_content = read_file(AGENTS_FILE)
        agents_guide = f"\n--- AGENTS.md (Code Style Guidelines) ---\n"
        agents_guide += "\n".join(agents_content.splitlines()[:100]) + "\n"
    
    return f"Project Python Files:\n{structure}\n\nKey Files:{key_files}\n{agents_guide}"


SYSTEM_PROMPT = """You are Ralph, an autonomous senior developer working on the TMS (Transport Management System) project.

**Your Mission:**
Complete ONE SPECIFIC TASK from PRD.md. Work iteratively until tests pass, then STOP.

**Project Context:**
- Backend: Python 3.11+, FastAPI, SQLAlchemy (async), PostgreSQL, Redis
- Frontend: React, TypeScript, Vite, Ant Design
- Tests: pytest (backend), npm test (frontend)

**Critical Rules:**
1. Read AGENTS.md guidelines for code style and testing patterns
2. Use absolute imports: `from src.module import Class`
3. Always add type hints in Python
4. Use async/await for database operations
5. Cache data BEFORE commit() to avoid PendingRollbackError
6. Write tests FIRST, then implement
7. **ВАЖНО:** Если модуль не существует, НЕ импортируйте его! Сначала проверьте структуру проекта.

**Your Workflow:**
1. Understand the current task
2. Check existing code structure (IMPORTANT: verify imports exist!)
3. Write/modify code following AGENTS.md patterns
4. Run tests: `pytest tests/test_*.py` or `npm test`
5. Fix errors if tests fail
6. When tests pass → Mark task complete → STOP

**Response Format:**

To write/update a file (path relative to project root):
```write:src/api/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok"}
```

To run a command (in project root):
```exec
pytest tests/test_health.py -v
```

To mark task complete and finish:
```done
Task completed successfully. All tests passing.
```

**CRITICAL:** 
- Only use ONE code block per response
- Work step-by-step
- If you see the SAME error 3 times, STOP and explain what's wrong
- Don't import modules that don't exist!
"""


def main() -> None:
    """Главная функция агента."""
    if not os.path.exists(PRD_FILE):
        log("❌ PRD.md not found in project root!", "red")
        print("\nCreate PRD.md with your tasks:")
        print("\n# Product Requirements Document")
        print("\n## Epic 1: Features")
        print("- [ ] Add healthcheck endpoint")
        print("- [ ] Add metrics endpoint\n")
        sys.exit(1)
    
    task_index, task_text = get_first_unchecked_task()
    
    if task_index is None:
        log("🎉 All tasks completed! No unchecked tasks in PRD.md", "green")
        clear_error_history()
        sys.exit(0)
    
    task_hash = hashlib.md5(f"{task_index}:{task_text}".encode()).hexdigest()[:8]
    
    log(f"📋 Current task #{task_index + 1}: {task_text}", "yellow")
    
    if INTERACTIVE_MODE:
        log("🎮 Режим: ИНТЕРАКТИВНЫЙ (после каждого действия ждём подтверждения)", "cyan")
        log("   Используй './ralph --auto' для автоматического режима", "cyan")
    else:
        log("🤖 Режим: АВТОМАТИЧЕСКИЙ", "cyan")
    
    with open(LOG_FILE, 'a') as f:
        f.write(f"\n\n{'='*80}\n")
        f.write(f"NEW AGENT SESSION - Task #{task_index + 1}: {task_text}\n")
        f.write(f"{'='*80}\n")
    
    for iteration in range(1, MAX_ITERATIONS + 1):
        log(f"\n{'='*60}", "blue")
        log(f"Iteration {iteration}/{MAX_ITERATIONS}", "blue")
        log(f"{'='*60}", "blue")
        
        recent_logs = "\n".join(read_file(LOG_FILE).splitlines()[-100:])
        
        user_prompt = f"""**CURRENT TASK:** {task_text}

**What previous agents tried (Recent Logs):**
{recent_logs}

**Project Context:**
{get_project_context()}

What's your next step to complete this task?
Remember: ONE action per response (write file OR run command).
If tests pass, use ```done``` to mark task complete.

**ВАЖНО:** Проверь что все импорты существуют перед использованием!
"""
        
        log("🤔 Thinking...", "blue")
        response = call_llm(SYSTEM_PROMPT, user_prompt)
        
        print(f"\n{'='*60}")
        print("AI Response:")
        print(f"{'='*60}")
        print(response)
        print(f"{'='*60}\n")
        
        with open(LOG_FILE, 'a') as f:
            f.write(f"\n=== Iteration {iteration} ===\n{response}\n")
        
        lines = response.splitlines()
        current_file = None
        write_buffer = []
        in_write_block = False
        action_taken = False
        
        for line in lines:
            # Detect write block start
            if line.strip().startswith("```write:"):
                current_file = line.strip().replace("```write:", "").strip()
                in_write_block = True
                write_buffer = []
                continue
            
            # Detect exec block start
            if line.strip().startswith("```exec"):
                current_file = "EXEC"
                in_write_block = True
                write_buffer = []
                continue
            
            # Detect done block
            if "```done" in line.lower():
                log("✅ AI marked task as DONE!", "green")
                mark_task_complete(task_index)
                log(f"🎉 Task #{task_index + 1} completed: {task_text}", "green")
                
                with open(LOG_FILE, 'a') as f:
                    f.write(f"\n✅ TASK COMPLETED SUCCESSFULLY!\n")
                
                clear_error_history()
                
                log("🔄 Checking for next task...", "blue")
                time.sleep(2)
                
                # Проверяем есть ли ещё задачи
                next_task_index, next_task_text = get_first_unchecked_task()
                if next_task_index is not None:
                    log(f"📋 Next task found: {next_task_text}", "yellow")
                    os.execv(sys.executable, ['python3'] + sys.argv)
                else:
                    log("🎉 ALL TASKS COMPLETED!", "green")
                    sys.exit(0)
            
            # Detect block end
            if line.strip() == "```" and in_write_block:
                in_write_block = False
                content = "\n".join(write_buffer)
                
                if current_file == "EXEC":
                    return_code, output = run_command(content.strip())
                    print(f"\n📊 Command output:\n{output}\n")
                    
                    if return_code != 0:
                        log(f"⚠️ Command failed with code {return_code}", "yellow")
                        
                        # Проверяем на зацикливание
                        is_looping, error_count = check_error_loop(output, task_hash)
                        if is_looping:
                            log(f"🔴 LOOP DETECTED! Same error repeated {error_count} times.", "red")
                            log("⛔ Stopping to prevent infinite loop. Please fix manually:", "red")
                            
                            # Извлекаем и показываем ошибку
                            stderr_match = re.search(r"STDERR:\n(.*?)(?:RETURN CODE|$)", output, re.DOTALL)
                            if stderr_match:
                                print(f"\n❌ Repeating error:\n{stderr_match.group(1).strip()}\n")
                            
                            with open(LOG_FILE, 'a') as f:
                                f.write(f"\n❌ LOOP DETECTED - Agent stopped after {error_count} same errors\n")
                            
                            sys.exit(1)
                    else:
                        log("✅ Command succeeded", "green")
                else:
                    target_path = os.path.join(PROJECT_ROOT, current_file)
                    log(f"📝 Writing to {current_file}...", "green")
                    write_file(target_path, content + "\n")
                
                action_taken = True
                
                # Интерактивный режим: спрашиваем продолжать ли
                if not ask_continue():
                    log("⏭️ Переход к следующей задаче...", "yellow")
                    break
                
                break
            
            if in_write_block:
                write_buffer.append(line)
        
        if not action_taken:
            log("⚠️ No action detected in response. Continuing...", "yellow")
        
        # Пауза только в автоматическом режиме
        if not INTERACTIVE_MODE:
            time.sleep(3)
    
    log(f"⏰ Max iterations ({MAX_ITERATIONS}) reached for this task.", "red")
    log("💾 Agent stopped. Please check LOG.md and fix manually.", "yellow")
    
    with open(LOG_FILE, 'a') as f:
        f.write(f"\n❌ AGENT STOPPED - Max iterations reached.\n")
    
    sys.exit(1)


if __name__ == "__main__":
    main()
