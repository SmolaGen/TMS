"""
End-to-End verification tests for health check infrastructure.
These tests verify the health check code structure and integration points.

For full Docker-based verification, run: ./scripts/verify_health_checks.sh
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestHealthCheckInfrastructure:
    """Verify all health check infrastructure is properly configured."""

    def test_docker_compose_health_checks_configured(self):
        """Verify docker-compose.yml has health checks for all required services."""
        import yaml

        compose_path = os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')
        with open(compose_path, 'r') as f:
            compose = yaml.safe_load(f)

        services = compose.get('services', {})

        # Core services that must have health checks
        required_healthchecks = ['postgis', 'redis', 'backend', 'ingest-worker', 'scheduler']

        for service in required_healthchecks:
            assert service in services, f"Service {service} not found in docker-compose.yml"
            assert 'healthcheck' in services[service], f"Service {service} missing healthcheck"

    def test_health_check_intervals_reasonable(self):
        """Verify health check intervals are reasonable (not too aggressive)."""
        import yaml

        compose_path = os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')
        with open(compose_path, 'r') as f:
            compose = yaml.safe_load(f)

        services = compose.get('services', {})

        for name, service in services.items():
            if 'healthcheck' in service:
                hc = service['healthcheck']
                interval = hc.get('interval', '30s')
                timeout = hc.get('timeout', '10s')

                # Parse interval (remove 's' suffix and convert to int)
                interval_sec = int(interval.replace('s', ''))
                timeout_sec = int(timeout.replace('s', ''))

                # Interval should be at least 10 seconds
                assert interval_sec >= 10, f"Service {name} has too aggressive health check interval: {interval}"
                # Timeout should be less than interval
                assert timeout_sec < interval_sec, f"Service {name} has timeout >= interval"

    def test_restart_policy_configured(self):
        """Verify restart policies are configured for all services."""
        import yaml

        compose_path = os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')
        with open(compose_path, 'r') as f:
            compose = yaml.safe_load(f)

        services = compose.get('services', {})

        for name, service in services.items():
            assert 'restart' in service, f"Service {name} missing restart policy"
            assert service['restart'] == 'unless-stopped', f"Service {name} should use 'unless-stopped' restart policy"


class TestHealthCheckCode:
    """Verify health check code modules are properly structured."""

    def test_health_check_module_imports(self):
        """Verify all health check modules can be imported."""
        from src.core.health_check import (
            HealthStatus,
            HealthCheckResult,
            HealthChecker,
            SyncHealthChecker,
            CompositeHealthChecker,
        )

        assert hasattr(HealthStatus, 'OK')
        assert hasattr(HealthStatus, 'DEGRADED')
        assert hasattr(HealthStatus, 'FAILED')

    def test_circuit_breaker_module_imports(self):
        """Verify circuit breaker module can be imported."""
        from src.core.circuit_breaker import (
            CircuitBreaker,
            CircuitBreakerOpenError,
            CircuitBreakerState,
        )

        assert hasattr(CircuitBreakerState, 'CLOSED')
        assert hasattr(CircuitBreakerState, 'OPEN')
        assert hasattr(CircuitBreakerState, 'HALF_OPEN')

    def test_graceful_degradation_imports(self):
        """Verify graceful degradation module can be imported."""
        from src.core.graceful_degradation import (
            GracefulDegradationManager,
            DegradationLevel,
            FallbackStrategy,
            FallbackCache,
        )

        assert hasattr(DegradationLevel, 'NONE')
        assert hasattr(DegradationLevel, 'PARTIAL')
        assert hasattr(DegradationLevel, 'COMPLETE')

    def test_health_checker_classes_defined(self):
        """Verify health checker classes are properly defined."""
        from src.fastapi_routes import (
            DatabaseHealthChecker,
            RedisHealthChecker,
            OSRMHealthChecker,
            PhotonHealthChecker,
        )

        # Verify they inherit from HealthChecker
        from src.core.health_check import HealthChecker

        assert issubclass(DatabaseHealthChecker, HealthChecker)
        assert issubclass(RedisHealthChecker, HealthChecker)
        assert issubclass(OSRMHealthChecker, HealthChecker)
        assert issubclass(PhotonHealthChecker, HealthChecker)


class TestHealthCheckScript:
    """Verify the healthcheck.py script is properly structured."""

    def test_healthcheck_script_exists(self):
        """Verify healthcheck.py exists in project root."""
        script_path = os.path.join(os.path.dirname(__file__), '..', 'healthcheck.py')
        assert os.path.exists(script_path), "healthcheck.py not found"

    def test_healthcheck_script_has_main(self):
        """Verify healthcheck.py has main function."""
        import importlib.util

        script_path = os.path.join(os.path.dirname(__file__), '..', 'healthcheck.py')
        spec = importlib.util.spec_from_file_location("healthcheck", script_path)
        module = importlib.util.module_from_spec(spec)

        # Check the module has expected functions
        with open(script_path, 'r') as f:
            content = f.read()

        assert 'def main()' in content, "healthcheck.py missing main() function"
        assert 'def check_http_endpoint()' in content, "healthcheck.py missing check_http_endpoint()"
        assert 'def check_database_connectivity()' in content, "healthcheck.py missing check_database_connectivity()"
        assert 'def check_redis_connectivity()' in content, "healthcheck.py missing check_redis_connectivity()"


class TestDockerfileHealthCheck:
    """Verify Dockerfile has proper health check configuration."""

    def test_dockerfile_has_healthcheck(self):
        """Verify Dockerfile includes HEALTHCHECK instruction."""
        dockerfile_path = os.path.join(os.path.dirname(__file__), '..', 'Dockerfile')
        with open(dockerfile_path, 'r') as f:
            content = f.read()

        assert 'HEALTHCHECK' in content, "Dockerfile missing HEALTHCHECK instruction"
        assert 'healthcheck.py' in content, "Dockerfile should reference healthcheck.py"

    def test_dockerfile_healthcheck_interval(self):
        """Verify Dockerfile HEALTHCHECK has reasonable interval."""
        dockerfile_path = os.path.join(os.path.dirname(__file__), '..', 'Dockerfile')
        with open(dockerfile_path, 'r') as f:
            content = f.read()

        # Check for reasonable interval (at least 30s)
        assert '--interval=30s' in content or '--interval=60s' in content, \
            "Dockerfile HEALTHCHECK should have interval of at least 30s"


class TestWorkerHealthChecks:
    """Verify worker health check implementations."""

    def test_ingest_worker_health_check(self):
        """Verify ingest worker has health check capability."""
        from src.workers.ingest_worker import IngestWorker

        # Verify the class has health check method
        assert hasattr(IngestWorker, 'get_health_status'), \
            "IngestWorker missing get_health_status method"

    def test_scheduler_health_check(self):
        """Verify scheduler worker has health check capability."""
        from src.workers.scheduler import TMSProjectScheduler

        # Verify the class has health check method
        assert hasattr(TMSProjectScheduler, 'get_health_status'), \
            "TMSProjectScheduler missing get_health_status method"

    def test_worker_health_check_server(self):
        """Verify worker health check server can be imported."""
        from src.workers.health_check_server import (
            start_health_check_server,
            WorkerHealthCheckServer,
        )

        # Verify the server class has expected methods
        assert hasattr(WorkerHealthCheckServer, 'register_worker')
        assert hasattr(WorkerHealthCheckServer, 'start')
        assert hasattr(WorkerHealthCheckServer, 'stop')


class TestConfigurationSettings:
    """Verify health check configuration is properly defined."""

    def test_health_check_config_exists(self):
        """Verify health check configuration parameters exist."""
        from src.config import settings

        assert hasattr(settings, 'HEALTH_CHECK_TIMEOUT'), "Missing HEALTH_CHECK_TIMEOUT"
        assert hasattr(settings, 'HEALTH_CHECK_INTERVAL'), "Missing HEALTH_CHECK_INTERVAL"
        assert hasattr(settings, 'HEALTH_CHECK_RETRIES'), "Missing HEALTH_CHECK_RETRIES"

    def test_circuit_breaker_config_exists(self):
        """Verify circuit breaker configuration parameters exist."""
        from src.config import settings

        assert hasattr(settings, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD'), \
            "Missing CIRCUIT_BREAKER_FAILURE_THRESHOLD"
        assert hasattr(settings, 'CIRCUIT_BREAKER_TIMEOUT'), \
            "Missing CIRCUIT_BREAKER_TIMEOUT"
        assert hasattr(settings, 'CIRCUIT_BREAKER_RECOVERY_TIMEOUT'), \
            "Missing CIRCUIT_BREAKER_RECOVERY_TIMEOUT"

    def test_config_values_reasonable(self):
        """Verify configuration values are reasonable."""
        from src.config import settings

        # Health check timeout should be positive
        assert settings.HEALTH_CHECK_TIMEOUT > 0
        # Circuit breaker failure threshold should be at least 1
        assert settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD >= 1
        # Circuit breaker timeout should be positive
        assert settings.CIRCUIT_BREAKER_TIMEOUT > 0


class TestVerificationScript:
    """Verify the E2E verification script exists and is executable."""

    def test_verification_script_exists(self):
        """Verify verify_health_checks.sh exists."""
        script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'verify_health_checks.sh')
        assert os.path.exists(script_path), "verify_health_checks.sh not found"

    def test_verification_script_executable(self):
        """Verify verify_health_checks.sh is executable."""
        script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'verify_health_checks.sh')
        assert os.access(script_path, os.X_OK), "verify_health_checks.sh is not executable"

    def test_verification_script_has_required_functions(self):
        """Verify verify_health_checks.sh has all required verification functions."""
        script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'verify_health_checks.sh')
        with open(script_path, 'r') as f:
            content = f.read()

        required_functions = [
            'check_docker',
            'start_services',
            'wait_for_service',
            'verify_health_endpoint',
            'verify_detailed_health_endpoint',
            'test_service_restart',
            'test_auto_recovery',
            'stop_services',
        ]

        for func in required_functions:
            assert func in content, f"verify_health_checks.sh missing function: {func}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
