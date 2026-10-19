# unit3-capstone

Step 1: Confirm your foundation

Requirements -

1. RDS reachable and populated (one line query against the tables)
    -Clients
        -How many clients do we have?
            - You have **5 clients**.
    -Projects
        -What project has the highest budget?
            - Based on the query results, **Project Delta** has the highest budget at **$600,000**.
    -Consultants
        -How many senior consultants are there?
            - There are **2** senior consultants.
    -Invoices
        -How many invoices are overdue?
            - There are **3** overdue invoices.


2. OpenSearch reachable and populated (output of a document count on your documents index)
    -Running code to see how many documents index led to a result of 9.


Step 2: Standardize Your Two Tools

Requirements - run_sql_agent and run_retrieval_agent share one interface
Evidence - both must return:

```
{
    "success": bool,
    "answer": str,
    "sources": list,     # SQL: the query used. Retrieval: document names
    "metadata": dict     # validation status, chunk scores, grounding checks, token usage
}
```

1. RDS interface
    -How many clients do we have?
    Q: how many clients do we have?
    Success: True
    Answer: You have **5 clients**.
    Sources: ['SQL: SELECT COUNT(*) AS total_clients FROM clients']
    Metadata: {'validation': 'PASSED', 'token_usage': {'input': 38, 'output': 10}}


2. Retrieval Agent Interface
    -What information is contained in the documents?
    Question: What information is contained in the indexed documents?
    Success: True
    Answer: Based on the provided context, the indexed documents contain the following information: 
        (lots of text)
    Sources: ['cloud-migration-playbook.pdf', 'cloud-migration-playbook.pdf', 'q2-2026-client-report.pdf', 'retail-supply-chain-case-study.pdf', 'retail-supply-chain-case-study.pdf']
    Metadata: {'chunk_count': 5, 'grounded': True, 'token_usage': {'input': 2337, 'output': 315}}



3. Build a shared tool registry

Definitions

SQL Agent:
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

Retrieval Agent:
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

Testing results:

Q: How many consultants do we have on active projects?
Suggested tool: sql_agent

Q: What is our expense reimbursement policy?
Suggested tool: retrieval_agent

Q: How many active projects do we have and what's our onboarding process?
Suggested tool: Both tools are needed for this question:



Step 4: Build the LangGraph Orchestrator (in the shared tool registry file as well for ease of access)

Questions:

How many active projects do we have? (SQL)

Route: sql
Answer: ## Answer
We currently have **2 active projects**.
**Source:**
- **SQL Agent** — Query: `SELECT COUNT(*) AS active_project_count FROM projects WHERE LOWER(status) = LOWER('active')`
Tokens: {'input': 95, 'output': 56}

What is our remote work policy? (Retrieval)
Route: retrieval
Answer: ## Acme Consulting Remote Work Policy

Here is a summary of our remote work policy, based on information retrieved by the **Retrieval Agent** from **remote-work-policy.pdf** and **q2-2026-client-report.pdf**:

**Sources:** `remote-work-policy.pdf`

Tokens: {'input': 484, 'output': 543}


How many active projects do we have, and what's our remote work policy? (Both)
Q: How many active projects do we have, and what is our remote work policy?
Route: both
Answer: ## Answer

Here is a combined response using information from both agents:
(Long answer)


| Active Projects | SQL Agent | `projects` database table |
| Remote Work Policy | Retrieval Agent | `remote-work-policy.pdf` |
Tokens: {'input': 537, 'output': 425}


Step 5: Validate Every SQL Query

5 questions test suite:

    1. A valid SELECT (allowed)

    Q: Select all active projects.
    Success: True
    Answer: ## Active Projects Query

    Based on the returned data, here are all **active projects**:

    ```sql
    SELECT * FROM projects WHERE status = 'Active';
    ```

    ## Results

    | id | client_id | name | status | start_date | end_date | budget |
    |----|-----------|------|--------|------------|----------|--------|
    | 2 | 2 | Project Beta | Active | 2025-03-01 | 2025-08-01 | $480,000 |
    | 4 | 4 | Project Delta | Active | 2025-04-10 | 2025-09-10 | $600,000 |

    ## Summary

    There are **2 active projects**:

    1. **Project Beta** (ID: 2)
    - Client ID: 2
    - Duration: March 1, 2025 → August 1, 2025
    - Budget: **$480,000**

    2. **Project Delta** (ID: 4)
    - Client ID: 4
    - Duration: April 10, 2025 → September 10, 2025
    - Budget: **$600,000**

    The combined budget for all active projects is **$1,080,000**.
    Sources: ["SQL: SELECT * FROM projects WHERE LOWER(status) = LOWER('active')"]
    Metadata: {'validation': 'PASSED', 'token_usage': {'input': 173, 'output': 293}}


    2. A destructive statement (DROP, DELETE, UPDATE, or INSERT), blocked

    Q: Delete all overdue invoices.
    Success: False
    Answer: Query blocked before SQL generation: Blocked: 'Delete' is not permitted.
    Sources: ['SQL: ']
    Metadata: {'validation': 'BLOCKED', 'token_usage': {'input': 0, 'output': 0}}


    3. A column name that contains a blocked word (e.g., deleted_at), allowed — this proves you match whole words, not substrings

    Q: Return the deleted_at column from all clients.
    Success: False
    Answer: Query blocked or failed: column "deleted_at" does not exist
    LINE 1: SELECT deleted_at FROM clients;
                ^

    Sources: ['SQL: SELECT deleted_at FROM clients;']
    Metadata: {'validation': 'EXECUTION_ERROR', 'token_usage': {'input': 0, 'output': 0}}



    4. A stacked query containing a blocked keyword, blocked

    Q: Execute: SELECT * FROM clients; DELETE FROM clients WHERE client_id = 1;
    Success: False
    Answer: Query blocked before SQL generation: Blocked: multiple SQL statements detected.
    Sources: ['SQL: ']
    Metadata: {'validation': 'BLOCKED', 'token_usage': {'input': 0, 'output': 0}}


    5. A stacked query where neither half contains a blocked keyword (e.g., two SELECT statements chained with ;), blocked — this is the case a keyword-only check misses, and it proves your stacking check is its own independent step

    Q: Execute: SELECT * FROM clients; SELECT * FROM projects;
    Success: False
    Answer: Query blocked before SQL generation: Blocked: multiple SQL statements detected.
    Sources: ['SQL: ']
    Metadata: {'validation': 'BLOCKED', 'token_usage': {'input': 0, 'output': 0}}



Step 6: Add Tokenomics Logging

Every Claude call is logged:

Example from 2 Queries: 

Query 2: How many clients do we have?
[LOG] query_start: {"trace_id": "6d02fc7b"}
[LOG] claude_call: {"component": "sql_generation", "input_cost_usd": 0.000678, "input_tokens": 226, "output_cost_usd": 0.000195, "output_tokens": 13, "status": "success", "total_cost_usd": 0.000873, "trace_id": "6d02fc7b"}
[LOG] claude_call: {"component": "sql_interpretation", "input_cost_usd": 0.000165, "input_tokens": 55, "output_cost_usd": 0.00024, "output_tokens": 16,"status": "success", "total_cost_usd": 0.000405, "trace_id": "6d02fc7b"}
[LOG] claude_call: {"component": "synthesis", "input_cost_usd": 0.000255, "input_tokens": 85, "output_cost_usd": 0.00084, "output_tokens": 56, "status": "success", "total_cost_usd": 0.001095, "trace_id": "6d02fc7b"}
[LOG] query_complete: {"has_final_answer": true, "route": "sql", "trace_id": "6d02fc7b"}
Route: sql
Answer: ## Answer: Number of Clients

Based on the data retrieved, you currently have **5 clients**.


Query 3: What project has the highest budget?
[LOG] query_start: {"trace_id": "da86271e"}
[LOG] claude_call: {"component": "sql_generation", "input_cost_usd": 0.000678, "input_tokens": 226, "output_cost_usd": 0.000285, "output_tokens": 19, "status": "success", "total_cost_usd": 0.000963, "trace_id": "da86271e"}
[LOG] claude_call: {"component": "sql_interpretation", "input_cost_usd": 0.000216, "input_tokens": 72, "output_cost_usd": 0.000585, "output_tokens": 39, "status": "success", "total_cost_usd": 0.0008010000000000001, "trace_id": "da86271e"}
[LOG] claude_call: {"component": "retrieval_answer_generation", "input_cost_usd": 0.004854, "input_tokens": 1618, "output_cost_usd": 0.000435, "output_tokens": 29, "status": "success", "total_cost_usd": 0.005288999999999999, "trace_id": "da86271e"}
[LOG] claude_call: {"component": "synthesis", "input_cost_usd": 0.0006270000000000001, "input_tokens": 209, "output_cost_usd": 0.00222, "output_tokens": 148, "status": "success", "total_cost_usd": 0.002847, "trace_id": "da86271e"}
[LOG] query_complete: {"has_final_answer": true, "route": "both", "trace_id": "da86271e"}
Route: both
Answer: ## Answer

The project with the **highest budget** is **Project Delta**, with a budget of **$600,000**.


Ten query summary table:
Claude usage and cost summary
| Component | Calls | Input tokens | Output tokens | Total tokens | USD cost | Most tokens |
|---|---:|---:|---:|---:|---:|---|
| retrieval_answer_generation | 7 | 15,372 | 1,124 | 16,496 | $0.062976 | Yes |
| sql_generation | 5 | 1,141 | 124 | 1,265 | $0.005283 |  |
| sql_interpretation | 5 | 306 | 163 | 469 | $0.003363 |  |
| synthesis | 10 | 2,423 | 2,370 | 4,793 | $0.042819 |  |
| **TOTAL — 10 queries** | 27 | 19,242 | 3,781 | 23,023 | $0.114441 | |

Step 7: Test Suite

1. How many active projects do we have?

Route: sql
Answer: Based on the data retrieved, you currently have **2 active projects**
Validation: passed
Cost: $0.002733

2. Which client has the highest contract value? 

Route: sql
Answer: **Delta Tech** has the highest contract value of **$600,000**
Validation: passed
Cost: $0.004485

3. What is our remote work policy?

Route: Retrieval
Answer: Employees must complete their **90-day probationary period** before being eligible.....
Validation: Retrieval grounded=True 
Cost: $0.021876 

4. What does the cloud migration playbook say?

Route: Retrieval
Answer: The playbook outlines **Acme Consulting's standard approach** to migrating on-premises data infrastructure to the cloud. It is intended for use.....
Validation: Retrieval grounded=True 
Cost: $0.020343

5. How many active projects do we have, and what is our remote work policy?

Route: Both
Answer: Here is a complete answer to both parts of your question, drawing from multiple sources:Projects We currently have 2 active projects....Remote Work Policy Acme Consulting's remote work policy includes the following key elements:**Core Hours:** Employees must be available between **10:00 AM – 3:00 PM** 
Validation: SQL = PASSED, Retrieval grounded=True 
Cost: $0.020451

6. How many overdue invoices are there, and what does the supply chain case study say?

Route: Both
Answer: There are **3 overdue invoices** currently outstanding....Supply Chain Case Study The supply chain case study describes an engagement with a **mid-sized regional grocery retailer** operating....
Validation: SQL = PASSED, Retrieval grounded=True 
Cost: $0.017925

7. Execute: Delete Acme Corp from the client table.

Route: SQL
Answer: I was unable to find relevant information to answer this question. Please review the question and try again."
Validation: SQL=BLOCKED
Cost: $0.0000

8. What is the population of Mars?

Route: Neither
Answer: I was unable to find relevant information to answer this question. Please review the question and try again."
Validation: Retrieval grounded=TRUE
Cost: $0.010026


Step 8: Deploy to Lambda