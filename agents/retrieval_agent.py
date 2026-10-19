"""
Retrieval agent solution — same underlying logic as
building-the-orchestrator-main/agents/retrieval_agent.py, wrapped in the
retrieval_agent()/check_grounding() interface that
shared-tool-registry-lab-solution's run_retrieval_agent() expects, per its
own import: `from retrieval_agent_solution import retrieval_agent, check_grounding`.
"""
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from sentence_transformers import SentenceTransformer
from bedrock_client import invoke_claude
from document_ingestion import INDEX_NAME

HOST = "search-vector-search-lesson-r63wtcf7rc5qmhrjnlrljpkf7y.us-east-1.es.amazonaws.com"
REGION = "us-east-1"

_embed_model = None


def get_embedding(text: str) -> list[float]:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model.encode(text).tolist()


def get_opensearch_client():
    credentials = boto3.Session().get_credentials()
    auth = AWS4Auth(credentials.access_key, credentials.secret_key,
                     REGION, "es", session_token=credentials.token)
    return OpenSearch(
        hosts=[{"host": HOST, "port": 443}],
        http_auth=auth, use_ssl=True, verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def retrieve(question: str, top_k: int = 5) -> list[dict]:
    query_vector = get_embedding(question)
    client = get_opensearch_client()
    response = client.search(
        index=INDEX_NAME,
        body={"size": top_k, "query": {"knn": {"embedding": {"vector": query_vector, "k": top_k}}}}
    )
    return [
        {"content": hit["_source"]["content"], "source": hit["_source"]["source"], "score": hit["_score"]}
        for hit in response["hits"]["hits"]
    ]


def generate_cited_answer(question: str, chunks: list[dict]) -> tuple[str, dict]:
    context = "\n\n".join([f"[Source {i+1}: {c['source']}]\n{c['content']}" for i, c in enumerate(chunks)])
    prompt = (
        "Answer the question using ONLY the context provided below. "
        "If the answer is not in the context, say 'I cannot find this information in the provided documents.' "
        "Always cite the source number(s) you used.\n\n"
        f"CONTEXT:\n{context}\n\nQUESTION: {question}\n\nANSWER:"
    )
    result = invoke_claude(prompt, max_tokens=500)
    return result["text"], {"input": result["input_tokens"], "output": result["output_tokens"]}


def check_grounding(answer: str, chunks: list[dict]) -> bool:
    import re
    cited_sources = re.findall(r"Source (\d+)", answer)
    if not cited_sources:
        return "cannot find" in answer.lower()
    return all(1 <= int(s) <= len(chunks) for s in cited_sources)



def run_retrieval_agent(question: str) -> dict:
    chunks = retrieve(question)
    if not chunks:
        return {
            "success": False,
            "answer": "No relevant documents found.",
            "sources": [],
            "metadata": {"chunk_count": 0, "grounded": False, "token_usage": {"input": 0, "output": 0}},
        }

    answer, usage = generate_cited_answer(question, chunks)
    return {
        "success": True,
        "answer": answer,
        "sources": [c["source"] for c in chunks],
        "metadata": {
            "chunk_count": len(chunks),
            "grounded": check_grounding(answer, chunks),
            "token_usage": usage,
        },
    }







##test question - output of a document count on your documents index
##this is indexing correctly.
# def count_indexed_documents() -> int:
#     """Return the number of documents currently indexed in OpenSearch."""
#     client = get_opensearch_client()
#     response = client.count(index=INDEX_NAME)
#     return response["count"]


# if __name__ == "__main__":
#     try:
#         document_count = count_indexed_documents()
#         print(f"Documents indexed in '{INDEX_NAME}': {document_count}")

#     except KeyError:
#         print(
#             "OPENSEARCH_DOMAIN is not set. "
#             "Set it before running this test."
#         )

#     except Exception as error:
#         print(f"Unable to count documents in '{INDEX_NAME}': {error}")

##test question
# making sure it fits the format of run_sql_agent

if __name__ == "__main__":
    test_questions = [
        "What information is contained in the indexed documents?",
        "What is our remote work policy?",
    ]

    for question in test_questions:
        result = run_retrieval_agent(question)

        print(f"\nQuestion: {question}")
        print(f"Success: {result['success']}")
        print(f"Answer: {result['answer']}")
        print(f"Sources: {result['sources']}")
        print(f"Metadata: {result['metadata']}")



