"""ContractIQ — AI-Powered Contract Review & Risk Analyzer.

Package layout mirrors SRS Section 6 (Recommended Project Structure):

    contractiq/
    ├── core/        shared config, models, LLM + embedding clients, vector store
    ├── ingestion/   PDF parsing, chunking, embedding pipeline (FR-1)
    ├── rag/         retrieval + Q&A layer (FR-6)
    ├── mcp_server/  MCP tool server (FR-7)
    ├── agents/      multi-agent LangGraph-style pipeline (FR-2..FR-5)
    ├── api/         FastAPI backend REST API (FR-8 backing)
    └── report/      PDF report generation (FR-9)
"""

__version__ = "1.0.0"
