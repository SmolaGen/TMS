#!/bin/bash
#
# 🤖 Enterprise Ralph — Главный Оркестратор (VibeProxy Enabled)
#

set -e

# ═══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════
MAX_ITERATIONS=50           # Максимум итераций
ERROR_THRESHOLD=3           # Порог для включения режима DEBUG
LINT_FIRST=true             # Линтинг перед тестами
AUTO_COMMIT=true            # Авто-коммит при успехе
ARCHITECT_INTERVAL=5        # Вызов Архитектора каждые N итераций
SLEEP_BETWEEN=10            # Пауза между итерациями (сек) - увеличена для rate limit

# Пути
RALPH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$RALPH_DIR")"
PRD_FILE="$PROJECT_ROOT/PRD.md"

# Директории
STATE_DIR="$RALPH_DIR/state"
LOGS_DIR="$RALPH_DIR/logs"
MEMORY_DIR="$RALPH_DIR/memory"

# Файлы состояния
LOG_FILE="$LOGS_DIR/activity.log"
ERROR_LOG="$STATE_DIR/error.log"
ERROR_HISTORY="$STATE_DIR/error_history.log"
ITERATION_FILE="$STATE_DIR/iteration_count.txt"
PLAN_FILE="$STATE_DIR/current_plan.md"

# ═══════════════════════════════════════════════════════════════
# ИНИЦИАЛИЗАЦИЯ
# ═══════════════════════════════════════════════════════════════
mkdir -p "$STATE_DIR" "$LOGS_DIR" "$MEMORY_DIR"

touch "$ERROR_HISTORY"
echo "0" > "$ITERATION_FILE"

echo "" >> "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════════" >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') | [START] 🚀 Enterprise Ralph запущен" >> "$LOG_FILE"
echo "═══════════════════════════════════════════════════════════════" >> "$LOG_FILE"

# ═══════════════════════════════════════════════════════════════
# УТИЛИТЫ
# ═══════════════════════════════════════════════════════════════
log() {
    local level="$1"
    local message="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | [$level] $message" >> "$LOG_FILE"
    echo "[$level] $message"
}

check_prd_exists() {
    if [ ! -f "$PRD_FILE" ]; then
        log "ERROR" "❌ Файл PRD.md не найден в корне проекта!"
        echo ""
        echo "Создайте файл PRD.md с задачами:"
        echo ""
        echo "# План разработки"
        echo ""
        echo "## Epic 1: Название"
        echo "- [ ] Первая задача"
        echo "- [ ] Вторая задача"
        exit 1
    fi
}

check_completion() {
    local pending=$(grep -c "\[ \]" "$PRD_FILE" 2>/dev/null || echo "0")
    if [ "$pending" -eq 0 ]; then
        log "SUCCESS" "🎉 Все задачи в PRD.md выполнены!"
        exit 0
    fi
    return 0
}

get_current_task() {
    grep -n "\[ \]" "$PRD_FILE" | head -n 1 | sed 's/.*\[ \] //' | head -c 80
}

# ═══════════════════════════════════════════════════════════════
# АНТИ-ЗАЛИПАНИЕ
# ═══════════════════════════════════════════════════════════════
FAIL_COUNT=0
LAST_ERROR_HASH=""

check_error_loop() {
    if [ ! -f "$ERROR_LOG" ]; then
        FAIL_COUNT=0
        return 0
    fi
    local current_hash=$(md5 -q "$ERROR_LOG" 2>/dev/null || md5sum "$ERROR_LOG" | cut -d' ' -f1)
    if [ "$current_hash" == "$LAST_ERROR_HASH" ]; then
        ((FAIL_COUNT++))
        if [ $FAIL_COUNT -ge $ERROR_THRESHOLD ]; then
            log "WARNING" "⚠️ Обнаружено залипание! Ошибка повторяется $FAIL_COUNT раз"
            echo "" >> "$ERROR_HISTORY"
            echo "=== Залипание обнаружено $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$ERROR_HISTORY"
            cat "$ERROR_LOG" >> "$ERROR_HISTORY"
            return 1
        fi
    else
        FAIL_COUNT=1
        LAST_ERROR_HASH="$current_hash"
    fi
    return 0
}

# ═══════════════════════════════════════════════════════════════
# СБОРКА КОНТЕКСТА
# ═══════════════════════════════════════════════════════════════
build_context() {
    local context_file="$STATE_DIR/current_context.md"
    log "CONTEXT" "📚 Собираем контекст..." >&2
    
    cat > "$context_file" << 'EOF'
# 🤖 КОНТЕКСТ ДЛЯ AI-АГЕНТА
---
EOF
    
    echo "## 📁 Структура Проекта" >> "$context_file"
    echo '```' >> "$context_file"
    tree -L 2 -I 'node_modules|.venv|__pycache__|.git|.next|dist' "$PROJECT_ROOT" 2>/dev/null | head -n 50 >> "$context_file"
    echo '```' >> "$context_file"
    echo "" >> "$context_file"
    
    if [ -f "$RALPH_DIR/prompts/system_prompt.md" ]; then
        echo "---" >> "$context_file"
        cat "$RALPH_DIR/prompts/system_prompt.md" >> "$context_file"
        echo "" >> "$context_file"
    fi
    
    echo "---" >> "$context_file"
    echo "## 📋 Задачи (PRD)" >> "$context_file"
    cat "$PRD_FILE" >> "$context_file"
    echo "" >> "$context_file"
    
    if [ -f "$ERROR_LOG" ] && [ -s "$ERROR_LOG" ]; then
        echo "---" >> "$context_file"
        echo "## ⚠️ ОШИБКА НА ПРЕДЫДУЩЕЙ ИТЕРАЦИИ" >> "$context_file"
        echo '```' >> "$context_file"
        tail -n 50 "$ERROR_LOG" >> "$context_file"
        echo '```' >> "$context_file"
    fi
    
    echo "$context_file"
}

# ═══════════════════════════════════════════════════════════════
# ЛИНТИНГ И ТЕСТЫ
# ═══════════════════════════════════════════════════════════════
run_lint() {
    log "LINT" "🔍 Запускаем быстрый линтинг..."
    cd "$PROJECT_ROOT"
    if [ -d "$PROJECT_ROOT/frontend" ]; then
        if ! npm run --prefix frontend typecheck 2>&1 | tee -a "$ERROR_LOG"; then
            log "LINT" "❌ TypeScript ошибки"
            return 1
        fi
    fi
    log "LINT" "✅ Линтинг пройден"
    return 0
}

run_tests() {
    log "TEST" "🧪 Запускаем тесты..."
    cd "$PROJECT_ROOT"
    # Добавьте свои команды тестов сюда
    log "TEST" "✅ Тесты пройдены (заглушка)"
    rm -f "$ERROR_LOG"
    return 0
}

# ═══════════════════════════════════════════════════════════════
# АВТО-КОММИТ
# ═══════════════════════════════════════════════════════════════
auto_commit() {
    if [ "$AUTO_COMMIT" != "true" ]; then return 0; fi
    local task="$1"
    local iteration="$2"
    cd "$PROJECT_ROOT"
    if git diff --quiet && git diff --staged --quiet; then return 0; fi
    
    git add -A
    git commit -m "feat(ralph): $task [#$iteration]" || true
    log "COMMIT" "✅ Коммит создан"
}

# ═══════════════════════════════════════════════════════════════
# ВЫЗОВ AI-АГЕНТА
# ═══════════════════════════════════════════════════════════════
call_agent() {
    local context_file="$1"
    local mode="$2"
    
    log "AGENT" "🤖 Вызываем агента (Mode: $mode)..."
    
    # ВЫЗОВ PYTHON ДРАЙВЕРА С VIBEPROXY
    if python3 "$RALPH_DIR/agent_driver.py" "$context_file"; then
        log "AGENT" "✅ Агент успешно отработал"
        return 0
    else
        log "ERROR" "❌ Сбой агента"
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════
# ГЛАВНЫЙ ЦИКЛ
# ═══════════════════════════════════════════════════════════════
main() {
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  🤖 Enterprise Ralph — Автономный AI-Агент (VibeProxy)"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    
    check_prd_exists
    check_completion
    
    local iteration=0
    
    while [ $iteration -lt $MAX_ITERATIONS ]; do
        ((iteration++))
        echo "$iteration" > "$ITERATION_FILE"
        
        echo ""
        echo "────────────────────────────────────────────"
        echo "  🔄 Итерация #$iteration / $MAX_ITERATIONS"
        echo "────────────────────────────────────────────"
        
        local current_task=$(get_current_task)
        log "TASK" "📌 Текущая задача: $current_task"
        
        # Сборка контекста
        local context_file=$(build_context)
        
        # Вызов Рабочего
        if ! call_agent "$context_file" "worker"; then
            log "ERROR" "❌ Агент вернул ошибку"
        fi
        
        # Тесты
        if run_tests; then
            auto_commit "$current_task" "$iteration"
            check_completion
            log "SUCCESS" "✅ Итерация завершена"
        else
            log "FAIL" "❌ Тесты упали"
        fi
        
        sleep $SLEEP_BETWEEN
    done
    
    log "LIMIT" "🛑 Достигнут лимит итераций"
    exit 1
}

main "$@"
