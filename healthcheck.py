#!/usr/bin/env python3
"""
Health check script for TMS Backend application.
Validates application health and critical dependencies.

Exit codes:
- 0: Healthy - all checks passed
- 1: Unhealthy - one or more checks failed
- 2: Unknown - unable to determine health status
"""

import sys
import subprocess
import os
from pathlib import Path

def check_http_endpoint():
    """Check if the backend HTTP endpoint is responding."""
    try:
        result = subprocess.run(
            ["curl", "-f", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "http://localhost:8000/health"],
            timeout=5,
            capture_output=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"HTTP check failed: {e}", file=sys.stderr)
        return False

def check_database_connectivity():
    """Check if database is accessible from the application."""
    try:
        # First try a quick HTTP call to the /health endpoint which checks DB
        result = subprocess.run(
            ["curl", "-f", "-s", "http://localhost:8000/health"],
            timeout=10,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Health endpoint checks database connectivity internally
            return True
        else:
            print("Database connectivity check failed via /health endpoint", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Database check failed: {e}", file=sys.stderr)
        return False

def check_redis_connectivity():
    """Check if Redis is accessible from the application."""
    try:
        # Redis check is also included in the /health endpoint
        result = subprocess.run(
            ["curl", "-f", "-s", "http://localhost:8000/health"],
            timeout=10,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Health endpoint checks Redis connectivity internally
            return True
        else:
            print("Redis connectivity check failed via /health endpoint", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Redis check failed: {e}", file=sys.stderr)
        return False

def main():
    """Run all health checks and exit with appropriate code."""
    checks = [
        ("HTTP endpoint", check_http_endpoint),
        ("Database connectivity", check_database_connectivity),
        ("Redis connectivity", check_redis_connectivity),
    ]

    all_passed = True
    failed_checks = []

    for check_name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
                failed_checks.append(check_name)
                print(f"FAIL: {check_name}", file=sys.stderr)
            else:
                print(f"PASS: {check_name}", file=sys.stderr)
        except Exception as e:
            all_passed = False
            failed_checks.append(f"{check_name} (exception: {e})")
            print(f"ERROR: {check_name}: {e}", file=sys.stderr)

    if all_passed:
        print("All health checks passed", file=sys.stderr)
        sys.exit(0)
    else:
        print(f"Health check failed. Failed checks: {', '.join(failed_checks)}",
              file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
