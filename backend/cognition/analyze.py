"""
CoMpaNeoN Unified Analysis Layer

Analyze sits between PromptManager / request handling and the intelligence
layers. It does not replace any existing authority.

Responsibilities:
    - language
    - intent
    - question type
    - question approach
    - directives
    - linguistic/POS analysis
    - domain
    - entities / terms
    - symbols
    - domain rules
    - required knowledge
    - required tools
    - reasoning path
    - project context

Existing modules remain authoritative for their own responsibilities.
"""

from typing import Any, Dict, List, Optional

from intent_analyzer import (
    analyze_intent,
    detect_domain,
    detect_entities,
)

from linguistic import LinguisticAnalyzer

try:
    from question_type_detector import (
        detect_question_type,
    )
except ImportError:
    detect_question_type = None

try:
    from directives import (
        detect_directives,
    )
except ImportError:
    detect_directives = None

try:
    from domain_rules import (
        normalize_domain,
        get_domain_rules,
        applicable_rules,
    )
except ImportError:
    normalize_domain = None
    get_domain_rules = None
    applicable_rules = None

try:
    from symbols import recognize_symbols
except ImportError:
    recognize_symbols = None


class Analyze:
    """
    Unified request-analysis authority.

    Analyze answers:

        What is being asked?
        How should it be approached?
        What domain is involved?
        What knowledge is required?
        What tools may be required?
        What existing CoMpaNeoN authorities must participate?
    """

    def __init__(self):
        self.linguistic = LinguisticAnalyzer()

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def analyze(
        self,
        query: str,
        language: Optional[str] = None,
        project_context: Optional[Dict[str, Any]] = None,
        workspace_context: Optional[Dict[str, Any]] = None,
        previous_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        query = (query or "").strip()

        if not query:
            return self._empty_result()

        # --------------------------------------------------------------
        # 1. INTENT
        # --------------------------------------------------------------

        try:
            intent_analysis = analyze_intent(
                query,
                language=language or "en",
            )
        except Exception as exc:
            intent_analysis = {
                "query": query,
                "language": language or "en",
                "intent": "",
                "domain": "",
                "entities": [],
                "error": str(exc),
            }

        detected_language = (
            intent_analysis.get("language")
            or language
            or self._resolve_language(query)
        )

        intent = intent_analysis.get("intent", "")

        # --------------------------------------------------------------
        # 2. DOMAIN
        # --------------------------------------------------------------

        domain = (
            intent_analysis.get("domain")
            or detect_domain(query)
            or ""
        )

        if normalize_domain:
            try:
                domain = normalize_domain(domain)
            except Exception:
                pass

        # --------------------------------------------------------------
        # 3. ENTITIES / TERMS
        # --------------------------------------------------------------

        entities = intent_analysis.get("entities")

        if entities is None:
            try:
                entities = detect_entities(query)
            except Exception:
                entities = []

        if not isinstance(entities, list):
            entities = list(entities) if entities else []

        # --------------------------------------------------------------
        # 4. QUESTION TYPE
        # --------------------------------------------------------------

        question_type = self._detect_question_type(query)

        # --------------------------------------------------------------
        # 5. QUESTION APPROACH
        # --------------------------------------------------------------

        question_approach = self._determine_question_approach(
            query=query,
            intent=intent,
            question_type=question_type,
            domain=domain,
        )

        # --------------------------------------------------------------
        # 6. DIRECTIVES
        # --------------------------------------------------------------

        directives = self._detect_directives(query)

        # --------------------------------------------------------------
        # 7. LINGUISTIC / POS
        # --------------------------------------------------------------

        linguistic = self._analyze_linguistic(
            query=query,
            language=detected_language,
        )

        # --------------------------------------------------------------
        # 8. SYMBOLS
        # --------------------------------------------------------------

        symbols = self._recognize_symbols(query)

        # --------------------------------------------------------------
        # 9. DOMAIN RULES
        # --------------------------------------------------------------

        domain_rule_context = self._domain_rules(
            query=query,
            domain=domain,
        )

        # --------------------------------------------------------------
        # 10. PROJECT CONTEXT
        # --------------------------------------------------------------

        project = self._normalize_project_context(
            project_context,
            workspace_context,
        )

        # --------------------------------------------------------------
        # 11. REQUIRED KNOWLEDGE
        # --------------------------------------------------------------

        required_knowledge = self._required_knowledge(
            query=query,
            domain=domain,
            intent=intent,
            question_type=question_type,
            entities=entities,
            project_context=project,
        )

        # --------------------------------------------------------------
        # 12. REQUIRED TOOLS
        # --------------------------------------------------------------

        required_tools = self._required_tools(
            query=query,
            domain=domain,
            intent=intent,
            question_type=question_type,
            question_approach=question_approach,
            directives=directives,
            project_context=project,
        )

        # --------------------------------------------------------------
        # 13. REASONING PATH
        # --------------------------------------------------------------

        reasoning_path = self._reasoning_path(
            question_type=question_type,
            question_approach=question_approach,
            domain=domain,
            intent=intent,
            required_knowledge=required_knowledge,
            required_tools=required_tools,
        )

        # --------------------------------------------------------------
        # 14. FINAL ANALYSIS OBJECT
        # --------------------------------------------------------------

        return {
            "query": query,

            "language": detected_language,

            "intent": intent,
            "intent_analysis": intent_analysis,

            "question_type": question_type,
            "question_approach": question_approach,

            "directives": directives,

            "domain": domain,
            "domain_rules": domain_rule_context,

            "entities": entities,

            "symbols": symbols,

            "linguistic": linguistic,

            "project_context": project,

            "required_knowledge": required_knowledge,
            "required_tools": required_tools,

            "reasoning_path": reasoning_path,

            "previous_context": previous_context or {},
        }

    # ------------------------------------------------------------------
    # LANGUAGE
    # ------------------------------------------------------------------

    def _resolve_language(self, query: str) -> str:

        try:
            result = self.linguistic.resolve_language(query)

            if isinstance(result, str):
                return result

            if isinstance(result, dict):
                return (
                    result.get("language")
                    or result.get("lang")
                    or "en"
                )

        except Exception:
            pass

        return "en"

    # ------------------------------------------------------------------
    # QUESTION TYPE
    # ------------------------------------------------------------------

    def _detect_question_type(self, query: str) -> str:

        if detect_question_type:

            try:
                result = detect_question_type(query)

                if isinstance(result, str):
                    return result

                if isinstance(result, dict):
                    return (
                        result.get("question_type")
                        or result.get("type")
                        or result.get("category")
                        or ""
                    )

            except Exception:
                pass

        q = query.lower().strip()

        if q.startswith(("what ", "what is ", "what are ")):
            return "definition"

        if q.startswith(("why ", "why does ", "why is ", "why are ")):
            return "causal"

        if q.startswith(("how ", "how do ", "how can ", "how to ")):
            return "procedural"

        if q.startswith(("compare ", "difference between ")):
            return "comparison"

        if q.startswith(("is ", "are ", "can ", "does ", "do ")):
            return "evaluation"

        if any(
            word in q
            for word in (
                "law",
                "legal",
                "legislation",
                "statute",
                "regulation",
            )
        ):
            return "legal_research"

        return "general"

    # ------------------------------------------------------------------
    # QUESTION APPROACH
    # ------------------------------------------------------------------

    def _determine_question_approach(
        self,
        query: str,
        intent: str,
        question_type: str,
        domain: str,
    ) -> str:

        q = query.lower()

        # Build / implementation
        if any(
            phrase in q
            for phrase in (
                "how do i build",
                "how do we build",
                "how to build",
                "implement",
                "create",
                "develop",
                "code",
                "program",
            )
        ):
            return "build"

        # Legal research
        if (
            question_type == "legal_research"
            or domain in ("law", "legal")
            or any(
                phrase in q
                for phrase in (
                    "find the law",
                    "what law governs",
                    "legal authority",
                    "statute",
                    "regulation",
                    "case law",
                )
            )
        ):
            return "legal_research"

        # Rule / authority evaluation
        if any(
            phrase in q
            for phrase in (
                "is this allowed",
                "is this permissible",
                "is this legal",
                "what are the rules",
                "under the rules",
                "according to",
                "under shariah",
            )
        ):
            return "rule_evaluation"

        # Comparison
        if (
            question_type == "comparison"
            or "compare" in q
            or "difference between" in q
        ):
            return "comparative"

        # Causal reasoning
        if question_type == "causal":
            return "causal_reasoning"

        # Procedural
        if question_type == "procedural":
            return "procedural"

        # Definition
        if question_type == "definition":
            return "definition_explanation"

        # Research
        if any(
            word in q
            for word in (
                "research",
                "investigate",
                "look up",
                "find information",
                "verify",
                "source",
                "sources",
            )
        ):
            return "research"

        # Analysis
        if any(
            word in q
            for word in (
                "analyze",
                "analyse",
                "examine",
                "evaluate",
                "assess",
            )
        ):
            return "analytical"

        return "direct_answer"

    # ------------------------------------------------------------------
    # DIRECTIVES
    # ------------------------------------------------------------------

    def _detect_directives(self, query: str) -> Dict[str, Any]:

        if detect_directives:

            try:
                result = detect_directives(query)

                if isinstance(result, dict):
                    return result

                if isinstance(result, list):
                    return {
                        "items": result,
                    }

                if isinstance(result, str):
                    return {
                        "items": [result],
                    }

            except Exception:
                pass

        return {
            "items": [],
        }

    # ------------------------------------------------------------------
    # LINGUISTIC
    # ------------------------------------------------------------------

    def _analyze_linguistic(
        self,
        query: str,
        language: str,
    ) -> Dict[str, Any]:

        try:
            result = self.linguistic.analyze(
                query,
                lang=language,
            )

            if isinstance(result, dict):
                return result

            return {
                "result": result,
            }

        except TypeError:

            # Some versions may use language rather than lang.
            try:
                result = self.linguistic.analyze(
                    query,
                    language=language,
                )

                if isinstance(result, dict):
                    return result

                return {
                    "result": result,
                }

            except Exception as exc:
                return {
                    "error": str(exc),
                }

        except Exception as exc:
            return {
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # SYMBOLS
    # ------------------------------------------------------------------

    def _recognize_symbols(self, query: str):

        if not recognize_symbols:
            return []

        try:
            result = recognize_symbols(query)

            return result if result is not None else []

        except Exception:
            return []

    # ------------------------------------------------------------------
    # DOMAIN RULES
    # ------------------------------------------------------------------

    def _domain_rules(
        self,
        query: str,
        domain: str,
    ) -> Dict[str, Any]:

        if not domain:
            return {}

        result = {
            "domain": domain,
            "rules": [],
            "applicable": [],
        }

        if get_domain_rules:

            try:
                rules = get_domain_rules(domain)

                if isinstance(rules, dict):
                    result.update(rules)
                else:
                    result["rules"] = rules or []

            except Exception as exc:
                result["error"] = str(exc)

        if applicable_rules:

            try:
                applicable = applicable_rules(
                    query,
                    domain,
                )

                result["applicable"] = (
                    applicable or []
                )

            except Exception:
                pass

        return result

    # ------------------------------------------------------------------
    # PROJECT CONTEXT
    # ------------------------------------------------------------------

    def _normalize_project_context(
        self,
        project_context: Optional[Dict[str, Any]],
        workspace_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:

        project = {}

        if isinstance(workspace_context, dict):
            project.update(workspace_context)

        if isinstance(project_context, dict):
            project.update(project_context)

        return project

    # ------------------------------------------------------------------
    # REQUIRED KNOWLEDGE
    # ------------------------------------------------------------------

    def _required_knowledge(
        self,
        query: str,
        domain: str,
        intent: str,
        question_type: str,
        entities: List[Any],
        project_context: Dict[str, Any],
    ) -> List[str]:

        knowledge = []

        if domain:
            knowledge.append(
                f"domain:{domain}"
            )

        if intent:
            knowledge.append(
                f"intent:{intent}"
            )

        if question_type:
            knowledge.append(
                f"question_type:{question_type}"
            )

        if entities:
            knowledge.append(
                "entity_context"
            )

        q = query.lower()

        if any(
            x in q
            for x in (
                "rule",
                "allowed",
                "permissible",
                "legal",
                "law",
                "shariah",
            )
        ):
            knowledge.append(
                "authoritative_rules"
            )

        if any(
            x in q
            for x in (
                "latest",
                "current",
                "today",
                "recent",
                "2026",
            )
        ):
            knowledge.append(
                "current_external_information"
            )

        if project_context:
            knowledge.append(
                "project_context"
            )

        return self._unique(knowledge)

    # ------------------------------------------------------------------
    # REQUIRED TOOLS
    # ------------------------------------------------------------------

    def _required_tools(
        self,
        query: str,
        domain: str,
        intent: str,
        question_type: str,
        question_approach: str,
        directives: Dict[str, Any],
        project_context: Dict[str, Any],
    ) -> List[str]:

        tools = []

        q = query.lower()

        # External research
        if any(
            x in q
            for x in (
                "research",
                "latest",
                "current",
                "recent",
                "verify",
                "source",
                "sources",
                "find",
                "look up",
            )
        ):
            tools.append("external_research")

        # Legal research
        if (
            question_approach == "legal_research"
            or domain in ("law", "legal")
        ):
            tools.append("legal_research")

        # Coding environment
        if (
            question_approach == "build"
            or domain in ("coding", "programming", "software")
            or any(
                x in q
                for x in (
                    "code",
                    "python",
                    "javascript",
                    "html",
                    "css",
                    "debug",
                    "compile",
                    "run",
                    "test",
                )
            )
        ):
            tools.extend(
                [
                    "coding_sandbox",
                    "console",
                    "tree_sitter",
                    "lsp",
                ]
            )

        # Visual explanation
        if any(
            x in q
            for x in (
                "diagram",
                "draw",
                "illustrate",
                "visualize",
                "architecture",
                "flowchart",
                "image",
            )
        ):
            tools.append("visual")

        # Project-aware operations
        if project_context:
            tools.append("project_context")

        return self._unique(tools)

    # ------------------------------------------------------------------
    # REASONING PATH
    # ------------------------------------------------------------------

    def _reasoning_path(
        self,
        question_type: str,
        question_approach: str,
        domain: str,
        intent: str,
        required_knowledge: List[str],
        required_tools: List[str],
    ) -> List[str]:

        path = [
            "parse_request",
            "identify_intent",
            "identify_question_type",
            "select_question_approach",
        ]

        if domain:
            path.append(
                "activate_domain_context"
            )

        if required_knowledge:
            path.append(
                "retrieve_required_knowledge"
            )

        if required_tools:
            path.append(
                "select_required_tools"
            )

        if question_approach == "comparative":
            path.append(
                "compare_evidence"
            )

        elif question_approach == "causal_reasoning":
            path.append(
                "construct_causal_chain"
            )

        elif question_approach == "procedural":
            path.append(
                "construct_procedure"
            )

        elif question_approach == "build":
            path.extend(
                [
                    "inspect_project_context",
                    "construct_implementation_plan",
                    "validate_implementation",
                ]
            )

        elif question_approach == "legal_research":
            path.extend(
                [
                    "identify_jurisdiction",
                    "identify_authority",
                    "retrieve_authoritative_sources",
                    "validate_source_context",
                ]
            )

        elif question_approach == "rule_evaluation":
            path.extend(
                [
                    "identify_applicable_rules",
                    "evaluate_against_rules",
                ]
            )

        elif question_approach == "research":
            path.extend(
                [
                    "retrieve_external_sources",
                    "evaluate_source_relevance",
                    "synthesize_evidence",
                ]
            )

        else:
            path.append(
                "construct_direct_answer"
            )

        path.extend(
            [
                "validate_constraints",
                "prepare_response",
            ]
        )

        return self._unique(path)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    @staticmethod
    def _unique(items):

        seen = set()
        output = []

        for item in items:

            key = str(item)

            if key in seen:
                continue

            seen.add(key)
            output.append(item)

        return output

    @staticmethod
    def _empty_result():

        return {
            "query": "",
            "language": "en",
            "intent": "",
            "intent_analysis": {},
            "question_type": "general",
            "question_approach": "direct_answer",
            "directives": {
                "items": [],
            },
            "domain": "",
            "domain_rules": {},
            "entities": [],
            "symbols": [],
            "linguistic": {},
            "project_context": {},
            "required_knowledge": [],
            "required_tools": [],
            "reasoning_path": [],
            "previous_context": {},
        }


# ----------------------------------------------------------------------
# FUNCTIONAL API
# ----------------------------------------------------------------------

_default_analyzer = Analyze()


def analyze(
    query: str,
    language: Optional[str] = None,
    project_context: Optional[Dict[str, Any]] = None,
    workspace_context: Optional[Dict[str, Any]] = None,
    previous_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    return _default_analyzer.analyze(
        query=query,
        language=language,
        project_context=project_context,
        workspace_context=workspace_context,
        previous_context=previous_context,
    )