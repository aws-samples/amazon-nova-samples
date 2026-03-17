# Amazon Nova Act for QA Automation

This project demonstrates how to use [Amazon Bedrock AgentCore Browser Tool](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-tool.html) and [Amazon Nova Act](https://novs.amazon.com/act) to automate quality assurance (QA) and end-to-end testing in a web browser. Tests are defined in JSON files and executed dynamically using [pytest](https://docs.pytest.org/en/stable/) with the [Amazon Nova Act SDK](https://github.com/aws/nova-act), enabling parallel test execution with custom HTML report generation via the [pytest-html-nova-act](https://pypi.org/project/pytest-html-nova-act/) plugin. Each test runs in its own isolated browser session, providing clean test environments and enabling parallel execution without interference between tests.

## Table of Contents

- [Repository Structure](#repository-structure)
- [Nova Act Test Methods](#nova-act-test-methods)
- [JSON Test Format](#json-test-format)
- [Project Usage](#project-usage)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment setup](#environment-setup)
  - [Quick start](#quick-start)
- [Test Output](#test-output)
  - [Nova Act SDK logs](#nova-act-sdk-logs)
  - [Test report](#test-report)
- [Test Configuration](#test-configuration)
  - [Pytest Plugins](#pytest-plugins)
- [Additional Resources](#additional-resources)

## Repository Structure

```
tests/
├── pyproject.toml  # Project dependencies and pytest config
├── .env.sample     # Sample .env file to copy
├── conftest.py     # Pytest fixtures
└── src/
    ├── config/     # App config (env var management, etc)
    ├── test_data/  # JSON files that define the tests to run
    └── utils/      # Utility functions and types
```

## Nova Act Test Methods

This project extends the base Nova Act SDK `NovaAct` class with enhanced testing capabilities:

1. `test()`

   - Flexible assertion with schema validation
   - Supports exact matching and contains operators
   - Handles primitive types and complex JSON structures

2. `test_bool()`

   - Simplified boolean assertions
   - Default expectation of True

3. `test_str()`

   - String-specific assertions
   - Supports exact and partial matching

Example usage:

```python
nova.test_bool("Am I on the landing page?")
nova.test_str("Text input validation message", "Please enter a valid email address")
nova.test(
    "Product price tiers",
    [
        {"name": "Bronze", "price": 0.99},
        {"name": "Silver", "price": 4.99},
        {"name": "Gold", "price": 9.99}
    ],
    {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "price": {"type": "number"}
            }
        }
    })
```

See [`src/utils/nova_act.py`](src/utils/nova_act.py) for complete reference

## JSON Test Format

Tests are defined in JSON files located in [`src/test_data/`](src/test_data/). Each JSON file represents a test case that is automatically discovered and executed by pytest. Each test step is iterated over and executed dynamically by Nova Act.

### Test Execution

Test execution is fully data-driven from JSON file values:

- Test ID and Name are used to create the test identifier and output in the HTML report
- Each test step is executed sequentially:
  - `action` fields are executed using `nova.act()` to perform an action
  - `expectedResult` fields are validated using `nova.test_bool()` to assert a boolean condition in the UI

> **Important Notes:**
> - At least one field is required per test step; using only `expectedResult` checks conditions without performing actions, while using only `action` performs actions without direct validation
> - Tests fail if an `expectedResult` evaluates to false or if an `action` cannot be completed

### JSON Schema

The below JSON schema defines the structure that all test JSON files must follow. Each test step can contain either an `action`, an `expectedResult`, or both.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["testId", "testName", "description", "testSteps"],
  "properties": {
    "testId": {
      "type": "string",
      "description": "Unique identifier for the test case"
    },
    "testName": {
      "type": "string",
      "description": "Human-readable name for the test"
    },
    "description": {
      "type": "string",
      "description": "Brief description of what the test validates"
    },
    "testSteps": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "action": {
            "type": "string",
            "description": "Nova Act action to perform (optional)"
          },
          "expectedResult": {
            "type": "string",
            "description": "Condition to validate with nova.test_bool() (optional)"
          }
        }
      }
    }
  }
}
```

## Project Usage

### Prerequisites

- Web application infrastructure deployed with CloudFront URL
  - See the `README.md` and `DEPLOYMENT.md` files of the web application section of this project for deployment instructions
- AWS credentials configured on your machine with permissions to create Bedrock AgentCore Browser Tool sessions for each test
- Python 3.11 or higher
- pip 23.0 or higher
- Operating system:
  - macOS (Sierra or later)
  - Ubuntu (22.04 LTS or later)
  - Windows:
    - Windows 10 or later
    - Windows Subsystem for Linux 2 (WSL2)
- Nova Act API key
  - Visit [Nova Act home page](https://nova.amazon.com/act) to generate your API key

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd tests

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install .
```

### Environment setup

1. Create a .env file based on the provided template:

```bash
cp .env.sample .env
```

2. Edit your new `.env` file to include:
   - `WEB_APP_URL`: Your CloudFront Distribution URL
     - See the `DEPLOYMENT.md` file in the web application section of this project
   - `NOVA_ACT_API_KEY`: Your Nova Act API Key
     - Visit [Nova Act home page](https://nova.amazon.com/act) to generate your API key

### Quick start

1. Run the test suite:

```bash
pytest
```

2. View test HTML report:

```bash
open reports/report.html
```

## Test Output

### Nova Act SDK logs

The project creates a `.nova_act` directory structure for each test in the root of this project. These directories include the Nova Act SDK HTML log output and browser user data directories:

```
.nova_act/
├── logs/                 # Test execution logs
│   └── {module}/{test}/  # Logs organized by module and test name
└── user-data-dir/        # Browser user data directories
    └── {module}/{test}/  # Separate profile per test
```

See [the Nova Act SDK documentation](https://github.com/aws/nova-act?tab=readme-ov-file#viewing-act-traces) for more details on logging.

### Test report

An HTML report is automatically generated in the `reports` directory at the project root for each test run as configured in `pyproject.toml`. The report includes:

- Test results and durations
- Failure details and stack traces
- Nova Act SDK screenshots and logs

See the [pytest-html](https://pytest-html.readthedocs.io/en/latest/) documentation for more details.

## Test Configuration

The [`pyproject.toml`](pyproject.toml) file has a `[tool.pytest.ini_options]` section which defines the pytest configuration for the tests. The default settings include:

- `-n auto`: Automatically detects CPU cores and runs tests in parallel
- `--html=reports/report.html`: Defines the location to write the pytest HTML report
- `--self-contained-html`: Creates a standalone HTML report file with embedded assets
- `--add-nova-act-report`: Integrates Nova Act screenshots and logs into the HTML report

This configuration can be extended to customize your tests as needed.

### Pytest Plugins

The project uses several pytest plugins to enhance testing capabilities:

1. [pytest-html](https://pypi.org/project/pytest-html):

   - Generates HTML test reports
   - Includes test results, durations, and failure details

2. [pytest-html-nova-act](https://pypi.org/project/pytest-html-nova-act):

   - Integrates the Nova Act SDK screenshots and log output with the pytest-html report

3. [pytest-xdist](https://pypi.org/project/pytest-xdist):

   - Enables parallel test execution
   - Distributes tests across multiple CPU cores

These plugins are automatically installed with the project dependencies. No additional configuration is required.

## Expected Test Failures

The following tests are expected to fail:

1. **QA-03-Product Display and Images Test**
2. **QA-05-Product Filter Functionality Test**

## Additional Resources

- [Amazon Nova Act](https://novs.amazon.com/act)
- [Amazon Nova Act SDK](https://github.com/aws/nova-act)
- [pytest-html-nova-act](https://pypi.org/project/pytest-html-nova-act/)
