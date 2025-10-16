from typing import Generator

from bedrock_agentcore.tools.browser_client import BrowserClient
import boto3
import pytest

from src.config import AppConfig
from src.utils import NovaAct, start_nova_act, load_all_test_data

"""
Pytest config and hooks
"""


def pytest_generate_tests(metafunc):
    """Pytest hook that runs during test collection to dynamically generate parametrized tests from JSON files.

    See: https://docs.pytest.org/en/stable/reference/reference.html#std-hook-pytest_generate_tests
    """
    if "test_case" in metafunc.fixturenames:
        test_cases = load_all_test_data()

        metafunc.parametrize(
            "test_case", test_cases, ids=lambda tc: f"{tc['testId']}-{tc['testName']}"
        )


def _get_test_id(request: pytest.FixtureRequest) -> str:
    """Extract test ID from pytest request."""
    return request.node.callspec.id


"""
Fixtures for Nova ACT QA testing.
"""


@pytest.fixture(scope="session")
def app_config() -> AppConfig:
    """Provide AppConfig instance for the entire test session."""
    return AppConfig()  # type: ignore


@pytest.fixture()
def agentcore_browser_client(
    request: pytest.FixtureRequest,
) -> Generator[BrowserClient, None, None]:
    """Start AgentCore Browser session with test ID as name, yield until test completion, then stop."""
    test_id = _get_test_id(request)
    region = boto3.Session().region_name or "us-east-1"
    client = BrowserClient(region=region)
    client.start(name=test_id)
    yield client
    client.stop()


@pytest.fixture()
def nova(
    request: pytest.FixtureRequest,
    app_config: AppConfig,
    agentcore_browser_client: BrowserClient,
) -> Generator[NovaAct, None, None]:
    """Start Nova Act browser instance with test ID for unique directories, yield until test completion, then stop."""
    test_id = _get_test_id(request)
    starting_page = app_config.WEB_APP_URL
    cdp_endpoint_url, cdp_headers = agentcore_browser_client.generate_ws_headers()
    nova = start_nova_act(starting_page, cdp_endpoint_url, cdp_headers, test_id)
    yield nova
    nova.stop()
