from typing import Any, Dict, Optional

from json_compare import compare
from nova_act import NovaAct as _NovaAct, ActResult, BOOL_SCHEMA

from ._types import STRING_SCHEMA, AssertType, JSONType
from .directories import initialize_nova_act_directories
from .exceptions import TestFailedError


class NovaAct(_NovaAct):
    """
    Extends the base NovaAct client.

    Methods
    -------
    is_result_valid()
      Returns the parsed response or false if the response is invalid
    test()
      Tests and asserts a condition, raises an error if condition is not met
    """

    def is_result_valid(self, result: ActResult) -> JSONType | None:
        """
        Returns the parsed response if result matches schema, False otherwise
        """
        return result.matches_schema and result.parsed_response

    def test(
        self,
        prompt: str,
        expected: JSONType,
        expected_schema: Optional[Dict[str, Any]] = BOOL_SCHEMA,
        assert_type: AssertType = AssertType.EXACT,
    ):
        """
        Runs a test case for the Nova Act client with flexible assertion capabilities.

        Args:
            self: An instance of the Nova Act client.
            prompt: The action to be performed by the Nova Act client.
            expected: The expected response from the Nova Act client.
            expected_schema: The expected type of the response. Defaults to None.
            assert_operator: The operator to use for assertion.
                            - EXACT: Performs an exact match (default).
                            - CONTAINS: Checks if the actual response (if string) contains the expected response (if string).

        Raises:
            AssertionError: If the actual response does not match the expected response
                            based on the specified operator or does not match the
                            expected response type.
        """

        if assert_type not in AssertType:
            raise ValueError(
                f"Invalid assert_type. Use {' or '.join([f'{assert_type.value!r}' for assert_type in AssertType])}"
            )

        act_result = self.act(prompt, schema=expected_schema)
        actual = self.is_result_valid(act_result)

        if assert_type == AssertType.EXACT:
            error_msg = f"Expected '{expected}' but got '{actual}'"
        elif assert_type == AssertType.CONTAINS:
            error_msg = f"'{expected}' not found in '{actual}'"

        if actual:
            # Compare primitives
            if isinstance(expected, (str, int, float, bool)):
                if assert_type == AssertType.EXACT:
                    assert expected == actual, error_msg
                else:
                    assert (
                        isinstance(expected, str)
                        and isinstance(actual, str)
                        and expected in actual
                    ) or expected == actual, error_msg
            else:
                # Compare List or Dict
                is_valid = compare(
                    expected,
                    actual,
                    ignore_list_seq=(assert_type == AssertType.CONTAINS),
                )
                assert is_valid, error_msg

            return actual

        raise TestFailedError(
            f"Invalid ActResult for prompt {prompt} and schema {expected_schema}: {act_result}"
        )

    def test_bool(self, prompt: str, expected: bool = True):
        """
        Runs a test case for the Nova Act client with a boolean assertion.

        Args:
            self: An instance of the Nova Act client.
            prompt: The action to be performed by the Nova Act client.
            expected: The expected response from the Nova Act client.

        Raises:
            AssertionError: If the actual response does not match the expected response
                            or does not match the expected response type.
        """
        return self.test(prompt, expected)

    def test_str(
        self, prompt: str, expected: str, assert_type: AssertType = AssertType.EXACT
    ):
        """
        Runs a test case for the Nova Act client with a string assertion.

        Args:
            self: An instance of the Nova Act client.
            prompt: The action to be performed by the Nova Act client.
            expected: The expected response from the Nova Act client.

        Raises:
            AssertionError: If the actual response does not match the expected response
                            or does not match the expected response type.
        """
        return self.test(
            prompt, expected, expected_schema=STRING_SCHEMA, assert_type=assert_type
        )

    def check(self, condition: str) -> bool:
        """
        Checks a condition with a boolean JSON schema and returns the result
        """
        result = self.act(condition, schema=BOOL_SCHEMA)
        return bool(self.is_result_valid(result))


def start_nova_act(
    starting_page: str,
    cdp_endpoint_url: str,
    cdp_headers: dict[str, str],
    test_id: str,
):
    logs_dir, user_data_dir = initialize_nova_act_directories(test_id)

    nova = NovaAct(
        starting_page=starting_page,
        cdp_endpoint_url=cdp_endpoint_url,
        cdp_headers=cdp_headers,
        headless=True,
        logs_directory=logs_dir,
        user_data_dir=user_data_dir,
        clone_user_data_dir=False,
    )

    nova.start()
    return nova
