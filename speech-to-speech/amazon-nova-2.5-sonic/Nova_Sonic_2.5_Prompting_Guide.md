---
doc_type: best-practices-guide
subject: Amazon Nova Sonic 2.5 voice agents
scope: system-prompt-and-tool-description-authoring
audience: [Builders building Voice AI apps]
version: 1.0
---

# Nova Sonic 2.5 Prompt Engineering — Best Practices Guide

This is the best practices guide for writing and reviewing Nova Sonic 2.5 system prompts and tool descriptions.

Looking for this same guidance wired into a coding agent (Claude Code, Kiro) instead? Use the `/nova-sonic25-prompt` Claude Code plugin or the matching Kiro power — see [`skills/nova-prompter/`](../../skills/nova-prompter/) in this repo for install instructions — rather than pasting this file into an agent's context.

## How to use this guide

The guide is organized as: (1) core mental models that explain *why* the rules work, (2) prescriptive rules grouped by area, (3) a platform-behavior note, (4) a review checklist, and (5) a quick-reference card. Read Part 1 once, then use Parts 2–3 as a reference while drafting a prompt, and Part 4 as a checklist before you ship it.

---

## Part 1 — Core mental models (the WHY)

These explain most of the specific rules below. Internalizing them generalizes better than memorizing the rules.

### A. Anything in context is available for vocalization
Any token sequence the model can see — system prompt, tool description, tool response, or a WRONG example — raises the probability the model will say it aloud, even when preceded by "never say." Consequence: describe desired behavior positively, keep forbidden phrases out of context entirely, and never name a tool inside its own response.

### B. Prioritization and proximity beat volume
An instruction competes with everything else in a long prompt. Two levers determine whether it fires: how PROMINENT it is (stated once, clearly, not buried among 20 other sections) and how CLOSE it is to the decision point where the model needs it. A correct rule buried deep and restated inconsistently underperforms the same rule stated once, early, and reinforced at the point of use.

### C. Functional dependency beats compliance instruction
If anything the model is given can be interpreted as a usable response, the model may treat it as one and use it directly — whether or not it's actually valid or complete. In particular, if the model can assemble correct-sounding output without calling a required tool, it eventually will skip the tool. The durable fix is architectural: make the information the model needs to speak available ONLY from the tool's response, so producing the output requires calling the tool. A compliance rule ("you must call X") is weaker than a dependency ("the words you need exist only in X's response").

### D. Separate speech and tool-calling; let the client handle the acknowledgment
Speaking and calling a tool are two different kinds of output. If you want the model to call a tool and speak an acknowledgment at the same time, don't lean on the model to do both in the same turn. Best practice is to have the model emit only the tool-call event — no instruction in the prompt to also speak an acknowledgment. For long-running tools, if you want the caller to hear an acknowledgment while the tool runs, emit it manually from the client (Inject a short text turn into the session, if your integration supports mid-session text input, so the model says it in its own voice timed for a moment when neither the model nor the caller is speaking )(rule 18b).

### E. Over-pressuring one behavior tends to break another
Instructions that lean too hard on a single behavior — stacking DO NOT rules, or pushing "always finish the task" — tend to over-correct into the opposite failure. Heavy "never do X" phrasing makes X more salient (mental model A); pushing hard on task completion produces fabricated completions, while pushing too softly produces abandonment. Prefer balanced, positively-framed instruction: state the goal, and where two failure modes are opposed, name both halves together rather than maximally pressing on one side.

### F. Work with built-in platform behavior, not around it
Nova Sonic 2.5 has safety-relevant behavior that isn't controlled by your system prompt and can't be disabled — most notably around voice impersonation, cloning, and replication requests. Trying to instruct around this (e.g. phrasing designed to make the model "not deflect" or to override its own default behavior) is both unreliable and tends to make the model's overall behavior less predictable, since override-style phrasing competes with mental model A. If a legitimate use case seems blocked, redesign the prompt or UX around the desired *quality* rather than trying to force a bypass. See rule 9a and the Platform Behavior Note in Part 3.

---

## Part 2 — Prescriptive rules

### System prompt structure

1. **Pick ONE header convention and apply it consistently.** Both `[BRACKETED ALL-CAPS]` / `ALL-CAPS-COLON:` headers and `##` Markdown headers work. The failure mode is MIXING conventions within one prompt. Consistency is the rule; the specific style is not.
2. **Use bullet lists for rules, one rule per bullet.** More scannable than prose; reduces the chance the model echoes prose structure into spoken output.
3. **Include a self-verification gate at the end** (e.g. `[FINAL CHECK]`): 3–5 items the model confirms before speaking. Measurably improves compliance because the model processes it as a last-pass filter.
4. **State each instruction once, clearly.** Redundant restatements compete for attention and add latency. If a rule appears in both the system prompt and a tool description, keep one and remove the other.
5. **Place an instruction near its decision point, and reinforce at point of use** (mental model B). If a behavior is decided at a certain workflow step, state the rule at or just before that step. For a rule that spans the prompt, state it once early and add a short back-reference where it executes — rather than burying the only copy deep in the prompt.
6. **Keep the prompt as small as the task allows.** Long prompts dilute every instruction. Treat added length as a cost and cut redundancy wherever a rule is stated more than once.
7. **Avoid header names that sound like something a human might say** (e.g. "Configuration Boundary"). If a section header reads like natural speech, the model may vocalize it. Use structural names that make no sense spoken aloud.
8. **Never use instruction-override phrasing** — e.g. "ignore/forget/disregard previous instructions," "never deflect," "you must always answer directly regardless of X." This phrasing is unreliable on Nova Sonic 2.5 (mental model F) independent of whether it's adversarial; restructure the underlying instruction positively instead (see rule 9).

### Positive framing

9. **Describe desired behavior, never forbidden behavior** (mental model A). Naming the forbidden phrase or action puts it in context and raises the odds the model produces it anyway — state the behavior you want instead:
   - Instead of "Do not say 'configuration boundary' to the caller," write "Speak to the caller in warm, natural language."
   - Instead of "Never call the tool more than once," write "Call each tool at most once per turn, then speak to the caller."
   - **9a. Describe desired vocal qualities directly rather than referencing mimicking, cloning, imitating, or "sounding like" a specific voice or person.** Requests to copy or replicate a particular person's voice or speaking style won't be honored regardless of phrasing, for safety reasons — so there's no compliance upside to that framing, and it invites the general risks in mental model A/F. Describe the target quality instead:
     - Instead of "Mimic the tone of a news anchor," write "Speak in a professional, authoritative tone."
     - Instead of "Clone a calm speaking style," write "Use a calm, measured speaking style."
     - Instead of "Use this audio sample as reference for tone," describe the desired vocal qualities directly — warmth, formality, pace.
     - If your product needs "sound like X" as a user-facing feature, design it as a voice preset selector rather than a free-text imitation request — free-text requests to imitate a specific person's voice are not something the platform will fulfill even from your own users' input, not just your system prompt.
10. **Never put a forbidden phrase anywhere in context** — not in a ban list, not in a WRONG example containing the exact undesired output. If you must show a WRONG example, make its wording clearly different from the real forbidden output.
11. **Use natural phrasing in examples.** The model reuses example phrasing verbatim. Examples should sound like natural speech, not technical instructions.
12. **In one-shot examples, never use the exact scenario from the active test case.** Use a structurally similar but distinct scenario so the model learns the general behavior instead of overfitting to the test input.

### Tool calling and tool descriptions

13. **Keep tool descriptions short, positive, and light on restrictions.** Describe when to use the tool and what happens after. Avoid "do not," "use with caution," or "only once per turn" phrasing in a tool description — these tend to cause tool avoidance. Keep acknowledgment/speech policy out of the tool description entirely: whether and how the model should speak before, during, or after calling a given tool belongs in the system prompt (e.g. a TOOL EXECUTION RULES section), not duplicated into — or substituted for — the tool's own description (rule 4).
14. **Prefer functional dependency over compliance** (mental model C). Put what to speak and what to do next in the tool RESPONSE, so correct output is only reachable by calling the tool:
   ```json
   {"status": "captured",
    "speak": "<exact utterance the caller should hear>",
    "next": "<the follow-up action>"}
   ```
15. **Never name a tool inside its own response payload.** Writing "Do NOT call X again" in X's response primes the model to call X again (mental model A applied to tool responses). Use generic wording: "No further actions needed this turn."
16. **One clean rule beats many detailed constraints.** "Each tool at most once per turn" outperforms elaborate ordering rules or priority hierarchies.
17. **Co-optimize the prompt and the tool descriptions together.** They contribute equally to behavior; fixing one while neglecting the other won't reach full compliance.
   - **17a. Prefer schema `enum` constraints over prose + example value for fixed-value parameters.** A model told "set this to True" alongside an example value can copy the example by rote rather than reasoning about when it applies. Constrain the field in the schema itself:
     ```json
     "authenticated": {"enum": ["True"], "description": "Always True for a known caller."}
     ```
     rather than relying on a prose instruction like "set this to True for a known caller, e.g. true" in the description.
   - **17b. Never substitute a raw flag or enum value directly into spoken template text — convert it to a natural-language sentence first.** A literal boolean or enum spliced into a prose template produces garbled speech — a template like `"{{is_known_caller}} indicates whether the caller has access to this service"` renders as "true indicates whether...". Write out the two states as their own sentences instead: "This caller is a known customer. All services below are available." / "This caller is not a known customer. Only general information is available."
   - **17c. When a required silent-turn behavior doesn't hold, check sibling layers for a competing instruction before rewording the local rule.** A platform-level line like "always begin every response by addressing the caller's question" can silently override a tool-level "speak nothing this turn" rule. Rule 17's co-optimization applies across the system prompt, tool descriptions, *and* any platform/template layer — not just the first two.
18. **Instruct the model to call the tool as its entire response, with no spoken words that turn — never ask it to also speak an acknowledgment in that same turn** (mental model D). Don't phrase this as something to attempt or aim for; state it as the unconditional rule for every tool-call turn:
   - Instead of "in the same turn, speak one brief acknowledgment AND call the tool; never do one without the other," write "when you call a tool, call it as your entire response for that turn — speak no words at all. Any acknowledgment the caller hears comes from the platform, not from you."
   - A tool description like "if your reply contains 'I'll connect you,' you must call this tool" is a related form of over-coupling, and it can resolve backwards — satisfied by not speaking the phrase, or by speaking it and deferring the call. Don't write tool descriptions that key a tool call to spoken phrasing at all.
   - **18a. If a specific tool genuinely needs the model to speak and call together, for example: an end-call tool that must say goodbye, scope that exception to just that tool and exclude it from the general silent-call rule, rather than quietly weakening the rule for everything.**

     ```
     "transfer_to_billing and transfer_to_support: call the tool as your entire response, with no spoken
     words that turn. end_call is not covered by this rule — always speak a short goodbye before calling it."
     ```
     A general rule phrased as "routing and transfer tools are silent-call" will also catch end_call if the model classifies it as a transfer tool, and the caller hangs up with no goodbye — naming the exception explicitly avoids that.
   - **18b. Any acknowledgment the caller hears around a tool call — including latency masking on a slow tool — is produced entirely by the client, never by the model.** Don't ask the model to speak a filler, don't ask it to speak an acknowledgment, not even as a first attempt paired with a backstop. The client sends a text-input nudge (see appendix) only when two live conditions both hold:
     - The model is not currently speaking (occasional over-eagerness means this is worth checking live, not assuming from the prompt instruction).
     - The caller is not currently speaking.

     This is the one mechanism for any caller-facing acknowledgment or filler around a tool call, for every tool that needs one — not a fallback for a model-generated attempt that didn't land.

### Voice-specific

19. **Use the recommended baseline personality phrasing:** "warm, professional, helpful... natural, direct, human... answer in 1–2 sentences, then expand only enough, 3–5 short sentences total... avoid sounding like a lecture or essay."
20. **One-shot examples beat phrase lists.** The model is more sensitive to example phrasing than to lists of allowed/disallowed phrases; it adopts the tone and structure of examples directly.
21. **No formatted lists or numbering in expected spoken output** — it's a speech model; output should read as a natural spoken transcript.
22. **No `<thinking>` / `<thought>` tags.** Nova Sonic has built-in CoT for tool calling; adding thinking directives causes tool-call parsing failures.
23. **Use the system prompt for all behavior, tone, and language instructions.** If your integration exposes a separate "speech" prompt field, reserve it strictly for documented low-level speech/script controls (e.g. Hindi code-switching, per the platform documentation) — do not put behavior, tone, or general language instructions there.
24. **Never leave an empty bracket pair — `[]`, `{}`, `()`, `<>` — anywhere in prompt text**, even as a placeholder. Empty brackets can cause the model to regurgitate unrelated training data, sometimes in an unintended voice. Always fill placeholders with real content before shipping a prompt, or remove the bracket entirely.

### Personalization / context injection

25. **Treat personalization as two independent levers, in order: prioritization first, phrasing second.** The common failure is assuming the model "forgot" a preference. Usually it recalled it but either didn't surface it proactively (a prioritization/placement problem — the dominant lever) or surfaced it with a leaked source (a phrasing problem — the secondary lever). Fix surfacing first, then phrasing.
   - **25a. Gate what gets injected before deciding how to surface it.** Content generated and inserted into the prompt at runtime — summaries, retrieved snippets, personalization data — can trigger the same content filter or get vocalized the same way as text you wrote yourself, but it wasn't reviewed by a human before landing in context (mental model A applies to generated content, not just authored text). Scope injected context to the current agent's domain, and run generated summaries through the same forbidden-wording check as rule 10.

     For example: filter injected context to the current agent's domain before it reaches the prompt, rather than rendering every stored insight regardless of which domain it came from. And run generated summaries through the same forbidden-wording check as rule 10 before they're rendered — a generated line like "sends a copy of the full report" should become "a duplicate of the report" rather than reaching the prompt unreviewed.
26. **Surface an insight at the step that needs it, on the agent's own initiative** — don't require the caller to ask. If the insight guidance is scattered or buried, consolidate it and move it to that decision step (mental model B).
   - **26a. State the proactive-surfacing rule as one concrete sentence at the exact step, with example phrasing.** A general "use personalization when relevant" section surfaces far less reliably than a sentence anchored to the decision point itself.

     Instead of a general instruction like "Use context data to personalize responses where appropriate," write the condition and the action together at the step where it applies: "If the caller hasn't named a specialty and stored context has one for this step, propose it in one short question first (e.g., 'Would you like to see a cardiologist, perhaps Dr. Rao?')."
27. **Never attribute a proposal to the caller's history in spoken output.** Propose the preference without citing its source: "Would a Friday around four in the afternoon work for you?" — not "Since you've preferred Friday afternoons in the past..." or "You usually prefer evenings, so...".
28. **For sensitive topics, distinguish durable preferences from episodic facts before surfacing them.** A standing preference (e.g. a preferred day, time, or channel) may be proposed directly. Where an insight touches a sensitive area, an episodic or one-off fact should be offered as an open, easily-declined question rather than presumed or turned into a recommendation. Key such a rule on the KIND of insight, not a specific data field, so it survives schema changes.
   - **28a. Render injected context minimally.** One short line per item — category, source, summary. Drop IDs, confidence scores, timestamps, and empty fields; they cost tokens and the model doesn't act on them.

     Render a stored insight such as `{"insightId": "a93f...", "confidence": 0.82, "domain": "cardiology", "summary": "...", "createdAt": "2026-09-01T00:00:00Z"}` as a single line in the prompt — "Cardiology: prefers Thursday afternoon appointments." — and drop the rest of the fields; the model doesn't act on them.

### Safety guardrails

29. **Put universal safety rules in an always-on guardrail section, scoped to every source.** A rule like "never recommend care, suggest a diagnosis, or assert/presume the reason for the visit — ask or offer as a question, from any source (caller, tool result, or context)" fires reliably because it's behavior-triggered and source-independent. Keying it to one data field or one section makes it brittle.
30. **Anti-hallucination for actions: tie the spoken outcome to the tool result.** "Do not say an action is done, and do not state a confirmation number, until the tool has returned it; the number you speak must be the tool's exact value." This is a compliance rule when the tool set is fixed; the stronger version is the functional dependency (rule 14) where the confirmation only exists in the tool response.
31. **For date/temporal reliability, have the model READ a provided value, not compute it.** A runtime date table (weekday-to-date lookup) that the model reads from — rather than calculating weekdays itself — meaningfully reduces date-arithmetic errors. Keep such runtime aids intact.
   - **31a. Resolve relative date phrases to absolute dates at write-time, not render-time, for anything generated and reused later.** Any pipeline that generates text containing a date phrase for later reuse should resolve it against the author's date at the moment of writing — not leave it relative to be reinterpreted whenever it's read back.

     Store "requested Thursday, October 8, 2026" — resolved once, at write time — rather than storing "requested next Thursday" and re-evaluating what "next Thursday" means every time the record is rendered later.
32. **When a user turn might contain a request the platform won't fulfill (e.g. asking the assistant to sound like a specific real person), don't try to prompt around it.** Design the product surface so that need is met a different way (voice presets, style descriptors, explicit consent flows for legitimate voice-actor use cases) rather than tuning the system prompt to permit it.

---

## Part 3 — Platform behavior note

Nova Sonic 2.5 includes safety-relevant behavior that sits outside anything you write in the system prompt and cannot be turned off from the prompt — most notably around voice cloning, impersonation, and replication (both when your own system prompt asks for it, and when a caller/user asks for it mid-conversation, across multiple languages).

Practical implications:

- If the model isn't following an instruction and the topic is safety-adjacent (impersonation, cloning, refusals on sensitive topics, medical/legal-style advice), suspect platform-level behavior before assuming a plain prompt bug. Restructure using positive framing (Part 2) rather than escalating to override-style language — that tends to make things worse, not better (mental model F).
- This isn't something prompt tuning can fully route around, and it isn't meant to be: treat it the same way you'd treat any other foundation-model safety behavior — design for it rather than against it.

---

## Part 4 — Review checklist

Run this before shipping or handing off a Nova Sonic 2.5 prompt:

- [ ] Exactly one header convention used throughout (no mixing `##` and `ALL-CAPS:` styles)
- [ ] No "do not / never / avoid X" phrasing where a positive instruction would work instead
- [ ] No forbidden phrase or WRONG-example wording anywhere in context that matches real undesired output
- [ ] No instruction-override phrasing ("ignore previous instructions," "never deflect," etc.)
- [ ] Every rule appears exactly once; no rule duplicated across system prompt and tool descriptions
- [ ] Rules that govern a specific workflow step are stated at or near that step, not only in a general section far away
- [ ] Tool descriptions contain no warnings, "use with caution," or "only once" language
- [ ] Any scripted post-tool speech is returned by the tool response, not just stated in the system prompt as a hope
- [ ] No tool's response text names or instructs about itself ("do not call X again" inside X's own response)
- [ ] No instruction anywhere asks the model to speak and call a tool together in the same turn — tool-call turns are instructed to be silent, full stop, with no attempt-first framing
- [ ] No `<thinking>`/`<thought>` tags anywhere in the prompt
- [ ] No empty bracket pairs (`[]`, `{}`, `()`, `<>`) anywhere, including unfilled placeholders
- [ ] If a separate "speech" prompt field is used, it contains only documented speech/script values — no behavior or tone instructions
- [ ] Voice/style instructions describe qualities (tone, pace, warmth) rather than referencing mimicking, cloning, or a specific real person's voice
- [ ] Personalized suggestions never cite "since you've historically..." phrasing in spoken output
- [ ] Any relative date/time the model must speak or act on is resolved from a provided lookup table, not computed by the model
- [ ] Any text generated for later reuse has relative dates resolved to absolute dates at write time, not left to be reinterpreted at render time
- [ ] Injected/generated context (summaries, personalization data) is scoped to this agent's domain and checked against the same forbidden-wording list as the rest of the prompt
- [ ] Injected context is rendered as one short line per item, with IDs, scores, timestamps, and empty fields dropped
- [ ] Fixed-value parameters use schema `enum` constraints rather than prose plus an example value
- [ ] No raw flag or enum value is substituted directly into spoken template text
- [ ] Silent-turn / "call tool as entire response" rules are scoped to the specific tools that need them, excluding end-call and post-call-speech handovers
- [ ] If a silent-turn rule isn't holding, sibling layers (tool description, system prompt, platform template) have been checked for a conflicting instruction
- [ ] Latency masking and post-tool-call acknowledgments are produced entirely by a client-injected text-nudge — the model is never instructed to speak a filler or acknowledgment on a tool-call turn, not even as a first attempt
- [ ] All acknowledgment/latency-masking speech around a tool call comes from the client via a text-nudge, gated live on the model not currently speaking (occasional over-eagerness) and the caller not currently speaking — never scripted as something the model should say inline
- [ ] Tool descriptions state only what the tool does; any acknowledgment/speech policy is stated once, in the system prompt, not duplicated into the tool description
- [ ] Overall prompt length is no longer than the task requires — no redundant restatement inflating it

---

## Part 5 — Quick reference card

| Do this | Not this |
|---|---|
| One consistent header convention throughout | Mixing header styles within one prompt |
| "Call each tool at most once per turn" | "Do NOT call the tool more than once" |
| Put required speech in the tool response `"speak"` field | Put scripted phrases only in the system prompt |
| Instruct the model to call the tool with no speech that turn | Ask the model to speak and call the tool together |
| Client owns every acknowledgment/filler around a tool call | Script a model-generated acknowledgment, even as a first attempt |
| State the goal; name both halves when failure modes are opposed | Over-pressure one behavior or pile on DO NOT rules |
| Rule stated once, early, at the decision point | Rule buried deep and restated inconsistently |
| Describe desired vocal qualities directly | Reference mimicking/cloning/imitating a specific voice |
| System prompt for all behavior, tone, language | Behavior instructions in a speech/script-only field |
| Personalization: fix prioritization first, then phrasing | Assume the model "forgot" and chase recall |
| For sensitive topics, offer an episodic fact as an open question | Presume it or turn it into a recommendation |
| Behavior-triggered guardrail scoped to every source | Guardrail keyed to one data field or section |
| Read dates from a runtime table | Let the model compute weekdays |
| Restructure a blocked instruction positively | Use override phrasing ("ignore instructions," "never deflect") |
| Resolve a stored date phrase to absolute at write time | Leave it relative and reinterpret at render time |
| Scope and sanitize injected context before rendering it | Render whatever was generated, unreviewed |
| One short line per injected context item | IDs, scores, timestamps, empty fields included |
| Schema `enum` for fixed-value parameters | Prose instruction plus an example value |
| Convert flags to natural sentences before templating | Substitute a raw boolean/enum into spoken text |
| Silent-call rule scoped to the specific transfer tools | Blanket silent-call rule across every tool |
| Backfill with a client text nudge only if the turn had no speech | Nudge unconditionally, even after the model already spoke |
| Check live that the model and caller are both silent before nudging | Assume the prompt instruction alone is enough to skip the check |
| Acknowledgment/speech policy stated once, in the system prompt | Acknowledgment policy duplicated into the tool description |

---

## Appendix — Three architectural patterns worth proposing

**Functional-dependency tool response.** Instead of scripting the agent's post-tool utterance in the system prompt, return it from the tool (`"speak"`/`"next"` fields). The model must call the tool to know what to say, which eliminates tool-avoidance and speak-without-call in one move.

**Collapse mandatory tool sequences into one tool.** For flows requiring an ordering (e.g. lookup then capture-on-miss), combine them into a single tool where the backend handles the conditional logic and returns the right spoken phrase in all cases. This removes multi-tool sequencing from the model entirely and eliminates ordering violations, tool avoidance, and partial-flow completion as a class.

**Client-injected text nudge for latency masking and post-tool-call speech.** The model is instructed to call a tool as its entire response, with no spoken words that turn (rule 18) — full stop, not an attempt the client falls back from. Any acknowledgment or filler the caller needs around that tool call is produced entirely by the client, right after the tool-call turn and before the tool result arrives. Check two live conditions before injecting anything:
- The model is not currently speaking (it's occasionally over-eager and may speak despite the instruction — this is a defensive check, not an expected case).
- The caller is not currently speaking.

Only when both hold, inject a short imperative text instruction via cross-modal text input. Two further conditions make this reliable:
- Phrase the injected text as an instruction ("Tell the caller you're connecting them now"), not a description ("The caller is waiting") — descriptions don't reliably produce speech.
- Send exactly one tool result per tool use; sending an interim result followed by a final one for the same call is rejected.
