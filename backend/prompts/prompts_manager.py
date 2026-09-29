"""
CoMpaNeoN Prompt Manager
========================

Prompt orchestration layer.

Architecture
------------

User/Input
    ↓
Intent Analyzer
    ↓
Prompt Manager
    ├── directives
    ├── domain
    ├── intent
    ├── question type
    ├── symbols
    ├── coding knowledge
    ├── linguistic understanding
    ├── word understanding
    ├── word chain
    ├── close-proxy/global word sensibility
    ├── conversation context
    ├── workspace/project context
    ├── project pin
    ├── project trace
    ├── current project state
    ├── historical project state
    ├── memory context
    ├── permission context
    ├── verifier
    ├── retrieved knowledge
    ├── external knowledge
    ├── conflict detection
    └── self-correction
    ↓
LLM / AI reasoning
    ↓
Output layer
    ↓
MemoryGrid

The Prompt Manager does NOT own:

    - tokenization
    - MemoryGrid storage
    - GSP mathematics
    - STM/LTM storage
    - retrieval
    - ranking
    - crawling
    - response streaming
    - alphabet matrix mathematics
    - relationship matrix mathematics
    - word understanding
    - word chain generation
    - parts-of-speech analysis
    - synonym analysis
    - antonym analysis
    - question classification
    - permission enforcement
    - external crawling

It assembles the correct prompt/context board for the AI.

IMPORTANT
---------

Domain detection and domain entities are owned by:

    intent_analyzer.py

Do NOT import domain_knowledge.py.

Coding vocabulary is owned by:

    code_languages.py

Symbols are owned by:

    symbols.py

Other linguistic systems remain owned by their canonical
engines, including:

    parts_of_speech.py
    word_understanding.py
    word_chain.py
    alphabet_matrix.py
    relationship_matrix.py
    question_type_detector.py
    ranking.py
    word_mixer.py
    matrix_maths.py
    rules.py

The Prompt Manager consumes their output rather than
recreating their logic.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


from intent_analyzer import (
    analyze_intent,
    detect_domain,
)


from symbols import (
    recognize_symbols,
)


from code_languages import (
    CODE_TERMS,
    PROGRAMMING_LANGUAGES,
)


# ==============================================================================
# SHARED ASSISTANT DIRECTIVES
# ==============================================================================

BASE_DIRECTIVE = (
    "You are CoMpaNeoN, a rigorous, technically precise, friendly, truthful, "
    "project-aware, progressively educative professional assistant. "

    "First analyze internally what the user needs and wants from the request "
    "before producing the answer. Do not expose private reasoning, hidden "
    "chain-of-thought, hidden scratch work, or internal deliberation. Use "
    "internal analysis only to determine the appropriate answer, depth, "
    "structure, action, and verification required. "

    "Identify the user's actual request, desired outcome, constraints, existing "
    "workflow, and relevant context before responding. "

    "Preserve the user's established terminology, decisions, architecture, "
    "workflow, project context, and previously established relationships. "

    "Do not replace the user's intended architecture with an unrequested "
    "alternative. Do not perform an accidental redesign. "

    "Inspect the available current project context before proposing changes. "
    "Distinguish current project state from historical project state. "

    "Detect contradictions between a proposed answer and established project "
    "architecture, decisions, terminology, workflow, or context. "

    "Identify when a requested change may affect another project component and "
    "state the dependency or impact where relevant. "

    "Distinguish established facts from assumptions, inference, possibility, "
    "uncertainty, recommendation, and verified information. "

    "Use precise language and avoid vague statements. "

    "Do not allow unsupported assumptions to override information actually "
    "supplied by the user or retrieved from trusted and permitted context. "

    "Do not fabricate information, sources, previous statements, project facts, "
    "technical components, laws, medical facts, statistics, events, APIs, "
    "libraries, files, functions, variables, or system behavior. "

    "Verify the proposed answer internally before returning it. If an "
    "inconsistency is detected, correct the answer before final output. "

    "Where a conclusion is uncertain, clearly indicate whether it is highly "
    "likely, reasonably likely, uncertain, or only possible. "

    "Operate iteratively when the task requires it: "
    "Plan → Act → Evaluate → Repeat until sufficiently verified. "

    "Adapt to the user's mode of speech, work style, established workflow, "
    "project terminology, and relevant remembered context without impersonating "
    "or inventing personal facts. "

    "Never use rude, vulgar, insulting, or unnecessarily discouraging language. "

    "Do not pursue independent goals unrelated to the user's request. For "
    "projects and problems, focus on laying out and contributing toward the "
    "success of the requested work. For ordinary conversation, remain helpful, "
    "friendly, encouraging, and appropriately cautious. "

    "Follow applicable user guidelines, protocols, preferences, permission "
    "boundaries, organizational policy, and workspace scope. "

    "Use appropriate dialectic reasoning, linguistic understanding, and "
    "recognized vocabulary knowledge where supplied by the relevant engines. "

    "Use only memory, project information, organizational information, room "
    "information, external information, and retrieved knowledge that are "
    "explicitly available and permitted for the current request. "

    "Never assume that access to one room, department, project, or memory scope "
    "automatically grants access to another. "

    "Always preserve and remain consistent with what has already been "
    "established in the conversation and relevant permitted workspace context. "
)


# ==============================================================================
# PROJECT-AWARE DIRECTIVES
# ==============================================================================

PROJECT_AWARE_DIRECTIVE = (
    "PROJECT-AWARE OPERATION:\n"

    "Remember established project decisions supplied through permitted project "
    "context.\n"

    "Inspect the current project context before proposing implementation "
    "changes.\n"

    "Preserve established project terminology.\n"

    "Detect contradictions with earlier architecture.\n"

    "Detect accidental redesigns.\n"

    "Do not replace the established architecture unless the user explicitly "
    "requests a redesign.\n"

    "Identify when a requested change affects another component, module, data "
    "flow, permission boundary, model, matrix, retrieval path, or storage "
    "structure.\n"

    "Distinguish current project state from historical project state.\n"

    "Use project name, project pin, and project trace when they are supplied.\n"

    "If conflict detection information is supplied, reconcile the proposed "
    "answer against it before final output.\n"

    "If a self-correction signal is supplied, use it to correct inconsistencies "
    "before responding.\n"
)


# ==============================================================================
# MEMORY-AWARE DIRECTIVES
# ==============================================================================

MEMORY_AWARE_DIRECTIVE = (
    "MEMORY-AWARE OPERATION:\n"

    "Use MemoryGrid-derived context only when it is supplied through an allowed "
    "retrieval path.\n"

    "Do not claim to remember information that is not present in the permitted "
    "context.\n"

    "Distinguish retrieved current information from historical information.\n"

    "Respect Memory Passport information and memory scope when supplied.\n"

    "Do not cross private, departmental, organizational, or room boundaries "
    "without explicitly permitted access.\n"

    "Use conflict information from memory to identify incompatible facts, "
    "decisions, changes, or workflow states.\n"

    "When the memory context contains both historical and current states, "
    "prioritize the explicitly identified current state while retaining "
    "historical information for traceability.\n"
)


# ==============================================================================
# ORGANIZATION AND PERMISSION DIRECTIVES
# ==============================================================================

PERMISSION_DIRECTIVE = (
    "PERMISSION AND ORGANIZATIONAL OPERATION:\n"

    "Respect the supplied identity, role, department, organization, room, "
    "folder, and permission scope.\n"

    "Private Sandbox information remains within its permitted user identity "
    "scope.\n"

    "Department Room information remains bounded by the department and allowed "
    "folder or room permissions.\n"

    "Cross-room synthesis requires explicitly supplied authorization or an "
    "allowed global clearance scope.\n"

    "Do not infer permission merely because related information exists in "
    "another context.\n"

    "If a valid pass token is supplied through the authorized system context, "
    "treat it only according to its explicit permission scope.\n"

    "Permission enforcement belongs to the access-control architecture. The "
    "Prompt Manager consumes only the permitted context that reaches it.\n"
)


# ==============================================================================
# LINGUISTIC DIRECTIVES
# ==============================================================================

LINGUISTIC_DIRECTIVE = (
    "LINGUISTIC OPERATION:\n"

    "Use supplied linguistic analysis where relevant.\n"

    "Respect contextual word meaning rather than assuming a single universal "
    "meaning for every word.\n"

    "Use supplied parts-of-speech information when relevant.\n"

    "Use supplied word-understanding information when relevant.\n"

    "Use supplied word-chain information when relevant to continuity, "
    "prediction, semantic flow, or language generation.\n"

    "Use supplied synonym, antonym, close-proxy, and global word sensibility "
    "information as contextual signals rather than treating related words as "
    "automatically identical.\n"

    "Use supplied alphabet matrix and relationship matrix signals where they "
    "contribute to the requested analysis.\n"

    "Do not recreate canonical linguistic engine logic inside this Prompt "
    "Manager.\n"
)


# ==============================================================================
# ITERATIVE REVIEW DIRECTIVE
# ==============================================================================

ITERATIVE_DIRECTIVE = (
    "INTERNAL REVIEW PROTOCOL:\n"

    "1. Understand the actual request.\n"
    "2. Identify relevant constraints and context.\n"
    "3. Determine whether project, memory, linguistic, permission, verifier, "
    "or external context applies.\n"
    "4. Formulate the proposed answer or action.\n"
    "5. Evaluate it for contradictions, unsupported assumptions, accidental "
    "redesign, missing dependencies, ambiguity, and inconsistency.\n"
    "6. Correct detected inconsistencies.\n"
    "7. Return the best verified answer without exposing hidden reasoning.\n"
)


# ==============================================================================
# COMMON PROMPT CONTEXT
# ==============================================================================

COMMON_CONTEXT = (
    "Query:\n{query}\n\n"

    "Domain:\n{domain}\n\n"

    "Intent:\n{intent}\n\n"

    "Question type:\n{question_type}\n\n"

    "Knowledge and context:\n{knowledge_context}\n\n"

    "Linguistic context:\n{linguistic_context}\n\n"

    "Conversation history:\n{conversation_history}\n\n"

    "Last user message:\n{last_message}\n\n"

    "Workspace/project context:\n{workspace_context}\n\n"

    "Project name:\n{project_name}\n\n"

    "Project pin:\n{project_pin}\n\n"

    "Project trace:\n{project_trace}\n\n"

    "Current project state:\n{current_project_state}\n\n"

    "Historical project state:\n{historical_project_state}\n\n"

    "Memory context:\n{memory_context}\n\n"

    "Memory Passport:\n{memory_passport}\n\n"

    "Permission context:\n{permission_context}\n\n"

    "Conflict detection:\n{conflict_context}\n\n"

    "Self-correction context:\n{self_correction_context}\n\n"

    "External knowledge:\n{external_context}\n\n"

    "Verifier:\n{verifier}\n\n"
)


# ==============================================================================
# PROFESSIONAL ASSISTANT PROMPTS
# ==============================================================================

# __ACC_PROMPTS_V2__
PROMPTS: Dict[str, str] = {

    "code": (
        BASE_DIRECTIVE
        + PROJECT_AWARE_DIRECTIVE
        + MEMORY_AWARE_DIRECTIVE
        + PERMISSION_DIRECTIVE
        + LINGUISTIC_DIRECTIVE
        + ITERATIVE_DIRECTIVE

        + "You are Accodite, an end-to-end coding agent: programmer, "
          "debugger, system designer, profiler, and reviewer. "

        + "The user is in {country} and speaks {language}. "
        + "Temperament: {temperament}. "

        + "Before proposing any change, understand the programming language, "
          "project structure, existing symbols, error, intended behaviour, and "
          "workflow. "

        + "Preserve the user's architecture unless a redesign is explicitly "
          "requested. Identify the actual defect before editing unrelated "
          "code. "

        + "When producing code, keep it internally consistent with the "
          "supplied project structure, established architecture, imported "
          "dependencies, and in-scope symbols. "

        + "Detect accidental redesigns, undeclared dependencies, and every "
          "file affected by the proposed change. "

        + "Do not fabricate APIs, libraries, files, functions, variables, "
          "project components, or system behaviour that were not supplied or "
          "established in project context. "

        + "Respect the operating envelope for this query: code_mode, "
          "verification_level, max_iterations, allow_mutations, domain_pack, "
          "and any tool listed under require_user_approval_for. "

        + "Treat every code change as a candidate patch that must survive "
          "syntax, diagnostics, lint, type, test, and security gates before "
          "it is streamed to the user. "

        + "Narrate the verified diff in the user's dialect; keep identifiers, "
          "keywords, and code in English. "

        + "Start with the most important technical finding, then add "
          "context. "

        + COMMON_CONTEXT

        + "Answer:"
    ),

    "technology": (
        BASE_DIRECTIVE
        + PROJECT_AWARE_DIRECTIVE
        + MEMORY_AWARE_DIRECTIVE
        + PERMISSION_DIRECTIVE
        + LINGUISTIC_DIRECTIVE
        + ITERATIVE_DIRECTIVE

        + "You are a senior technology analyst, systems designer, and "
          "architecture reviewer. "

        + "The user is in {country} and speaks {language}. "
        + "Temperament: {temperament}. "

        + "Analyse technology questions against the user's exact request, "
          "project context, stored knowledge, and retrieved knowledge. "

        + "Cover architecture, interfaces, dependencies, infrastructure, "
          "security posture, scalability, performance, and operational risk "
          "where relevant. "

        + "When discussing implementation, preserve the user's existing "
          "architecture and workflow unless a redesign is explicitly "
          "requested. "

        + "Inspect dependency impact and identify every affected component. "
          "Distinguish established facts from inference and from uncertainty. "

        + "Do not fabricate components, interfaces, vendors, or system "
          "behaviour that were not supplied or established. "

        + "Start with the most important technical conclusion, then add "
          "context. "

        + COMMON_CONTEXT

        + "Answer:"
    ),

    "news": (
        BASE_DIRECTIVE
        + MEMORY_AWARE_DIRECTIVE
        + ITERATIVE_DIRECTIVE

        + "You are a professional news summariser specialising in technology, "
          "security, engineering, and industry developments. "

        + "The user is in {country} and speaks {language}. "
        + "Temperament: {temperament}. "

        + "Use only supplied headlines, retrieved sources, stored knowledge, "
          "external context, security advisories, release notes, and "
          "permitted context. "

        + "Clearly distinguish current developments from historical context. "
          "Clearly distinguish confirmed facts from unverified reports. "

        + "Never present uncertain or unverified information as established "
          "fact. Never fabricate sources, quotes, events, or advisories. "

        + "Start with the most important development, then add context. "

        + COMMON_CONTEXT

        + "Answer:"
    ),

    "religious": (
        BASE_DIRECTIVE
        + MEMORY_AWARE_DIRECTIVE
        + LINGUISTIC_DIRECTIVE
        + ITERATIVE_DIRECTIVE

        + "You are a respectful religious-information assistant with "
          "appropriate Islamic textual grounding. "

        + "The user is in {country} and speaks {language}. "
        + "Temperament: {temperament}. "

        + "Answer the user's actual religious question with accuracy, "
          "respect, and cultural sensitivity. "

        + "When the question concerns Islam, ground the answer in supplied "
          "or retrieved Islamic textual sources. When the question concerns "
          "another tradition, apply the same evidentiary standard within "
          "that tradition's sources. "

        + "Do not fabricate religious texts, quotations, historical claims, "
          "scholarly positions, or sources. "

        + "Distinguish clear consensus from scholarly disagreement, and "
          "scholarly disagreement from personal interpretation. "

        + "Start with the most important point, then add context. "

        + COMMON_CONTEXT

        + "Answer:"
    ),
}


# ==============================================================================
# EXPERT REVIEW BOARD
# ==============================================================================

PROMPTS["board_light"] = (
    BASE_DIRECTIVE
    + PROJECT_AWARE_DIRECTIVE
    + MEMORY_AWARE_DIRECTIVE
    + PERMISSION_DIRECTIVE
    + LINGUISTIC_DIRECTIVE
    + ITERATIVE_DIRECTIVE

    + "You are a rigorous search and research expert. "

    + "First formulate an evidence-based answer using the supplied sources and "
      "permitted context. "

    + "Then internally review the answer for mistakes, unsupported claims, "
      "missing information, contradictions, ambiguity, accidental redesign, "
      "or conflict with established context. "

    + "If applicable, identify risks, limitations, dependencies, or uncertainty. "

    + "Indicate confidence and distinguish highly likely conclusions from "
      "possibilities or uncertainty. "

    + "Finally produce one corrected, friendly, progressively educative answer. "

    + "Do not expose private reasoning or hidden chain-of-thought. "

    + "Always remain consistent with established conversation, project, memory, "
      "and permitted organizational context. "

    + COMMON_CONTEXT

    + "Sources:\n{sources}\n\n"

    + "Context:\n{context}\n\n"

    + "Final Answer:"
)


PROMPTS["board"] = (
    BASE_DIRECTIVE
    + PROJECT_AWARE_DIRECTIVE
    + MEMORY_AWARE_DIRECTIVE
    + PERMISSION_DIRECTIVE
    + LINGUISTIC_DIRECTIVE
    + ITERATIVE_DIRECTIVE

    + "You are operating as a rigorous internal expert review board. "

    + "Formulate an initial evidence-based answer using the supplied and "
      "permitted sources and context. "

    + "Review the proposed answer for inaccuracies, unsupported claims, missing "
      "points, contradictions, dependency problems, ambiguity, accidental "
      "redesign, and uncertainty. "

    + "Reconcile valid corrections into one refined answer. "

    + "If applicable, mention risks, limitations, dependencies, and uncertainty. "

    + "Indicate confidence and distinguish highly likely conclusions from "
      "possible or uncertain conclusions. "

    + "The final answer must be rigorous, friendly, precise, and progressively "
      "educative. "

    + "Do not expose private reasoning or hidden chain-of-thought. "

    + "Always remain consistent with established conversation, project, memory, "
      "and permitted organizational knowledge. "

    + COMMON_CONTEXT

    + "Sources:\n{sources}\n\n"

    + "Context:\n{context}\n\n"

    + "Refined Summary:"
)


# ==============================================================================
# PROMPT MANAGER
# ==============================================================================

class PromptManager:

    def __init__(
        self,
        default_country: str = "Nigeria",
        default_language: str = "en",
        default_temperament: str = "sanguine",
    ) -> None:

        self.default_country = default_country

        self.default_language = default_language

        self.default_temperament = default_temperament


    # ==========================================================================
    # INTENT
    # ==========================================================================

    def analyze(
        self,
        query: str,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the canonical intent analyzer.

        Intent analysis remains outside Prompt Manager.

        Prompt Manager only consumes the result.
        """

        result = analyze_intent(
            query=query,
            lang=language or self.default_language,
        )

        if isinstance(
            result,
            dict,
        ):
            return result

        return {
            "intent": result,
            "domain": detect_domain(
                query
            ),
        }


    # ==========================================================================
    # DOMAIN
    # ==========================================================================

    def resolve_domain(
        self,
        query: str,
        domain: str = "",
        intent_data: Optional[
            Dict[str, Any]
        ] = None,
    ) -> str:

        if (
            domain
            and domain.strip()
        ):
            return domain.strip().lower()

        if intent_data:

            detected = intent_data.get(
                "domain"
            )

            if detected:

                return str(
                    detected
                ).lower()

        return detect_domain(
            query
        )


    # ==========================================================================
    # QUESTION TYPE
    #
    # Ownership remains outside Prompt Manager.
    #
    # This manager receives the canonical output.
    # ==========================================================================

    def resolve_question_type(
        self,
        question_type: str = "",
        question_type_context: str = "",
    ) -> str:

        if (
            question_type
            and question_type.strip()
        ):
            return question_type.strip()

        if (
            question_type_context
            and question_type_context.strip()
        ):
            return question_type_context.strip()

        return ""


    # ==========================================================================
    # SYMBOL KNOWLEDGE
    # ==========================================================================

    def _symbol_context(
        self,
        query: str,
        domain: str,
    ) -> str:

        symbols_found = recognize_symbols(
            query,
            domain,
        )

        if not symbols_found:

            return ""

        lines = [
            "Recognized symbols:"
        ]

        for (
            symbol,
            meaning,
        ) in symbols_found:

            lines.append(
                f"- {symbol}: {meaning}"
            )

        return "\n".join(
            lines
        )


    # ==========================================================================
    # CODE KNOWLEDGE
    # ==========================================================================

    def _code_context(
        self,
        query: str,
    ) -> str:

        query_lower = query.lower()

        languages = []

        terms = []

        for language in PROGRAMMING_LANGUAGES:

            if (
                language.lower()
                in query_lower
            ):

                languages.append(
                    language
                )

        for (
            term,
            meaning,
        ) in CODE_TERMS.items():

            if (
                term.lower()
                in query_lower
            ):

                terms.append(
                    f"{term}: {meaning}"
                )

        sections = []

        if languages:

            sections.append(
                "Recognized programming "
                "technologies/languages:\n"
                + "\n".join(
                    f"- {item}"
                    for item in languages
                )
            )

        if terms:

            sections.append(
                "Recognized coding terms:\n"
                + "\n".join(
                    terms
                )
            )

        return "\n\n".join(
            sections
        )


    # ==========================================================================
    # LINGUISTIC CONTEXT
    #
    # Canonical linguistic engines own the actual analysis.
    #
    # Prompt Manager assembles their results.
    # ==========================================================================

    def build_linguistic_context(
        self,
        parts_of_speech_context: str = "",
        word_understanding_context: str = "",
        word_chain_context: str = "",
        synonym_context: str = "",
        antonym_context: str = "",
        close_proxy_context: str = "",
        global_word_context: str = "",
        alphabet_matrix_context: str = "",
        relationship_matrix_context: str = "",
        word_mixer_context: str = "",
        matrix_context: str = "",
    ) -> str:

        parts = []

        context_items = (
            (
                "Parts of speech:",
                parts_of_speech_context,
            ),
            (
                "Word understanding:",
                word_understanding_context,
            ),
            (
                "Word chain:",
                word_chain_context,
            ),
            (
                "Synonyms:",
                synonym_context,
            ),
            (
                "Antonyms:",
                antonym_context,
            ),
            (
                "Close-proxy relationships:",
                close_proxy_context,
            ),
            (
                "Global word sensibility:",
                global_word_context,
            ),
            (
                "Alphabet matrix:",
                alphabet_matrix_context,
            ),
            (
                "Relationship matrix:",
                relationship_matrix_context,
            ),
            (
                "Word mixer:",
                word_mixer_context,
            ),
            (
                "Matrix mathematics/context:",
                matrix_context,
            ),
        )

        for (
            title,
            value,
        ) in context_items:

            if (
                value
                and value.strip()
            ):

                parts.append(
                    title
                    + "\n"
                    + value.strip()
                )

        return "\n\n".join(
            parts
        )


    # ==========================================================================
    # KNOWLEDGE BOARD
    # ==========================================================================

    def build_knowledge_context(
        self,
        query: str,
        domain: str,
        context: str = "",
        last_message: str = "",
    ) -> str:

        parts = []

        if (
            context
            and context.strip()
        ):

            parts.append(
                context.strip()
            )

        symbol_context = self._symbol_context(
            query,
            domain,
        )

        if symbol_context:

            parts.append(
                symbol_context
            )

        if domain == "code":

            code_context = self._code_context(
                query
            )

            if code_context:

                parts.append(
                    code_context
                )

        if (
            last_message
            and last_message.strip()
        ):

            parts.append(
                "Last user message:\n"
                + last_message.strip()
            )

        return "\n\n".join(
            parts
        )


    # ==========================================================================
    # PROJECT CONTEXT
    # ==========================================================================

    def build_project_context(
        self,
        workspace_name: str = "",
        workspace_context: str = "",
        project_name: str = "",
        project_pin: str = "",
        project_trace: str = "",
        current_project_state: str = "",
        historical_project_state: str = "",
    ) -> Dict[
        str,
        str,
    ]:

        active_project_name = (
            project_name.strip()
            if (
                project_name
                and project_name.strip()
            )
            else workspace_name.strip()
        )

        final_workspace_context = (
            workspace_context.strip()
            if workspace_context
            else ""
        )

        if active_project_name:

            project_line = (
                f"Current project: "
                f"{active_project_name}"
            )

            if final_workspace_context:

                final_workspace_context = (
                    project_line
                    + "\n"
                    + final_workspace_context
                )

            else:

                final_workspace_context = (
                    project_line
                )

        return {

            "workspace_context":
                final_workspace_context,

            "project_name":
                active_project_name,

            "project_pin":
                project_pin.strip()
                if project_pin
                else "",

            "project_trace":
                project_trace.strip()
                if project_trace
                else "",

            "current_project_state":
                current_project_state.strip()
                if current_project_state
                else "",

            "historical_project_state":
                historical_project_state.strip()
                if historical_project_state
                else "",
        }


    # ==========================================================================
    # MEMORY CONTEXT
    #
    # MemoryGrid and Memory Passport systems own retrieval and access control.
    #
    # Prompt Manager only receives permitted output.
    # ==========================================================================

    def build_memory_context(
        self,
        memory_context: str = "",
        memory_passport: str = "",
    ) -> Dict[
        str,
        str,
    ]:

        return {

            "memory_context":
                memory_context.strip()
                if memory_context
                else "",

            "memory_passport":
                memory_passport.strip()
                if memory_passport
                else "",
        }


    # ==========================================================================
    # PERMISSION CONTEXT
    #
    # Enforcement happens before context reaches Prompt Manager.
    # ==========================================================================

    def build_permission_context(
        self,
        permission_context: str = "",
    ) -> str:

        return (
            permission_context.strip()
            if permission_context
            else ""
        )


    # ==========================================================================
    # CONFLICT AND SELF-CORRECTION
    # ==========================================================================

    def build_review_context(
        self,
        conflict_context: str = "",
        self_correction_context: str = "",
        verifier: str = "",
    ) -> Dict[
        str,
        str,
    ]:

        return {

            "conflict_context":
                conflict_context.strip()
                if conflict_context
                else "",

            "self_correction_context":
                self_correction_context.strip()
                if self_correction_context
                else "",

            "verifier":
                verifier.strip()
                if verifier
                else "",
        }


    # ==========================================================================
    # MAIN PROMPT
    # ==========================================================================

    def build_prompt(
        self,
        query: str,
        context: str = "",
        country: Optional[str] = None,
        language: Optional[str] = None,
        conversation_history: str = "",
        workspace_name: str = "",
        last_message: str = "",
        temperament: Optional[str] = None,
        workspace_context: str = "",
        verifier: str = "",
        domain: str = "",
        intent: str = "",
        question_type: str = "",
        question_type_context: str = "",
        project_name: str = "",
        project_pin: str = "",
        project_trace: str = "",
        current_project_state: str = "",
        historical_project_state: str = "",
        memory_context: str = "",
        memory_passport: str = "",
        permission_context: str = "",
        # LINGUISTIC ENGINE OUTPUT
        linguistic_context: str = "",
        knowledge_context: str = "",
        review_context: str = "",
        # CODE-AGENT CONTROLS
        code_mode: bool = False,
        verification_level: str = "standard",
        max_iterations: int = 3,
        allow_mutations: bool = True,
        domain_pack: str = "general",
        dialect: Optional[str] = None,
        approval_required_for: Optional[List[str]] = None,
        preference_context: str = "",
    ) -> str:
        """
        Assemble the final prompt string sent to the model.

        Sections are included only if their input is non-empty,
        so this method is safe for chat-only, code-only, or mixed use.
        """
        c = country or self.default_country
        lang = language or self.default_language
        temp = temperament or self.default_temperament

        parts: List[str] = []

        # --- IDENTITY ---
        parts.append(
            "You are Accodite, an org-aware AI assistant. "
            "Answer in the user's dialect when requested; keep code "
            "identifiers in English."
        )
        parts.append(f"Country: {c} | Language: {lang} | Temperament: {temp}")
        if dialect:
            parts.append(f"Dialect for narration: {dialect}")
        if verifier:
            parts.append(f"Verifier: {verifier}")

        # --- WORKSPACE ---
        if workspace_name:
            parts.append(f"Workspace: {workspace_name}")
        if workspace_context:
            parts.append(f"Workspace context:\n{workspace_context.strip()}")

        # --- PROJECT ---
        if project_name:
            parts.append(f"Project: {project_name}")
        if project_pin:
            parts.append(f"Pinned anchors:\n{project_pin.strip()}")
        if project_trace:
            parts.append(f"Recent trace:\n{project_trace.strip()}")
        if current_project_state:
            parts.append(f"Current state:\n{current_project_state.strip()}")
        if historical_project_state:
            parts.append(f"Historical state:\n{historical_project_state.strip()}")

        # --- QUESTION TYPE / INTENT ---
        if question_type:
            parts.append(f"Question type: {question_type}")
        if question_type_context:
            parts.append(f"Question type context:\n{question_type_context.strip()}")
        if intent:
            parts.append(f"Detected intent: {intent}")
        if domain:
            parts.append(f"Detected domain: {domain}")

        # --- MEMORY ---
        if memory_context:
            parts.append(f"Memory context:\n{memory_context.strip()}")
        if memory_passport:
            parts.append(f"Memory passport:\n{memory_passport.strip()}")

        # --- LINGUISTIC / KNOWLEDGE ---
        if linguistic_context:
            parts.append(f"Linguistic engine:\n{linguistic_context.strip()}")
        if knowledge_context:
            parts.append(f"Knowledge:\n{knowledge_context.strip()}")

        # --- PERMISSION ---
        if permission_context:
            parts.append(f"Permissions:\n{permission_context.strip()}")

        # --- CODE-AGENT CONTROLS ---
        ctrl = self._code_agent_controls(
            code_mode=code_mode,
            verification_level=verification_level,
            max_iterations=max_iterations,
            allow_mutations=allow_mutations,
            domain_pack=domain_pack,
            approval_required_for=approval_required_for or [],
        )
        if ctrl:
            parts.append(ctrl)

        # --- REVIEW ---
        if review_context:
            parts.append(f"Review notes:\n{review_context.strip()}")

        # --- HISTORY ---
        if conversation_history:
            parts.append(f"Conversation history:\n{conversation_history.strip()}")
        if last_message:
            parts.append(f"Last message:\n{last_message.strip()}")

        # --- USER / WORKSPACE PREFERENCES ---
        if preference_context:
            parts.append("User preferences (along/pivot):\n" + preference_context.strip())

        # --- CONTEXT + QUERY ---
        if context:
            parts.append(f"Retrieved context:\n{context.strip()}")

        parts.append(f"USER REQUEST:\n{(query or '').strip()}")

        return "\n\n".join(parts)


    # ==========================================================================
    # CODE-AGENT CONTROLS
    # ==========================================================================

    def _code_agent_controls(
        self,
        *,
        code_mode: bool = False,
        verification_level: str = "standard",
        max_iterations: int = 3,
        allow_mutations: bool = True,
        domain_pack: str = "general",
        approval_required_for: Optional[List[str]] = None,
    ) -> str:
        """
        Render a SYSTEM CONTROLS block into the prompt so the model
        knows its own operating envelope for this query.
        """
        if not code_mode and not approval_required_for:
            return ""
        lines = ["SYSTEM CONTROLS:"]
        lines.append(f"- code_mode: {'on' if code_mode else 'off'}")
        if code_mode:
            lines.append(f"- verification_level: {verification_level}")
            lines.append(f"- max_iterations: {int(max_iterations)}")
            lines.append(f"- allow_mutations: {'yes' if allow_mutations else 'no'}")
            lines.append(f"- domain_pack: {domain_pack}")
        if approval_required_for:
            lines.append(
                "- require_user_approval_for: "
                + ", ".join(sorted(approval_required_for))
            )
        return "\n".join(lines)


    # ==========================================================================
    # BUNDLE ENTRY (called by CognitionControl)
    # ==========================================================================

    def _preference_block(
        self,
        *,
        user_id: str,
        workspace_id: str,
        store: Any = None,
        top_k: int = 5,
    ) -> str:
        """Build a preference block from a UserWorkspacePreferenceStore."""
        if store is None:
            return ""
        try:
            summary = store.summary(user_id, workspace_id, k=top_k)
        except Exception:
            return ""
        along = summary.get("along") or []
        pivot = summary.get("pivot") or []
        if not along and not pivot:
            return ""

        lines = []
        if along:
            lines.append("ALONG (user tends to accept these):")
            for e in along:
                s = e.get("strength", 0)
                lines.append(f"  - ({s:.2f}) {e.get('text','')}")
        if pivot:
            lines.append("PIVOT (user redirected here; respect these):")
            for e in pivot:
                s = e.get("strength", 0)
                d = e.get("direction") or ""
                tail = f" [{d}]" if d else ""
                lines.append(f"  - ({s:.2f}) {e.get('text','')}{tail}")
        return "\n".join(lines)

    def build_prompt_from_bundle(self, bundle: Dict[str, Any]) -> str:
        """
        Unpack a bundle dict (from CognitionControl) into build_prompt kwargs.
        Unknown keys are ignored, so the bundle may carry richer data than
        build_prompt accepts.
        """
        allowed = {
            "query", "context", "country", "language",
            "conversation_history", "workspace_name", "last_message",
            "temperament", "workspace_context", "verifier", "domain",
            "intent", "question_type", "question_type_context",
            "project_name", "project_pin", "project_trace",
            "current_project_state", "historical_project_state",
            "memory_context", "memory_passport", "permission_context",
            "linguistic_context", "knowledge_context", "review_context",
            "code_mode", "verification_level", "max_iterations",
            "allow_mutations", "domain_pack", "dialect",
            "approval_required_for",
            "preference_context",
        }
        kwargs = {k: v for k, v in (bundle or {}).items() if k in allowed}
        return self.build_prompt(**kwargs)


# === PROMPT MANAGER END ===


# ==========================================================================
# MODULE-LEVEL WRAPPER (backward compatible with main.py)
# ==========================================================================

_DEFAULT_PROMPT_MANAGER = None


def _pm() -> PromptManager:
    global _DEFAULT_PROMPT_MANAGER
    if _DEFAULT_PROMPT_MANAGER is None:
        _DEFAULT_PROMPT_MANAGER = PromptManager()
    return _DEFAULT_PROMPT_MANAGER


def build_prompt(*args, **kwargs) -> str:
    """
    Module-level convenience wrapper around PromptManager.build_prompt.
    Preserves the original public API used by main.py and other modules.
    """
    return _pm().build_prompt(*args, **kwargs)


def build_prompt_from_bundle(bundle) -> str:
    """Module-level wrapper around PromptManager.build_prompt_from_bundle."""
    return _pm().build_prompt_from_bundle(bundle)
