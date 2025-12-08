# Workflow Context Manager Pattern - Multiple Sessions

## Prerequisites
- Completed `2_workflow_decorator.py`
- Understanding of @workflow decorator pattern
- AWS credentials with Nova Act permissions
- Familiarity with Python context managers

## Overview
This example demonstrates the Workflow context manager's ability to manage multiple browser sessions within a single workflow. This pattern is ideal for workflows that need to interact with multiple websites or perform parallel tasks, all tracked under one workflow run in AWS.

## Code Walkthrough

### Section 1: Workflow Context Manager Initialization
```python
with Workflow(
    workflow_definition_name="getting-started-workflow",
    model_id="nova-act-latest"
) as workflow:
```
**Explanation**: The Workflow context manager creates a workflow definition that can be shared across multiple NovaAct sessions. Unlike the @workflow decorator which wraps a single function, the context manager enables multiple independent browser sessions within one workflow run.

### Section 2: Multiple Sessions - First Session
```python
# First session - Wikipedia
with NovaAct(
    starting_page="https://en.wikipedia.org",
    workflow=workflow,
    headless=True
) as nova1:
    result1 = nova1.act("Find and return the main heading of the page")
```
**Explanation**: The first browser session navigates to Wikipedia. The `workflow` parameter links this session to the workflow definition, ensuring it's tracked as part of the overall workflow run. Each session operates independently but logs to the same workflow.

### Section 3: Multiple Sessions - Second Session
```python
# Second session - Nova Act site
with NovaAct(
    starting_page="https://nova.amazon.com/act",
    workflow=workflow,
    headless=True
) as nova2:
    result2 = nova2.act("Find and return the main heading of the page")
```
**Explanation**: The second browser session navigates to a different site. Both sessions are tracked independently in AWS but grouped under the same workflow run. This enables complex workflows that need to gather data from multiple sources or perform parallel operations.

### Section 4: Pattern Comparison
```python
# Decorator Pattern - Single Session
@workflow(workflow_definition_name="name", model_id="nova-act-latest")
def my_workflow():
    with NovaAct(starting_page="url") as nova:
        # Single session workflow

# Context Manager Pattern - Multiple Sessions
with Workflow(workflow_definition_name="name", model_id="nova-act-latest") as workflow:
    with NovaAct(starting_page="url1", workflow=workflow) as nova1:
        # First session
    with NovaAct(starting_page="url2", workflow=workflow) as nova2:
        # Second session
```
**Explanation**: The decorator pattern is ideal for single-session workflows, while the context manager excels at managing multiple sessions. All sessions share the same workflow context and are logged together in AWS.

## Running the Example
```bash
cd /path/to/nova-act/tutorials/path-to-production/01-workflow-basics
python 3_workflow_context_manager.py
```

**Expected Output:**
```
Multi-Session Workflow Execution
============================================================
[OK] Workflow context manager initialized
  Workflow definition: getting-started-workflow
  Pattern: Multiple independent sessions
  Logging: All sessions tracked in one workflow run

Session 1: Wikipedia
  Browser session 1 started
  Result: Wikipedia

Session 2: Nova Act
  Browser session 2 started
  Result: Amazon Nova Act

✓ Completed: Both sessions executed successfully
  • Each session tracked independently
  • Both sessions logged to same workflow run
  • All traces available in Nova Act console
```

## When to Use Each Pattern

### Use @workflow Decorator When:
- Single browser session per workflow
- Simple, straightforward automation tasks
- Function-based workflow design

### Use Workflow Context Manager When:
- **Multiple browser sessions needed** (key advantage)
- Gathering data from multiple websites
- Parallel operations across different sites
- Complex workflows requiring session coordination

## Key Advantages of Context Manager

### Multiple Sessions
The primary advantage demonstrated in this example:
- Run multiple browser sessions in one workflow
- Each session tracked independently in AWS
- All sessions grouped under one workflow run
- Enables complex multi-site automation

### Other Use Cases
1. **Error Handling & Cleanup**
   ```python
   try:
       with Workflow(...) as workflow:
           # Automatic cleanup on error
   except Exception as e:
       # Workflow ensures proper resource cleanup
   ```

2. **Conditional Execution**
   ```python
   with Workflow(...) as workflow:
       with NovaAct(..., workflow=workflow) as nova:
           result = nova.act("check condition")
           if "condition_met" in result:
               # Dynamic workflow logic
   ```

3. **Parameterized Workflows**
   ```python
   def main(payload):
       url = payload.get("url")
       with Workflow(...) as workflow:
           with NovaAct(starting_page=url, workflow=workflow) as nova:
               # Use payload data
   ```

## Troubleshooting
- **Workflow parameter missing**: Ensure `workflow=workflow` is passed to each NovaAct instance
- **Session conflicts**: Each NovaAct instance creates an independent session
- **Workflow definition not found**: Run `1_workflow_definitions.py` first
- **Multiple sessions not appearing**: Check Nova Act console for session-level traces

## Next Steps
- Run `4_deploy_workflow.py` to learn deployment to AWS infrastructure
- Experiment with different multi-session patterns
- Consider which pattern fits your workflow requirements
