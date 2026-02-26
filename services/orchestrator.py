import asyncio
import logging
from typing import Dict, Any

from services.github import parse_github_url, get_repo_info, get_repo_tree, get_raw_file_content, GitHubClientError
from services.processor import filter_paths, build_tree_string, prioritize_files
from services.llm import generate_summary

logger = logging.getLogger(__name__)

async def process_github_repo(url_str: str) -> Dict[str, Any]:
    """
    Orchestrates the fetching, filtering, and LLM summarization of a GitHub repository.
    
    This function acts as the central brain of the service, tying together the external
    GitHub API calls, local path filtering, concurrent file downloading, and OpenAI processing.
    
    Raises:
        ValueError: If the provided GitHub URL cannot be parsed.
        GitHubClientError: If any GitHub API request fails or the repository is inaccessible.
    """
    owner, repo = parse_github_url(url_str)
    logger.info(f"\n{'='*50}\n🚀 ANALYZING REPOSITORY: {owner}/{repo}\n{'='*50}")

    # 1. Get default branch
    try:
        repo_info = await get_repo_info(owner, repo)
        default_branch = repo_info.get("default_branch", "main")
        logger.info(f" ├─ 📡 [METADATA] Fetched {len(repo_info)} keys. Default branch: '{default_branch}'")
    except Exception as e:
        raise GitHubClientError(f"Could not access repository: {owner}/{repo}. It may be private or invalid. Details: {e}")

    # 2. Get the full repository tree structure
    # We use recursive=1 to get all files in a single flat list without repeatedly querying directories
    try:
        tree_data = await get_repo_tree(owner, repo, default_branch)
        logger.info(f" ├─ 🌳 [GIT TREE] Fetched raw tree with {len(tree_data)} total items. First item preview: {tree_data[0]['path'] if tree_data else 'None'}")
    except Exception as e:
        raise GitHubClientError(f"Failed to fetch repo tree: {e}")
        
    # Extract only the actual file paths (type 'blob') and ignore directoriy paths (type 'tree')
    all_paths = [item["path"] for item in tree_data if item["type"] == "blob"]
    
    # 3. Filter paths to remove noise
    # Drop binaries, lock files, node_modules, etc. using .gitignore style rules
    clean_paths = filter_paths(all_paths)
    logger.info(f" ├─ 🧹 [FILTERING] Dropped {len(all_paths) - len(clean_paths)} noise files. Remaining paths: {len(clean_paths)}")
    
    file_tree_str = build_tree_string(clean_paths)
    indented_tree = "\n".join([f" │      {line}" for line in file_tree_str.split("\n")])
    logger.info(f" ├─ 📄 [TREE MAP] Generated clean tree string:\n{indented_tree}")
    
    # 4. Prioritize and fetch contents
    # We can't send thousands of files to the LLM due to context limits.
    # So we pick the most important ones (READMEs, configs, top-level source files).
    priority_paths = prioritize_files(clean_paths, max_files=10)
    formatted_priority = "\n".join([f" │      - {p}" for p in priority_paths])
    logger.info(f" ├─ ⭐ [PRIORITIZATION] Selected top {len(priority_paths)} files for LLM context:\n{formatted_priority}")
    logger.info(f" ├─ 📥 [FETCHING] Concurrently downloading file contents...")
    
    # Fetch all priority files concurrently to save time
    fetch_tasks = [get_raw_file_content(owner, repo, default_branch, p) for p in priority_paths]
    contents = await asyncio.gather(*fetch_tasks)
    
    # Build a single giant string containing the content of all priority files
    context_string = ""
    for path, content in zip(priority_paths, contents):
        if content.strip():
            context_string += f"\n\n--- FILE: {path} ---\n{content}\n"
            
    # 5. Generate Summary via LLM
    logger.info(f" └─ 🧠 [LLM] Sending {len(context_string)} characters of context to LLM...\n{'='*50}\n")
    summary_data = await generate_summary(repo, file_tree_str, context_string)
    
    return summary_data
