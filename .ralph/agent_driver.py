#!/usr/bin/env python3
import sys
import json
import urllib.request
import urllib.error
import os

# CONFIG
API_KEY = "sk-vibeproxy-placeholder"
API_URL = "http://127.0.0.1:8317/v1/chat/completions"
MODEL = "gemini-claude-sonnet-4-5-thinking"

def call_llm(messages):
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.1
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.load(response)["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"API Error: {e}", file=sys.stderr)
        return None

def apply_changes(response_text):
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
            # Save file
            path = os.path.abspath(current_file) # Should be relative to cwd
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write("\n".join(write_buffer))
            files_changed.append(current_file)
            print(f"Applied change to: {current_file}")
            continue
        
        if in_block:
            write_buffer.append(line)
            
    return files_changed

def main():
    if len(sys.argv) < 2:
        print("Usage: agent_driver.py <context_file>")
        sys.exit(1)
        
    context_file = sys.argv[1]
    with open(context_file, 'r', encoding='utf-8') as f:
        context = f.read()
        
    messages = [
        {"role": "system", "content": "You are an autonomous developer. Read the context. Perform the task. Output code in ```write:path/to/file``` blocks. Output ```done``` when finished."},
        {"role": "user", "content": context}
    ]
    
    print("Sending request to VibeProxy...")
    response = call_llm(messages)
    
    if not response:
        sys.exit(1)
        
    print("\n--- AI Response ---\n")
    print(response)
    print("\n-------------------\n")
    
    changes = apply_changes(response)
    
    if changes:
        sys.exit(0)
    else:
        print("No file changes detected.")
        sys.exit(0)

if __name__ == "__main__":
    main()
