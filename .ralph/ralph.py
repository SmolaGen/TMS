#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import time

# --- CONFIGURATION ---
API_KEY = "sk-vibeproxy-placeholder"
API_URL = "http://127.0.0.1:8317/v1/chat/completions"
MODEL = "gemini-claude-sonnet-4-5-thinking"
MAX_ITERATIONS = 15

# Files inside .ralph directory (where this script lives)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TODO_FILE = os.path.join(SCRIPT_DIR, "TODO.md")
LOG_FILE = os.path.join(SCRIPT_DIR, "LOG.md")

# Project root (one level up from .ralph)
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# --- HELPERS ---
def log(msg, color="blue"):
    colors = { "blue": "\033[94m", "green": "\033[92m", "red": "\033[91m", "end": "\033[0m" }
    print(f"{colors.get(color, '')}[RALPH] {msg}{colors['end']}")

def call_llm(system_prompt, user_prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }
    headers = { "Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}" }
    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.load(response)["choices"][0]["message"]["content"]
    except urllib.error.URLError as e:
        log(f"API Error: {e}", "red")
        sys.exit(1)

def read_file(path):
    return open(path, 'r', encoding='utf-8', errors='ignore').read() if os.path.exists(path) else ""

def write_file(path, content):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f: f.write(content)

def run_command(cmd):
    log(f"Exec: {cmd}", "blue")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT)
    output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    with open(LOG_FILE, 'a') as f: f.write(f"\nCMD: {cmd}\n{output}\n")
    return output

def get_project_context():
    cmd = f"find . -maxdepth 3 -not -path '*/.*' -not -path '*venv*' -not -path '*node_modules*' | head -n 50"
    structure = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT).stdout.strip()
    
    key_files = ""
    # Check specific files in project root
    for fname in ["package.json", "requirements.txt", "Dockerfile", "docker-compose.yml", "main.py", "app.py", "README.md"]:
        fpath = os.path.join(PROJECT_ROOT, fname)
        if os.path.exists(fpath):
            content = read_file(fpath)
            key_files += f"\n--- {fname} ---\n" + "\n".join(content.splitlines()[:50]) + "\n"
    return f"Project Structure:\n{structure}\n\nKey Files:{key_files}"

# --- MAIN LOGIC ---
SYSTEM_PROMPT = """You are Ralph, an autonomous senior developer.
Your goal is to complete the tasks in .ralph/TODO.md.

Current State:
- You are an agent running inside the .ralph folder.
- The project root is one level up.
- You can read/write files relative to the project root.

INSTRUCTIONS:
1. Read TODO.md.
2. If the plan is vague, REWRITE it with detailed technical steps.
3. Pick the first unchecked task (- [ ]).
4. Perform the work (Write code, run tests).
5. Mark the task as done (- [x]).
6. If all tasks are [x], output the DONE block.

RESPONSE FORMAT (Use these blocks):

To write a file (relative to project root):
```write:src/main.py```
file content...
```

To update the plan (absolute path provided automatically):
```plan```
# Updated Plan
- [x] Task 1
- [ ] Task 2
```

To run a shell command (in project root):
```exec```
npm test
```

To finish:
```done```
Mission complete.
"""

def main():
    task = sys.argv[1] if len(sys.argv) > 1 else ""
    if task and not os.path.exists(TODO_FILE):
        write_file(TODO_FILE, f"# Plan\n- [ ] Analysis: {task}\n")
        log(f"Initialized task: {task}", "green")
    
    if not os.path.exists(TODO_FILE):
        log("No active task. Usage: ./ralph.py \"Task description\"", "red")
        sys.exit(1)

    log(f"Starting Ralph Loop for project: {PROJECT_ROOT}")

    for i in range(1, MAX_ITERATIONS + 1):
        log(f"=== Iteration {i}/{MAX_ITERATIONS} ===")
        
        recent_logs = "\n".join(read_file(LOG_FILE).splitlines()[-30:])
        user_prompt = f"""Current Plan:
{read_file(TODO_FILE)}

Recent Logs:
{recent_logs}

{get_project_context()}

Your turn. What is the next step?"""

        log("Thinking...")
        response = call_llm(SYSTEM_PROMPT, user_prompt)
        print(f"--- Response ---\n{response}\n----------------")
        
        lines = response.splitlines()
        current_file = None
        write_buffer = []
        in_write_block = False
        processed = False

        for line in lines:
            if line.strip().startswith("```write:"):
                current_file = line.strip().replace("```write:", "").strip()
                in_write_block = True; write_buffer = []; continue
            
            if line.strip().startswith("```plan"):
                current_file = TODO_FILE
                in_write_block = True; write_buffer = []; continue
                
            if line.strip().startswith("```exec"):
                current_file = "EXEC"
                in_write_block = True; write_buffer = []; continue
            
            if line.strip() == "```done```":
                log("Job done!", "green"); sys.exit(0)

            if line.strip() == "```" and in_write_block:
                in_write_block = False
                content = "\n".join(write_buffer)
                if current_file == "EXEC":
                    run_command(content.strip())
                else:
                    # If writing plan, overwrite TODO_FILE. If writing code, relative to project root.
                    target_path = current_file if current_file == TODO_FILE else os.path.join(PROJECT_ROOT, current_file)
                    log(f"Writing to {target_path}...", "green")
                    write_file(target_path, content + "\n")
                processed = True
                break  # Только одно действие за итерацию
            
            if in_write_block: write_buffer.append(line)

        if not processed: log("No actions performed.", "red")
        time.sleep(2)

if __name__ == "__main__":
    main()
