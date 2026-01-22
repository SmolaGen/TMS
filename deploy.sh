#!/bin/bash

# Configuration
SERVER_USER="root"
SERVER_IP="185.207.1.122"
REMOTE_DIR="/root/Project_TMS_Avto_orders"
FRONTEND_DIR="/var/www/tms"
SSH_KEY="~/.ssh/id_ed25519"

echo "🚀 Starting deployment to $SERVER_IP..."

# 1. Sync Project Files
echo "📦 Syncing project files..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.DS_Store' \
    --exclude '.env' \
    --exclude 'frontend' \
    --exclude '.pytest_cache' \
    --exclude '.agent' \
    --exclude '.cursor' \
    --exclude '.windsurf' \
    --exclude 'docs' \
    --exclude 'tests' \
    -e "ssh -i $SSH_KEY" \
    ./ \
    $SERVER_USER@$SERVER_IP:$REMOTE_DIR/

if [ $? -ne 0 ]; then
    echo "❌ Project sync failed"
    exit 1
fi

# 2. Sync Frontend Files
echo "🖼️ Syncing frontend files..."
rsync -avz --delete \
    -e "ssh -i $SSH_KEY" \
    ./frontend/dist/ \
    $SERVER_USER@$SERVER_IP:$FRONTEND_DIR/

if [ $? -ne 0 ]; then
    echo "❌ Frontend sync failed"
    exit 1
fi

# 3. Restart Services
echo "🔄 Restarting services..."
# Restart backend container and reload system nginx
ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP "docker restart tms-backend && systemctl reload nginx"

if [ $? -ne 0 ]; then
    echo "❌ Restart failed"
    exit 1
fi

echo "✅ Deployment completed successfully!"
