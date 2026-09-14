# Helzer AI module

The AI layer is intentionally separated from the giveaway domain.

```text
ai/
├── __init__.py      # public AI entry point
├── service.py       # AI service helpers/facade
├── prompts.py       # personality, language and behavior rules
├── triggers.py      # Helzer word/mention trigger parsing
└── memory.py        # persistent conversation storage
```

The existing `ai_agent.py` remains the compatibility action engine for Discord tools and high-risk confirmations. `main.py` imports the public AI entry point from `ai/`, so future AI features can be added without putting more unrelated code into the root module.

The current conversation behavior is:

- server messages: normal Discord text replies
- DM messages: Components V2 replies
- trigger: `Helzer`, a direct mention, or a reply to Helzer
- Sinhala/Singlish/English mixed-language support
- recent conversational context
- no forced mention on normal replies
