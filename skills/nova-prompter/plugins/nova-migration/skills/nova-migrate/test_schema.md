# Test file schema

`nova-migrate` accepts test files in JSONL or YAML. Pick whichever fits — both
support the same fields.

## Required fields

- `input` — what gets fed to the model (string or object; objects are JSON-stringified)

## Optional fields

- `id` — stable identifier (auto-generated as `t000`, `t001`, ... if omitted)
- `expected_output` — reference output. Required if running with `--baseline-from-tests` (no source-model calls)
- `expected_behavior` — natural-language description of what a good output looks like (used by the judge when no `expected_output` is given)
- `rubric_overrides` — per-test rubric tweaks (e.g., weight a criterion higher, add a test-specific criterion)
- `tags` — list of strings, used in the final report to group scores (e.g., `["edge_case"]`, `["happy_path"]`)

## JSONL example

```jsonl
{"id": "simple_1", "input": "Summarize: The quick brown fox jumps over the lazy dog.", "expected_behavior": "One-sentence summary preserving the subject and action.", "tags": ["happy_path"]}
{"id": "edge_empty", "input": "Summarize: ", "expected_behavior": "Graceful refusal or request for content; no hallucination.", "tags": ["edge_case"]}
```

## YAML example

```yaml
tests:
  - id: simple_1
    input: "Summarize: The quick brown fox jumps over the lazy dog."
    expected_behavior: "One-sentence summary preserving the subject and action."
    tags: [happy_path]

  - id: edge_empty
    input: "Summarize: "
    expected_behavior: "Graceful refusal or request for content; no hallucination."
    tags: [edge_case]
    rubric_overrides:
      refusal_quality: { weight: 2 }
```

## Notes

- If neither `expected_output` nor `expected_behavior` is provided, the judge
  falls back to scoring against the global rubric only. Works, but weaker signal.
- `input` can be a structured object for tool-use / agent prompts; the helper
  will serialize it as JSON before sending to the model.
