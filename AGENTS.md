# AGENTS.md — ArthX

This file is the standing-instructions entry point auto-loaded by Google Antigravity agents (Gemini/Claude) working in this workspace.

**Before doing anything else, read these two files in full:**

1. **CLAUDE.md** — architecture, tech stack, MVP scope decisions, coding conventions, security rules, explainability requirements, and testing expectations for this project. This is the non-negotiable source of truth for *how* to build.
2. **TASK.md** — the exact, ordered execution roadmap: phases, tasks, acceptance criteria, what's parallelizable, what's demo-critical, what to cut if behind schedule, and where to escalate.

## Rules for every agent session in this workspace

- Do not start writing code before reading both files above.
- Execute tasks from TASK.md **in order**, respecting 🔴 critical-path and ⚡ parallelizable markers.
- Do not mark a task complete until its acceptance criterion (stated in TASK.md) is verifiably met.
- Do not introduce new technologies, dependencies, or architecture changes beyond what CLAUDE.md specifies. If something is ambiguous, choose the simplest solution that keeps the end-to-end demo working, note the assumption in a code comment, and continue — don't stop and don't silently redesign.
- Inspect existing code before modifying it. Do not rewrite working code to add a feature.
- When a 🧠 escalation point in TASK.md is hit, or an error repeats after two fix attempts, stop and flag it for Claude Code escalation rather than continuing to retry — do not attempt to solve it indefinitely on your own.
- Every AI output (anomaly flag, forecast, assistant answer) must be grounded in real data from this project, per the explainability rules in CLAUDE.md Section 7.

## Project name

The project is called **ArthX**. Use this name consistently in code comments, UI text, README content, and any generated documentation — do not default to a placeholder or generic name.
