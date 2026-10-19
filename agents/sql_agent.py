import os
import re
import psycopg2
from dotenv import load_dotenv
from tokenomics_logger import invoke_claude_logged
load_dotenv()

SCHEMA_CONTEXT = """
Tables available:
- clients(id, name, industry, region, contract_value, created_date)
- projects(id, client_id, name, status, start_date, end_date, budget)
- consultants(id, name, grade, specialisation, project_id, billable_hours)
- invoices(id, project_id, amount, status, due_date, paid_date)

All monetary values are in USD. Dates are in ISO 8601 format.
status in projects is one of: 'active', 'completed', 'on-hold'.
"""

BLOCKED_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
                    "EXEC", "EXECUTE", "GRANT", "REVOKE"]


def generate_sql(question: str) -> str:
    prompt = (
        f"{SCHEMA_CONTEXT}\n\n"
        f"Generate a SQL query to answer: {question}\n\n"
        "Return ONLY the SQL query. No explanation, no markdown, no backticks."
        "Use case-insensitive matching for all text comparisons. "
        "For example, use LOWER(status) = LOWER('Active') "
        "instead of status = 'Active'. "
        "Do not assume that capitalization in the question matches the database."
    )
    result = invoke_claude_logged("sql_generation", prompt, max_tokens=512)
    sql = result["text"].strip()
    return sql.removeprefix("```sql").removeprefix("```").removesuffix("```").strip()


SQL_COMMANDS = {"SELECT"} | set(BLOCKED_KEYWORDS)

SQL_COMMAND_RE = re.compile(
    r"\b(?:" + "|".join(map(re.escape, sorted(SQL_COMMANDS))) + r")\b",
    re.IGNORECASE,
)

BLOCKED_WORD_RE = re.compile(
    r"\b(?:" + "|".join(map(re.escape, sorted(BLOCKED_KEYWORDS))) + r")\b",
    re.IGNORECASE,
)



def validate_sql(query: str) -> dict:
    query = query.strip()

    if not query:
        return {"valid": False, "reason": "Blocked: empty SQL query."}

    if ";" in query.rstrip(";"):
        return {
            "valid": False,
            "reason": "Blocked: multiple statements detected.",
        }

    if not re.match(r"^\s*SELECT\b", query, re.IGNORECASE):
        return {
            "valid": False,
            "reason": "Only SELECT queries are permitted.",
        }

    blocked_match = BLOCKED_WORD_RE.search(query)

    if blocked_match:
        return {
            "valid": False,
            "reason": (
                f"Blocked: '{blocked_match.group(0)}' "
                "is not permitted."
            ),
        }

    return {"valid": True, "reason": "OK"}

##block innappropriate SQL commands and keywords before generation, this will save tokens and prevent the model 
# from generating SQL that will be blocked anyway.

def validate_requested_sql(question: str) -> dict:
    """Reject explicit destructive or stacked SQL before generation."""
    question = question.strip()

    has_sql_command = SQL_COMMAND_RE.search(question)
    has_multiple_statements = ";" in question.rstrip(";")
    blocked_match = BLOCKED_WORD_RE.search(question)

    if has_multiple_statements and has_sql_command:
        return {
            "valid": False,
            "reason": "Blocked: multiple SQL statements detected.",
        }

    if blocked_match and has_sql_command:
        return {
            "valid": False,
            "reason": (
                f"Blocked: '{blocked_match.group(0)}' "
                "is not permitted."
            ),
        }

    return {"valid": True, "reason": "OK"}


def execute_query_safely(sql: str) -> dict:
    validation = validate_sql(sql)

    if not validation["valid"]:
        return {
            "success": False,
            "error": validation["reason"],
            "validation": "BLOCKED",
            "sql": sql,
        }

    conn = None

    try:
        conn = psycopg2.connect(
            host=os.getenv("RDS_HOST"),
            port=int(os.getenv("RDS_PORT")),
            dbname=os.getenv("RDS_DATABASE"),
            user=os.getenv("RDS_USER"),
            password=os.getenv("RDS_PASSWORD"),
        )

        conn.set_session(readonly=True, autocommit=False)

        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [description[0] for description in cur.description]

        conn.rollback()

        return {
            "success": True,
            "columns": cols,
            "rows": rows,
            "validation": "PASSED",
            "sql": sql,
        }

    except Exception as error:
        if conn is not None:
            conn.rollback()

        return {
            "success": False,
            "error": str(error),
            "validation": "EXECUTION_ERROR",
            "sql": sql,
        }

    finally:
        if conn is not None:
            conn.close()


def validated_sql_agent(question: str) -> dict:
    request_validation = validate_requested_sql(question)

    if not request_validation["valid"]:
        return {
            "answer": (
                f"Query blocked before SQL generation: "
                f"{request_validation['reason']}"
            ),
            "sql": "",
            "validation": "BLOCKED",
            "token_usage": {"input": 0, "output": 0},
        }

    sql = generate_sql(question)
    result = execute_query_safely(sql)

    if not result["success"]:
        return {
            "answer": f"Query blocked or failed: {result['error']}",
            "sql": sql,
            "validation": result["validation"],
            "token_usage": {"input": 0, "output": 0},
        }

    prompt = (
        f"Question: {question}\n"
        f"Columns: {result['columns']}\n"
        f"Data: {result['rows'][:20]}\n\n"
        "Answer using only the returned SELECT data. "
        "Do not claim that any rows were inserted, updated, or deleted."
    )

    interpretation = invoke_claude_logged("sql_interpretation", prompt, max_tokens=500)

    return {
        "answer": interpretation["text"],
        "sql": sql,
        "validation": result["validation"],
        "token_usage": {
            "input": interpretation["input_tokens"],
            "output": interpretation["output_tokens"],
        },
    }


def run_sql_agent(question: str) -> dict:
    result = validated_sql_agent(question)
    return {
        "success": result["validation"] == "PASSED",
        "answer": result["answer"],
        "sources": [f"SQL: {result['sql']}"],
        "metadata": {"validation": result["validation"], "token_usage": result["token_usage"]},
    }

##Question testing

# if __name__ == "__main__":
#     test_questions = [
#         "how many clients do we have?",
#         "What project has the highest budget?",
#         "how many senior consultants are there?",
#         "how many invoices are overdue?",
#     ]

#     for question in test_questions:
#         result = run_sql_agent(question)

#         print(f"\nQ: {question}")
#         print(f"Success: {result['success']}")
#         print(f"Answer: {result['answer']}")
#         print(f"Sources: {result['sources']}")
#         print(f"Metadata: {result['metadata']}")


##testing questions with blocked SQL commands and keywords
# if __name__ == "__main__":
#     test_questions = [
#         # 1. Valid SELECT — allowed
#         "Select all active projects.",

#         # 2. Destructive statement — blocked
#         "Delete all overdue invoices.",

#         # 3. Blocked word inside column name — allowed
#         "Return the deleted_at column from all clients.",

#         # 4. Stacked query containing a blocked keyword — blocked
#         "Execute: SELECT * FROM clients; DELETE FROM clients WHERE client_id = 1;",

#         # 5. Stacked query with two SELECT statements — blocked
#         "Execute: SELECT * FROM clients; SELECT * FROM projects;",
#     ]

#     for question in test_questions:
#         result = run_sql_agent(question)

#         print(f"\nQ: {question}")
#         print(f"Success: {result['success']}")
#         print(f"Answer: {result['answer']}")
#         print(f"Sources: {result['sources']}")
#         print(f"Metadata: {result['metadata']}")

