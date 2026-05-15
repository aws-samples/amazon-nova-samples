# Rubric template

Used by the skill when deriving a rubric from the task description. The derived
rubric is shown to the user for edits before any scoring runs.

## Guidelines for generating criteria

- **Task-specific**, not generic. "Output is valid JSON matching `expected_schema`"
  beats "Output is well-formatted". "Summary preserves all named entities from the
  input" beats "Summary is good".
- **Checkable**, not subjective. Each criterion should let the judge produce a
  defensible 1–5 score from the test's input, the candidate output, and the
  baseline output.
- **4–6 criteria** is the sweet spot. More = noise; fewer = missed failure modes.
- **Cover task success + failure modes.** E.g., for a summarization task:
  correctness, completeness, format adherence, refusal behavior on empty input.

## Scale (applied per criterion, per test)

- **5** — fully meets the criterion; equal to or better than baseline
- **4** — minor issue, still ships
- **3** — noticeable gap vs baseline or criterion
- **2** — significant regression or failure
- **1** — criterion not met at all

## Output format the rubric file should take (after user edits)

```markdown
# Rubric

## Criteria

1. **correctness** — Output answers the user's question without factual errors.
2. **format_adherence** — Output matches the required structure (JSON / markdown / plain text per task).
3. **completeness** — All parts of the input are addressed; nothing dropped.
4. **refusal_behavior** — On malformed / empty / out-of-scope input, output refuses cleanly rather than hallucinating.

## Regression threshold

A test is flagged as regressed if Nova scores ≥ 1 point below baseline on any
criterion.
```
