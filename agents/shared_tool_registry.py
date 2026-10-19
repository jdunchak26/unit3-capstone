import os
from dotenv import load_dotenv
from bedrock_client import invoke_claude
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional
import re

load_dotenv()

# ── Part 1: Standardized Agent Wrappers ─────────────────────────────────────
# These wrap the actual agent logic from Day 2 (sql_agent.py) and
# Day 3 (retrieval_agent_solution.py), reshaping their output into the
# shared {success, answer, sources, metadata} contract.

def run_sql_agent(question: str) -> dict:
    from sql_agent import run_sql_agent as sql_agent_runner

    return sql_agent_runner(question)


def run_retrieval_agent(question: str) -> dict:
    from retrieval_agent import run_retrieval_agent as retrieval_runner

    return retrieval_runner(question)


# ── Part 2: Tool Registry ────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "sql_agent": {
        "function": run_sql_agent,
        "schema": {
            "name": "sql_agent",
            "description": (
                "Use this tool to query the relational database for structured business "
                "information about clients, projects, consultants, invoices, and related "
                "operational records. It is appropriate for questions requiring exact "
                "counts, totals, averages, rankings, filters, status checks, date-based "
                "comparisons, or other calculations that should be derived from database "
                "records. Examples include the number of active projects, total invoice "
                "value for a client, consultants assigned to a project, overdue invoices."
                "Do not use this tool for policies, procedures, qualitative"
                "guidance, document-based explanations, or project narratives that are "
                "not represented as structured database fields."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"]
            }
        }
    },
    "retrieval_agent": {
        "function": run_retrieval_agent,
        "schema": {
            "name": "retrieval_agent",
            "description": (
                "Use this tool to search indexed documents for unstructured or "
                "semi-structured information, including policies, procedures, guidance, "
                "onboarding materials, expense rules, controls, case studies, and project "
                "narratives. It is appropriate for questions asking what a policy says, "
                "how a process works, what steps are required, or what information is "
                "described in source documents. The tool should return a grounded answer "
                "supported by retrieved document chunks, along with source references and "
                "grounding metadata. It may also provide a clear refusal when the indexed "
                "documents do not contain enough information to answer reliably."
                "Do not use this tool for exact counts, totals, rankings, database lookups, or "
                "calculations that should be performed against structured relational data."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"]
            }
        }
    }
}


# def get_all_schemas() -> list:
#     return [tool["schema"] for tool in TOOL_REGISTRY.values()]


# def call_tool(tool_name: str, question: str) -> dict:
#     if tool_name not in TOOL_REGISTRY:
#         return {"success": False, "answer": f"Unknown tool: {tool_name}", "sources": [], "metadata": {}}
#     return TOOL_REGISTRY[tool_name]["function"](question)




###Langgraph
class OrchestratorState(TypedDict):
    question: str
    route: Optional[str]
    sql_result: Optional[dict]
    retrieval_result: Optional[dict]
    final_answer: Optional[str]
    token_usage: Optional[dict]

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "for",
    "from", "have", "how", "in", "is", "it", "of", "on", "or", "our",
    "that", "the", "this", "to", "use", "what", "we", "with",
}


def _normalize_word(word: str) -> str:
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("s") and len(word) > 4:
        return word[:-1]
    return word


def _meaningful_words(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.casefold())
    return {
        _normalize_word(word)
        for word in words
        if word not in STOP_WORDS and len(word) > 2
    }


def _question_parts(question: str) -> list[str]:
    parts = re.split(
        r",|;|\?|\s+\band\b\s+"
        r"(?=(?:what|which|how|where|when|who|is|are|do|does|can)\b)",
        question.casefold(),
    )
    return [part.strip() for part in parts if part.strip()]


def _tool_score(question: str, description: str) -> int:
    positive_description = re.split(
        r"\bdo not use\b",
        description,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]

    return len(
        _meaningful_words(question)
        & _meaningful_words(positive_description)
    )


def route_question(state: OrchestratorState) -> OrchestratorState:
    selected_tools = set()

    for part in _question_parts(state["question"]):
        scores = {
            tool_name: _tool_score(
                part,
                tool_config["schema"]["description"],
            )
            for tool_name, tool_config in TOOL_REGISTRY.items()
        }

        best_score = max(scores.values(), default=0)

        if best_score == 0:
            continue

        selected_tools.update(
            tool_name
            for tool_name, score in scores.items()
            if score == best_score
        )

    has_sql = "sql_agent" in selected_tools
    has_retrieval = "retrieval_agent" in selected_tools

    if has_sql and has_retrieval:
        route = "both"
    elif has_sql:
        route = "sql"
    else:
        route = "retrieval"

    return {**state, "route": route}







def call_sql_agent(state: OrchestratorState) -> OrchestratorState:
    if state["route"] not in ["sql", "both"]:
        return state
    result = run_sql_agent(state["question"])
    return {**state, "sql_result": result}


def call_retrieval_agent(state: OrchestratorState) -> OrchestratorState:
    if state["route"] not in ["retrieval", "both"]:
        return state
    result = run_retrieval_agent(state["question"])
    return {**state, "retrieval_result": result}


def synthesise(state: OrchestratorState) -> OrchestratorState:
    context = ""

    if state.get("sql_result") and state["sql_result"].get("success"):
        r = state["sql_result"]
        context += f"SQL Agent Result:\n{r['answer']}\nSources: {r['sources']}\n\n"

    if state.get("retrieval_result") and state["retrieval_result"].get("success"):
        r = state["retrieval_result"]
        context += f"Retrieval Agent Result:\n{r['answer']}\nSources: {r['sources']}\n\n"

    if not context:
        return {
            **state,
            "final_answer": "I was unable to find relevant information to answer this question.",
            "token_usage": {"input": 0, "output": 0}
        }

    prompt = (
        f"Using the information below, answer the following question clearly.\n"
        f"Cite which agent(s) and source(s) the information came from.\n\n"
        f"Question: {state['question']}\n\n"
        f"Information:\n{context}"
    )
    result = invoke_claude(prompt, max_tokens=800)

    return {
        **state,
        "final_answer": result["text"],
        "token_usage": {
            "input": result["input_tokens"],
            "output": result["output_tokens"]
        }
    }


def build_orchestrator():
    graph = StateGraph(OrchestratorState)
    graph.add_node("router", route_question)
    graph.add_node("sql_agent", call_sql_agent)
    graph.add_node("retrieval_agent", call_retrieval_agent)
    graph.add_node("synthesiser", synthesise)

    graph.set_entry_point("router")
    graph.add_edge("router", "sql_agent")
    graph.add_edge("sql_agent", "retrieval_agent")
    graph.add_edge("retrieval_agent", "synthesiser")
    graph.add_edge("synthesiser", END)

    return graph.compile()


orchestrator = build_orchestrator()


if __name__ == "__main__":
    test_questions = [
        "How many active projects do we have?",                                  # sql only
        "What is our remote work policy?",                                        # retrieval only
        "How many active projects do we have, and what is our remote work policy?", # both
    ]

    for q in test_questions:
        print(f"\n{'='*60}\nQ: {q}")
        result = orchestrator.invoke({
            "question": q, "route": None, "sql_result": None,
            "retrieval_result": None, "final_answer": None, "token_usage": None
        })
        print(f"Route: {result['route']}")
        print(f"Answer: {result['final_answer']}")
        print(f"Tokens: {result['token_usage']}")



# ── Part 4: Simple Routing Preview ──────────────────────────────────────────

# def suggest_tool(question: str) -> str:
#     schemas_description = "\n".join([f"- {s['name']}: {s['description']}" for s in get_all_schemas()])

#     prompt = (
#         f"Available tools:\n{schemas_description}\n\n"
#         f"Question: {question}\n\n"
#         "Which tool should handle this? Reply with only the tool name."
#     )
#     result = invoke_claude(prompt, max_tokens=20)
#     return result["text"].strip()

## testing questions
# if __name__ == "__main__":
#     print("=" * 70)
#     print("PART 3: Registry Direct Tests")
#     print("=" * 70)
#     print("Registered tools:", [s["name"] for s in get_all_schemas()])

#     result1 = call_tool("sql_agent", "How many active projects do we have?")
#     print("\nSQL agent test:", result1)

#     result2 = call_tool("retrieval_agent", "What is our onboarding process?")
#     print("\nRetrieval agent test:", result2)

#     result3 = call_tool("nonexistent_tool", "test")
#     print("\nUnknown tool test:", result3)

#     print("\n" + "=" * 70)
#     print("PART 4: Routing Suggestion Preview")
#     print("=" * 70)
#     for q in [
#         "How many consultants do we have on active projects?",
#         "What is our expense reimbursement policy?",
#         "How many active projects do we have and what's our onboarding process?",
#     ]:
#         print(f"\nQ: {q}")
#         print(f"Suggested tool: {suggest_tool(q)}")