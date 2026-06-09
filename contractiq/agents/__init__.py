"""Multi-agent pipeline (SRS FR-2..FR-5) orchestrated as a LangGraph-style graph."""
from .orchestrator import Orchestrator, run_pipeline

__all__ = ["Orchestrator", "run_pipeline"]
