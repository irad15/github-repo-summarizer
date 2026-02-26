import pathspec
from typing import List

# Define patterns to ignore
IGNORE_PATTERNS = [
    # Binaries / Media
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.pdf", "*.eot", "*.svg", "*.ttf", "*.woff", "*.woff2",
    "*.mp4", "*.webm", "*.mp3", "*.wav", "*.zip", "*.tar", "*.gz", "*.7z", "*.exe", "*.dll", "*.so", "*.dylib",
    
    # Build / Virtual Envs
    "node_modules/", "venv/", ".venv/", "env/", ".env", "build/", "dist/", "target/", "out/", "__pycache__/", "*.pyc",
    ".next/", ".nuxt/", ".cache/",
    
    # Git / IDE
    ".git/", ".github/", ".vscode/", ".idea/", "*.iml",
    
    # Lock files
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock", "Gemfile.lock", "Cargo.lock",
    
    # Boilerplate / Empty
    "__init__.py"
]

def filter_paths(paths: List[str]) -> List[str]:
    """
    Filter out noise files and directories using pathspec.
    
    This function acts exactly like a .gitignore file, compiling our IGNORE_PATTERNS
    and dropping any file paths that match (e.g., node_modules, compiled binaries).
    This dramatically reduces the amount of text we process later.
    """
    spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, IGNORE_PATTERNS)
    return [path for path in paths if not spec.match_file(path)]

def build_tree_string(paths: List[str]) -> str:
    """
    Convert a flat list of file paths into a multiline string.
    
    While a visual tree drawing (with └── shapes) looks nicer to humans, 
    a sorted flat list of paths is perfectly understandable to an LLM 
    for grasping the directory structure mapping.
    """
    paths.sort()
    return "\n".join(paths)

def prioritize_files(paths: List[str], max_files: int = 15) -> List[str]:
    """
    Algorithmically determine which files give the LLM the best summary signal.
    
    Because LLMs have a fixed context limit (e.g., ~128k tokens), we cannot send
    every file in a large repository (like a 5,000 file backend). Instead, we:
    1. Grab configuration, dependency, and explicit documentation files first.
    2. Grab core entrypoint source code files (main, app, index) near the root level.
    3. Fill any remaining slots up to `max_files` with arbitrary source code.
    """
    paths.sort() # Sorted to ensure deterministic behavior across identical runs
    
    priority_files = []
    
    # Category 1: Configuration, Documentation, and Dependency definitions
    # These files usually contain descriptions, library names, and architecture clues.
    key_files = ["README.md", "README", "package.json", "pyproject.toml", "requirements.txt", "Dockerfile", "docker-compose.yml", "setup.py", "go.mod", "Cargo.toml"]
    for path in paths:
        filename = path.split('/')[-1]
        if filename in key_files or "readme" in filename.lower():
            if path not in priority_files:
                priority_files.append(path)
                
    # Category 2: Core entrypoint source files 
    # e.g., 'main.py', or 'src/index.ts'. We limit depth to avoid deep utility scripts.
    core_names = ["main.py", "app.py", "index.js", "index.ts", "app.js", "app.ts", "main.go", "main.rs"]
    for path in paths:
        filename = path.split('/')[-1]
        depth = len(path.split('/'))
        if filename in core_names and depth <= 3:
            if path not in priority_files:
                priority_files.append(path)
                
    # Category 3: General source files to fill up the budget
    # Give the LLM a taste of the actual business logic syntax.
    source_exts = [".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".c", ".h", ".cs", ".rb", ".php"]
    for path in paths:
        if len(priority_files) >= max_files:
            break
        if any(path.endswith(ext) for ext in source_exts):
            if path not in priority_files:
                priority_files.append(path)
                
    return priority_files[:max_files]
