"""Language registry for tree-sitter + LSP routing."""
EXT_TO_LANG = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "tsx",
    ".go": "go", ".rs": "rust", ".rb": "ruby",
    ".java": "java", ".kt": "kotlin",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".cs": "csharp", ".php": "php", ".swift": "swift",
    ".sh": "bash", ".bash": "bash",
    ".sql": "sql", ".html": "html", ".css": "css",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".md": "markdown", ".rst": "rst",
}

LANG_LSP = {
    "python":     ["pylsp"],
    "javascript": ["typescript-language-server", "--stdio"],
    "typescript": ["typescript-language-server", "--stdio"],
    "tsx":        ["typescript-language-server", "--stdio"],
    "go":         ["gopls"],
    "rust":       ["rust-analyzer"],
    "c":          ["clangd"],
    "cpp":        ["clangd"],
    "csharp":     ["omnisharp"],
    "ruby":       ["solargraph", "stdio"],
    "php":        ["intelephense", "--stdio"],
    "bash":       ["bash-language-server", "start"],
    "json":       ["vscode-json-language-server", "--stdio"],
    "yaml":       ["yaml-language-server", "--stdio"],
}

def lang_for(path: str) -> str:
    for ext, lang in EXT_TO_LANG.items():
        if path.endswith(ext):
            return lang
    return "text"

def lsp_command(lang: str):
    return LANG_LSP.get(lang, [])
