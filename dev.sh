#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Starting TMS Development Environment ===${NC}"

# 1. Environment Setup
if [ ! -f .env ]; then
    echo -e "${BLUE}Creating .env from .env.example...${NC}"
    cp .env.example .env
fi

# 2. Start Backend Services
echo -e "${BLUE}Starting Docker services (Database, Redis, Backend)...${NC}"
docker-compose up -d backend postgis redis

# Check if docker started successfully
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Backend services started successfully!${NC}"
else
    echo -e "\033[0;31mFailed to start backend services. Check docker logs.${NC}"
    exit 1
fi

# 3. Start Frontend
echo -e "${BLUE}Starting Frontend...${NC}"
cd frontend

if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    npm install
fi

echo -e "${GREEN}Starting frontend dev server...${NC}"
echo -e "${GREEN}Application will be available at: http://localhost:3000${NC}"
npm run dev
