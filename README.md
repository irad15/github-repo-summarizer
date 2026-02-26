# GitHub Repo Summarizer API

This is a FastAPI-based service that takes a GitHub repository URL and returns a human-readable summary of the project: what it does, what technologies it uses, and how it is structured.

## Prerequisites
- Python 3.10+
- An OpenAI API Key (or a compatible LLM provider API Key)

## Setup Instructions

1. **Clone or Extract the Source Code**:
   Navigate to the directory containing this code.

2. **Create a Virtual Environment** (Optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the root directory (or export it directly to your terminal) and provide your OpenAI API key:
   ```bash
   OPENAI_API_KEY="sk-your-api-key-here"
   ```

5. **Run the Server**:
   Start the FastAPI development server using Uvicorn:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Usage

You can test the API by sending a `POST` request to `/summarize` with a valid public GitHub repository URL.

```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/username/repository"}'
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/psf/requests"}'
```

### Expected Response

```json
{
  "summary": "**Requests** is a popular Python library for making HTTP requests...",
  "technologies": ["Python", "urllib3", "certifi"],
  "structure": "The project follows a standard Python package layout..."
}
```

## Design Decisions

### Model Choice
I chose **OpenAI's `gpt-4o-mini`**. It was selected for its native, highly reliable Structured Outputs (`response_format={"type": "json_object"}`), ensuring the API strictly adheres to the requested JSON schema without hallucinations breaking the parsing logic, while being extremely fast and cost-effective.

### File Handling Approach (Context Management & Memory Safety)
Handling large repositories correctly is the biggest challenge of this task. To prevent out-of-memory crashes on massive repositories and ensure we stay within the LLM's context limits, I used the **GitHub Git Trees REST API** (`/git/trees/main?recursive=1`) to pull just the repository structure instead of downloading a full ZIP archive.

Based on this tree structure, here is how I handle the contents:

* **What I skip**: I aggressively filter out noise using `pathspec`. This includes binary files (images, PDFs), compiled code (`.pyc`, `.o`), lock files (`package-lock.json`, `poetry.lock`), dependency folders (`node_modules/`, `venv/`), and hidden IDE/Git metadata (`.git/`, `.vscode/`).
* **What I include**: From the remaining files, I heuristically prioritize up to 10 key files to fully download. I specifically include root-level documentation (`README.md`), configuration/dependency files (`package.json`, `pyproject.toml`), and core entrypoint source files (`main.py`, `app.js`, `index.ts`). I also include a flat text representation of the entire filtered directory tree.
* **Why**: The LLM does not need to read 5,000 files of deep utility functions to summarize a project. By skipping non-text noise and deep utility scripts, we save bandwidth, improve speed, and prevent context window overflow. By specifically including the structural file tree, the README, and the core dependency/entrypoint files, we provide the LLM with the highest-density signal possible to accurately deduce the project's purpose, technologies, and architecture.
