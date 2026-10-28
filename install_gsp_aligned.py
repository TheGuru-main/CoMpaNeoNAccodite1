#!/usr/bin/env python3
# install_gsp_aligned.py — run from repo root: python3 install_gsp_aligned.py
from pathlib import Path
import base64, re

ROOT = Path(".").resolve()
if not (ROOT / "backend").is_dir():
    raise SystemExit("Run from CoMpaNeoNAccodite1 root")

def w(rel, data: bytes):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    print("wrote", rel, len(data))

w("backend/gsp_chain.py", base64.b64decode("IiIiCkdTUCBuYW1lIGlkZW50aXR5IOKAlCBTQU1FIGNoYWluIGFzIHRyYWluaW5nL3Rva2VuaXplci4KClNvdXJjZSBvZiB0cnV0aDogYmFja2VuZC50b2tlbml6ZXIudG9rZW5pemVyCiAgLSBtdWx0aWxpbmd1YWwgQUxQSEFCRVRTIChlbiwgeW8sIGZyLCBhciwg4oCmKQogIC0gZGlnaXRzIOKGkiBESUdJVF9NQVJLRVJTIGV4cGFuZGVkIHRvIGxldHRlciBpbmRleGVzIChub3QgcmF3IDAtOSkKICAtIHVpZF9zZXF1ZW5jZSh0b2tlbiwgbGFuZykg4oaSIGxpc3RbaW50XSAgKDAtYmFzZWQ7IEEvYSDihpIgMCBrZXB0KQogIC0gc2VyaWFsaXplX3VpZChzZXEpIOKGkiBzdHJpbmcgKGxlYWRpbmcgMCBwcmVzZXJ2ZWQgYXMgY2hhcmFjdGVyKQoKUmVwbyB1aWQgYW5kIGRvYyB1aWQgTVVTVCB1c2UgdGhpcyBwYXRoIHNvIHBsYWNlbWVudCBtYXRjaGVzIHRyYWluIHZvY2FiLgoiIiIKZnJvbSBfX2Z1dHVyZV9fIGltcG9ydCBhbm5vdGF0aW9ucwoKZnJvbSB0eXBpbmcgaW1wb3J0IEFueSwgRGljdCwgTGlzdCwgU2VxdWVuY2UsIFR1cGxlCgpSX1JPV1MgPSA2NApOX0NPTFMgPSA1NApST1dfTUlOLCBST1dfTUFYID0gMSwgNjQKQ09MX01JTiwgQ09MX01BWCA9IDAsIDUzCgp0cnk6CiAgICBmcm9tIHRva2VuaXplci50b2tlbml6ZXIgaW1wb3J0ICgKICAgICAgICB1aWRfc2VxdWVuY2UgYXMgX3Rva191aWRfc2VxdWVuY2UsCiAgICAgICAgc2VyaWFsaXplX3VpZCBhcyBfdG9rX3NlcmlhbGl6ZV91aWQsCiAgICAgICAgYWxwaGFiZXRfaW5kZXggYXMgX3Rva19hbHBoYWJldF9pbmRleCwKICAgICAgICBub3JtYWxpemVfbGFuZyBhcyBfdG9rX25vcm1hbGl6ZV9sYW5nLAogICAgKQogICAgX0hBU19UT0sgPSBUcnVlCmV4Y2VwdCBFeGNlcHRpb246CiAgICB0cnk6CiAgICAgICAgZnJvbSB0b2tlbml6ZXIgaW1wb3J0ICgKICAgICAgICAgICAgdWlkX3NlcXVlbmNlIGFzIF90b2tfdWlkX3NlcXVlbmNlLAogICAgICAgICAgICBzZXJpYWxpemVfdWlkIGFzIF90b2tfc2VyaWFsaXplX3VpZCwKICAgICAgICAgICAgYWxwaGFiZXRfaW5kZXggYXMgX3Rva19hbHBoYWJldF9pbmRleCwKICAgICAgICAgICAgbm9ybWFsaXplX2xhbmcgYXMgX3Rva19ub3JtYWxpemVfbGFuZywKICAgICAgICApCiAgICAgICAgX0hBU19UT0sgPSBUcnVlCiAgICBleGNlcHQgRXhjZXB0aW9uIGFzIF9lOgogICAgICAgIF9IQVNfVE9LID0gRmFsc2UKICAgICAgICBfVE9LX0VSUiA9IF9lCgoKZGVmIGxldHRlcl9jaGFpbihuYW1lOiBzdHIsIGxhbmc6IHN0ciA9ICJlbiIpIC0+IExpc3RbaW50XToKICAgICIiIk9yZGVyZWQgMC1iYXNlZCBpbmRleGVzIOKAlCBpZGVudGljYWwgdG8gdHJhaW5pbmcgdWlkX3NlcXVlbmNlLiIiIgogICAgbmFtZSA9IHN0cihuYW1lIG9yICIiKQogICAgaWYgbm90IG5hbWU6CiAgICAgICAgcmV0dXJuIFtdCiAgICBpZiBub3QgX0hBU19UT0s6CiAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKGYidG9rZW5pemVyIHVuYXZhaWxhYmxlIGZvciBsZXR0ZXJfY2hhaW46IHtfVE9LX0VSUiFyfSIpCiAgICByZXR1cm4gbGlzdChfdG9rX3VpZF9zZXF1ZW5jZShuYW1lLCBsYW5nKSkKCgpkZWYgY2hhaW5fdG9fc3RyKGNoYWluOiBTZXF1ZW5jZVtpbnRdKSAtPiBzdHI6CiAgICBpZiBfSEFTX1RPSzoKICAgICAgICByZXR1cm4gX3Rva19zZXJpYWxpemVfdWlkKGNoYWluKQogICAgcmV0dXJuICIiLmpvaW4oc3RyKGludCh4KSkgZm9yIHggaW4gY2hhaW4pCgoKZGVmIGNoYWluX3RvX2NvbXBhY3QoY2hhaW46IFNlcXVlbmNlW2ludF0pIC0+IHN0cjoKICAgICIiIlNhbWUgYXMgc2VyaWFsaXplX3VpZCAodHJhaW5pbmcgaWRlbnRpdHkgc3RyaW5nKS4iIiIKICAgIHJldHVybiBjaGFpbl90b19zdHIoY2hhaW4pCgoKZGVmIGNoYWluX3N1bShjaGFpbjogU2VxdWVuY2VbaW50XSkgLT4gaW50OgogICAgcmV0dXJuIGludChzdW0oaW50KHgpIGZvciB4IGluIGNoYWluKSkKCgpkZWYgc3RhcnRfcm93X2Zvcl9uYW1lKG5hbWU6IHN0ciwgbGFuZzogc3RyID0gImVuIikgLT4gRGljdFtzdHIsIEFueV06CiAgICBuYW1lID0gc3RyKG5hbWUgb3IgIiIpCiAgICBjaGFpbiA9IGxldHRlcl9jaGFpbihuYW1lLCBsYW5nKQogICAgTCA9IG1heChsZW4obmFtZSksIDEpCiAgICBTID0gY2hhaW5fc3VtKGNoYWluKQogICAgc3RhcnRfcm93ID0gKChMICsgUyAtIDEpICUgUl9ST1dTKSArIDEKICAgIHVpZCA9IGNoYWluX3RvX3N0cihjaGFpbikKICAgIHJldHVybiB7CiAgICAgICAgIm5hbWUiOiBuYW1lLAogICAgICAgICJsYW5nIjogbGFuZywKICAgICAgICAiTCI6IEwsCiAgICAgICAgIlMiOiBTLAogICAgICAgICJjaGFpbiI6IGNoYWluLAogICAgICAgICJ1aWRfc3RyIjogdWlkLAogICAgICAgICJ1aWRfY29tcGFjdCI6IHVpZCwKICAgICAgICAic3RhcnRfcm93Ijogc3RhcnRfcm93LAogICAgICAgICJyb290X2tleSI6IGYicntzdGFydF9yb3c6MDJkfSIsCiAgICAgICAgImdyaWRfcm93cyI6IFJfUk9XUywKICAgICAgICAiZ3JpZF9jb2xzIjogTl9DT0xTLAogICAgICAgICJzb3VyY2UiOiAidG9rZW5pemVyLnVpZF9zZXF1ZW5jZSIsCiAgICB9CgoKZGVmIHVpZF9mcm9tX25hbWUobmFtZTogc3RyLCBsYW5nOiBzdHIgPSAiZW4iKSAtPiBzdHI6CiAgICByZXR1cm4gY2hhaW5fdG9fc3RyKGxldHRlcl9jaGFpbihuYW1lLCBsYW5nKSkKCgpkZWYgdmVyaWZ5X3VpZF9tYXRjaGVzX25hbWUobmFtZTogc3RyLCB1aWQ6IHN0ciwgbGFuZzogc3RyID0gImVuIikgLT4gYm9vbDoKICAgIGV4cGVjdGVkID0gdWlkX2Zyb21fbmFtZShuYW1lLCBsYW5nKQogICAgdSA9ICh1aWQgb3IgIiIpLnN0cmlwKCkKICAgIGlmIHUgPT0gZXhwZWN0ZWQ6CiAgICAgICAgcmV0dXJuIFRydWUKICAgICMgYWNjZXB0IGxpc3QtZm9ybSBqb2luZWQgd2l0aG91dCBzZXBhcmF0b3JzIG9ubHkKICAgIHRyeToKICAgICAgICBpZiBsaXN0KGxldHRlcl9jaGFpbihuYW1lLCBsYW5nKSkgPT0gW2ludCh4KSBmb3IgeCBpbiB1LnNwbGl0KCIuIikgaWYgeCAhPSAiIl06CiAgICAgICAgICAgIHJldHVybiBUcnVlCiAgICBleGNlcHQgRXhjZXB0aW9uOgogICAgICAgIHBhc3MKICAgIHJldHVybiBGYWxzZQoKCmRlZiB2YWxpZGF0ZV9jZWxsKHJvdzogaW50LCBjb2w6IGludCkgLT4gVHVwbGVbaW50LCBpbnRdOgogICAgcm93ID0gaW50KHJvdykKICAgIGNvbCA9IGludChjb2wpCiAgICBpZiByb3cgPCBST1dfTUlOIG9yIHJvdyA+IFJPV19NQVg6CiAgICAgICAgcmFpc2UgVmFsdWVFcnJvcihmInJvdyBtdXN0IGJlIHtST1dfTUlOfS4ue1JPV19NQVh9IikKICAgIGlmIGNvbCA8IENPTF9NSU4gb3IgY29sID4gQ09MX01BWDoKICAgICAgICByYWlzZSBWYWx1ZUVycm9yKGYiY29sIG11c3QgYmUge0NPTF9NSU59Li57Q09MX01BWH0iKQogICAgcmV0dXJuIHJvdywgY29sCg=="))
w("frontend/ui/js/gsp_docs.js", base64.b64decode("LyoqCiAqIEdTUCBkb2NzOiBFeGNlbCAoY29uZmlndXJhYmxlKSwgU2hlZXQgKHJvdyAxLi42NCwgY29sIDAuLjUzKSwgV29ya3NwYWNlIHBsYWNlbWVudC4KICogZG9jX3VpZCAvIHJlcG9fdWlkID0gbGV0dGVyLWNoYWluIG9mIG5hbWUgKEE9MCwgZGlnaXRzIGV4YWN0LCBfLS4g4oaSIDI2Kzsgbm8gc3RyaXAgbGVhZGluZyAwKS4KICovCihmdW5jdGlvbiAoKSB7CiAgLy8gQ2hhaW4gc291cmNlIG9mIHRydXRoID0gYmFja2VuZCB0b2tlbml6ZXIgKG11bHRpbGluZ3VhbCArIGRpZ2l0IG1hcmtlcnMpLgogIC8vIERvIG5vdCBpbnZlbnQgYSBwYXJhbGxlbCBhLXogbWFwIGluIHRoZSBicm93c2VyLgogIHZhciBfY2hhaW5DYWNoZSA9IHt9OwogIGFzeW5jIGZ1bmN0aW9uIGZldGNoQ2hhaW4obmFtZSwgbGFuZykgewogICAgbmFtZSA9IFN0cmluZyhuYW1lIHx8ICIiKTsKICAgIGxhbmcgPSBsYW5nIHx8ICJlbiI7CiAgICB2YXIga2V5ID0gbGFuZyArICI6IiArIG5hbWU7CiAgICBpZiAoX2NoYWluQ2FjaGVba2V5XSkgcmV0dXJuIF9jaGFpbkNhY2hlW2tleV07CiAgICB2YXIgZGF0YSA9IGF3YWl0IGFwaSgKICAgICAgIi9zYW5kYm94L2dzcC9jaGFpbj9uYW1lPSIgKyBlbmNvZGVVUklDb21wb25lbnQobmFtZSkgKyAiJmxhbmc9IiArIGVuY29kZVVSSUNvbXBvbmVudChsYW5nKQogICAgKTsKICAgIF9jaGFpbkNhY2hlW2tleV0gPSBkYXRhOwogICAgcmV0dXJuIGRhdGE7CiAgfQogIGZ1bmN0aW9uIHVpZEZyb21OYW1lU3luYyhuYW1lKSB7CiAgICAvLyBjYWNoZSBvbmx5OyBwcmVmZXIgZmV0Y2hDaGFpbgogICAgdmFyIGhpdCA9IF9jaGFpbkNhY2hlWyJlbjoiICsgbmFtZV07CiAgICByZXR1cm4gaGl0ID8gaGl0LnVpZF9zdHIgfHwgaGl0LnVpZF9jb21wYWN0IDogIiI7CiAgfQogIHdpbmRvdy5hY2RGZXRjaEdzcENoYWluID0gZmV0Y2hDaGFpbjsKICB3aW5kb3cuYWNkVWlkRnJvbU5hbWUgPSBmdW5jdGlvbiAobmFtZSkgewogICAgcmV0dXJuIHVpZEZyb21OYW1lU3luYyhuYW1lKTsKICB9OwogIHdpbmRvdy5hY2RMZXR0ZXJDaGFpbiA9IGZ1bmN0aW9uIChuYW1lKSB7CiAgICB2YXIgaGl0ID0gX2NoYWluQ2FjaGVbImVuOiIgKyBuYW1lXTsKICAgIHJldHVybiBoaXQgJiYgaGl0LmNoYWluID8gaGl0LmNoYWluIDogW107CiAgfTsKICB3aW5kb3cuYWNkU3RhcnRSb3dGb3JOYW1lID0gZnVuY3Rpb24gKG5hbWUpIHsKICAgIHZhciBoaXQgPSBfY2hhaW5DYWNoZVsiZW46IiArIG5hbWVdOwogICAgcmV0dXJuIGhpdCA/IGhpdC5zdGFydF9yb3cgOiBudWxsOwogIH07CgogIHZhciBzdGF0ZSA9IHsKICAgIGtpbmQ6ICJzaGVldCIsCiAgICBwYXJlbnRSZXBvOiAiIiwKICAgIGRvY05hbWU6ICIiLAogICAgZG9jVWlkOiAiIiwKICAgIGRhdGE6IG51bGwsCiAgICBtZXRhOiBudWxsLAogICAgLy8gZXhjZWwgY29uZmlnCiAgICBuUm93czogMTAwLAogICAgbkNvbHM6IDI2LAogIH07CgogIGZ1bmN0aW9uIHRva2VuKCkgewogICAgdHJ5IHsKICAgICAgcmV0dXJuIGxvY2FsU3RvcmFnZS5nZXRJdGVtKCJjb01wYU5lb05fdG9rZW4iKSB8fCAiIjsKICAgIH0gY2F0Y2ggKGUpIHsKICAgICAgcmV0dXJuICIiOwogICAgfQogIH0KCiAgYXN5bmMgZnVuY3Rpb24gYXBpKHBhdGgsIG1ldGhvZCwgYm9keSkgewogICAgdmFyIGggPSB7IEFjY2VwdDogImFwcGxpY2F0aW9uL2pzb24iIH07CiAgICB2YXIgdCA9IHRva2VuKCk7CiAgICBpZiAodCkgaC5BdXRob3JpemF0aW9uID0gIkJlYXJlciAiICsgdDsKICAgIGlmIChib2R5ICE9IG51bGwpIGhbIkNvbnRlbnQtVHlwZSJdID0gImFwcGxpY2F0aW9uL2pzb24iOwogICAgdmFyIHJlcyA9IGF3YWl0IGZldGNoKHBhdGgsIHsKICAgICAgbWV0aG9kOiBtZXRob2QgfHwgIkdFVCIsCiAgICAgIGhlYWRlcnM6IGgsCiAgICAgIGJvZHk6IGJvZHkgIT0gbnVsbCA/IEpTT04uc3RyaW5naWZ5KGJvZHkpIDogdW5kZWZpbmVkLAogICAgfSk7CiAgICB2YXIgdGV4dCA9IGF3YWl0IHJlcy50ZXh0KCk7CiAgICB2YXIgZGF0YSA9IG51bGw7CiAgICB0cnkgewogICAgICBkYXRhID0gdGV4dCA/IEpTT04ucGFyc2UodGV4dCkgOiBudWxsOwogICAgfSBjYXRjaCAoZSkgewogICAgICBkYXRhID0geyByYXc6IHRleHQgfTsKICAgIH0KICAgIGlmICghcmVzLm9rKSB0aHJvdyBuZXcgRXJyb3IoKGRhdGEgJiYgKGRhdGEuZGV0YWlsIHx8IGRhdGEuZXJyb3IpKSB8fCB0ZXh0IHx8IHJlcy5zdGF0dXMpOwogICAgcmV0dXJuIGRhdGE7CiAgfQoKICBmdW5jdGlvbiBhY3RpdmVSZXBvKCkgewogICAgdHJ5IHsKICAgICAgaWYgKHdpbmRvdy5hY2RHZXRBY3RpdmVSZXBvKSByZXR1cm4gd2luZG93LmFjZEdldEFjdGl2ZVJlcG8oKTsKICAgIH0gY2F0Y2ggKGUpIHt9CiAgICB2YXIgc2VsID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImNvZGVSZXBvU2VsZWN0Iik7CiAgICBpZiAoc2VsICYmIHNlbC52YWx1ZSkgcmV0dXJuIHNlbC52YWx1ZTsKICAgIHJldHVybiBzdGF0ZS5wYXJlbnRSZXBvIHx8ICIiOwogIH0KCiAgZnVuY3Rpb24gZW5zdXJlUGFuZWwoKSB7CiAgICB2YXIgcCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJnc3BEb2NQYW5lbCIpOwogICAgaWYgKHApIHJldHVybiBwOwogICAgcCA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoImRpdiIpOwogICAgcC5pZCA9ICJnc3BEb2NQYW5lbCI7CiAgICBwLnN0eWxlLmNzc1RleHQgPQogICAgICAiZGlzcGxheTpub25lO3Bvc2l0aW9uOmZpeGVkO2luc2V0OjA7ei1pbmRleDoxMDA1MDtiYWNrZ3JvdW5kOiMwYjEyMjA7Y29sb3I6I2UyZThmMDtmbGV4LWRpcmVjdGlvbjpjb2x1bW47IjsKICAgIHAuaW5uZXJIVE1MID0KICAgICAgJzxkaXYgc3R5bGU9ImRpc3BsYXk6ZmxleDtnYXA6OHB4O2FsaWduLWl0ZW1zOmNlbnRlcjtwYWRkaW5nOjEwcHggMTJweDtib3JkZXItYm90dG9tOjFweCBzb2xpZCAjMWUyOTNiO2ZsZXgtd3JhcDp3cmFwIj4nICsKICAgICAgJzxidXR0b24gdHlwZT0iYnV0dG9uIiBpZD0iZ3NwRG9jQmFjayIgY2xhc3M9ImJ0biI+4oaQIEJhY2s8L2J1dHRvbj4nICsKICAgICAgJzxzdHJvbmcgaWQ9ImdzcERvY1RpdGxlIj5Eb2NzPC9zdHJvbmc+JyArCiAgICAgICc8c3BhbiBpZD0iZ3NwRG9jTWV0YSIgc3R5bGU9Im9wYWNpdHk6MC43O2ZvbnQtc2l6ZToxMnB4Ij48L3NwYW4+JyArCiAgICAgICc8c3BhbiBzdHlsZT0iZmxleDoxIj48L3NwYW4+JyArCiAgICAgICc8aW5wdXQgaWQ9ImdzcERvY05hbWVJbnB1dCIgcGxhY2Vob2xkZXI9ImRvYyBuYW1lIiBzdHlsZT0ibWF4LXdpZHRoOjE0MHB4O3BhZGRpbmc6NnB4O2JvcmRlci1yYWRpdXM6OHB4O2JvcmRlcjoxcHggc29saWQgIzMzNDE1NTtiYWNrZ3JvdW5kOiMwZjE3MmE7Y29sb3I6I2UyZThmMCIgLz4nICsKICAgICAgJzxidXR0b24gdHlwZT0iYnV0dG9uIiBpZD0iZ3NwRG9jQ3JlYXRlIiBjbGFzcz0iYnRuIj5DcmVhdGU8L2J1dHRvbj4nICsKICAgICAgJzxidXR0b24gdHlwZT0iYnV0dG9uIiBpZD0iZ3NwRG9jUmVmcmVzaCIgY2xhc3M9ImJ0biI+TGlzdDwvYnV0dG9uPicgKwogICAgICAiPC9kaXY+IiArCiAgICAgICc8ZGl2IHN0eWxlPSJkaXNwbGF5OmZsZXg7ZmxleDoxO21pbi1oZWlnaHQ6MCI+JyArCiAgICAgICc8ZGl2IGlkPSJnc3BEb2NMaXN0IiBzdHlsZT0id2lkdGg6MjAwcHg7b3ZlcmZsb3c6YXV0bztib3JkZXItcmlnaHQ6MXB4IHNvbGlkICMxZTI5M2I7cGFkZGluZzo4cHg7Zm9udC1zaXplOjEzcHgiPjwvZGl2PicgKwogICAgICAnPGRpdiBpZD0iZ3NwRG9jR3JpZFdyYXAiIHN0eWxlPSJmbGV4OjE7b3ZlcmZsb3c6YXV0bztwYWRkaW5nOjhweCI+PC9kaXY+JyArCiAgICAgICI8L2Rpdj4iOwogICAgZG9jdW1lbnQuYm9keS5hcHBlbmRDaGlsZChwKTsKICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJnc3BEb2NCYWNrIikub25jbGljayA9IGZ1bmN0aW9uICgpIHsKICAgICAgcC5zdHlsZS5kaXNwbGF5ID0gIm5vbmUiOwogICAgICBkb2N1bWVudC5ib2R5LmNsYXNzTGlzdC5yZW1vdmUoImdzcC1kb2Mtb3BlbiIpOwogICAgfTsKICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJnc3BEb2NDcmVhdGUiKS5vbmNsaWNrID0gZnVuY3Rpb24gKCkgewogICAgICBjcmVhdGVEb2MoKTsKICAgIH07CiAgICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZ3NwRG9jUmVmcmVzaCIpLm9uY2xpY2sgPSBmdW5jdGlvbiAoKSB7CiAgICAgIHJlZnJlc2hMaXN0KCk7CiAgICB9OwogICAgcmV0dXJuIHA7CiAgfQoKICBmdW5jdGlvbiBvcGVuS2luZChraW5kKSB7CiAgICBzdGF0ZS5raW5kID0ga2luZCB8fCAic2hlZXQiOwogICAgc3RhdGUucGFyZW50UmVwbyA9IGFjdGl2ZVJlcG8oKTsKICAgIHZhciBwID0gZW5zdXJlUGFuZWwoKTsKICAgIHAuc3R5bGUuZGlzcGxheSA9ICJmbGV4IjsKICAgIGRvY3VtZW50LmJvZHkuY2xhc3NMaXN0LmFkZCgiZ3NwLWRvYy1vcGVuIik7CiAgICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZ3NwRG9jVGl0bGUiKS50ZXh0Q29udGVudCA9CiAgICAgIGtpbmQgPT09ICJ4bHN4IiA/ICJFeGNlbCIgOiBraW5kID09PSAid29ya3NwYWNlIiA/ICJXb3Jrc3BhY2UgZ3JpZCIgOiAiU3ByZWFkc2hlZXQiOwogICAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImdzcERvY01ldGEiKS50ZXh0Q29udGVudCA9IHN0YXRlLnBhcmVudFJlcG8KICAgICAgPyAicGFyZW50IHJlcG86ICIgKyBzdGF0ZS5wYXJlbnRSZXBvCiAgICAgIDogIm9wZW4gYSBjb2Rlc3BhY2UgcmVwbyBmaXJzdCAocGFyZW50KSI7CiAgICByZWZyZXNoTGlzdCgpOwogIH0KCiAgYXN5bmMgZnVuY3Rpb24gY3JlYXRlRG9jKCkgewogICAgdmFyIG5hbWUgPSAoZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImdzcERvY05hbWVJbnB1dCIpLnZhbHVlIHx8ICIiKS50cmltKCk7CiAgICBpZiAoIW5hbWUpIHsKICAgICAgYWxlcnQoIkVudGVyIGRvYyBuYW1lIik7CiAgICAgIHJldHVybjsKICAgIH0KICAgIGlmICghc3RhdGUucGFyZW50UmVwbykgewogICAgICBhbGVydCgiU2VsZWN0L29wZW4gYSBjb2Rlc3BhY2UgcmVwbyBmaXJzdCDigJQgZG9jcyBhcmUgY2hpbGRyZW4gb2YgYSByZXBvIik7CiAgICAgIHJldHVybjsKICAgIH0KICAgIHZhciBib2R5ID0gewogICAgICBzY29wZTogInVzZXIiLAogICAgICBwYXJlbnRfcmVwbzogc3RhdGUucGFyZW50UmVwbywKICAgICAgZG9jX25hbWU6IG5hbWUsCiAgICAgIGtpbmQ6IHN0YXRlLmtpbmQgPT09ICJ4bHN4IiA/ICJ4bHN4IiA6IHN0YXRlLmtpbmQgPT09ICJ3b3Jrc3BhY2UiID8gIndvcmtzcGFjZSIgOiAic2hlZXQiLAogICAgICBuX3Jvd3M6IHN0YXRlLm5Sb3dzLAogICAgICBuX2NvbHM6IHN0YXRlLm5Db2xzLAogICAgfTsKICAgIHRyeSB7CiAgICAgIHRyeSB7IGF3YWl0IGZldGNoQ2hhaW4obmFtZSk7IH0gY2F0Y2ggKGUpIHt9CiAgICAgIHZhciByZXMgPSBhd2FpdCBhcGkoIi9zYW5kYm94L2RvY3MiLCAiUE9TVCIsIGJvZHkpOwogICAgICBzdGF0ZS5kb2NOYW1lID0gcmVzLmRvY19uYW1lOwogICAgICBzdGF0ZS5kb2NVaWQgPSByZXMuZG9jX3VpZDsKICAgICAgYXdhaXQgcmVmcmVzaExpc3QoKTsKICAgICAgYXdhaXQgb3BlbkRvYyhyZXMuZG9jX25hbWUpOwogICAgfSBjYXRjaCAoZSkgewogICAgICBhbGVydChTdHJpbmcoZS5tZXNzYWdlIHx8IGUpKTsKICAgIH0KICB9CgogIGFzeW5jIGZ1bmN0aW9uIHJlZnJlc2hMaXN0KCkgewogICAgdmFyIGJveCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJnc3BEb2NMaXN0Iik7CiAgICBpZiAoIWJveCkgcmV0dXJuOwogICAgYm94LmlubmVySFRNTCA9ICIiOwogICAgaWYgKCFzdGF0ZS5wYXJlbnRSZXBvKSB7CiAgICAgIGJveC50ZXh0Q29udGVudCA9ICJObyBwYXJlbnQgcmVwbyI7CiAgICAgIHJldHVybjsKICAgIH0KICAgIHRyeSB7CiAgICAgIHZhciBkYXRhID0gYXdhaXQgYXBpKAogICAgICAgICIvc2FuZGJveC9kb2NzP3BhcmVudF9yZXBvPSIgKyBlbmNvZGVVUklDb21wb25lbnQoc3RhdGUucGFyZW50UmVwbykgKyAiJnNjb3BlPXVzZXIiCiAgICAgICk7CiAgICAgIChkYXRhLmRvY3MgfHwgW10pLmZvckVhY2goZnVuY3Rpb24gKGQpIHsKICAgICAgICBpZiAoc3RhdGUua2luZCA9PT0gInhsc3giICYmIGQua2luZCAhPT0gInhsc3giKSByZXR1cm47CiAgICAgICAgaWYgKHN0YXRlLmtpbmQgPT09ICJzaGVldCIgJiYgZC5raW5kICE9PSAic2hlZXQiKSByZXR1cm47CiAgICAgICAgaWYgKHN0YXRlLmtpbmQgPT09ICJ3b3Jrc3BhY2UiICYmIGQua2luZCAhPT0gIndvcmtzcGFjZSIpIHJldHVybjsKICAgICAgICB2YXIgcm93ID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgiZGl2Iik7CiAgICAgICAgcm93LnN0eWxlLmNzc1RleHQgPSAicGFkZGluZzo2cHggNHB4O2N1cnNvcjpwb2ludGVyO2JvcmRlci1yYWRpdXM6NnB4IjsKICAgICAgICByb3cudGV4dENvbnRlbnQgPSBkLmRvY19uYW1lICsgIiDCtyByIiArIChkLnN0YXJ0X3JvdyB8fCAiPyIpOwogICAgICAgIHJvdy5vbmNsaWNrID0gZnVuY3Rpb24gKCkgewogICAgICAgICAgb3BlbkRvYyhkLmRvY19uYW1lKTsKICAgICAgICB9OwogICAgICAgIGJveC5hcHBlbmRDaGlsZChyb3cpOwogICAgICB9KTsKICAgIH0gY2F0Y2ggKGUpIHsKICAgICAgYm94LnRleHRDb250ZW50ID0gU3RyaW5nKGUubWVzc2FnZSB8fCBlKTsKICAgIH0KICB9CgogIGFzeW5jIGZ1bmN0aW9uIG9wZW5Eb2MoZG9jTmFtZSkgewogICAgc3RhdGUuZG9jTmFtZSA9IGRvY05hbWU7CiAgICB0cnkgewogICAgICB2YXIgZGF0YSA9IGF3YWl0IGFwaSgKICAgICAgICAiL3NhbmRib3gvZG9jcy8iICsKICAgICAgICAgIGVuY29kZVVSSUNvbXBvbmVudChkb2NOYW1lKSArCiAgICAgICAgICAiP3BhcmVudF9yZXBvPSIgKwogICAgICAgICAgZW5jb2RlVVJJQ29tcG9uZW50KHN0YXRlLnBhcmVudFJlcG8pICsKICAgICAgICAgICImc2NvcGU9dXNlciIKICAgICAgKTsKICAgICAgc3RhdGUubWV0YSA9IGRhdGEubWV0YSB8fCB7fTsKICAgICAgc3RhdGUuZGF0YSA9IGRhdGEuZGF0YSB8fCB7IGNlbGxzOiB7fSB9OwogICAgICBzdGF0ZS5kb2NVaWQgPSBzdGF0ZS5tZXRhLmRvY191aWQgfHwgdWlkRnJvbU5hbWUoZG9jTmFtZSk7CiAgICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJnc3BEb2NNZXRhIikudGV4dENvbnRlbnQgPQogICAgICAgIHN0YXRlLnBhcmVudFJlcG8gKwogICAgICAgICIgLyAiICsKICAgICAgICBkb2NOYW1lICsKICAgICAgICAiIMK3IHVpZCAiICsKICAgICAgICBzdGF0ZS5kb2NVaWQgKwogICAgICAgICIgwrcgc3RhcnRfcm93ICIgKwogICAgICAgIChzdGF0ZS5tZXRhLnN0YXJ0X3JvdyB8fCBzdGFydFJvd0Zvck5hbWUoZG9jTmFtZSkpOwogICAgICByZW5kZXJHcmlkKCk7CiAgICB9IGNhdGNoIChlKSB7CiAgICAgIGFsZXJ0KFN0cmluZyhlLm1lc3NhZ2UgfHwgZSkpOwogICAgfQogIH0KCiAgZnVuY3Rpb24gY2VsbEtleShyLCBjKSB7CiAgICByZXR1cm4gciArICI6IiArIGM7CiAgfQoKICBmdW5jdGlvbiByZW5kZXJHcmlkKCkgewogICAgdmFyIHdyYXAgPSBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZ3NwRG9jR3JpZFdyYXAiKTsKICAgIGlmICghd3JhcCkgcmV0dXJuOwogICAgd3JhcC5pbm5lckhUTUwgPSAiIjsKICAgIHZhciBjZWxscyA9IChzdGF0ZS5kYXRhICYmIHN0YXRlLmRhdGEuY2VsbHMpIHx8IHt9OwogICAgdmFyIGlzRXhjZWwgPSBzdGF0ZS5raW5kID09PSAieGxzeCIgfHwgKHN0YXRlLm1ldGEgJiYgc3RhdGUubWV0YS5raW5kID09PSAieGxzeCIpOwogICAgdmFyIHIwLCByMSwgYzAsIGMxOwogICAgaWYgKGlzRXhjZWwpIHsKICAgICAgcjAgPSAwOwogICAgICBjMCA9IDA7CiAgICAgIHIxID0gTWF0aC5taW4oKHN0YXRlLmRhdGEgJiYgc3RhdGUuZGF0YS5uX3Jvd3MpIHx8IHN0YXRlLm5Sb3dzLCA0MCkgLSAxOwogICAgICBjMSA9IE1hdGgubWluKChzdGF0ZS5kYXRhICYmIHN0YXRlLmRhdGEubl9jb2xzKSB8fCBzdGF0ZS5uQ29scywgMjApIC0gMTsKICAgICAgaWYgKHN0YXRlLm1ldGEgJiYgc3RhdGUubWV0YS5raW5kID09PSAieGxzeCIpIHsKICAgICAgICB2YXIgY2ZnID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgiZGl2Iik7CiAgICAgICAgY2ZnLnN0eWxlLm1hcmdpbkJvdHRvbSA9ICI4cHgiOwogICAgICAgIGNmZy5pbm5lckhUTUwgPQogICAgICAgICAgJ1Jvd3MgPGlucHV0IGlkPSJnc3BFeGNlbFJvd3MiIHR5cGU9Im51bWJlciIgbWluPSIxIiBtYXg9IjUwMDAiIHZhbHVlPSInICsKICAgICAgICAgICgoc3RhdGUuZGF0YSAmJiBzdGF0ZS5kYXRhLm5fcm93cykgfHwgc3RhdGUublJvd3MpICsKICAgICAgICAgICciIHN0eWxlPSJ3aWR0aDo2NHB4IiAvPiBDb2xzIDxpbnB1dCBpZD0iZ3NwRXhjZWxDb2xzIiB0eXBlPSJudW1iZXIiIG1pbj0iMSIgbWF4PSI1MTIiIHZhbHVlPSInICsKICAgICAgICAgICgoc3RhdGUuZGF0YSAmJiBzdGF0ZS5kYXRhLm5fY29scykgfHwgc3RhdGUubkNvbHMpICsKICAgICAgICAgICciIHN0eWxlPSJ3aWR0aDo2NHB4IiAvPiA8c3BhbiBzdHlsZT0ib3BhY2l0eTowLjY7Zm9udC1zaXplOjEycHgiPmNvbmZpZyBzdG9yZWQgb24gY3JlYXRlOyB2aWV3IGNhcHBlZCBmb3IgVUk8L3NwYW4+JzsKICAgICAgICB3cmFwLmFwcGVuZENoaWxkKGNmZyk7CiAgICAgIH0KICAgIH0gZWxzZSB7CiAgICAgIHIwID0gMTsKICAgICAgcjEgPSA2NDsKICAgICAgYzAgPSAwOwogICAgICBjMSA9IDUzOwogICAgfQogICAgdmFyIHRhYmxlID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgidGFibGUiKTsKICAgIHRhYmxlLnN0eWxlLmNzc1RleHQgPSAiYm9yZGVyLWNvbGxhcHNlOmNvbGxhcHNlO2ZvbnQtc2l6ZToxMXB4O3VzZXItc2VsZWN0Om5vbmUiOwogICAgdmFyIGhlYWQgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCJ0ciIpOwogICAgaGVhZC5hcHBlbmRDaGlsZChkb2N1bWVudC5jcmVhdGVFbGVtZW50KCJ0aCIpKTsKICAgIGZvciAodmFyIGMgPSBjMDsgYyA8PSBjMTsgYysrKSB7CiAgICAgIHZhciB0aCA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoInRoIik7CiAgICAgIHRoLnRleHRDb250ZW50ID0gYzsKICAgICAgdGguc3R5bGUuY3NzVGV4dCA9ICJwYWRkaW5nOjJweCA0cHg7b3BhY2l0eTowLjU7cG9zaXRpb246c3RpY2t5O3RvcDowO2JhY2tncm91bmQ6IzBiMTIyMCI7CiAgICAgIGhlYWQuYXBwZW5kQ2hpbGQodGgpOwogICAgfQogICAgdGFibGUuYXBwZW5kQ2hpbGQoaGVhZCk7CiAgICB2YXIgbWF4UiA9IGlzRXhjZWwgPyByMSA6IE1hdGgubWluKHIxLCAyNCk7IC8vIFVJIHdpbmRvdzsgZnVsbCByYW5nZSBzdGlsbCBlZGl0YWJsZSB2aWEgcHJvbXB0IGZvciBmYXIgY2VsbHMKICAgIGZvciAodmFyIHIgPSByMDsgciA8PSBtYXhSOyByKyspIHsKICAgICAgdmFyIHRyID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgidHIiKTsKICAgICAgdmFyIHJoID0gZG9jdW1lbnQuY3JlYXRlRWxlbWVudCgidGgiKTsKICAgICAgcmgudGV4dENvbnRlbnQgPSByOwogICAgICByaC5zdHlsZS5jc3NUZXh0ID0gInBhZGRpbmc6MnB4IDZweDtvcGFjaXR5OjAuNSI7CiAgICAgIHRyLmFwcGVuZENoaWxkKHJoKTsKICAgICAgZm9yICh2YXIgY29sID0gYzA7IGNvbCA8PSBjMTsgY29sKyspIHsKICAgICAgICAoZnVuY3Rpb24gKHJvdywgY29sKSB7CiAgICAgICAgICB2YXIgdGQgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCJ0ZCIpOwogICAgICAgICAgdmFyIGtleSA9IGNlbGxLZXkocm93LCBjb2wpOwogICAgICAgICAgdmFyIGVudHJ5ID0gY2VsbHNba2V5XTsKICAgICAgICAgIHRkLnRleHRDb250ZW50ID0gZW50cnkgJiYgZW50cnkudmFsdWUgIT0gbnVsbCA/IFN0cmluZyhlbnRyeS52YWx1ZSkuc2xpY2UoMCwgMTIpIDogIiI7CiAgICAgICAgICB0ZC50aXRsZSA9ICJyIiArIHJvdyArICIgYyIgKyBjb2wgKyAoZW50cnkgJiYgZW50cnkucGxhY2VtZW50ID8gIiBwbGFjZWQiIDogIiIpOwogICAgICAgICAgdGQuc3R5bGUuY3NzVGV4dCA9CiAgICAgICAgICAgICJib3JkZXI6MXB4IHNvbGlkICMxZTI5M2I7bWluLXdpZHRoOjI4cHg7aGVpZ2h0OjIycHg7dGV4dC1hbGlnbjpjZW50ZXI7Y3Vyc29yOnBvaW50ZXI7IiArCiAgICAgICAgICAgIChlbnRyeSAmJiBlbnRyeS5wbGFjZWQgPyAiYmFja2dyb3VuZDojMTM0ZTRhOyIgOiAiIik7CiAgICAgICAgICB0ZC5vbmNsaWNrID0gZnVuY3Rpb24gKCkgewogICAgICAgICAgICBvbkNlbGxUYXAocm93LCBjb2wsIGVudHJ5KTsKICAgICAgICAgIH07CiAgICAgICAgICB0ci5hcHBlbmRDaGlsZCh0ZCk7CiAgICAgICAgfSkociwgY29sKTsKICAgICAgfQogICAgICB0YWJsZS5hcHBlbmRDaGlsZCh0cik7CiAgICB9CiAgICB3cmFwLmFwcGVuZENoaWxkKHRhYmxlKTsKICAgIGlmICghaXNFeGNlbCAmJiBtYXhSIDwgNjQpIHsKICAgICAgdmFyIG5vdGUgPSBkb2N1bWVudC5jcmVhdGVFbGVtZW50KCJkaXYiKTsKICAgICAgbm90ZS5zdHlsZS5jc3NUZXh0ID0gIm1hcmdpbi10b3A6OHB4O29wYWNpdHk6MC42O2ZvbnQtc2l6ZToxMnB4IjsKICAgICAgbm90ZS50ZXh0Q29udGVudCA9ICJTaG93aW5nIHJvd3MgMS4uIiArIG1heFIgKyAiIG9mIDEuLjY0LCBjb2xzIDAuLjUzIOKAlCB0YXAgYW55IHZpc2libGUgY2VsbCB0byBlZGl0L3BsYWNlLiI7CiAgICAgIHdyYXAuYXBwZW5kQ2hpbGQobm90ZSk7CiAgICB9CiAgfQoKICBhc3luYyBmdW5jdGlvbiBvbkNlbGxUYXAocm93LCBjb2wsIGVudHJ5KSB7CiAgICB2YXIgcGxhY2VNb2RlID0gc3RhdGUua2luZCA9PT0gIndvcmtzcGFjZSIgfHwgKHN0YXRlLm1ldGEgJiYgc3RhdGUubWV0YS5raW5kID09PSAid29ya3NwYWNlIik7CiAgICB2YXIgY3VyID0gZW50cnkgJiYgZW50cnkudmFsdWUgIT0gbnVsbCA/IFN0cmluZyhlbnRyeS52YWx1ZSkgOiAiIjsKICAgIHZhciBtc2cgPQogICAgICAiQ2VsbCByb3c9IiArCiAgICAgIHJvdyArCiAgICAgICIgY29sPSIgKwogICAgICBjb2wgKwogICAgICAiXG5zdGFydF9yb3c9IiArCiAgICAgIChzdGF0ZS5tZXRhICYmIHN0YXRlLm1ldGEuc3RhcnRfcm93KSArCiAgICAgICIgZG9jX3VpZD0iICsKICAgICAgc3RhdGUuZG9jVWlkICsKICAgICAgKGVudHJ5ICYmIGVudHJ5LnBsYWNlbWVudCA/ICJcbihwbGFjZWQpIiA6ICIiKSArCiAgICAgICJcblxuVmFsdWU6IjsKICAgIHZhciB2YWwgPSBwcm9tcHQobXNnLCBjdXIpOwogICAgaWYgKHZhbCA9PSBudWxsKSByZXR1cm47CiAgICB0cnkgewogICAgICB2YXIgcmVzID0gYXdhaXQgYXBpKCIvc2FuZGJveC9kb2NzL2NlbGwiLCAiUE9TVCIsIHsKICAgICAgICBzY29wZTogInVzZXIiLAogICAgICAgIHBhcmVudF9yZXBvOiBzdGF0ZS5wYXJlbnRSZXBvLAogICAgICAgIGRvY19uYW1lOiBzdGF0ZS5kb2NOYW1lLAogICAgICAgIGRvY191aWQ6IHN0YXRlLmRvY1VpZCwKICAgICAgICByb3c6IHJvdywKICAgICAgICBjb2w6IGNvbCwKICAgICAgICB2YWx1ZTogdmFsLAogICAgICAgIHBsYWNlOiBwbGFjZU1vZGUsCiAgICAgIH0pOwogICAgICBpZiAoIXN0YXRlLmRhdGEpIHN0YXRlLmRhdGEgPSB7IGNlbGxzOiB7fSB9OwogICAgICBpZiAoIXN0YXRlLmRhdGEuY2VsbHMpIHN0YXRlLmRhdGEuY2VsbHMgPSB7fTsKICAgICAgc3RhdGUuZGF0YS5jZWxsc1tjZWxsS2V5KHJvdywgY29sKV0gPSByZXMuZW50cnk7CiAgICAgIHJlbmRlckdyaWQoKTsKICAgIH0gY2F0Y2ggKGUpIHsKICAgICAgYWxlcnQoU3RyaW5nKGUubWVzc2FnZSB8fCBlKSk7CiAgICB9CiAgfQoKICB3aW5kb3cuYWNkT3BlbkV4Y2VsID0gZnVuY3Rpb24gKCkgewogICAgb3BlbktpbmQoInhsc3giKTsKICB9OwogIHdpbmRvdy5hY2RPcGVuU2hlZXQgPSBmdW5jdGlvbiAoKSB7CiAgICBvcGVuS2luZCgic2hlZXQiKTsKICB9OwogIHdpbmRvdy5hY2RPcGVuV29ya3NwYWNlR3JpZCA9IGZ1bmN0aW9uICgpIHsKICAgIG9wZW5LaW5kKCJ3b3Jrc3BhY2UiKTsKICB9OwogIHdpbmRvdy5hY2RHc3BEb2NzID0geyBvcGVuS2luZDogb3BlbktpbmQsIHVpZEZyb21OYW1lOiB1aWRGcm9tTmFtZSwgbGV0dGVyQ2hhaW46IGxldHRlckNoYWluIH07CgogIGZ1bmN0aW9uIGluamVjdEJ1dHRvbnMoKSB7CiAgICB2YXIgc3BlY3MgPSBbCiAgICAgIHsgaWQ6ICJidG5Hc3BFeGNlbCIsIGxhYmVsOiAiRXhjZWwiLCBmbjogImFjZE9wZW5FeGNlbCIgfSwKICAgICAgeyBpZDogImJ0bkdzcFNoZWV0IiwgbGFiZWw6ICJTaGVldCIsIGZuOiAiYWNkT3BlblNoZWV0IiB9LAogICAgICB7IGlkOiAiYnRuR3NwV29ya3NwYWNlIiwgbGFiZWw6ICJXb3Jrc3BhY2UiLCBmbjogImFjZE9wZW5Xb3Jrc3BhY2VHcmlkIiB9LAogICAgXTsKICAgIGZ1bmN0aW9uIGFkZFRvKHBhcmVudCwgcHJlZml4KSB7CiAgICAgIGlmICghcGFyZW50KSByZXR1cm47CiAgICAgIHNwZWNzLmZvckVhY2goZnVuY3Rpb24gKHMpIHsKICAgICAgICB2YXIgaWQgPSBwcmVmaXggKyBzLmlkOwogICAgICAgIGlmIChkb2N1bWVudC5nZXRFbGVtZW50QnlJZChpZCkpIHJldHVybjsKICAgICAgICB2YXIgYiA9IGRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoImJ1dHRvbiIpOwogICAgICAgIGIudHlwZSA9ICJidXR0b24iOwogICAgICAgIGIuaWQgPSBpZDsKICAgICAgICBiLmNsYXNzTmFtZSA9ICJidG4iOwogICAgICAgIGIudGV4dENvbnRlbnQgPSBzLmxhYmVsOwogICAgICAgIGIuc3R5bGUubWFyZ2luID0gIjAgNHB4IjsKICAgICAgICBiLm9uY2xpY2sgPSBmdW5jdGlvbiAoZXYpIHsKICAgICAgICAgIGV2LnByZXZlbnREZWZhdWx0KCk7CiAgICAgICAgICBpZiAod2luZG93W3MuZm5dKSB3aW5kb3dbcy5mbl0oKTsKICAgICAgICB9OwogICAgICAgIHBhcmVudC5hcHBlbmRDaGlsZChiKTsKICAgICAgfSk7CiAgICB9CiAgICAvLyBIb21lIGh1YiBhY3Rpb25zCiAgICBhZGRUbyhkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiaG9tZUFjdGlvbnMiKSB8fCBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiaG9tZUh1YiIpLCAiaG9tZSIpOwogICAgLy8gV29ya3NwYWNlIC8gbWFpbiB0b3AgYmFyCiAgICBhZGRUbyhkb2N1bWVudC5xdWVyeVNlbGVjdG9yKCIjbWFpblNjcmVlbiAudG9wLW5hdiIpIHx8IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3IoIi50b3AtbmF2IiksICJ3cyIpOwogICAgLy8gQ29kZXNwYWNlIHRvb2xiYXIKICAgIGFkZFRvKGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJjb2RlVG9vbGJhciIpIHx8IGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3IoIiNjb2RlUGFuZWwgLmNvZGUtdG9vbGJhciIpLCAiY3MiKTsKICB9CgogIGlmIChkb2N1bWVudC5yZWFkeVN0YXRlID09PSAibG9hZGluZyIpIHsKICAgIGRvY3VtZW50LmFkZEV2ZW50TGlzdGVuZXIoIkRPTUNvbnRlbnRMb2FkZWQiLCBpbmplY3RCdXR0b25zKTsKICB9IGVsc2UgewogICAgaW5qZWN0QnV0dG9ucygpOwogIH0KICBzZXRUaW1lb3V0KGluamVjdEJ1dHRvbnMsIDgwMCk7CiAgY29uc29sZS5sb2coIlthY2RdIGdzcF9kb2NzIHJlYWR5Iik7Cn0pKCk7Cg=="))

# patch sandbox_api.py
p = ROOT / "backend/api/sandbox_api.py"
t = p.read_text(encoding="utf-8")

if "from gsp_chain import" not in t:
    t = t.replace(
        "from sandbox.runner import SandboxRunner\n",
        "from sandbox.runner import SandboxRunner\n"
        "from gsp_chain import (\n"
        "    letter_chain, uid_from_name, start_row_for_name, verify_uid_matches_name,\n"
        "    validate_cell, R_ROWS as GSP_R_ROWS, N_COLS as GSP_N_COLS,\n"
        ")\n",
        1,
    )
    print("import gsp_chain")

old_block = '''def _uid_digit_sum(uid: str) -> int:
    digits = [int(ch) for ch in (uid or "") if ch.isdigit()]
    if digits:
        return sum(digits)
    return sum((ord(ch) % 10) for ch in (uid or "0") if ch.isalnum()) or 0


def compute_start_row(repo_name: str, repo_uid: str) -> dict:
    L = max(len(repo_name or ""), 1)
    S = _uid_digit_sum(repo_uid)
    start_row = ((L + S - 1) % R_ROWS) + 1
    return {
        "L": L,
        "S": S,
        "start_row": start_row,
        "root_key": f"r{start_row:02d}",
        "repo": repo_name,
        "grid_rows": R_ROWS,
    }


def _new_repo_uid() -> str:
    return secrets.token_hex(16)
'''

new_block = '''def compute_start_row(repo_name: str, repo_uid: str = "") -> dict:
    """start_row from training tokenizer letter-chain of the name."""
    info = start_row_for_name(repo_name or "")
    expected = uid_from_name(repo_name or "")
    if repo_uid and not verify_uid_matches_name(repo_name or "", repo_uid):
        raise HTTPException(400, "repo_uid does not match tokenizer letter-chain of repo name")
    return {
        "L": info["L"],
        "S": info["S"],
        "start_row": info["start_row"],
        "root_key": info["root_key"],
        "repo": repo_name,
        "repo_uid": expected,
        "chain": info["chain"],
        "grid_rows": R_ROWS,
        "grid_cols": GSP_N_COLS,
    }


def _repo_uid_from_name(name: str) -> str:
    return uid_from_name(name)
'''

if old_block in t:
    t = t.replace(old_block, new_block, 1)
    print("compute_start_row OK")
else:
    print("WARN: compute block not found — may already be patched")

old_v = '''def _verify_repo_key(rdir: Path, repo: str, repo_uid: str) -> dict:
    meta = _read_meta(rdir)
    if not meta:
        raise HTTPException(403, "repo has no GSP key metadata")
    stored = str(meta.get("repo_uid") or "")
    if not repo_uid or not secrets.compare_digest(stored, str(repo_uid)):
        raise HTTPException(403, "invalid repo key (name + uid pair required)")
    if meta.get("repo") and meta.get("repo") != repo:
        raise HTTPException(403, "repo name mismatch")
    return meta
'''
new_v = '''def _verify_repo_key(rdir: Path, repo: str, repo_uid: str) -> dict:
    meta = _read_meta(rdir)
    if not meta:
        raise HTTPException(403, "repo has no GSP key metadata")
    if meta.get("repo") and meta.get("repo") != repo:
        raise HTTPException(403, "repo name mismatch")
    expected = uid_from_name(repo)
    stored = str(meta.get("repo_uid") or expected)
    if not repo_uid or not verify_uid_matches_name(repo, str(repo_uid)):
        raise HTTPException(403, "invalid repo key (uid must be tokenizer letter-chain of name)")
    if stored and not verify_uid_matches_name(repo, stored):
        meta["repo_uid"] = expected
        meta["chain"] = letter_chain(repo)
        _write_meta(rdir, meta)
    return meta
'''
if old_v in t:
    t = t.replace(old_v, new_v, 1)
    print("verify OK")

t = t.replace(
    "    repo_uid = _new_repo_uid()\n    gsp = compute_start_row(req.name, repo_uid)",
    "    repo_uid = _repo_uid_from_name(req.name)\n    gsp = compute_start_row(req.name, repo_uid)",
    1,
)
t = t.replace(
    '"note": "Save repo_uid secret. Required with repo name for push/commit."',
    '"note": "repo_uid is tokenizer letter-chain of name (same as training). Required with name for push/commit.",\n        "chain": letter_chain(req.name)',
    1,
)

# list_repos enrich
old_list = '''        out.append({
            "name": d.name,
            "scope": scope,
            "files": nfiles,
            "updated_at": d.stat().st_mtime,
            "start_row": meta.get("start_row"),
            "root_key": meta.get("root_key"),
        })
'''
new_list = '''        uid = meta.get("repo_uid") or uid_from_name(d.name)
        out.append({
            "name": d.name,
            "scope": scope,
            "files": nfiles,
            "updated_at": d.stat().st_mtime,
            "start_row": meta.get("start_row") or start_row_for_name(d.name)["start_row"],
            "root_key": meta.get("root_key") or start_row_for_name(d.name)["root_key"],
            "repo_uid": uid,
            "chain": meta.get("chain") or letter_chain(d.name),
        })
'''
if old_list in t:
    t = t.replace(old_list, new_list, 1)
    print("list_repos OK")

DOCS = r'''

# --- Docs (sheet/xlsx/workspace) — uid from tokenizer letter-chain ---
class DocCreate(BaseModel):
    scope: str = Field("user", pattern="^(user|org|ai)$")
    parent_repo: str
    doc_name: str
    kind: str = Field("sheet", pattern="^(sheet|xlsx|workspace)$")
    n_rows: int = Field(100, ge=1, le=5000)
    n_cols: int = Field(26, ge=1, le=512)

class DocCellWrite(BaseModel):
    scope: str = Field("user", pattern="^(user|org|ai)$")
    parent_repo: str
    doc_name: str
    doc_uid: str = ""
    row: int
    col: int
    value: str = ""
    place: bool = False

def _docs_dir(scope: str, repo: str) -> Path:
    return _repo_dir(scope, repo) / "docs"

def _doc_dir(scope: str, repo: str, doc_name: str) -> Path:
    if not doc_name or not SAFE_NAME.match(doc_name):
        raise HTTPException(400, "invalid doc name")
    return _docs_dir(scope, repo) / doc_name

def _doc_data_path(ddir: Path) -> Path:
    return ddir / "data.json"

@router.post("/docs")
async def create_doc(req: DocCreate):
    rdir = _repo_dir(req.scope, req.parent_repo)
    if not rdir.exists():
        raise HTTPException(404, "parent repo not found")
    ddir = _doc_dir(req.scope, req.parent_repo, req.doc_name)
    if ddir.exists():
        raise HTTPException(409, "doc already exists")
    ddir.mkdir(parents=True, exist_ok=True)
    info = start_row_for_name(req.doc_name)
    uid = uid_from_name(req.doc_name)
    meta = {
        "kind": req.kind,
        "doc_name": req.doc_name,
        "doc_uid": uid,
        "chain": info["chain"],
        "L": info["L"],
        "S": info["S"],
        "start_row": info["start_row"],
        "root_key": info["root_key"],
        "parent_repo": req.parent_repo,
        "scope": req.scope,
        "created_at": time.time(),
        "grid": {"rows": "1..64", "cols": "0..53"} if req.kind in ("sheet", "workspace") else {
            "n_rows": req.n_rows, "n_cols": req.n_cols, "configurable": True
        },
    }
    _write_meta(ddir, meta)
    if req.kind in ("sheet", "workspace"):
        data = {"cells": {}, "row_min": 1, "row_max": 64, "col_min": 0, "col_max": 53}
    else:
        data = {"cells": {}, "n_rows": req.n_rows, "n_cols": req.n_cols, "configurable": True}
    _doc_data_path(ddir).write_text(json.dumps(data), encoding="utf-8")
    return {"ok": True, **meta}

@router.get("/docs")
async def list_docs(parent_repo: str, scope: str = "user"):
    root = _docs_dir(scope, parent_repo)
    if not root.exists():
        return {"docs": [], "parent_repo": parent_repo}
    out = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        meta = _read_meta(d) or {}
        name = meta.get("doc_name") or d.name
        out.append({
            "doc_name": name,
            "doc_uid": meta.get("doc_uid") or uid_from_name(name),
            "kind": meta.get("kind") or "sheet",
            "start_row": meta.get("start_row"),
            "chain": meta.get("chain") or letter_chain(name),
            "parent_repo": parent_repo,
        })
    return {"docs": out, "parent_repo": parent_repo}

@router.get("/docs/{doc_name}")
async def get_doc(doc_name: str, parent_repo: str, scope: str = "user"):
    ddir = _doc_dir(scope, parent_repo, doc_name)
    if not ddir.exists():
        raise HTTPException(404, "doc not found")
    meta = _read_meta(ddir) or {}
    data = {}
    dp = _doc_data_path(ddir)
    if dp.is_file():
        try:
            data = json.loads(dp.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    return {"meta": meta, "data": data}

@router.post("/docs/cell")
async def write_doc_cell(req: DocCellWrite):
    ddir = _doc_dir(req.scope, req.parent_repo, req.doc_name)
    if not ddir.exists():
        raise HTTPException(404, "doc not found")
    meta = _read_meta(ddir) or {}
    expected = uid_from_name(req.doc_name)
    if req.doc_uid and not verify_uid_matches_name(req.doc_name, req.doc_uid):
        raise HTTPException(403, "doc_uid does not match tokenizer letter-chain of doc_name")
    kind = meta.get("kind") or "sheet"
    try:
        if kind in ("sheet", "workspace"):
            row, col = validate_cell(req.row, req.col)
        else:
            row, col = int(req.row), int(req.col)
    except ValueError as e:
        raise HTTPException(400, str(e))
    dp = _doc_data_path(ddir)
    data = json.loads(dp.read_text(encoding="utf-8")) if dp.is_file() else {"cells": {}}
    cells = data.setdefault("cells", {})
    key = f"{row}:{col}"
    entry = {"value": req.value, "row": row, "col": col}
    if req.place or kind == "workspace":
        entry["placed"] = True
        entry["placement"] = {
            "row": row, "col": col,
            "doc_start_row": meta.get("start_row"),
            "doc_uid": expected, "doc_name": req.doc_name,
        }
    cells[key] = entry
    dp.write_text(json.dumps(data), encoding="utf-8")
    return {"ok": True, "key": key, "entry": entry, "doc_uid": expected}

@router.get("/gsp/chain")
async def gsp_chain_preview(name: str, lang: str = "en"):
    return start_row_for_name(name, lang=lang or "en")
'''

if "/docs/cell" not in t:
    t = t.rstrip() + "\n" + DOCS
    print("docs API OK")
else:
    print("docs API already present")

p.write_text(t, encoding="utf-8")
print("sandbox_api written")

# index.html
h = ROOT / "frontend/ui/index.html"
ht = h.read_text(encoding="utf-8")
if "gsp_docs.js" not in ht:
    ht = ht.replace(
        '<script src="js/code_console.js"></script>',
        '<script src="js/gsp_docs.js"></script>\n<script src="js/code_console.js"></script>',
        1,
    )
    h.write_text(ht, encoding="utf-8")
    print("index.html OK")

# code_console expose
cc = ROOT / "frontend/ui/js/code_console.js"
ct = cc.read_text(encoding="utf-8")
if "acdGetActiveRepo" not in ct:
    ct = ct.replace(
        "  window.openCodePanel = showPanel;",
        "  window.openCodePanel = showPanel;\n"
        "  window.acdGetActiveRepo = function () { return repo || null; };\n",
        1,
    )
    cc.write_text(ct, encoding="utf-8")
    print("code_console OK")

# verify
import sys
sys.path.insert(0, str(ROOT / "backend"))
from gsp_chain import letter_chain, uid_from_name
from tokenizer.tokenizer import uid_sequence, serialize_uid
assert letter_chain("Accodite") == list(uid_sequence("Accodite", "en"))
assert uid_from_name("Accodite") == serialize_uid(uid_sequence("Accodite", "en"))
print("ALIGNED", uid_from_name("Accodite")[:32])
print("DONE — git add / commit / push")
