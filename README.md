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

