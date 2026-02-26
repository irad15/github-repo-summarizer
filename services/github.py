import httpx
from typing import Dict, Any, List

class GitHubClientError(Exception):
    pass

def parse_github_url(url: str) -> tuple[str, str]:
    """
    Extract the repository owner and repository name from a standardized GitHub URL.
    
    Example: 'https://github.com/tiangolo/fastapi' returns ('tiangolo', 'fastapi')
    """
    url = str(url).rstrip('/')
    parts = url.split('/')
    if len(parts) >= 2 and "github.com" in url:
        repo = parts[-1]
        owner = parts[-2]
        
        # Handle cases where the user pasted a clone URL ending in .git
        if repo.endswith('.git'):
            repo = repo[:-4]
        return owner, repo
    raise ValueError("Invalid GitHub URL format.")

async def get_repo_info(owner: str, repo: str) -> Dict[str, Any]:
    """
    Fetch base repository info from the GitHub REST API.
    
    This is primarily used to determine the repository's default branch
    (e.g., 'main' vs 'master') so we know where to fetch the tree from.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers={"Accept": "application/vnd.github.v3+json"})
        if response.status_code != 200:
            raise GitHubClientError(f"Failed to fetch repo info: {response.text}")
        return response.json()

async def get_repo_tree(owner: str, repo: str, branch: str) -> List[Dict[str, Any]]:
    """
    Fetch the full recursive file tree for a specific branch.
    
    Using ?recursive=1 allows us to get the entire folder structure in a single
    API call, which is highly efficient. This does NOT download the file contents.
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers={"Accept": "application/vnd.github.v3+json"})
        if response.status_code != 200:
            raise GitHubClientError(f"Failed to fetch repo tree: {response.text}")
        
        data = response.json()
        if "tree" not in data:
            if data.get("truncated"):
                raise GitHubClientError("Repository tree is too large (truncated).")
            raise GitHubClientError("Invalid tree response from GitHub.")
        return data["tree"]

async def get_raw_file_content(owner: str, repo: str, branch: str, file_path: str) -> str:
    """
    Fetch the raw text content of a specific file from GitHub's raw content CDN.
    
    If the file cannot be fetched (e.g., due to size or encoding), it silently
    returns an empty string so the summarizer can continue with other files.
    """
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code != 200:
            # Silently ignore failed file fetches to keep moving and avoid crashing the whole process
            return "" 
        return response.text

