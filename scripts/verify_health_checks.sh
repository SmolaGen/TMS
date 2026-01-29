#!/bin/bash
# E2E Health Check Verification Script
# This script verifies all services start and pass health checks with docker-compose
# Subtask: subtask-6-3 - Verify all services start and pass health checks

set -e

echo "==================================="
echo "E2E Health Check Verification Script"
echo "==================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
MAX_WAIT_TIME=180  # Maximum seconds to wait for services
CHECK_INTERVAL=5   # Seconds between health checks
BACKEND_URL="http://localhost:8000"

# Counters for results
PASSED=0
FAILED=0

# Function to print results
print_pass() {
    echo -e "${GREEN}PASS${NC}: $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}FAIL${NC}: $1"
    ((FAILED++))
}

print_info() {
    echo -e "${YELLOW}INFO${NC}: $1"
}

# Function to check if Docker is running
check_docker() {
    echo ""
    print_info "Checking Docker availability..."
    if docker info >/dev/null 2>&1; then
        print_pass "Docker is running"
        return 0
    else
        print_fail "Docker is not running. Please start Docker first."
        return 1
    fi
}

# Function to start services
start_services() {
    echo ""
    print_info "Starting services with docker-compose..."
    docker compose up -d postgis redis backend ingest-worker scheduler
    if [ $? -eq 0 ]; then
        print_pass "Services started successfully"
    else
        print_fail "Failed to start services"
        return 1
    fi
}

# Function to wait for a service to become healthy
wait_for_service() {
    local service=$1
    local elapsed=0

    print_info "Waiting for $service to become healthy (max ${MAX_WAIT_TIME}s)..."

    while [ $elapsed -lt $MAX_WAIT_TIME ]; do
        local status=$(docker compose ps $service --format "{{.Health}}" 2>/dev/null || echo "unknown")

        if [ "$status" == "healthy" ]; then
            print_pass "$service is healthy"
            return 0
        fi

        sleep $CHECK_INTERVAL
        elapsed=$((elapsed + CHECK_INTERVAL))
    done

    print_fail "$service did not become healthy within ${MAX_WAIT_TIME}s (status: $status)"
    return 1
}

# Function to wait for all services to be healthy
wait_for_all_services() {
    echo ""
    print_info "Waiting for all services to reach healthy state..."

    local services=("postgis" "redis" "backend" "ingest-worker" "scheduler")
    local all_healthy=true

    for service in "${services[@]}"; do
        if ! wait_for_service "$service"; then
            all_healthy=false
        fi
    done

    if [ "$all_healthy" = true ]; then
        print_pass "All core services are healthy"
        return 0
    else
        print_fail "Not all services became healthy"
        return 1
    fi
}

# Function to verify /health endpoint returns 200
verify_health_endpoint() {
    echo ""
    print_info "Verifying /health endpoint..."

    local response=$(curl -s -w "\n%{http_code}" "${BACKEND_URL}/health" 2>/dev/null)
    local status_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n-1)

    if [ "$status_code" == "200" ]; then
        print_pass "/health returns 200 OK"
        echo "  Response: $body"

        # Verify response structure
        if echo "$body" | jq -e '.status' >/dev/null 2>&1; then
            print_pass "/health response has 'status' field"
        else
            print_fail "/health response missing 'status' field"
        fi

        if echo "$body" | jq -e '.checks' >/dev/null 2>&1; then
            print_pass "/health response has 'checks' field"
        else
            print_fail "/health response missing 'checks' field"
        fi

        return 0
    else
        print_fail "/health returned $status_code (expected 200)"
        return 1
    fi
}

# Function to verify /health/detailed endpoint
verify_detailed_health_endpoint() {
    echo ""
    print_info "Verifying /health/detailed endpoint..."

    local response=$(curl -s -w "\n%{http_code}" "${BACKEND_URL}/health/detailed" 2>/dev/null)
    local status_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n-1)

    if [ "$status_code" == "200" ] || [ "$status_code" == "503" ]; then
        print_pass "/health/detailed returns $status_code"
        echo "  Response: $body"

        # Verify required checks are present
        local checks=("database" "redis")
        for check in "${checks[@]}"; do
            if echo "$body" | jq -e ".checks.$check" >/dev/null 2>&1; then
                local check_status=$(echo "$body" | jq -r ".checks.$check.status")
                if [ "$check_status" == "ok" ]; then
                    print_pass "Dependency '$check' is OK"
                else
                    print_info "Dependency '$check' status: $check_status"
                fi
            else
                print_fail "Missing '$check' in /health/detailed response"
            fi
        done

        # Optional checks (OSRM and Photon may not be running in basic setup)
        local optional_checks=("osrm" "photon")
        for check in "${optional_checks[@]}"; do
            if echo "$body" | jq -e ".checks.$check" >/dev/null 2>&1; then
                local check_status=$(echo "$body" | jq -r ".checks.$check.status")
                print_info "Optional dependency '$check' status: $check_status"
            else
                print_info "Optional dependency '$check' not present (may need routing/geocoding profiles)"
            fi
        done

        return 0
    else
        print_fail "/health/detailed returned unexpected status $status_code"
        return 1
    fi
}

# Function to test service restart behavior
test_service_restart() {
    echo ""
    print_info "Testing service restart behavior..."

    # Restart backend service
    print_info "Restarting backend service..."
    docker compose restart backend

    # Wait a moment for restart to initiate
    sleep 5

    # Wait for backend to become healthy again
    if wait_for_service "backend"; then
        print_pass "Backend recovered after restart"
    else
        print_fail "Backend did not recover after restart"
        return 1
    fi

    # Verify health endpoint still works
    local response=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/health" 2>/dev/null)
    if [ "$response" == "200" ]; then
        print_pass "/health endpoint works after restart"
    else
        print_fail "/health endpoint failed after restart (status: $response)"
        return 1
    fi
}

# Function to verify auto-recovery
test_auto_recovery() {
    echo ""
    print_info "Testing auto-recovery (simulating Redis reconnection)..."

    # Restart Redis
    print_info "Restarting Redis service..."
    docker compose restart redis

    # Wait for Redis to come back
    if wait_for_service "redis"; then
        print_pass "Redis recovered"
    else
        print_fail "Redis did not recover"
        return 1
    fi

    # Give backend a moment to reconnect
    sleep 5

    # Verify backend health check still passes
    local response=$(curl -s "${BACKEND_URL}/health" 2>/dev/null)
    local db_status=$(echo "$response" | jq -r '.checks.database.status' 2>/dev/null)
    local redis_status=$(echo "$response" | jq -r '.checks.redis.status' 2>/dev/null)

    if [ "$redis_status" == "ok" ]; then
        print_pass "Backend auto-recovered Redis connection"
    else
        print_fail "Backend did not auto-recover Redis connection (status: $redis_status)"
    fi

    if [ "$db_status" == "ok" ]; then
        print_pass "Database connection remains healthy"
    else
        print_fail "Database connection degraded (status: $db_status)"
    fi
}

# Function to check docker health status for all services
check_docker_health_status() {
    echo ""
    print_info "Checking Docker health status for all services..."

    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"

    local healthy_count=$(docker compose ps --format "{{.Health}}" 2>/dev/null | grep -c "healthy" || echo "0")
    print_info "Healthy services: $healthy_count"
}

# Function to stop services
stop_services() {
    echo ""
    print_info "Stopping services..."
    docker compose down
    if [ $? -eq 0 ]; then
        print_pass "Services stopped successfully"
    else
        print_fail "Failed to stop services cleanly"
    fi
}

# Main execution
main() {
    echo ""
    echo "Starting E2E Health Check Verification"
    echo "======================================="

    # Step 1: Check Docker
    if ! check_docker; then
        echo ""
        echo "Verification cannot proceed without Docker."
        exit 1
    fi

    # Step 2: Start services
    if ! start_services; then
        echo ""
        echo "Verification cannot proceed - failed to start services."
        exit 1
    fi

    # Step 3: Wait for all services to be healthy
    wait_for_all_services

    # Step 4: Verify /health endpoint
    verify_health_endpoint

    # Step 5: Verify /health/detailed endpoint
    verify_detailed_health_endpoint

    # Step 6: Check Docker health status
    check_docker_health_status

    # Step 7: Test service restart
    test_service_restart

    # Step 8: Test auto-recovery
    test_auto_recovery

    # Step 9: Stop services
    stop_services

    # Print summary
    echo ""
    echo "======================================="
    echo "Verification Summary"
    echo "======================================="
    echo -e "Passed: ${GREEN}$PASSED${NC}"
    echo -e "Failed: ${RED}$FAILED${NC}"

    if [ $FAILED -eq 0 ]; then
        echo ""
        echo -e "${GREEN}All E2E health check verifications passed!${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}Some verifications failed. Please review the output above.${NC}"
        exit 1
    fi
}

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
