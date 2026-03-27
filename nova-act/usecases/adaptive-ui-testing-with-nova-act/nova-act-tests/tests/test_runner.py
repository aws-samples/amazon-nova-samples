import pytest
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from nova_act import workflow, NovaAct

# Load environment variables from .env file
load_dotenv()

TEST_CASES_DIR = Path(__file__).parent.parent / "test_cases"

def load_test_cases():
    """Load all JSON test cases"""
    test_cases = []
    for file in TEST_CASES_DIR.glob("*.json"):
        with open(file) as f:
            test_cases.append(json.load(f))
    return test_cases

@pytest.mark.parametrize("test_case", load_test_cases(), ids=lambda tc: tc["testId"])
def test_with_nova_act(test_case):
    """Execute test case using Nova Act"""
    
    workflow_kwargs = {"model_id": "nova-act-latest"}
    
    # IAM authentication requires a workflow definition name
    # API key authentication does not
    api_key = os.getenv("NOVA_ACT_API_KEY")
    if api_key:
        workflow_kwargs["nova_act_api_key"] = api_key
    else:
        workflow_name = os.getenv("NOVA_ACT_WORKFLOW_NAME", "adaptive-ui-testing")
        workflow_kwargs["workflow_definition_name"] = workflow_name
    
    @workflow(**workflow_kwargs)
    def run_student_test():
        """Execute student registration test using Nova Act"""
        import os
        from pathlib import Path
        
        # Create screenshots directory
        screenshots_dir = Path(__file__).parent.parent / "screenshots" / test_case['testId']
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Nova Act with starting page (ignore HTTPS for local testing)
        nova = NovaAct(
            starting_page=test_case['url'],
            ignore_https_errors=True,
            tty=False,  # Disable TTY for pytest
            headless=False,  # Show browser so you can see the actions
            logs_directory=str(screenshots_dir)  # Save screenshots and logs
        )
        
        # Start the Nova Act client
        nova.start()
        
        # Execute each test step
        for step in test_case["testSteps"]:
            action = step.get("action", "")
            expected = step["expectedResult"]
            
            # Build instruction - simpler format
            if action:
                instruction = f"{action}"
            else:
                instruction = f"Verify that {expected}"
            
            # Execute with Nova Act
            nova.act(instruction)
        
        return "Test completed successfully"
    
    # Execute the workflow with Nova Act
    try:
        result = run_student_test()
        print(f"\n✓ Test {test_case['testId']}: {test_case['testName']}")
        print(f"  Result: {result}")
        assert True
    except Exception as e:
        error_msg = str(e)
        print(f"\n✗ Test {test_case['testId']}: {test_case['testName']}")
        print(f"  Error: {error_msg}")
        
        # Provide helpful error messages
        if "Failed to start" in error_msg:
            print("\n  Possible causes:")
            print("  - Browser automation failed to initialize")
            print("  - Check if Chromium is installed: npx playwright install chromium")
        elif "timeout" in error_msg.lower():
            print("\n  Possible causes:")
            print("  - Element not found on page")
            print("  - Page took too long to load")
            print("  - Check if server is running on http://localhost:8000")
        elif "selector" in error_msg.lower():
            print("\n  Possible causes:")
            print("  - UI element not found")
            print("  - Selector may have changed")
        
        pytest.fail(f"Nova Act test failed: {error_msg}")
