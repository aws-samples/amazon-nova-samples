from nova_act.nova_act import _TRACE_LOGGER

from src.utils import NovaAct


def test_web_application(nova: NovaAct, test_case: dict):
    """
    Single pytest test that executes all JSON-defined test cases.
    Each JSON file becomes a separate test instance via parametrize.
    See conftest.py::pytest_generate_tests() for details.
    """
    test_id = test_case.get("testId", "Unknown")
    test_name = test_case.get("testName", "Unknown Test")
    description = test_case.get("description", "No description")
    test_steps = test_case.get("testSteps", [])
    source_file = test_case.get("_source_file", "Unknown file")

    _TRACE_LOGGER.info(f"Executing test: {test_id} - {test_name}")
    _TRACE_LOGGER.info(f"Description: {description}")
    _TRACE_LOGGER.info(f"Source: {source_file}")

    for i, step in enumerate(test_steps, 1):
        action = step.get("action")
        expected_result = step.get("expectedResult")

        _TRACE_LOGGER.info(
            f"\nStep {i}: Processing action='{action}', expected='{expected_result}'\n"
        )

        if action:
            nova.act(action)

        if expected_result:
            nova.test_bool(expected_result)

    _TRACE_LOGGER.info(f"✓ Test {test_id} completed successfully")
