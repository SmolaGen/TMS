import os
import sys
import re
import json
import time
import hashlib
import requests
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

# --- Configuration ---
VIBEPROXY_API_KEY = os.getenv("VIBEPROXY_API_KEY")
VIBEPROXY_URL = os.getenv("VIBEPROXY_URL", "https://api.vibe.sh/v1")
VIBEPROXY_MODEL = os.getenv("VIBEPROXY_MODEL", "gpt-4o")

PROJECT_ROOT = os.getcwd()
PRD_FILE = os.path.join(PROJECT_ROOT, "PRD.md")
LOG_FILE = os.path.join(PROJECT_ROOT, ".ralph", "LOG.md")
ERROR_HISTORY_FILE = os.path.join(PROJECT_ROOT, ".ralph", "state", "error_history.json")
ARCHITECT_PROMPT_FILE = os.path.join(PROJECT_ROOT, ".ralph", "prompts", "architect_prompt.md")
PLAN_FILE = os.path.join(PROJECT_ROOT, ".ralph", "state", "current_plan.md")

MAX_ITERATIONS = 3
INTERACTIVE_MODE = "--auto" not in sys.argv

# Ensure directories exist
os.makedirs(os.path.dirname(ERROR_HISTORY_FILE), exist_ok=True)
os.makedirs(os.path.dirname(PLAN_FILE), exist_ok=True)

# --- Logging Utils ---
def log(message: str, color: str = "white") -> None:
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

def write_file(path: str, content: str) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def read_file(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

# --- Core Tools ---
def run_command(command: str) -> Tuple[int, str]:
    import subprocess
    log(f"Exec: {command}", "magenta")
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=PROJECT_ROOT
        )
        stdout, stderr = process.communicate()
        output = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}\nRETURN CODE: {process.returncode}"
        return process.returncode, output
    except Exception as e:
        return 1, str(e)

def ask_continue() -> bool:
    if not INTERACTIVE_MODE:
        return True
    
    log("\n" + "━" * 50, "cyan")
    log("Действие выполнено. Что дальше?", "cyan")
    log("  [Enter] - продолжить", "white")
    log("  [q]     - остановить агента", "white")
    log("  [s]     - пропустить эту задачу", "white")
    log("━" * 50, "cyan")
    
    try:
        choice = input("\n👉 Ваш выбор: ").strip().lower()
        if choice == 'q':
            log("🛑 Агент остановлен пользователем", "red")
            sys.exit(0)
        if choice == 's':
            log("⏭️ Задача пропущена", "yellow")
            return False
        return True
    except (KeyboardInterrupt, EOFError):
        log("\n⛔ Агент остановлен (Ctrl+C)", "red")
        sys.exit(0)

# --- Planner Logic ---
def clear_plan() -> None:
    if os.path.exists(PLAN_FILE):
        os.remove(PLAN_FILE)
        log("🗑️ Текущий план удалён", "cyan")

def run_architect(task_text: str) -> None:
    log("🏛️ Запуск Архитектора для планирования...", "cyan")
    architect_system_prompt = read_file(ARCHITECT_PROMPT_FILE)
    
    if not architect_system_prompt:
        log("❌ Architect prompt file missing!", "red")
        sys.exit(1)
        
    user_prompt = f"""**TASKS FOR PLANNING:**
{task_text}

**Project Structure:**
{get_project_context()}

Создай план в файле `.ralph/state/current_plan.md`. 
Если нужно изменить PRD.md (добавить новые задачи), используй блок ```prd.
"""
    log("🤔 Проектирую решение...", "blue")
    plan_content = call_llm(architect_system_prompt, user_prompt)
    
    # Парсим ответ на наличие ```prd и ```markdown (для плана)
    lines = plan_content.splitlines()
    in_prd = False
    in_plan = False
    prd_buffer = []
    plan_buffer = []
    
    for line in lines:
        if line.startswith("```prd"):
            in_prd = True; continue
        if line.startswith("```markdown") and not in_prd:
            in_plan = True; continue
        if line.strip() == "```":
            in_prd = False; in_plan = False; continue
        
        if in_prd: prd_buffer.append(line)
        if in_plan: plan_buffer.append(line)
        
    if plan_buffer:
        write_file(PLAN_FILE, "\n".join(plan_buffer))
        log(f"✅ План сохранён в: {PLAN_FILE}", "green")
    else:
        # Если нет блока markdown, сохраняем всё как план (fallback)
        write_file(PLAN_FILE, plan_content)
        log(f"✅ Ответ сохранён в план", "green")
        
    if prd_buffer:
        write_file(PRD_FILE, "\n".join(prd_buffer))
        log("✅ PRD.md обновлён новыми задачами", "green")
        
    log("Проверь план и запусти './ralph' для выполнения.", "yellow")
    sys.exit(0)

# --- Context Utils ---
def get_project_context() -> str:
    structure = run_command("find . -maxdepth 2 -not -path '*/.*'")[1]
    prd = read_file(PRD_FILE)
    config = read_file(os.path.join(PROJECT_ROOT, "src", "config.py"))
    return f"Files:\n{structure}\n\nPRD:\n{prd}\n\nConfig:\n{config}"

def get_first_unchecked_task() -> Tuple[Optional[int], Optional[str]]:
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
    if not os.path.exists(PRD_FILE): return
    prd_content = read_file(PRD_FILE)
    lines = prd_content.splitlines()
    if task_line_index < len(lines):
        lines[task_line_index] = lines[task_line_index].replace("[ ]", "[x]")
        write_file(PRD_FILE, "\n".join(lines))

# --- LLM Integration ---
def call_llm(system_prompt: str, user_prompt: str) -> str:
    if not VIBEPROXY_API_KEY:
        log("❌ VIBEPROXY_API_KEY is not set!", "red")
        sys.exit(1)
        
    headers = {"Authorization": f"Bearer {VIBEPROXY_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": VIBEPROXY_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }
    
    try:
        response = requests.post(f"{VIBEPROXY_URL}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        log(f"❌ LLM Call Failed: {e}", "red")
        if hasattr(e, 'response') and e.response is not None:
             log(f"Response: {e.response.text}", "red")
        sys.exit(1)

# --- Error Management ---
def clear_error_history() -> None:
    if os.path.exists(ERROR_HISTORY_FILE):
        os.remove(ERROR_HISTORY_FILE)

def check_error_loop(stderr: str, task_hash: str) -> Tuple[bool, int]:
    if not stderr or "STDERR:" not in stderr: return False, 0
    err_part = stderr.split("STDERR:\n")[1].split("\nRETURN CODE:")[0].strip()
    if not err_part: return False, 0
    
    err_hash = hashlib.md5(err_part.encode()).hexdigest()[:12]
    history = {}
    if os.path.exists(ERROR_HISTORY_FILE):
        with open(ERROR_HISTORY_FILE, 'r') as f:
            history = json.load(f)
            
    key = f"{task_hash}:{err_hash}"
    count = history.get(key, 0) + 1
    history[key] = count
    
    with open(ERROR_HISTORY_FILE, 'w') as f:
        json.dump(history, f)
        
    return count >= 3, count

# --- SYSTEM PROMPTS ---
SYSTEM_PROMPT = """You are Ralph, an autonomous senior developer working on the TMS project.

**Your Mission:**
Complete ONE TASK from PRD.md in a SINGLE response. Do ALL steps at once.

**Critical Rules:**
1. Use absolute imports: `from src.module import Class`
2. Always add type hints
3. **NEVER delete existing code** that is not related to your task
4. **NEVER remove** `settings = Settings()` from config.py
5. Check what files exist before importing

**Response Format — USE MULTIPLE BLOCKS:**

```write:path/to/file.py
# file content
```

```exec
pytest tests/test_file.py -v
```

```done
Task completed.
```

**IMPORTANT:**
- Use MULTIPLE code blocks in ONE response
- Write ALL files first, then run tests
- End with ```done``` when tests pass
"""

# --- Main Flow ---
def main() -> None:
    args = sys.argv[1:]
    manual_task = " ".join([a for a in args if not a.startswith("-")])
    
    task_index = None
    task_text = None

    if manual_task:
        task_text = manual_task
        log(f"📝 Задача: {task_text}", "cyan")
    else:
        if not os.path.exists(PRD_FILE):
            log("❌ PRD.md not found!", "red")
            sys.exit(1)
        task_index, task_text = get_first_unchecked_task()

    if "--plan" in sys.argv:
        if not task_text:
            log("⚠️ Нет задачи для планирования!", "yellow")
            sys.exit(1)
        run_architect(task_text)

    if task_text is None:
        log("🎉 All tasks completed!", "green")
        clear_error_history()
        sys.exit(0)
    
    display_index = task_index + 1 if task_index is not None else 0
    task_hash = hashlib.md5(f"{display_index}:{task_text}".encode()).hexdigest()[:8]
    
    log(f"📋 Task #{display_index}: {task_text}", "yellow")
    
    current_plan = read_file(PLAN_FILE)
    if current_plan:
        log("📖 Использую план из current_plan.md", "cyan")

    log(f"🎮 Режим: {'ИНТЕРАКТИВНЫЙ' if INTERACTIVE_MODE else 'АВТОМАТИЧЕСКИЙ'}", "cyan")
    
    with open(LOG_FILE, 'a') as f:
        f.write(f"\n\n{'='*80}\nNEW SESSION: {task_text}\n{'='*80}\n")
    
    for iteration in range(1, MAX_ITERATIONS + 1):
        log(f"\nIteration {iteration}/{MAX_ITERATIONS}", "blue")
        
        recent_logs = "\n".join(read_file(LOG_FILE).splitlines()[-100:])
        
        user_prompt = f"**TASK:** {task_text}\n\n**CONTEXT:**\n{get_project_context()}\n"
        if iteration > 1:
            user_prompt += f"\n**LOGS:**\n{recent_logs}\n"
        if current_plan:
            user_prompt += f"\n**PLAN:**\n{current_plan}\n"
        user_prompt += "\nDo the work. End with ```done```.\n"
        
        log("🤔 Thinking...", "blue")
        response = call_llm(SYSTEM_PROMPT, user_prompt)
        print(f"\nAI Response:\n{response}\n")
        
        with open(LOG_FILE, 'a') as f:
            f.write(f"\n=== Iteration {iteration} ===\n{response}\n")
        
        lines = response.splitlines()
        success, done_found, action_taken = True, False, False
        in_block, cur_file, buffer = False, None, []

        for line in lines:
            if not success: break
            if line.startswith("```write:"):
                cur_file, in_block, buffer = line.replace("```write:", "").strip(), True, []
                continue
            if line.startswith("```exec"):
                cur_file, in_block, buffer = "EXEC", True, []
                continue
            if line.startswith("```prd"):
                cur_file, in_block, buffer = "PRD", True, []
                continue
            if "```done" in line.lower():
                done_found = True
                continue
            if line.strip() == "```" and in_block:
                in_block, content = False, "\n".join(buffer)
                if cur_file == "EXEC":
                    ret, out = run_command(content.strip())
                    print(f"\nOutput:\n{out}")
                    if ret != 0:
                        success = False
                        is_l, count = check_error_loop(out, task_hash)
                        if is_l: log("🔴 LOOP DETECTED!", "red"); sys.exit(1)
                    else: log("✅ OK", "green")
                elif cur_file == "PRD":
                    write_file(PRD_FILE, content + "\n"); log("📝 Updated PRD", "green")
                else:
                    write_file(os.path.join(PROJECT_ROOT, cur_file), content + "\n"); log(f"📝 Wrote {cur_file}", "green")
                action_taken = True
                continue
            if in_block: buffer.append(line)

        if success and done_found:
            log("✅ DONE!", "green")
            if task_index is not None: mark_task_complete(task_index)
            clear_plan()
            sys.exit(0)
        
        if not action_taken: log("⚠️ No action", "yellow")
        if action_taken and not ask_continue(): break

if __name__ == "__main__":
    main()
