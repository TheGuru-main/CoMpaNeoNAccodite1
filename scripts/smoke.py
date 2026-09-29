"""End-to-end smoke: gate a clean file, gate a broken file, stream it."""
import sys, pathlib, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BE = ROOT / "backend"
sys.path.insert(0, str(BE))
for d in BE.iterdir():
    if d.is_dir():
        sys.path.insert(0, str(d))

from agent.stream_gate import StreamGate
from agent.default_tools import build_registry
from agent.tools import ToolCall

def main():
    tmp = tempfile.mkdtemp(prefix="accd-smoke-")
    reg = build_registry(root=tmp)

    def call(name, **args):
        return reg.dispatch(ToolCall(
            name=name, args=args,
            actor_id="smoke", organization_id=None, workspace_id="smoke",
        ))

    w = call("fs.write_file", path="hello.py",
             content="def add(a, b):\n    return a + b\n")
    print("write:", w.ok)

    g = StreamGate(root=tmp)
    frames = list(g.stream(path="hello.py",
                           source="def add(a, b):\n    return a + b\n"))
    rebuilt = "".join(f[len("#token#"):] for f in frames if f.startswith("#token#"))
    print("stream round-trip:", rebuilt == "def add(a, b):\n    return a + b\n")

    bad = list(g.stream(path="broken.py", source="def f(\n"))
    print("broken rejected:", bad and bad[0].startswith("#error#"))

    print("smoke OK")

if __name__ == "__main__":
    main()
