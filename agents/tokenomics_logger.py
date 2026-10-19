import json
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_PATH = Path("/tmp/agent_decisions.jsonl")

INPUT_COST_PER_TOKEN = 3 / 1_000_000
OUTPUT_COST_PER_TOKEN = 15 / 1_000_000

TRACE_ID = ContextVar("trace_id", default="standalone")
TRACE_QUESTION = ContextVar("trace_question", default="")
TRACE_USAGE = ContextVar("trace_usage", default=None)


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

    print(f"[LOG] {stage}: {json.dumps(details, sort_keys=True)}")

    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")


@contextmanager
def trace_context(trace_id: str, question: str):
    trace_id_token = TRACE_ID.set(trace_id)
    question_token = TRACE_QUESTION.set(question)

    try:
        yield
    finally:
        TRACE_ID.reset(trace_id_token)
        TRACE_QUESTION.reset(question_token)


def record_usage(
    component: str,
    input_tokens: int,
    output_tokens: int,
    total_cost_usd: float,
    status: str,
    error: str | None = None,
) -> None:
    usage = TRACE_USAGE.get()

    if usage is None:
        return

    usage["input_tokens"] += input_tokens
    usage["output_tokens"] += output_tokens
    usage["total_cost_usd"] += total_cost_usd

    usage["calls"].append(
        {
            "component": component,
            "status": status,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_cost_usd": total_cost_usd,
            "error": error,
        }
    )


def build_cost_summary(usage: dict[str, Any]) -> dict[str, Any]:
    input_tokens = usage["input_tokens"]
    output_tokens = usage["output_tokens"]

    input_cost_usd = input_tokens * INPUT_COST_PER_TOKEN
    output_cost_usd = output_tokens * OUTPUT_COST_PER_TOKEN

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "input_cost_usd": round(input_cost_usd, 10),
        "output_cost_usd": round(output_cost_usd, 10),
        "total_cost_usd": round(
            input_cost_usd + output_cost_usd,
            10,
        ),
        "calls": list(usage["calls"]),
    }


def invoke_claude_logged(
    component: str,
    prompt: str,
    max_tokens: int,
) -> dict:
    from bedrock_client import invoke_claude

    trace_id = TRACE_ID.get()
    question = TRACE_QUESTION.get()

    try:
        result = invoke_claude(
            prompt,
            max_tokens=max_tokens,
        )
    except Exception as error:
        record_usage(
            component=component,
            input_tokens=0,
            output_tokens=0,
            total_cost_usd=0.0,
            status="error",
            error=str(error),
        )

        log_decision(
            "claude_call",
            question,
            {
                "trace_id": trace_id,
                "component": component,
                "status": "error",
                "input_tokens": 0,
                "output_tokens": 0,
                "input_cost_usd": 0.0,
                "output_cost_usd": 0.0,
                "total_cost_usd": 0.0,
                "error": str(error),
            },
        )
        raise

    input_tokens = int(result.get("input_tokens", 0) or 0)
    output_tokens = int(result.get("output_tokens", 0) or 0)

    input_cost_usd = input_tokens * INPUT_COST_PER_TOKEN
    output_cost_usd = output_tokens * OUTPUT_COST_PER_TOKEN
    total_cost_usd = input_cost_usd + output_cost_usd

    record_usage(
        component=component,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_cost_usd=total_cost_usd,
        status="success",
    )

    log_decision(
        "claude_call",
        question,
        {
            "trace_id": trace_id,
            "component": component,
            "status": "success",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost_usd": input_cost_usd,
            "output_cost_usd": output_cost_usd,
            "total_cost_usd": total_cost_usd,
        },
    )

    return result


def clear_log() -> None:
    LOG_PATH.unlink(missing_ok=True)


def run_traced_query(
    graph: Any,
    question: str,
) -> dict:
    trace_id = uuid.uuid4().hex[:8]

    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_cost_usd": 0.0,
        "calls": [],
    }

    usage_token = TRACE_USAGE.set(usage)

    try:
        with trace_context(trace_id, question):
            log_decision(
                "query_start",
                question,
                {"trace_id": trace_id},
            )

            try:
                result = graph.invoke(
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
            except Exception as error:
                cost = build_cost_summary(usage)

                log_decision(
                    "query_failed",
                    question,
                    {
                        "trace_id": trace_id,
                        "error": str(error),
                        "cost": cost,
                    },
                )
                raise

            cost = build_cost_summary(usage)

            log_decision(
                "query_complete",
                question,
                {
                    "trace_id": trace_id,
                    "route": result.get("route"),
                    "has_final_answer": bool(
                        result.get("final_answer")
                    ),
                    "cost": cost,
                },
            )

            return {
                **result,
                "_trace_id": trace_id,
                "token_usage": {
                    "input": usage["input_tokens"],
                    "output": usage["output_tokens"],
                },
                "cost": cost,
            }

    finally:
        TRACE_USAGE.reset(usage_token)


