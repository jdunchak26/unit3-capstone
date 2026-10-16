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