#!/bin/bash
# Скрипт Архитектора — только планирование

RALPH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$RALPH_DIR")"
STATE_DIR="$RALPH_DIR/state"
PLAN_FILE="$STATE_DIR/current_plan.md"

mkdir -p "$STATE_DIR"

echo "🏛️ Запуск Архитектора..."
echo ""

# Собираем контекст для планирования
CONTEXT_FILE="$STATE_DIR/architect_context.md"

cat > "$CONTEXT_FILE" << 'EOF'
# РЕЖИМ: АРХИТЕКТОР

EOF

# Добавляем промпт архитектора
cat "$RALPH_DIR/prompts/architect_prompt.md" >> "$CONTEXT_FILE"
echo "" >> "$CONTEXT_FILE"

# Добавляем структуру проекта
echo "## Структура проекта" >> "$CONTEXT_FILE"
echo '```' >> "$CONTEXT_FILE"
tree -L 2 -I 'node_modules|.venv|__pycache__|.git' "$PROJECT_ROOT" 2>/dev/null | head -n 50 >> "$CONTEXT_FILE"
echo '```' >> "$CONTEXT_FILE"

# Добавляем PRD
echo "" >> "$CONTEXT_FILE"
echo "## Задачи (PRD)" >> "$CONTEXT_FILE"
cat "$PROJECT_ROOT/PRD.md" >> "$CONTEXT_FILE" 2>/dev/null || echo "PRD.md не найден"

echo "Контекст для Архитектора записан в: $CONTEXT_FILE"
echo ""
echo "TODO: Вызовите AI с этим контекстом"
echo "План будет сохранён в: $PLAN_FILE"
