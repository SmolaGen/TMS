---
name: Testing (Pytest)
description: Best practices for writing backend tests using Pytest, fixtures, and database handling in TMS.
---

# Testing Skill

## Test Structure
- **Location**: `tests/` directory.
- **Naming**: `test_*.py`.
- **Configuration**: `tests/conftest.py` contains global fixtures.

## Key Fixtures (`conftest.py`)
Always use these fixtures to ensure isolation and proper setup.

### 1. Database Session (`db_session`)
Provides a fresh, isolated database session for each test. Tables are created before and dropped after.
```python
def test_create_user(db_session: Session):
    user = User(username="test")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
```

### 2. FastAPI Client (`client`)
Uses `TestClient` with dependency overrides to use the test database.
```python
def test_read_main(client):
    response = client.get("/")
    assert response.status_code == 200
```

### 3. Service Fixtures
Use pre-configured service fixtures like `auth_service_instance` or `driver_service_instance` when testing business logic directly.

## Integration Testing Pattern
When testing API endpoints that require authentication or DB access:
1. Use `client` fixture.
2. If Auth is needed, mock the token or use a logged-in state (check `test_api_auth.py` for examples).
3. Use `db_session` to verify side effects in the database.

## Environment Variables
`conftest.py` automatically loads `.env` and sets `APP_ENV=test`. Do not manually load `.env` in test files.
