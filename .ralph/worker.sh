#!/bin/bash
# Скрипт Рабочего — выполнение шагов плана

RALPH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$RALPH_DIR")"
STATE_DIR="$RALPH_DIR/state"
PLAN_FILE="$STATE_DIR/current_plan.md"

echo "👷 Запуск Рабочего..."
echo ""

if [ ! -f "$PLAN_FILE" ]; then
    echo "❌ План не найден: $PLAN_FILE"
    echo "Сначала запустите Архитектора: ./architect.sh"
    exit 1
fi

# Собираем контекст для выполнения
CONTEXT_FILE="$STATE_DIR/worker_context.md"

cat > "$CONTEXT_FILE" << 'EOF'
# РЕЖИМ: РАБОЧИЙ

EOF

# Добавляем промпт рабочего
cat "$RALPH_DIR/prompts/worker_prompt.md" >> "$CONTEXT_FILE"
echo "" >> "$CONTEXT_FILE"

# Добавляем текущий план
echo "## Текущий План" >> "$CONTEXT_FILE"
cat "$PLAN_FILE" >> "$CONTEXT_FILE"

# Добавляем ошибку, если есть
if [ -f "$STATE_DIR/error.log" ]; then
    echo "" >> "$CONTEXT_FILE"
    echo "## ⚠️ ОШИБКА" >> "$CONTEXT_FILE"
    echo '```' >> "$CONTEXT_FILE"
    tail -n 30 "$STATE_DIR/error.log" >> "$CONTEXT_FILE"
    echo '```' >> "$CONTEXT_FILE"
fi

echo "Контекст для Рабочего записан в: $CONTEXT_FILE"
echo ""
echo "TODO: Вызовите AI с этим контекстом"
