# 103 Plan explanation and customer message (LLM)

**Status:** Proposed · **Owner:** unassigned · **Depends on:** 004, 005

## Why

The plan cards are numbers. A service manager wants one plain sentence on why this plan, and a
customer message they can send without rewriting it. This is the only place an LLM is used.

## Rules

1. The LLM explains and drafts. It never chooses or changes the plan, the source or any number.
2. Two calls only: (a) explain the chosen option in at most two sentences; (b) draft one message per customer whose promise is newly missed.
3. The prompt contains only the proposal's own facts: vehicle, RO number, part, source, arrival, promise and new finish times, jobs moved, missed promises. No customer names, phone numbers or other personal data.
4. Every time and number in the LLM's text must appear in the facts it was given. If a check fails, the template text is used instead.
5. The provider and key come from environment variables (`LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`). No key in the repo, ever.
6. With no key, a timeout (5 s), or an error, the app uses today's fixed template and shows a visible "LLM off, template text" notice. Nothing else changes.
7. The log records who wrote each message: `llm:<model>` or `fixed template`.
8. Tests never call a real LLM. They use a fake that returns set text.

## API

The approve response and the proposal gain `explanation` and `explained_by`. Customer messages
keep their current shape plus `written_by`.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | No key set: template text and the "LLM off" flag | `test_without_a_key_the_template_is_used` (to write) |
| A2 | Fake LLM text with a time not in the facts is rejected and the template used | `test_llm_text_with_invented_numbers_is_rejected` (to write) |
| A3 | Fake LLM text that passes is used and the log says `llm:<model>` | `test_llm_text_is_used_and_labelled` (to write) |
| A4 | The approved plan is identical with and without the LLM | `test_llm_never_changes_the_plan` (to write) |
| A5 | The prompt contains no field outside the allowed list | `test_prompt_contains_only_plan_facts` (to write) |

## Out of scope

Sending messages, chat with the LLM, voice.

## Open questions

- Which provider can we get a key for? Any works; a free tier is enough. Team decides.
