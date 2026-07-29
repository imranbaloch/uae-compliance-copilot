"""FastAPI + web dashboard layer on top of the `compliance_copilot` agent
library. This package is a *consumer* of the core library — it imports
`Supervisor` and the `compliance_copilot.memory.state` models but the core
agent code has no dependency on this package. Run with:

    uvicorn api.app:app --reload

See README.md's "API & Web layer" section for the full guide.
"""
