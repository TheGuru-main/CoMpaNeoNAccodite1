"""
Accodite Console
================
Interactive REPL for the Accodite pipeline.

Commands:
    :help                    show this
    :status                  show environment status
    :tools                   list registered tools
    :rooms                   show room type -> mode
    :emit <path>             stream tokens for a source string read from stdin
    :verify <path>           run the 6-stage pipeline on a file
    :ask <text>              run the natural-language pipeline (if wired)
    :quit / :q               exit
"""
from __future__ import annotations
import os, sys, json, pathlib, shlex

BE = pathlib.Path(__file__).parent / "backend"
sys.path.insert(0, str(BE))
for d in BE.iterdir():
    if d.is_dir():
        sys.path.insert(0, str(d))


BANNER = r"""
    ___                 _ _ _
   / _ \               | (_) |
  / /_\ \ ___ ___   __| |_| |_ ___
  |  _  |/ __/ _ \ / _` | | __/ _ \
  | | | | (_| (_) | (_| | | ||  __/
  \_| |_/\___\___/ \__,_|_|\__\___|
  Accodite Console
  type :help for commands
"""


def _safe_import(name):
    try:
        return __import__(name)
    except Exception as e:
        return f"__err__: {type(e).__name__}: {e}"


def cmd_status(args):
    print(f"python   : {sys.version.split()[0]}")
    print(f"cwd      : {os.getcwd()}")
    print(f"backend  : {BE}")
    for mod in ("torch", "fastapi", "sqlalchemy", "langdetect",
                "tree_sitter", "tree_sitter_languages",
                "reportlab"):
        r = _safe_import(mod)
        ok = not (isinstance(r, str) and r.startswith("__err__"))
        print(f"  {'OK ' if ok else 'MISS'}  {mod}")


def cmd_tools(args):
    try:
        from agent.default_tools import build_registry
    except Exception as e:
        print(f"cannot build registry: {e}")
        return
    reg = build_registry(root=os.path.expanduser("~"))
    names = sorted(reg._tools.keys())
    print(f"{len(names)} tools registered:")
    for n in names:
        spec = reg._tools[n]
        print(f"  {n:24s} {spec.category:10s} {'(mutating)' if spec.mutating else ''}")


def cmd_rooms(args):
    from agent.trigger import room_mode, RoomMode
    print("members | mode")
    for n in (0, 1, 2, 5, 100):
        print(f"{n:7d} | {room_mode(n).value}")


def cmd_verify(args):
    if not args:
        print("usage: :verify <path>")
        return
    path = args[0]
    p = pathlib.Path(path)
    if not p.is_absolute():
        p = pathlib.Path.cwd() / p
    if not p.exists():
        print(f"not found: {p}")
        return
    from verification.pipeline import VerificationPipeline
    pipe = VerificationPipeline(root=str(p.parent), stop_on_first_failure=True)
    report = pipe.verify(path=p.name, source=p.read_text(encoding="utf-8"))
    print(f"ok={report.ok}  stopped_at={report.stopped_at}")
    for s in report.stages:
        print(f"  {s.name:12s} ok={s.ok} skipped={s.skipped} findings={len(s.findings)}")


def cmd_emit(args):
    if not args:
        print("usage: :emit <path>   (reads source, streams tokens)")
        return
    path = args[0]
    p = pathlib.Path(path)
    if not p.is_absolute():
        p = pathlib.Path.cwd() / p
    if not p.exists():
        print(f"not found: {p}")
        return
    from agent.stream_gate import StreamGate
    gate = StreamGate(root=str(p.parent))
    for frame in gate.stream(path=p.name, source=p.read_text(encoding="utf-8")):
        sys.stdout.write(frame + "\n")
    sys.stdout.flush()


def cmd_ask(args):
    print("(ask not yet wired — pending main.py integration)")
    print("input:", " ".join(args))


COMMANDS = {
    ":help":   lambda a: print(__doc__),
    ":status": cmd_status,
    ":tools":  cmd_tools,
    ":rooms":  cmd_rooms,
    ":verify": cmd_verify,
    ":emit":   cmd_emit,
    ":ask":    cmd_ask,
}


def main():
    print(BANNER)
    while True:
        try:
            line = input("accd> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in (":quit", ":q", "quit", "exit"):
            break
        if line.startswith(":"):
            parts = shlex.split(line)
            fn = COMMANDS.get(parts[0])
            if fn is None:
                print(f"unknown command: {parts[0]}")
                continue
            try:
                fn(parts[1:])
            except Exception as e:
                print(f"error: {type(e).__name__}: {e}")
            continue
        # default: treat as ask
        cmd_ask(shlex.split(line))


if __name__ == "__main__":
    main()
