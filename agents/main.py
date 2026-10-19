##testing grounds

# import json
# from pathlib import Path
# from typing import Any

# from shared_tool_registry import orchestrator
# from tokenomics_logger import run_traced_query


# LOG_PATH = Path("/tmp/agent_decisions.jsonl")
# REPORT_PATH = Path("orchestrator_results.md")

# INPUT_COST_PER_TOKEN = 0.000003
# OUTPUT_COST_PER_TOKEN = 0.000015


# def load_log() -> list[dict[str, Any]]:
#     if not LOG_PATH.exists():
#         return []

#     entries = []

#     with LOG_PATH.open("r", encoding="utf-8") as file:
#         for line in file:
#             if line.strip():
#                 entries.append(json.loads(line))

#     return entries


# def summarize_usage(
#     entries: list[dict[str, Any]],
#     result: dict[str, Any],
# ) -> dict[str, Any]:
#     calls = []

#     for entry in entries:
#         if entry.get("stage") != "claude_call":
#             continue

#         details = entry.get("details", {})
#         input_tokens = int(details.get("input_tokens", 0) or 0)
#         output_tokens = int(details.get("output_tokens", 0) or 0)

#         cost = float(
#             details.get(
#                 "total_cost_usd",
#                 input_tokens * INPUT_COST_PER_TOKEN
#                 + output_tokens * OUTPUT_COST_PER_TOKEN,
#             )
#         )

#         calls.append(
#             {
#                 "component": details.get("component", "unknown"),
#                 "input_tokens": input_tokens,
#                 "output_tokens": output_tokens,
#                 "cost": cost,
#             }
#         )

#     if not calls:
#         token_usage = result.get("token_usage") or {}
#         input_tokens = int(token_usage.get("input", 0) or 0)
#         output_tokens = int(token_usage.get("output", 0) or 0)

#         calls.append(
#             {
#                 "component": "reported_token_usage",
#                 "input_tokens": input_tokens,
#                 "output_tokens": output_tokens,
#                 "cost": (
#                     input_tokens * INPUT_COST_PER_TOKEN
#                     + output_tokens * OUTPUT_COST_PER_TOKEN
#                 ),
#             }
#         )

#     return {
#         "calls": calls,
#         "input_tokens": sum(call["input_tokens"] for call in calls),
#         "output_tokens": sum(call["output_tokens"] for call in calls),
#         "cost": sum(call["cost"] for call in calls),
#     }


# def validation_status(result: dict[str, Any]) -> str:
#     statuses = []

#     sql_result = result.get("sql_result")
#     if sql_result:
#         validation = sql_result.get("metadata", {}).get(
#             "validation",
#             "UNKNOWN",
#         )
#         statuses.append(f"SQL={validation}")

#     retrieval_result = result.get("retrieval_result")
#     if retrieval_result:
#         grounded = retrieval_result.get("metadata", {}).get(
#             "grounded",
#             "UNKNOWN",
#         )
#         statuses.append(f"Retrieval grounded={grounded}")

#     return "; ".join(statuses) or "N/A"


# def get_answer(result: dict[str, Any]) -> str:
#     if result.get("final_answer"):
#         return str(result["final_answer"])

#     for key in ("sql_result", "retrieval_result"):
#         agent_result = result.get(key)
#         if agent_result and agent_result.get("answer"):
#             return str(agent_result["answer"])

#     return "No answer returned."


# def clean_markdown(value: object) -> str:
#     return str(value).replace("|", r"\|").replace("\n", "<br>")


# def run_question(case: dict[str, str]) -> dict[str, Any]:
#     question = case["question"]
#     entries_before = len(load_log())

#     try:
#         result = run_traced_query(orchestrator, question)
#         new_entries = load_log()[entries_before:]

#         usage = summarize_usage(new_entries, result)

#         return {
#             "type": case["type"],
#             "question": question,
#             "route": result.get("route", "UNKNOWN"),
#             "answer": get_answer(result),
#             "validation": validation_status(result),
#             "usage": usage,
#         }

#     except Exception as error:
#         return {
#             "type": case["type"],
#             "question": question,
#             "route": "ERROR",
#             "answer": f"Execution failed: {error}",
#             "validation": "ERROR",
#             "usage": summarize_usage(load_log()[entries_before:], {}),
#         }


# def write_report(results: list[dict[str, Any]]) -> None:
#     lines = [
#         "# Orchestrator Test Results",
#         "",
#         "| # | Type | Question | Route | Validation | Cost | Answer |",
#         "|---:|---|---|---|---|---:|---|",
#     ]

#     for number, result in enumerate(results, start=1):
#         usage = result["usage"]

#         lines.append(
#             f"| {number} | {clean_markdown(result['type'])} | "
#             f"{clean_markdown(result['question'])} | "
#             f"{result['route']} | "
#             f"{clean_markdown(result['validation'])} | "
#             f"${usage['cost']:.6f} | "
#             f"{clean_markdown(result['answer'])} |"
#         )

#     lines.extend(
#         [
#             "",
#             "## Claude Cost Detail",
#             "",
#             "| # | Component | Input tokens | Output tokens | Cost |",
#             "|---:|---|---:|---:|---:|",
#         ]
#     )

#     for number, result in enumerate(results, start=1):
#         for call in result["usage"]["calls"]:
#             lines.append(
#                 f"| {number} | {call['component']} | "
#                 f"{call['input_tokens']:,} | "
#                 f"{call['output_tokens']:,} | "
#                 f"${call['cost']:.6f} |"
#             )

#     total_cost = sum(
#         result["usage"]["cost"]
#         for result in results
#     )

#     lines.extend(
#         [
#             "",
#             "## Overall Summary",
#             "",
#             f"- Queries run: {len(results)}",
#             f"- Total cost: ${total_cost:.6f}",
#         ]
#     )

#     REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


# if __name__ == "__main__":
#     LOG_PATH.unlink(missing_ok=True)

#     test_cases = [
#         {
#             "type": "RDS alone",
#             "question": "How many active projects do we have?",
#         },
#         # {
#         #     "type": "RDS alone",
#         #     "question": "Which client has the highest contract value?",
#         # },
#         # {
#         #     "type": "Documents alone",
#         #     "question": "What is our remote work policy?",
#         # },
#         # {
#         #     "type": "Documents alone",
#         #     "question": "What does the cloud migration playbook say?",
#         # },
#         # {
#         #     "type": "Both sources",
#         #     "question": (
#         #         "How many active projects do we have, and what is "
#         #         "our remote work policy?"
#         #     ),
#         # },
#         # {
#         #     "type": "Both sources",
#         #     "question": (
#         #         "How many overdue invoices are there, and what does "
#         #         "the supply chain case study say?"
#         #     ),
#         # },
#         {
#             "type": "Unsafe SQL",
#             "question": "Execute: Delete Acme Corp from the client table.",
#         },
#         # {
#         #     "type": "Neither source",
#         #     "question": "What is the population of Mars?",
#         # },
#     ]

#     results = []

#     for number, test_case in enumerate(test_cases, start=1):
#         print(f"\nRunning question {number}: {test_case['question']}")
#         result = run_question(test_case)
#         results.append(result)

#         print(f"Route: {result['route']}")
#         print(f"Validation: {result['validation']}")
#         print(f"Cost: ${result['usage']['cost']:.6f}")
#         print(f"Answer: {result['answer']}")

#     write_report(results)
#     print(f"\nReport written to: {REPORT_PATH.resolve()}")
