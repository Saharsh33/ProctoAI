# Docker Testing Guide

## Running Tests with Docker

### Prerequisites
Ensure your environment is set up:
```bash
cp .env.example .env
```

## Test Commands

### Run All Tests
```bash
# Using make
make test

# Using docker-compose directly
docker-compose exec backend pytest

# Using helper script
./docker-helper.sh test
```

### Run Tests with Coverage
```bash
# Using make
make test-cov

# Using docker-compose directly
docker-compose exec backend pytest --cov=app --cov-report=html tests/

# View coverage report (after running)
open htmlcov/index.html
```

### Run Specific Test File
```bash
make test TEST_PATH=tests/test_auth.py
docker-compose exec backend pytest tests/test_auth.py
```

### Run Tests Matching Pattern
```bash
# Tests containing "auth" in name
docker-compose exec backend pytest -k auth

# Tests for a specific class
docker-compose exec backend pytest -k "TestAuth"
```

### Run Tests with Different Verbosity
```bash
# Verbose output
docker-compose exec backend pytest -v

# Very verbose with local variables
docker-compose exec backend pytest -vv

# Quiet mode
docker-compose exec backend pytest -q
```

### Run Tests and Stop on First Failure
```bash
docker-compose exec backend pytest -x
```

### Run Last Failed Tests
```bash
docker-compose exec backend pytest --lf
```

### Run Failed Tests First
```bash
docker-compose exec backend pytest --ff
```

## Continuous Testing (Development)

### Setup
1. Start development environment:
```bash
make up-dev
```

2. In another terminal, start pytest with watch:
```bash
docker-compose exec backend pytest-watch
```

Or use the development container with pytest-watch:
```bash
docker-compose exec backend python -m pytest_watch
```

## Test Environment

### Database for Tests
Tests use a separate test database (auto-created from fixtures):

```python
# In your test files, use the provided fixtures:
@pytest.fixture
def db(test_db):
    """Database session for testing"""
    return test_db

def test_something(db):
    # db is automatically rolled back after test
    pass
```

### Fixtures Available

Create a `conftest.py` in your tests directory:

```python
import pytest
from app.db.session import SessionLocal, engine
from app.models.base import Base

@pytest.fixture(scope="session")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db(test_db):
    """Database session for each test"""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()
```

## Performance Testing

### Load Testing with Locust
```bash
# Install locust
pip install locust

# Create locustfile.py in fastapi-backend/

# Run load tests
docker-compose exec backend locust -f locustfile.py --host=http://localhost:8000
```

### Example Locustfile
```python
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 5)
    
    @task
    def health_check(self):
        self.client.get("/health")
    
    @task
    def list_exams(self):
        self.client.get("/api/v1/exams/")
```

## Integration Testing

Run tests with actual services:

```bash
# Start test environment
docker-compose -f docker-compose.dev.yml up

# In another terminal, run integration tests
docker-compose exec backend pytest tests/integration/ -v
```

## Debugging Tests

### Using PDB (Python Debugger)
```bash
# Add breakpoint in your test:
def test_something():
    x = 5
    breakpoint()  # Debugger will stop here
    assert x == 5

# Run with -s flag to see debug output
docker-compose exec backend pytest -s tests/test_file.py
```

### Interactive Python Shell
```bash
docker-compose exec backend python -i -c "
from app.db.session import SessionLocal
from app.models.user import User
db = SessionLocal()
users = db.query(User).all()
"
```

### View Pytest Output
```bash
# Show print statements
docker-compose exec backend pytest -s

# Show local variables on failure
docker-compose exec backend pytest -l

# Show setup and teardown
docker-compose exec backend pytest -vs --setup-show
```

## Test Organization

Recommended structure:
```
tests/
├── conftest.py              # Shared fixtures
├── __init__.py
├── test_auth.py             # Authentication tests
├── test_exam.py             # Exam API tests
├── test_reports.py          # Reporting tests
├── test_proctoring.py       # Proctoring tests
├── integration/             # Integration tests
│   ├── conftest.py
│   ├── test_full_flow.py
│   └── test_database.py
├── unit/                    # Unit tests
│   ├── test_validators.py
│   └── test_utils.py
└── fixtures/               # Test data
    ├── users.json
    └── exams.json
```

## Continuous Integration Testing

### GitHub Actions
Tests run automatically on:
- Push to `main` or `dev` branch
- Pull requests

Workflow file: `.github/workflows/docker.yml`

Run locally to test before pushing:
```bash
# Simulate CI workflow
docker-compose build backend
docker-compose run --rm backend pytest
docker-compose run --rm backend flake8 app
docker-compose run --rm backend black --check app
```

## Test Markers

Use pytest markers for categorizing tests:

```python
import pytest

@pytest.mark.slow
def test_heavy_operation():
    pass

@pytest.mark.integration
def test_with_database():
    pass

@pytest.mark.unit
def test_function():
    pass
```

Run by marker:
```bash
# Only slow tests
docker-compose exec backend pytest -m slow

# Skip slow tests
docker-compose exec backend pytest -m "not slow"

# Integration tests only
docker-compose exec backend pytest -m integration
```

## Reporting

### Generate Coverage Report
```bash
make test-cov

# Open report
open htmlcov/index.html
```

### Generate HTML Test Report
```bash
docker-compose exec backend pytest --html=report.html --self-contained-html

# Open report
open report.html
```

### Generate JUnit XML Report
```bash
docker-compose exec backend pytest --junit-xml=test-results.xml
```

## Troubleshooting

### Tests Fail with Database Locked
```bash
# Kill any lingering connections
docker-compose exec postgres pkill -f postgres

# Restart
make restart-prod
make test
```

### Fixtures Not Found
Ensure `conftest.py` is in your tests directory:
```bash
ls tests/conftest.py
```

### Import Errors in Tests
Verify the app module is importable:
```bash
docker-compose exec backend python -c "import app"
```

### Tests Run Too Slow
1. Use `-x` flag to stop on first failure
2. Run specific tests: `pytest tests/test_auth.py`
3. Use markers: `pytest -m unit`
4. Add `@pytest.mark.skip` for slow tests during dev

## Best Practices

1. **Keep tests fast** - Use fixtures and factories
2. **Test isolation** - Each test should be independent
3. **Clear names** - Test names should describe what's being tested
4. **Mock external services** - Don't call real APIs in tests
5. **Use factories** - Generate test data with factory_boy
6. **One assertion per test** - When possible
7. **Test error cases** - Not just the happy path
8. **Keep fixtures simple** - Complex fixtures make tests hard to debug

## Example Test Structure

```python
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.db.session import SessionLocal

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

class TestAuth:
    def test_login_success(self, client):
        response = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "password"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    def test_login_invalid_credentials(self, client):
        response = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "wrong"}
        )
        assert response.status_code == 401
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [Docker Testing Best Practices](https://docs.docker.com/develop/dev-best-practices/)
