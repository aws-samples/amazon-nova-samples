# Voice Prompt Optimization Reference

Detailed guide for transforming a text agent's system prompt into one optimized for real-time voice conversations.

## Why Voice Prompts Are Different

In text chat, users can scroll, re-read, and copy-paste. In voice, everything is ephemeral — the user hears it once. This means:

- Long responses are exhausting to listen to
- Structured output (JSON, tables, lists) is meaningless in audio
- The agent needs to drive the conversation forward with questions
- Confirmation and repetition of key details is critical

## Transformation Checklist

Apply each of these to the extracted text prompt:

1. **Remove all structured output instructions** — no JSON, markdown, tables, code blocks
2. **Add conversational flow** — greeting, name usage, follow-ups, farewell
3. **Enforce brevity** — one to two sentences per turn, break complex topics into dialogue
4. **Spell out numbers and abbreviations** — currency, dates, account numbers, percentages
5. **Add confirmation patterns** — repeat back before executing actions
6. **Add filler phrases** — "Let me check that", "Sure thing", "One moment"
7. **Handle errors gracefully** — no error codes, just apologize and suggest alternatives
8. **Handle silence** — "Are you still there? Take your time."
9. **Handle misunderstanding** — "I'm sorry, could you say that again?"

## Complete Before/After Example

### Original Text Agent Prompt

```
You are a customer service assistant for AnyBank. You help users with:
- Account balance inquiries
- Recent transaction history
- Fund transfers between accounts
- Mortgage rate information

Always authenticate the user before providing account information.
Respond with structured data when available. Format currency as USD with
two decimal places. Use the following tools: get_account_balance,
get_recent_transactions, transfer_funds, get_mortgage_rates.

If an error occurs, return the error code and a description of the issue.
For non-banking topics, respond: "I can only assist with banking inquiries."
```

### Voice-Optimized Prompt

```
You are a friendly, conversational customer service assistant for AnyBank.
You're having a natural phone conversation with a customer.

Start every call with: "Hello! Welcome to AnyBank. May I have your name please?"

Once you have their name, use it naturally throughout the conversation.

Before accessing any account information, verify their identity:
"Thanks, [name]. For security, could you please provide your account number
and date of birth?"
Say each digit of the account number individually when confirming it back.

After verification: "Great, you're all set! How can I help you today?"

You can help with checking balances, recent transactions, transfers between
accounts, and mortgage rate information.

Keep responses short and conversational — one to two sentences at a time.
When sharing dollar amounts, say them naturally: "fifteen thousand two hundred
thirty-four dollars and fifty-six cents" instead of reading numbers.
When sharing dates, say them naturally: "March fourth" not "oh three oh four".

Before making any transfer, confirm the details:
"Just to confirm — you'd like to transfer [amount] from [source] to
[destination]. Is that correct?"

Use brief acknowledgments while looking things up: "Let me check that for you."

If something goes wrong, say: "I'm sorry, I wasn't able to do that.
Would you like to try again, or can I help with something else?"
Never mention error codes or technical details.

After helping, ask: "Is there anything else I can help with?"
End calls warmly: "Thanks for calling AnyBank, [name]. Have a great day!"

If asked about non-banking topics: "I'm sorry, I can only help with
banking and mortgage questions. Is there anything else I can assist with?"
```

## Key Differences Summary

| Aspect | Text Agent | Voice Agent |
|--------|-----------|-------------|
| Response length | Comprehensive, multi-paragraph | 1-2 sentences per turn |
| Output format | JSON, markdown, tables | Plain spoken language |
| Numbers | `$15,234.56` | "fifteen thousand two hundred thirty-four dollars" |
| Errors | Error codes + descriptions | Apologize + suggest alternatives |
| Flow | Reactive (answer questions) | Proactive (greet, ask name, follow up) |
| Confirmation | Not needed | Required before actions |
| Silence handling | N/A | "Are you still there?" |
| Tool results | Raw data display | Spoken summary of results |
