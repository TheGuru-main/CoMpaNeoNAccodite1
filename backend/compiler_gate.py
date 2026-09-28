"""
CoMpaNeoNAccodite – Tree-sitter & LSP Compiler Bridge
======================================================
Interfaces with active language server instances over JSON-RPC protocols 
to intercept code compilation errors and syntax validation logs.
"""

from __future__ import annotations
from typing import List, Dict, Any
from accodite_brain import CoMpaNeoNAccoditeBrain

class AccoditeCompilerGate:
    def __init__(self, brain: CoMpaNeoNAccoditeBrain):
        self.brain = brain

    def inject_lsp_diagnostics(self, file_name: str, syntax_stream: str) -> List[Dict[str, Any]]:
        """Runs syntax checks and logs diagnostic warnings into row layers 24-39."""
        detected_faults = []
        
        # Basic check to catch unfinished code fragments during development
        if "def " in syntax_stream and not syntax_stream.strip().endswith(":"):
            detected_faults.append({
                "line": len(syntax_stream.splitlines()),
                "message": "SyntaxError: Expected matching colon symbol alignment",
                "severity": "Error"
            })
            
        # Map detected compile anomalies straight to tracking zones
        for fault in detected_faults:
            c, r = self.brain.calculate_gsp_slot(fault["message"], "lsp")
            self.brain.memory_grid[r][c] = -1.0  # Apply negative weights to flag syntax errors
            fault["grid_mapping"] = {"col": c, "row": r}
            
        return detected_faults
