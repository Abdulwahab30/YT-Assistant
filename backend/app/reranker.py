from sentence_transformers import CrossEncoder


RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Loaded once when app starts
reranker_model = CrossEncoder(RERANKER_MODEL_NAME)


def rerank_chunks(
    question: str,
    chunks: list[dict],
    top_n: int = 5
) -> list[dict]:
    """
    Reranks retrieved chunks using a cross-encoder model.

    Input:
    - question
    - chunks from vector search

    Output:
    - chunks sorted by reranker relevance score
    """

    if not chunks:
        return []

    pairs = []

    for chunk in chunks:
        pairs.append((question, chunk["text"]))

    scores = reranker_model.predict(pairs)

    reranked = []

    for chunk, score in zip(chunks, scores):
        new_chunk = dict(chunk)
        new_chunk["rerank_score"] = float(score)
        reranked.append(new_chunk)

    reranked.sort(
        key=lambda item: item["rerank_score"],
        reverse=True
    )

    return reranked[:top_n]