#!/usr/bin/env python3
import os
import sys
import re
import json
import time
import hashlib
import shutil
import signal
import atexit
import subprocess
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

# Import local modules
import utils
import llm_client
from tools.registry import ToolRegistry
from memory.memory_manager import MemoryManager
from flow.flow_manager import FlowManager

# --- Global State ---
_shutdown_requested = False

def signal_handler(signum, frame):
    global _shutdown_requested
    utils.log_local("⛔ Shutdown requested, finishing current iteration...", "yellow")
    _shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# --- Paths & Config ---
PROJECT_ROOT = utils.PROJECT_ROOT
RALPH_DIR = utils.RALPH_DIR
PRD_FILE = os.path.join(PROJECT_ROOT, "PRD.md")
LOG_FILE = utils.LOG_FILE
LOGS_DIR = utils.LOGS_DIR
STATE_DIR = utils.STATE_DIR
ERROR_HISTORY_FILE = utils.ERROR_HISTORY_FILE
ARCHITECT_PROMPT_FILE = os.path.join(RALPH_DIR, "prompts", "architect_prompt.md")
PLAN_FILE = os.path.join(STATE_DIR, "current_plan.md")
SKIPPED_TASKS_FILE = os.path.join(STATE_DIR, "skipped_tasks.json")

# Constants from Config
CONFIG = utils.load_config()
MAX_ITERATIONS = CONFIG.get('execution', {}).get('max_iterations', 3)
MAX_SESSIONS_PER_TASK = CONFIG.get('execution', {}).get('max_sessions_per_task', 3)
INTERACTIVE_MODE = "--auto" not in sys.argv and CONFIG.get('execution', {}).get('interactive_mode', True)
VIBEPROXY_API_KEY = os.getenv("VIBEPROXY_API_KEY", "sk-vibeproxy-placeholder")

# Ensure directories exist
os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# --- New Modules (Phase 1) ---
tool_registry = None  # Инициализируется в main()
memory_manager = None  # Инициализируется в main()
flow_manager = None  # Инициализируется в main()

# --- LLM Client Setup ---
RETRY_CONFIG = CONFIG.get('llm', {}).get('retry_policy', {})
retry_policy = llm_client.RetryPolicy(
    initial_interval=RETRY_CONFIG.get('initial_interval', 1.0),
    backoff_factor=RETRY_CONFIG.get('backoff_factor', 2.0),
    max_interval=RETRY_CONFIG.get('max_interval', 10.0),
    max_attempts=RETRY_CONFIG.get('max_attempts', 3)
)

client = llm_client.VibeProxyClient(
    api_key=VIBEPROXY_API_KEY,
    url=CONFIG.get('llm', {}).get('url', "http://127.0.0.1:8317/v1"),
    model=CONFIG.get('llm', {}).get('model', "gemini-2.5-flash"),
    retry_policy=retry_policy
)

# --- Logging System ---
def log(message: str, color: str = "white") -> None:
    utils.log_local(message, color)

def rotate_log_if_needed():
    """Ротация LOG.md при превышении размера"""
    max_size_mb = CONFIG.get('logging', {}).get('max_log_size_mb', 10)
    max_size = max_size_mb * 1024 * 1024
    
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > max_size:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = os.path.join(LOGS_DIR, f"LOG.{timestamp}.md")
        shutil.move(LOG_FILE, archive_path)
        log(f"📦 Log rotated to {archive_path}", "cyan")

def start_task_log(task_name: str, task_index: int = 0) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"\n\n---\n\n## 🎯 Task #{task_index}: {task_name}\n**Начало:** {now}\n\n| # | Время | Статус | Действие | Детали |\n|---|-------|--------|----------|--------|\n"
    rotate_log_if_needed()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(header)

def log_iteration(iter_num: int, status: str, action: str, brief: str = "") -> None:
    now = datetime.now().strftime("%H:%M")
    status_icon = "✅" if status == "OK" else "❌" if status == "FAIL" else "⚠️"
    row = f"| {iter_num} | {now} | {status_icon} {status} | {action} | {brief} |\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(row)

def add_iteration_details(iter_num: int, meta: dict, details_list: list, error: str = None) -> None:
    content = f"\n<details>\n<summary>📝 Итерация {iter_num}: {meta.get('Action', 'Анализ')}</summary>\n\n"
    
    if meta.get('Thoughts') and "n/a" not in meta['Thoughts'].lower():
        content += f"### 🧠 Мысли\n{meta['Thoughts']}\n\n"
    
    if meta.get('Plan') and "n/a" not in meta['Plan'].lower():
        content += f"### 📋 План\n{meta['Plan']}\n\n"
        
    if details_list:
        content += "### 🛠️ Инструменты\n"
        for d in details_list:
            # Красиво форматируем вывод команд
            if d.startswith("Result (code"):
                content += f"  - *{d}*\n"
            else:
                content += f"- {d}\n"
    
    if error:
        content += f"\n### ❌ Ошибка\n```\n{error}\n```\n\n"
        
    content += "\n</details>\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(content)

def finalize_task_log(status: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    status_icon = "✅" if status == "DONE" else "❌" if status == "FAILED" else "⏭️"
    footer = f"\n**Завершено:** {now} | **Статус:** {status_icon} {status}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(footer)

# --- Sandbox Execution ---
def validate_command(command: str) -> Tuple[bool, str]:
    """Guardrail для команд по паттерну CrewAI"""
    whitelist = CONFIG.get('commands', {}).get('whitelist', [])
    blocked = CONFIG.get('commands', {}).get('blocked_patterns', [])
    
    parts = command.split()
    if not parts:
        return False, "Empty command"
    
    cmd_name = parts[0]
    if cmd_name not in whitelist:
        return False, f"Command '{cmd_name}' not in whitelist"
    
    for pattern in blocked:
        if pattern in command:
            return False, f"Blocked pattern detected: {pattern}"
    
    return True, ""

def run_command(command: str) -> Tuple[int, str]:
    """Выполняет команду в Docker контейнере (песочнице)"""
    is_safe, reason = validate_command(command)
    if not is_safe:
        return 1, f"SECURITY BLOCKED: {reason}"

    log(f"Sandbox Exec: {command}", "magenta")
    
    # Подготовка Docker команды
    # Мы маунтим корень проекта в /app внутри контейнера
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{PROJECT_ROOT}:/app",
        "-w", "/app",
        "ralph-sandbox",
        "bash", "-c", command
    ]
    
    try:
        process = subprocess.Popen(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        output = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}\nRETURN CODE: {process.returncode}"
        return process.returncode, output
    except Exception as e:
        return 1, f"Docker Execution Error: {e}"

# --- State Management ---
def get_first_unchecked_task() -> Tuple[Optional[int], Optional[str]]:
    if not os.path.exists(PRD_FILE):
        return None, None
    with open(PRD_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if re.search(r'^\s*-\s*\[\s*\]\s+', line):
            task_text = re.sub(r'^\s*-\s*\[\s*\]\s+', '', line).strip()
            return i, task_text
    return None, None

def mark_task_complete(task_line_index: int) -> None:
    if not os.path.exists(PRD_FILE): return
    with open(PRD_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    if task_line_index < len(lines):
        lines[task_line_index] = lines[task_line_index].replace("[ ]", "[x]")
        with open(PRD_FILE, 'w', encoding='utf-8') as f:
            f.writelines(lines)

def check_task_session_limit(task_hash: str) -> bool:
    history = {}
    if os.path.exists(ERROR_HISTORY_FILE):
        try:
            with open(ERROR_HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except: pass
    
    key = f"session_limit:{task_hash}"
    count = history.get(key, 0) + 1
    history[key] = count
    
    with open(ERROR_HISTORY_FILE, 'w') as f:
        json.dump(history, f)
        
    return count > MAX_SESSIONS_PER_TASK

# --- Core Logic ---
from agents.roles import AgentRole
from flow.task_stage import TaskStage


def get_system_prompt() -> str:
    """Возвращает основной системный промпт."""
    path = os.path.join(RALPH_DIR, "prompts", "system_prompt.md")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Ты — Ralph, автономный AI-разработчик."

def get_project_context() -> str:
    """Собирает контекст проекта (структура файлов и PRD)."""
    try:
        # Используем find для структуры, исключая скрытые папки
        structure = subprocess.getoutput(f"find . -maxdepth 2 -not -path '*/.*'")
    except Exception as e:
        structure = f"Error getting file structure: {e}"
        
    prd = ""
    if os.path.exists(PRD_FILE):
        try:
            with open(PRD_FILE, 'r', encoding='utf-8') as f:
                prd = f.read()
        except Exception as e:
            prd = f"Error reading PRD.md: {e}"
    
    return f"Files Structure:\n{structure}\n\nPRD Content:\n{prd}"

def get_prompt_for_role(role: Optional[AgentRole]) -> str:
    """Выбирает системный промпт в зависимости от текущей роли в DAG"""
    if not role:
        return get_system_prompt()
        
    role_file = {
        AgentRole.ARCHITECT: "architect_prompt.md",
        AgentRole.RESEARCHER: "researcher_prompt.md",
        AgentRole.DEVELOPER: "system_prompt.md",
        AgentRole.TESTER: "tester_prompt.md",
        AgentRole.REVIEWER: "reviewer_prompt.md",
    }.get(role, "system_prompt.md")
    
    prompt_path = os.path.join(RALPH_DIR, "prompts", role_file)
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    return get_system_prompt()

def execute_iteration(task_index: int, task_text: str, task_hash: str, iteration: int, current_plan: str) -> bool:
    """Выполняет одну итерацию задачи на текущей стадии DAG."""
    task_obj = flow_manager.get_task_by_index(task_index)
    current_role = task_obj.current_role if task_obj else AgentRole.DEVELOPER
    current_stage = task_obj.stage if task_obj else TaskStage.CODING
    
    role_val = current_role.value if current_role else "N/A"
    stage_val = current_stage.value if current_stage else "N/A"
    
    log(f"\nIteration {iteration}/{MAX_ITERATIONS} | Role: {role_val} | Stage: {stage_val}", "blue")
    
    if not current_role:
        log("⚠️ No role assigned for this stage. Skipping...", "yellow")
        return False
    
    recent_logs = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
            recent_logs = "".join(lines[-300:])
            
    user_prompt = f"**TASK:** {task_text}\n\n**CONTEXT:**\n{get_project_context()}\n"
    if iteration > 1:
        user_prompt += f"\n**RECENT LOGS:**\n{recent_logs}\n"
    if current_plan:
        user_prompt += f"\n**CURRENT PLAN:**\n{current_plan}\n"
    
    if memory_manager:
        memory_context = memory_manager.recall(task_text)
        user_prompt += f"\n**MEMORY CONTEXT:**\n{memory_context}\n"
    
    user_prompt += f"\nCurrently you are acting as {current_role.value}. Stage: {current_stage.value}.\n"
    user_prompt += "\nDo the work. Remember to start with ```log and end with ```done```.\n"
    
    log("🤔 Thinking...", "blue")
    system_prompt = get_prompt_for_role(current_role)
    response = client.call(system_prompt, user_prompt)
    
    # Meta parsing
    meta = {"Action": "N/A", "Thoughts": "N/A", "Plan": "N/A"}
    log_match = re.search(r"```log\s+(.*?)\s+```", response, re.DOTALL | re.IGNORECASE)
    if log_match:
        log_block = log_match.group(1).strip()
        current_key = None
        for line in log_block.splitlines():
            line_lower = line.lower()
            if ":" in line and any(k in line_lower for k in ["action", "thoughts", "plan", "мысли", "план"]):
                k, v = line.split(":", 1)
                k_clean = k.strip().lower()
                if "action" in k_clean: current_key = "Action"
                elif "thoughts" in k_clean: current_key = "Thoughts"
                elif "plan" in k_clean: current_key = "Plan"
                if current_key:
                    if meta[current_key] == "N/A": meta[current_key] = v.strip()
                    else: meta[current_key] += "\n" + v.strip()
            elif current_key and line.strip():
                meta[current_key] += "\n" + line.strip()
        
        log("---", "blue")
        if meta["Thoughts"] != "N/A": log(f"🧠 {meta['Thoughts']}", "magenta")
        if meta["Action"] != "N/A": log(f"🎬 {meta['Action']}", "cyan")
        log("---", "blue")

    # Block Parsing
    lines = response.splitlines()
    success, done_found, action_taken = True, False, False
    in_block, cur_file, buffer = False, None, []
    iter_details = []
    modified_files = []

    for line in lines:
        if not success: break
        if line.startswith("```tool:"):
            tool_name = line.replace("```tool:", "").strip()
            cur_file, in_block, buffer = f"TOOL:{tool_name}", True, []
            continue
        if line.startswith("```write:"):
            cur_file, in_block, buffer = line.replace("```write:", "").strip(), True, []
            continue
        if line.startswith("```exec"):
            cur_file, in_block, buffer = "EXEC", True, []
            continue
        if "```done" in line.lower() or "<promise>plan_ready</promise>" in line.lower():
            done_found = True
            continue
        
        if line.strip() == "```" and in_block:
            in_block, content = False, "\n".join(buffer)
            if cur_file.startswith("TOOL:"):
                tool_name = cur_file.replace("TOOL:", "")
                try:
                    params = json.loads(content)
                    if tool_registry:
                        res = tool_registry.execute_tool(tool_name, params)
                        if res['success']:
                            log(f"✅ {tool_name} OK", "green")
                            if tool_name == "write_file": modified_files.append(params['path'])
                        else:
                            log(f"❌ {tool_name} FAIL: {res['message']}", "red")
                            success = False
                        iter_details.append(f"{tool_name}: {res['message']}")
                except:
                    success = False
            elif cur_file == "EXEC":
                iter_details.append(f"Exec: {content.strip()}")
                ret, out = run_command(content.strip())
                if ret != 0: success = False
                action_taken = True
            else:
                path = os.path.join(PROJECT_ROOT, cur_file)
                ok, msg = utils.safe_write(path, content + "\n")
                if ok: modified_files.append(cur_file)
                else: success = False
                action_taken = True
            continue
        if in_block: buffer.append(line)

    # Обработка переходов в Flow Manager
    handoff = flow_manager.process_stage_result(task_index, success and done_found, {
        "success": success and done_found,
        "role": current_role.value,
        "stage": current_stage.value,
        "modified_files": modified_files,
        "response": response
    })
    
    status = "OK" if success else "FAIL"
    log_iteration(iteration, status, meta["Action"][:50], "Stage: " + handoff.next_stage.value)
    
    if memory_manager:
        memory_manager.remember(task_hash, task_text, iteration, meta["Thoughts"], meta["Plan"], json.dumps(iter_details), success, None, modified_files)

    # Если стадия изменилась на DONE, задача полностью завершена
    return handoff.next_stage == TaskStage.DONE

def main():
    global tool_registry, memory_manager, flow_manager
    log("🚀 Ralph Orchestrator v3.1 (DAG Flow Manager)", "cyan")
    
    tool_registry = ToolRegistry()
    memory_manager = MemoryManager()
    flow_manager = FlowManager(PRD_FILE)
    
    cycle = flow_manager.check_circular_dependencies()
    if cycle: log(f"⚠️ Circular dependency: {cycle}", "yellow")
    
    subprocess.run(["docker", "build", "-t", "ralph-sandbox", "-f", os.path.join(RALPH_DIR, "Dockerfile.sandbox"), PROJECT_ROOT], check=False)

    while not _shutdown_requested:
        task_index, task_text = flow_manager.get_next_task()
        if not task_text:
            log("🎉 All tasks completed or PRD empty!", "green")
            break
            
        task_hash = utils.generate_task_hash(task_index, task_text)
        
        # Проверяем, не выполнена ли задача ранее
        if memory_manager and memory_manager.long_term.get_task_status(task_hash) == "done":
            log(f"⏭️ Skipping Task #{task_index + 1} (already done in memory)", "green")
            mark_task_complete(task_index)
            continue
            
        if memory_manager:
            memory_manager.long_term.store_task(task_hash, task_text)

        log(f"📋 Task #{task_index + 1}: {task_text}", "yellow")
        start_task_log(task_text, task_index + 1)
        
        current_plan = ""
        if os.path.exists(PLAN_FILE):
            with open(PLAN_FILE, 'r') as f: current_plan = f.read()

        task_completed = False
        for iteration in range(1, MAX_ITERATIONS + 1):
            if _shutdown_requested: break
            
            task_completed = execute_iteration(task_index, task_text, task_hash, iteration, current_plan)
            
            # Check if task became BLOCKED
            current_task_obj = flow_manager.get_task_by_index(task_index)
            if current_task_obj and current_task_obj.stage == TaskStage.BLOCKED:
                log("⛔ Task is BLOCKED. Stopping iterations.", "red")
                break
                
            if task_completed:
                mark_task_complete(task_index)
                if memory_manager:
                    memory_manager.mark_task_complete(task_hash)
                finalize_task_log("DONE")
                if os.path.exists(PLAN_FILE): os.remove(PLAN_FILE)
                break
            
            if INTERACTIVE_MODE:
                log("Wait for intervention or [Enter] to continue...", "cyan")
                choice = input("> ").strip().lower()
                if choice == 'q': sys.exit(0)
                if choice == 's': break
        
        if not task_completed:
            if memory_manager:
                memory_manager.mark_task_failed(task_hash)
            finalize_task_log("STALLED")
            time.sleep(5)

    if _shutdown_requested:
        log("👋 Graceful shutdown complete.", "green")

if __name__ == "__main__":
    main()
