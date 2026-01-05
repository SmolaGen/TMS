---
description: Быстрый деплой проекта на сервер 185.207.1.122
---

Этот воркфлоу выполняет полную сборку и развертывание проекта.

// turbo-all
1. Сборка фронтенда:
```bash
cd frontend && npm run build
```

2. Синхронизация файлов бэкенда и конфигураций:
```bash
rsync -avz -e "ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
  --exclude '*/__pycache__*' \
  --exclude '*.pyc' \
  --exclude '._* ' \
  --exclude '.DS_Store' \
  src/ alembic/ requirements.txt docker-compose.yml \
  root@185.207.1.122:/root/tms/
```

3. Синхронизация статики фронтенда:
```bash
rsync -avz -e "ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
  frontend/dist/ \
  root@185.207.1.122:/var/www/tms/
```

4. Очистка временных файлов macOS на сервере:
```bash
ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@185.207.1.122 \
  "find /root/tms -name '._*' -delete"
```

5. Перезапуск сервисов и применение миграций:
```bash
ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@185.207.1.122 \
  "cd /root/tms && \
   docker-compose up -d backend ingest-worker && \
   docker-compose exec -T backend alembic upgrade head"
```

6. Проверка здоровья:
```bash
ssh -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@185.207.1.122 \
  "curl -f http://localhost:8000/health"
```
