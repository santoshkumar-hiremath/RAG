Markdown# Unified RAG Ingestion & Intelligence Pipeline (PCAI)

This repository contains a high-performance **Retrieval-Augmented Generation (RAG)** pipeline designed to centralize technical intelligence. It bridges the gap between static local documentation and dynamic cloud-based knowledge from the HPE Confluence Wiki (Project PCAI).

---

## 🚀 Execution Workflow (Order of Operations)

To ensure the system has the latest data and correct access, follow this specific sequence:

### 1. Authenticate
Run this to handle Okta/SSO authentication and capture session tokens.
```bash
python auth_session.py
What it does: Opens a visible browser for you to log in manually via Okta.Why: It saves a storage_state.json file. The ingestion script uses this to bypass MFA and reach internal Wiki pages.2. Ingest & IndexRun this to build or refresh the "brain" of the AI.Bashpython ingest.py
What it does: * Scans /data_files for PDF, TXT, and DOCX.Recursively crawls the Project PCAI Wiki (CPC Space).Chunks text ($1200$ chars) and generates vector embeddings.Output: Creates combined_index.faiss and metadata.json.3. Launch the UIRun this to start the Q&A interface.Bashstreamlit run app.py
What it does: Opens a local web interface. The AI searches your indexed files and provides cited, step-by-step answers.🛠 Project ComponentsScriptRoleDescriptionauth_session.pyAuthenticatorManages secure SSO session persistence to bypass Okta MFA.ingest.pyProcessorHandles multi-source scraping, semantic chunking, and FAISS indexing.app.pyInterfaceStreamlit UI for querying Llama 3 via Ollama with full citations.🧠 Technical StackLLM: Llama 3 (via Ollama) — Runs 100% locally for data privacy and security.Embeddings: all-MiniLM-L6-v2 — Optimized for semantic similarity.Vector Store: FAISS — Provides sub-millisecond nearest-neighbor search.Automation: Playwright — Navigates and renders JavaScript-heavy Confluence pages.Hardware Acceleration: Automatically utilizes Mac MPS (Metal Performance Shaders) for GPU-accelerated indexing.💡 Key FeaturesRecursive Discovery: Automatically traverses child pages in the CPC Wiki space.Hydration Awareness: Uses specialized delays to ensure Confluence content is fully rendered before extraction.Semantic Integrity: Employs a $200$-character chunk overlap to prevent technical steps from being split across chunks.Privacy Focused: All data remains on the local environment; no internal docs are sent to external cloud APIs.Hallucination Guardrails: The system is prompted to respond "Information not provided" if the answer is not present in the local knowledge base.📁 Directory StructurePlaintexthpe-rag/
├── data_files/          # Drop local PDF/DOCX/TXT files here
├── auth_session.py      # Script to refresh SSO login
├── ingest.py            # Main ingestion and indexing script
├── app.py               # Streamlit Q&A interface
├── storage_state.json   # Generated session tokens (Sensitive)
├── combined_index.faiss # Generated Vector Database
└── metadata.json        # Mapping of chunks to source URLs/Files
🔧 TroubleshootingWiki Timeout: If ingest.py fails to scrape the Wiki, your session has likely expired. Re-run python auth_session.py.Missing Data: Ensure all local files are placed inside the /data_files folder before running ingest.py.Ollama Connection: Ensure the Ollama app is running in the background before launching app.py.
