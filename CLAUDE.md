# CLAUDE.md

Study repo for the **CCAR-F exam (Claude Certified Architect – Foundations)**. The labs are a hands-on showcase of the exam's concepts, not a production product.

## Goal and priorities

- Learn to understand and apply, not just to pass. The target is the certificate; the stretch target is passing **before 18 Dec 2026**, with Jan 2027 as the fallback.
- Exam-guide topics come first. Off-exam topics (API drift, Managed Agents, production hardening, rate limits and abuse controls, refactors) wait until after the exam.
- The exam has 60 questions in 120 minutes, single and multiple response, drawn from 4 of 6 scenarios. Passing is 720/1000. Domain weights: D1 Agentic architecture 27%, D2 Tool design & MCP 18%, D3 Claude Code config 20%, D4 Prompt engineering & structured output 20%, D5 Context & reliability 15%.
- **The study plan lives in a Google Doc** and is the source of truth: https://docs.google.com/document/d/1kBxV2NGxrJYMKb9A19ViMDO7fd7HPihL80anpqMW9ls/edit. The `.docx` in the repo root is a stale copy. Check off checklist items there as they finish.

## How to work with me

- **Always ask before making any Claude API call** (running `main.py`, `sandbox.py`, or anything that hits the API), unless I explicitly say to run it. Editing files is fine without asking.
- Teach hands-on and keep it light: small build → break → observe experiments, each tied to an exam task statement, then a short exam angle (how it's asked, the distractors). No long concept lectures, no deep refactors or folder reshuffles.
- Don't reveal an experiment's result before I run it.
- I write in English or Vietnamese. Reply in English unless I ask for Vietnamese; explain compressed exam wording in Vietnamese when I'm confused.
- Give a recommendation, not a survey of options.

## Repo layout

- `config.py`: the shared Anthropic client, `MODEL` (`claude-haiku-5-5`), `MAX_TURNS`, the log path, and the `SIMULATE_*_TIMEOUT` env flags.
- `core/`: code that any lab can reuse.
  - `core/tools/executor.py`: `ToolExecutor[S: ToolSession, C]` runs pre-hooks, then `context_factory(session)`, then the handler with its retry policy, then post-hooks.
  - `core/tools/errors.py`: `ToolError` and its subclasses (validation, transient, business, permission, internal).
  - `core/tools/retry.py`: `RetryPolicy` (`retry_by`: `code`, `model`, or `none`).
  - `core/tools/hooks.py`: the `PreHook` and `PostHook` types.
  - `core/tools/session.py`: `ToolSession`.
  - `core/tools/results.py`: the `ToolResult` types.
  - `core/claude_blocks.py`: block helpers, including `to_tool_result_block`.
  - Also: `core/agent_logger.py` (developer log, `tail -f logs/agent.log`), `core/console.py`, `core/stop_reasons.py`.
- `lab01_customer_support_agent/`: **Build A**, a hand-written Client SDK customer support agent.
  - `main.py`: the agentic loop and `TEST_QUERIES`.
  - `system_prompt.txt`
  - `session.py`: `AgentSession`, which holds trusted facts written only by post-hooks.
  - `context.py`: a frozen `ToolContext` built from the session.
  - `hooks/identity.py`: the verification and active-account pre-hooks, plus the record-customer post-hook.
  - `tools/`: the tool schemas and handlers, plus the `TOOL_HANDLERS`, `RETRY_POLICIES`, `PRE_HOOKS` and `POST_HOOKS` registries.
  - `data.py`: mock data.
- `sandbox.py`: a scratch file for single API experiments.
- `claude-certified-architect/`: a cloned reference repo. **Never modify, lint or stage it.**

Run from the repo root (imports resolve from both the root and the lab folder):

```bash
PYTHONPATH=.:lab01_customer_support_agent .venv/bin/python lab01_customer_support_agent/main.py
```

## Design rules already in the code

- The loop is driven by `stop_reason` (`tool_use` / `end_turn`). A `tool_result` block only accepts `type`, `tool_use_id`, `content` and `is_error`. Custom fields such as `error_category` and `is_retryable` go inside the `content` JSON.
- Handlers raise typed `ToolError`s, and the executor turns them into results. Writes such as `process_refund` are never auto-retried. A timeout means the outcome is unknown.
- Pre-hooks block and fail closed, and a deny always carries a reason. Post-hooks observe and record and fail open; they never alter the result.
- Only post-hooks write trusted facts into the session. Handlers get `handler(ctx, **tool_input)` with a frozen `ToolContext`, so Claude can't spoof identity through tool input.
- Ownership uses scoped queries. `lookup_order` returns `found=false` for another customer's order, which keeps it safe from enumeration. `process_refund` raises a permission error instead.
- Refunds over $500 return a business error with `requires_escalation=True`. A suspended account is blocked by `require_active_account`.
- `escalate_to_human` takes a structured handoff schema. Code adds the identity facts from ctx; Claude supplies the judgment fields.

## Conventions

- Python 3.14, using PEP 695 generics and `type` aliases, `@dataclass(frozen=True)`, and `functools.partial` rather than lambdas where narrowing matters.
- Ruff runs through pre-commit (line length 120, double quotes). Match the existing comment style.
- Commits use gitmoji, scoped like `:sparkles: CS Agent: …`. Stage explicitly (`git add core lab01_customer_support_agent …`), never `git add .`.
- `.env` holds the API key and the optional `SIMULATE_LOOKUP_TIMEOUT=1` / `SIMULATE_CUSTOMER_TIMEOUT=1`. Turn those off for normal runs.

## Current status (update as it moves)

- Build A checklist items 1–6 are done: loop, structured errors, hooks, ctx and ownership, handoff, escalation criteria.
- **Next is item 7, case facts (task 5.1).**
  - It needs a true multi-turn `Conversation` (`messages` + `session`) that appends the `end_turn` response and resets on a new test query.
  - Then add `session.case_facts`, keyed by entity (customer; orders with refunds nested inside each order; escalation). Merge, don't append, and make `case_facts.customer` the single source.
  - Write the facts with post-hooks, from successful results only.
  - Add a `<case_facts>` block to the system prompt, rebuilt inside the loop before every API call.
  - Add a small compaction simulator for the experiment.
- After that: item 8 (`tool_choice` experiments), then Build B (MCP server mini-lab) and Build C (Agent SDK subagents, hooks and sessions).
