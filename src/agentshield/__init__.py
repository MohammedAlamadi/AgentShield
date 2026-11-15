"""AgentShield: a lightweight three-layer defence against indirect prompt injection.

Layer 1 - injection detection (ProtectAI DeBERTa classifier, CPU)
Layer 2 - content isolation (source-tagged delimiters, Spotlighting "delimiting" variant)
Layer 3 - deterministic tool-call authorization guard (deny by default, trusted task scope)

All tools act on a synthetic in-memory environment only.
"""

__version__ = "0.1.0"
