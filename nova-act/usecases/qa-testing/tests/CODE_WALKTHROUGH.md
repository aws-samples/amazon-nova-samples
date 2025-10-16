# Complete Code Walkthrough: pytest + Nova Act + AgentCore Browser

## Overview
This document provides a detailed walkthrough of how `pytest .` integrates with Nova Act and AgentCore Browser to run automated web tests. The system uses a data-driven approach where JSON files define test cases that are executed by Nova Act's AI-powered browser automation.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     pytest     │───▶│    Nova Act     │───▶│ AgentCore       │
│   Test Runner   │    │   AI Agent      │    │   Browser       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  JSON Test      │    │  Natural Lang   │    │   Chrome        │
│  Definitions    │    │  Instructions   │    │   Browser       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Detailed Code Flow

### 1. When You Type `pytest .`

**Command**: `pytest .`

**What happens**:
1. pytest discovers test files in the current directory
2. Finds `src/test_runner.py` which contains the main test function
3. Loads `src/conftest.py` for configuration and fixtures
4. Executes the pytest hooks and fixtures

### 2. Test Discovery and Generation (`conftest.py`)

**File**: `src/conftest.py`

```python
def pytest_generate_tests(metafunc):
    """Pytest hook that runs during test collection to dynamically generate parametrized tests from JSON files."""
    if "test_case" in metafunc.fixturenames:
        test_cases = load_all_test_data()  # Load all JSON test files
        
        metafunc.parametrize(
            "test_case", test_cases, ids=lambda tc: f"{tc['testId']}-{tc['testName']}"
        )
```

**Process**:
1. **Test Discovery**: pytest calls `pytest_generate_tests()` during collection phase
2. **JSON Loading**: `load_all_test_data()` scans `src/test_data/` directory for `*.json` files
3. **Dynamic Parametrization**: Each JSON file becomes a separate test case
4. **Test ID Generation**: Creates unique test IDs like `QA-01-Homepage Load Test`

### 3. JSON Test File Loading (`utils/test_loader.py`)

**File**: `src/utils/test_loader.py`

```python
def load_all_test_data() -> List[Dict[str, Any]]:
    """Load all test data from JSON files."""
    test_files = get_all_test_files()
    test_data = []
    
    for file_path in test_files:
        with open(file_path, "r") as f:
            data = json.load(f)
            data["_source_file"] = file_path.name  # Add metadata
            test_data.append(data)
    
    return test_data
```

**JSON Test Structure**:
```json
{
  "testId": "QA-01",
  "testName": "Homepage Load Test",
  "description": "Verify that the home page loads correctly",
  "testSteps": [
    {
      "action": "Navigate to homepage",           // Optional: Action to perform
      "expectedResult": "Home page loads successfully"  // Required: What to verify
    }
  ]
}
```

### 4. Fixture Setup and Browser Initialization

**Session-Scoped Configuration**:
```python
@pytest.fixture(scope="session")
def app_config() -> AppConfig:
    """Provide AppConfig instance for the entire test session."""
    return AppConfig()  # Loads WEB_APP_URL and NOVA_ACT_API_KEY from .env
```

**AgentCore Browser Client**:
```python
@pytest.fixture()
def agentcore_browser_client(request: pytest.FixtureRequest) -> Generator[BrowserClient, None, None]:
    """Start AgentCore Browser session with test ID as name."""
    test_id = _get_test_id(request)  # Extract test ID from pytest request
    region = boto3.Session().region_name or "us-east-1"
    client = BrowserClient(region=region)  # AWS Bedrock AgentCore Browser
    client.start(name=test_id)  # Start browser session
    yield client
    client.stop()  # Cleanup after test
```

**Nova Act Instance**:
```python
@pytest.fixture()
def nova(request: pytest.FixtureRequest, app_config: AppConfig, agentcore_browser_client: BrowserClient) -> Generator[NovaAct, None, None]:
    """Start Nova Act browser instance."""
    test_id = _get_test_id(request)
    starting_page = app_config.WEB_APP_URL
    cdp_endpoint_url, cdp_headers = agentcore_browser_client.generate_ws_headers()
    nova = start_nova_act(starting_page, cdp_endpoint_url, cdp_headers, test_id)
    yield nova
    nova.stop()
```

### 5. Nova Act Initialization (`utils/nova_act.py`)

**Nova Act Wrapper Class**:
```python
class NovaAct(_NovaAct):
    """Extends the base NovaAct client with testing capabilities."""
    
    def test_bool(self, prompt: str, expected: bool = True):
        """Runs a test case with boolean assertion."""
        return self.test(prompt, expected)
```

**Initialization Function**:
```python
def start_nova_act(starting_page: str, cdp_endpoint_url: str, cdp_headers: dict[str, str], test_id: str):
    logs_dir, user_data_dir = initialize_nova_act_directories(test_id)
    
    nova = NovaAct(
        starting_page=starting_page,        # URL to start testing
        cdp_endpoint_url=cdp_endpoint_url,  # AgentCore Browser WebSocket endpoint
        cdp_headers=cdp_headers,            # Authentication headers
        headless=True,                      # Run in headless mode
        logs_directory=logs_dir,            # Test-specific log directory
        user_data_dir=user_data_dir,        # Test-specific browser profile
        screen_width=1920,
        screen_height=1080,
    )
    
    nova.start()  # Initialize the AI agent and browser
    return nova
```

### 6. Test Execution (`test_runner.py`)

**Main Test Function**:
```python
def test_web_application(nova: NovaAct, test_case: dict):
    """Single pytest test that executes all JSON-defined test cases."""
    test_id = test_case.get("testId", "Unknown")
    test_name = test_case.get("testName", "Unknown Test")
    test_steps = test_case.get("testSteps", [])
    
    _TRACE_LOGGER.info(f"Executing test: {test_id} - {test_name}")
    
    for i, step in enumerate(test_steps, 1):
        action = step.get("action")
        expected_result = step.get("expectedResult")
        
        _TRACE_LOGGER.info(f"Step {i}: Processing action='{action}', expected='{expected_result}'")
        
        if action:
            nova.act(action)  # Perform action using AI agent
            
        if expected_result:
            nova.test_bool(expected_result)  # Verify expected result
    
    _TRACE_LOGGER.info(f"✓ Test {test_id} completed successfully")
```

## Component Integration Details

### 1. pytest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
addopts = "-n auto --dist loadgroup --html=reports/report.html --self-contained-html --add-nova-act-report --log-level=INFO"
```

**Key Options**:
- `-n auto`: Parallel execution with automatic worker count
- `--dist loadgroup`: Distribute tests by groups (each JSON file = one group)
- `--html=reports/report.html`: Generate HTML test report
- `--add-nova-act-report`: Include Nova Act-specific reporting

### 2. Environment Configuration (`.env`)

```env
WEB_APP_URL=http://localhost:3000
NOVA_ACT_API_KEY=your_api_key_here
```

**Configuration Loading**:
```python
class AppConfig(BaseConfig):
    WEB_APP_URL: str      # Target application URL
    NOVA_ACT_API_KEY: str # Nova Act API authentication
```

### 3. Dependencies (`pyproject.toml`)

```toml
dependencies = [
    "bedrock-agentcore>=0.1.5",    # AWS AgentCore Browser client
    "nova-act>=2.1.36.0",          # Nova Act AI agent
    "pytest>=8.4.2",               # Test framework
    "pytest-xdist>=3.8.0",         # Parallel test execution
    "pytest-html>=4.1.1",          # HTML reporting
    "boto3>=1.40.39",               # AWS SDK
]
```

## Execution Flow Diagram

```
1. pytest . command
   │
   ├─▶ pytest_generate_tests() hook
   │   ├─▶ load_all_test_data()
   │   │   ├─▶ Scan src/test_data/*.json
   │   │   └─▶ Load JSON test definitions
   │   └─▶ metafunc.parametrize() creates test instances
   │
   ├─▶ For each test instance:
   │   ├─▶ app_config fixture (session scope)
   │   │   └─▶ Load .env configuration
   │   │
   │   ├─▶ agentcore_browser_client fixture
   │   │   ├─▶ Initialize AWS Bedrock AgentCore Browser
   │   │   ├─▶ client.start(name=test_id)
   │   │   └─▶ Generate WebSocket headers
   │   │
   │   ├─▶ nova fixture
   │   │   ├─▶ start_nova_act()
   │   │   │   ├─▶ Initialize directories
   │   │   │   ├─▶ Create NovaAct instance
   │   │   │   └─▶ nova.start()
   │   │   └─▶ Connect to AgentCore Browser via WebSocket
   │   │
   │   └─▶ test_web_application()
   │       ├─▶ For each test step:
   │       │   ├─▶ nova.act(action) - AI performs action
   │       │   └─▶ nova.test_bool(expected_result) - AI verifies result
   │       └─▶ Test completion
   │
   └─▶ Cleanup:
       ├─▶ nova.stop()
       └─▶ agentcore_browser_client.stop()
```

## Key Integration Points

### 1. pytest ↔ Nova Act
- **Data Flow**: JSON test definitions → pytest parametrization → Nova Act execution
- **Fixture Management**: pytest manages Nova Act lifecycle through fixtures
- **Parallel Execution**: pytest-xdist distributes tests across workers

### 2. Nova Act ↔ AgentCore Browser
- **Communication**: WebSocket connection using Chrome DevTools Protocol (CDP)
- **Authentication**: AWS credentials and session headers
- **Browser Control**: Nova Act sends AI-generated browser commands to AgentCore

### 3. AgentCore Browser ↔ Web Application
- **Browser Engine**: Chromium-based browser controlled via CDP
- **Rendering**: Full browser rendering with JavaScript execution
- **Interaction**: Real browser interactions (clicks, typing, navigation)

## AI-Powered Testing Process

### 1. Natural Language Processing
```python
# Example: "Click the search button"
nova.act("Click the search button")
```
**Process**:
1. Nova Act receives natural language instruction
2. AI analyzes current page state (DOM, visual elements)
3. AI determines appropriate browser action
4. Action is executed via AgentCore Browser

### 2. Intelligent Verification
```python
# Example: "Search results show laptop-related products"
nova.test_bool("Search results show laptop-related products")
```
**Process**:
1. Nova Act analyzes current page state
2. AI evaluates whether condition is met
3. Returns boolean result for pytest assertion

### 3. Context Awareness
- **Page Understanding**: AI understands page structure and content
- **Element Recognition**: Identifies buttons, forms, links without selectors
- **State Management**: Maintains context across test steps

## Error Handling and Logging

### 1. Test Failures
```python
class TestFailedError(Exception):
    """Raised when Nova Act test assertion fails."""
    pass
```

### 2. Logging System
- **Nova Act Logs**: Stored in `.nova_act/logs/{test_id}/`
- **pytest Logs**: Console output with INFO level
- **HTML Reports**: Generated in `reports/report.html`

### 3. Parallel Execution Safety
- **Isolated Environments**: Each test gets unique browser profile
- **Resource Management**: Proper cleanup of browser sessions
- **Load Distribution**: Tests distributed by JSON file groups

## Summary

When you run `pytest .`, the system:

1. **Discovers** all JSON test files and creates parametrized test instances
2. **Initializes** AWS AgentCore Browser sessions for each test
3. **Connects** Nova Act AI agents to browser sessions via WebSocket
4. **Executes** natural language test instructions using AI
5. **Verifies** results through AI-powered assertions
6. **Reports** results in HTML format with Nova Act integration
7. **Cleans up** all resources after test completion

This creates a powerful, AI-driven testing framework that combines the structure of pytest with the intelligence of Nova Act and the reliability of AWS AgentCore Browser infrastructure.
