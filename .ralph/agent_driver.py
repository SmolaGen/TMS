#!/usr/bin/env python3
"""
Enterprise Ralph — AI Agent Driver
Вызывает VibeProxy API с retry и backoff.
"""
import sys
import json
import urllib.request
import urllib.error
import os
import time

# CONFIG
API_KEY = os.getenv("VIBEPROXY_API_KEY", "sk-vibeproxy-placeholder")
API_URL = os.getenv("VIBEPROXY_URL", "http://127.0.0.1:8317/v1/chat/completions")
MODEL = os.getenv("VIBEPROXY_MODEL", "gemini-2.5-flash")  # Работающая модель VibeProxy

MAX_RETRIES = 3
RETRY_DELAY = 10  # секунд

def log(msg, level="INFO"):
    print(f"[{level}] {msg}", file=sys.stderr)

def call_llm(messages):
    """Вызов LLM API с retry и exponential backoff."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 8192
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    for attempt in range(1, MAX_RETRIES + 1):
        log(f"Запрос к VibeProxy (попытка {attempt}/{MAX_RETRIES})...")
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                data = json.load(response)
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            log(f"HTTP Error {e.code}: {e.reason}", "ERROR")
            if e.code == 429:  # Rate limit
                wait_time = RETRY_DELAY * attempt
                log(f"Rate limited. Ждём {wait_time}с...", "WARN")
                time.sleep(wait_time)
            elif e.code >= 500:  # Server error
                log(f"Server error. Ждём {RETRY_DELAY}с...", "WARN")
                time.sleep(RETRY_DELAY)
            else:
                # 400, 401 и т.д. — не ретраим
                return None
        except Exception as e:
            log(f"Error: {e}", "ERROR")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                return None
    
    log("Все попытки исчерпаны", "ERROR")
    return None

def apply_changes(response_text):
    """Парсит ответ AI и применяет изменения к файлам."""
    lines = response_text.splitlines()
    current_file = None
    write_buffer = []
    in_block = False
    files_changed = []

    for line in lines:
        if line.strip().startswith("```write:"):
            current_file = line.strip().replace("```write:", "").strip()
            in_block = True
            write_buffer = []
            continue
        
        if line.strip() == "```" and in_block:
            in_block = False
            if current_file:
                # Путь относительно cwd (PROJECT_ROOT)
                path = os.path.abspath(current_file)
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write("\n".join(write_buffer) + "\n")
                files_changed.append(current_file)
                log(f"✅ Записан файл: {current_file}")
            continue
        
        if in_block:
            write_buffer.append(line)
    
    # Проверяем на маркер завершения
    if "```done```" in response_text.lower():
        log("🎉 Агент завершил работу (done)")
        
    return files_changed

def main():
    if len(sys.argv) < 2:
        log("Usage: agent_driver.py <context_file>", "ERROR")
        sys.exit(1)
        
    context_file = sys.argv[1]
    
    if not os.path.exists(context_file):
        log(f"Файл контекста не найден: {context_file}", "ERROR")
        sys.exit(1)
    
    log(f"Читаем контекст: {context_file}")
    with open(context_file, 'r', encoding='utf-8') as f:
        context = f.read()
    
    log(f"Размер контекста: {len(context)} символов")
    
    messages = [
        {
            "role": "system",
            "content": """You are an autonomous developer. 
Read the context carefully. Perform ONE task from the PRD.
Output code changes in ```write:path/to/file``` blocks.
After completing a task, update PRD.md to mark it as [x].
Output ```done``` when completely finished."""
        },
        {"role": "user", "content": context}
    ]
    
    response = call_llm(messages)
    
    if not response:
        log("Не удалось получить ответ от AI", "ERROR")
        sys.exit(1)
    
    log(f"Получен ответ ({len(response)} символов)")
    
    # Показываем первые 500 символов для отладки
    preview = response[:500] + "..." if len(response) > 500 else response
    print(f"\n--- AI Response Preview ---\n{preview}\n---------------------------\n")
    
    changes = apply_changes(response)
    
    if changes:
        log(f"Применено изменений: {len(changes)}")
        sys.exit(0)
    else:
        log("Нет изменений файлов в ответе", "WARN")
        sys.exit(0)

if __name__ == "__main__":
    main()
