#!/bin/bash
#
# 🤖 Enterprise Ralph — Главный Оркестратор
#
# Двухуровневая агентная система с умным контекстом,
# анти-залипанием и памятью проекта.
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
SLEEP_BETWEEN=3             # Пауза между итерациями (сек)

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

# Инициализация файлов
touch "$ERROR_HISTORY"
echo "0" > "$ITERATION_FILE"

# Начало лога
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
    # Подсчёт невыполненных задач
    local pending=$(grep -c "\[ \]" "$PRD_FILE" 2>/dev/null || echo "0")
    
    if [ "$pending" -eq 0 ]; then
        log "SUCCESS" "🎉 Все задачи в PRD.md выполнены!"
        echo ""
        echo "════════════════════════════════════════════"
        echo "  ✅ MISSION COMPLETE"
        echo "════════════════════════════════════════════"
        exit 0
    fi
    
    return 0
}

get_current_task() {
    # Получаем первую невыполненную задачу
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
            log "DEBUG" "🔍 Включаем режим анализа..."
            
            # Записываем в историю
            echo "" >> "$ERROR_HISTORY"
            echo "=== Залипание обнаружено $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$ERROR_HISTORY"
            cat "$ERROR_LOG" >> "$ERROR_HISTORY"
            
            # Возвращаем 1 для включения режима DEBUG
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
    
    log "CONTEXT" "📚 Собираем контекст..."
    
    # Начало контекста
    cat > "$context_file" << 'EOF'
# 🤖 КОНТЕКСТ ДЛЯ AI-АГЕНТА

---

EOF
    
    # 1. Структура проекта
    echo "## 📁 Структура Проекта" >> "$context_file"
    echo '```' >> "$context_file"
    tree -L 2 -I 'node_modules|.venv|__pycache__|.git|.next|dist' "$PROJECT_ROOT" 2>/dev/null | head -n 50 >> "$context_file"
    echo '```' >> "$context_file"
    echo "" >> "$context_file"
    
    # 2. Системный промпт
    if [ -f "$RALPH_DIR/prompts/system_prompt.md" ]; then
        echo "---" >> "$context_file"
        cat "$RALPH_DIR/prompts/system_prompt.md" >> "$context_file"
        echo "" >> "$context_file"
    fi
    
    # 3. Технический стек
    if [ -f "$RALPH_DIR/context/tech_stack.md" ]; then
        echo "---" >> "$context_file"
        cat "$RALPH_DIR/context/tech_stack.md" >> "$context_file"
        echo "" >> "$context_file"
    fi
    
    # 4. Память проекта
    if [ -f "$MEMORY_DIR/decisions.md" ]; then
        echo "---" >> "$context_file"
        echo "## 🧠 Память Проекта" >> "$context_file"
        echo "### Архитектурные Решения" >> "$context_file"
        tail -n 30 "$MEMORY_DIR/decisions.md" >> "$context_file"
        echo "" >> "$context_file"
    fi
    
    if [ -f "$MEMORY_DIR/lessons_learned.md" ]; then
        echo "### Уроки (Lessons Learned)" >> "$context_file"
        tail -n 20 "$MEMORY_DIR/lessons_learned.md" >> "$context_file"
        echo "" >> "$context_file"
    fi
    
    # 5. PRD
    echo "---" >> "$context_file"
    echo "## 📋 Задачи (PRD)" >> "$context_file"
    cat "$PRD_FILE" >> "$context_file"
    echo "" >> "$context_file"
    
    # 6. Текущий план (если есть)
    if [ -f "$PLAN_FILE" ] && [ -s "$PLAN_FILE" ]; then
        echo "---" >> "$context_file"
        echo "## 📝 Текущий План" >> "$context_file"
        cat "$PLAN_FILE" >> "$context_file"
        echo "" >> "$context_file"
    fi
    
    # 7. Ошибка (если есть)
    if [ -f "$ERROR_LOG" ] && [ -s "$ERROR_LOG" ]; then
        echo "---" >> "$context_file"
        echo "## ⚠️ ОШИБКА НА ПРЕДЫДУЩЕЙ ИТЕРАЦИИ" >> "$context_file"
        echo "" >> "$context_file"
        echo '```' >> "$context_file"
        tail -n 50 "$ERROR_LOG" >> "$context_file"
        echo '```' >> "$context_file"
        echo "" >> "$context_file"
        echo "**ВАЖНО:** Исправь эту ошибку ПЕРЕД тем, как продолжать!" >> "$context_file"
    fi
    
    # 8. Режим DEBUG (анти-залипание)
    if ! check_error_loop; then
        echo "---" >> "$context_file"
        echo "## 🔴 РЕЖИМ DEBUG" >> "$context_file"
        echo "" >> "$context_file"
        echo "Ты уже **$FAIL_COUNT раз** пытался исправить эту ошибку и не смог." >> "$context_file"
        echo "" >> "$context_file"
        echo "**СТОП. НЕ ПИШИ КОД.**" >> "$context_file"
        echo "" >> "$context_file"
        echo "Вместо этого:" >> "$context_file"
        echo "1. Проанализируй ошибку глубже" >> "$context_file"
        echo "2. Напиши 3 гипотезы, почему это происходит" >> "$context_file"
        echo "3. Предложи ПРИНЦИПИАЛЬНО НОВЫЙ подход" >> "$context_file"
        echo "4. Запиши анализ в файл \`.ralph/memory/lessons_learned.md\`" >> "$context_file"
        
        # Сбрасываем счётчик
        FAIL_COUNT=0
        LAST_ERROR_HASH=""
    fi
    
    echo "$context_file"
}

# ═══════════════════════════════════════════════════════════════
# ЛИНТИНГ И ТЕСТЫ
# ═══════════════════════════════════════════════════════════════
run_lint() {
    log "LINT" "🔍 Запускаем быстрый линтинг..."
    
    cd "$PROJECT_ROOT"
    
    # Frontend (TypeScript)
    if [ -d "$PROJECT_ROOT/frontend" ]; then
        if ! npm run --prefix frontend typecheck 2>&1 | tee -a "$ERROR_LOG"; then
            log "LINT" "❌ TypeScript ошибки"
            return 1
        fi
    fi
    
    # Backend (Python)
    if [ -d "$PROJECT_ROOT/src" ]; then
        if command -v ruff &> /dev/null; then
            if ! ruff check src/ 2>&1 | tee -a "$ERROR_LOG"; then
                log "LINT" "❌ Python lint ошибки"
                return 1
            fi
        fi
    fi
    
    log "LINT" "✅ Линтинг пройден"
    return 0
}

run_tests() {
    log "TEST" "🧪 Запускаем тесты..."
    
    cd "$PROJECT_ROOT"
    
    # Backend тесты (pytest)
    if [ -f "$PROJECT_ROOT/pytest.ini" ]; then
        if ! pytest tests/ --tb=short 2>&1 | tee "$ERROR_LOG"; then
            log "TEST" "❌ Тесты упали"
            return 1
        fi
    fi
    
    # Frontend тесты (если есть)
    if [ -d "$PROJECT_ROOT/frontend" ] && [ -f "$PROJECT_ROOT/frontend/package.json" ]; then
        if grep -q '"test"' "$PROJECT_ROOT/frontend/package.json"; then
            if ! npm run --prefix frontend test 2>&1 | tee -a "$ERROR_LOG"; then
                log "TEST" "❌ Frontend тесты упали"
                return 1
            fi
        fi
    fi
    
    log "TEST" "✅ Тесты пройдены"
    rm -f "$ERROR_LOG"
    return 0
}

# ═══════════════════════════════════════════════════════════════
# АВТО-КОММИТ
# ═══════════════════════════════════════════════════════════════
auto_commit() {
    if [ "$AUTO_COMMIT" != "true" ]; then
        return 0
    fi
    
    local task="$1"
    local iteration="$2"
    
    cd "$PROJECT_ROOT"
    
    # Проверяем, есть ли изменения
    if git diff --quiet && git diff --staged --quiet; then
        log "COMMIT" "📝 Нет изменений для коммита"
        return 0
    fi
    
    git add -A
    git commit -m "feat(ralph): $task [итерация #$iteration]" \
        -m "Автоматический коммит от Enterprise Ralph" \
        -m "Задача: $task"
    
    log "COMMIT" "✅ Коммит создан: $task"
}

# ═══════════════════════════════════════════════════════════════
# ВЫЗОВ AI-АГЕНТА
# ═══════════════════════════════════════════════════════════════
call_agent() {
    local context_file="$1"
    local mode="$2"  # "architect" или "worker"
    
    log "AGENT" "🤖 Вызываем агента в режиме: $mode"
    
    # TODO: Заменить на реальный вызов AI CLI
    # Примеры:
    #
    # Claude Code:
    # cat "$context_file" | claude -p "Выполни задачу"
    #
    # Cursor:
    # cursor-cli --context "$context_file" --auto-approve
    #
    # OpenAI:
    # cat "$context_file" | llm -m gpt-4o "Выполни задачу"
    #
    # Anthropic API:
    # cat "$context_file" | anthropic complete --model claude-3-opus
    
    echo "⚠️ AI-агент ещё не настроен!"
    echo "Отредактируйте функцию call_agent() в ralph.sh"
    echo ""
    echo "Контекст записан в: $context_file"
    
    # Временно выходим для настройки
    return 1
}

# ═══════════════════════════════════════════════════════════════
# ГЛАВНЫЙ ЦИКЛ
# ═══════════════════════════════════════════════════════════════
main() {
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  🤖 Enterprise Ralph — Автономный AI-Агент Разработки"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    
    # Проверки
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
        
        # Получаем текущую задачу
        local current_task=$(get_current_task)
        log "TASK" "📌 Текущая задача: $current_task"
        
        # Вызов Архитектора (каждые N итераций или в начале)
        if [ $((iteration % ARCHITECT_INTERVAL)) -eq 1 ]; then
            log "ARCHITECT" "🏛️ Вызываем Архитектора для планирования..."
            # TODO: вызвать architect.sh
        fi
        
        # Сборка контекста
        local context_file=$(build_context)
        
        # Вызов Рабочего (AI)
        if ! call_agent "$context_file" "worker"; then
            log "ERROR" "❌ Агент вернул ошибку"
            # Продолжаем цикл, агент увидит ошибку на следующей итерации
        fi
        
        # Линтинг (быстрый чек)
        if [ "$LINT_FIRST" == "true" ]; then
            if ! run_lint; then
                log "LINT" "❌ Линтинг не пройден, переходим к следующей итерации"
                sleep $SLEEP_BETWEEN
                continue
            fi
        fi
        
        # Тесты
        if run_tests; then
            # Успех!
            auto_commit "$current_task" "$iteration"
            
            # Проверяем, все ли задачи выполнены
            check_completion
            
            log "SUCCESS" "✅ Итерация #$iteration завершена успешно"
        else
            log "FAIL" "❌ Тесты упали на итерации #$iteration"
        fi
        
        sleep $SLEEP_BETWEEN
    done
    
    log "LIMIT" "🛑 Достигнут лимит итераций ($MAX_ITERATIONS)"
    echo ""
    echo "════════════════════════════════════════════"
    echo "  ⏱️ ЛИМИТ ИТЕРАЦИЙ ДОСТИГНУТ"
    echo "  Проверьте логи: $LOG_FILE"
    echo "════════════════════════════════════════════"
    exit 1
}

# Запуск
main "$@"
