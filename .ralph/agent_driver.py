#!/usr/bin/env python3
import sys
import os
import re
import json

# Add parent dir to path to import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import utils
import llm_client

CONFIG = utils.load_config()

def apply_changes(response_text: str):
    """Парсит ответ AI и применяет изменения к файлам с использованием safe_write."""
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
                path = os.path.abspath(current_file)
                content = "\n".join(write_buffer) + "\n"
                
                success, msg = utils.safe_write(path, content)
                if success:
                    print(f"[AGENT] ✅ Записан файл: {current_file}")
                    files_changed.append(current_file)
                else:
                    print(f"[AGENT] ❌ Запись заблокирована ({current_file}): {msg}")
            continue
        
        if in_block:
            write_buffer.append(line)
    
    return files_changed

def main():
    if len(sys.argv) < 2:
        print("Usage: agent_driver.py <context_file>")
        sys.exit(1)
        
    context_file = sys.argv[1]
    if not os.path.exists(context_file):
        print(f"Error: Context file not found {context_file}")
        sys.exit(1)

    with open(context_file, 'r', encoding='utf-8') as f:
        context = f.read()

    # Инициализация клиента
    api_key = os.getenv("VIBEPROXY_API_KEY", "sk-vibeproxy-placeholder")
    proxy_url = CONFIG.get('llm', {}).get('url', "http://127.0.0.1:8317/v1")
    model = CONFIG.get('llm', {}).get('model', "gemini-2.5-flash")
    
    client = llm_client.VibeProxyClient(api_key, proxy_url, model)
    
    system_prompt = "You are an autonomous developer. Output code changes in ```write:path/to/file``` blocks. Update PRD.md when done. End with ```done```."
    
    print(f"[AGENT] Calling LLM model {model}...")
    try:
        response = client.call(system_prompt, context)
        print(f"[AGENT] Applying changes...")
        changes = apply_changes(response)
        
        if "```done```" in response.lower():
            print("[AGENT] 🎉 Task marked as DONE by agent")
            
        print(f"[AGENT] Applied {len(changes)} changes.")
    except Exception as e:
        print(f"[AGENT] ❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
