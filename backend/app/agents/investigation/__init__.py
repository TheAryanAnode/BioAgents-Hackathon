"""CRAFT-powered real-world evidence investigation sub-graph.

A user-initiated, multi-agent loop that stress-tests a literature hypothesis
against PanCancer genomics + IDC imaging via the CRAFT MCP semantic layer.
"""

from app.agents.investigation.orchestrator import investigate

__all__ = ["investigate"]
