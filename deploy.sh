#!/bin/bash

# Configuration
SERVER_USER="root"
SERVER_IP="185.207.1.122"
REMOTE_DIR="/root/Project_TMS_Avto_orders"
SSH_KEY="~/.ssh/id_ed25519"

echo "🚀 Starting deployment to $SERVER_IP..."

# 1. Sync files using rsync
# Exclude local-only files and directories
echo "📦 Syncing files..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.DS_Store' \
    --exclude '.env' \
    --exclude 'frontend/node_modules' \
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
    echo "❌ Rsync failed"
    exit 1
fi

# 2. Restart Backend Service
echo "🔄 Restarting tms-backend..."
ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP "cd $REMOTE_DIR && docker restart tms-backend"

if [ $? -ne 0 ]; then
    echo "❌ Restart failed"
    exit 1
fi

echo "✅ Deployment completed successfully!"
