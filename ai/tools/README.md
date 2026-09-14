# AI Tools

Discord action tools are currently owned by the compatibility action engine in `ai_agent.py`.

The tool surface is intentionally kept behind the modular `ai/` boundary so it can be split into moderation, messaging, server, and scheduling modules without changing behavior.
