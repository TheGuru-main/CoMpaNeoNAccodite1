"""
CoMpaNeoNAccodite – Production AI Core Brain
==============================================
Orchestrates autonomous code development loops, manages 46x64 memory maps, 
and interfaces with Tree-sitter and LSP diagnostics to handle task requests.
"""

from __future__ import annotations
import json
import hashlib
from typing import Dict, Any, List, Tuple
from code_tokenizer import word_cell, split_code_identifiers

class CoMpaNeoNAccoditeBrain:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.COLS = 46
        self.ROWS = 64
        # Initialize an empty 46x64 array for local validation tracking
        self.memory_grid = [[0.0 for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.active_repo_ledger: Dict[str, Any] = {}

    def calculate_gsp_slot(self, token: str, zone_name: str) -> Tuple[int, int]:
        """Calculates precise grid coordinates using your signature hash metrics."""
        meta = word_cell(token, lang="en")
        lsum = meta["Lsum"]
        ssum = meta["Ssum"]
        
        # Scale columns to fit the strict 46-column layout
        col = (meta["c"] + lsum) % self.COLS
        
        # Route row allocations to their dedicated category bands
        zones = {"repo": (0, 7), "ast": (8, 23), "lsp": (24, 39), "runway": (40, 51), "actuator": (52, 63)}
        r_min, r_max = zones.get(zone_name, (8, 23))
        row = r_min + ((lsum + ssum) % ((r_max - r_min) + 1))
        
        return col, row

    def map_incoming_task(self, prompt: str, code_draft: str) -> List[Tuple[int, int]]:
        """Maps project prompts and code parameters across tracking tracks."""
        activated_coordinates = []
        
        # 1. Parse prompt keywords to extract task parameters
        prompt_tokens = split_code_identifiers(prompt)
        for token in prompt_tokens:
            c, r = self.calculate_gsp_slot(token, "runway")
            self.memory_grid[r][c] = 1.0
            activated_coordinates.append((c, r))
            
        # 2. Parse structural draft code entities into the AST tracking layers
        code_tokens = split_code_identifiers(code_draft)
        for token in code_tokens:
            c, r = self.calculate_gsp_slot(token, "ast")
            self.memory_grid[r][c] = 1.0
            activated_coordinates.append((c, r))
            
        return activated_coordinates
