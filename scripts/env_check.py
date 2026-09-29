"""Accodite environment check."""
import sys, pathlib, importlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
BE = ROOT / "backend"
sys.path.insert(0, str(BE))
for d in BE.iterdir():
    if d.is_dir():
        sys.path.insert(0, str(d))

REQUIRED_MODULES = [
    "org.roles",
    "org.room_types",
    "agent.trigger",
    "agent.tools",
    "agent.default_tools",
    "agent.stream_gate",
    "agent.stream_follow",
    "tree_sitter.parser",
    "tree_sitter.languages",
    "sandbox.runner",
    "lsp.manager",
    "verification.pipeline",
    "model.head_router",
    "cognition.control",
    "cognition.pattern_detector",
    "memory.pstm",
    "memory.ltm_gate",
    "prompts.prompts_manager",
    "code_tokenizer",
]

OPTIONAL = ["torch", "fastapi", "sqlalchemy", "langdetect",
            "tree_sitter", "tree_sitter_languages", "reportlab"]

def main():
    print("== required modules ==")
    failed = 0
    for m in REQUIRED_MODULES:
        try:
            importlib.import_module(m)
            print(f"  OK    {m}")
        except Exception as e:
            print(f"  FAIL  {m}: {type(e).__name__}: {e}")
            failed += 1
    print()
    print("== optional deps ==")
    for m in OPTIONAL:
        try:
            importlib.import_module(m)
            print(f"  OK    {m}")
        except Exception:
            print(f"  MISS  {m}")
    print()
    print("exit:", 1 if failed else 0)
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
