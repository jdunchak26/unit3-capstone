import json
import uuid
from datetime import datetime, timezone
from typing import Any

from shared_tool_registry import route_question


LOG_PATH = "/tmp/agent_decisions.jsonl"


def log_decision(
    stage: str,
    question: str,
    details: dict[str, Any],
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "question": question,
        "details": details,
    }

    print(f"[LOG] {stage}: {json.dumps(details, default=str)}")

    with open(LOG_PATH, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")


def route_question_logged(
    state: dict[str, Any],
) -> dict[str, Any]:
    result = route_question(state)

    log_decision(
        "routing",
        state["question"],
        {
            "route": result["route"],
        },
    )

    return result


def run_traced_query(
    orchestrator: Any,
    question: str,
) -> dict[str, Any]:
    trace_id = uuid.uuid4().hex[:8]

    log_decision(
        "query_start",
        question,
        {
            "trace_id": trace_id,
        },
    )

    result = orchestrator.invoke(
        {
            "question": question,
            "route": None,
            "sql_result": None,
            "retrieval_result": None,
            "final_answer": None,
            "token_usage": None,
            "trace_id": trace_id,
        }
    )

    sql_result = result.get("sql_result") or {}
    retrieval_result = result.get("retrieval_result") or {}

    log_decision(
        "query_complete",
        question,
        {
            "trace_id": trace_id,
            "route": result.get("route"),
            "sql_validation": (
                sql_result.get("metadata", {}).get("validation")
            ),
            "retrieval_grounded": (
                retrieval_result.get("metadata", {}).get("grounded")
            ),
            "retrieval_chunk_count": (
                retrieval_result.get("metadata", {}).get("chunk_count")
            ),
            "token_usage": result.get("token_usage"),
        },
    )

    return {
        **result,
        "_trace_id": trace_id,
    }
