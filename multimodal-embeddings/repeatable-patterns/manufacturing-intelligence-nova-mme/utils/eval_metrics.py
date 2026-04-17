"""Retrieval evaluation metrics for the hackathon."""

import numpy as np


def recall_at_k(retrieved_ids, relevant_ids, k=None):
    """Fraction of relevant documents that appear in the top-K retrieved results."""
    if k is not None:
        retrieved_ids = retrieved_ids[:k]
    if not relevant_ids:
        return 0.0
    return len(set(retrieved_ids) & set(relevant_ids)) / len(set(relevant_ids))


def precision_at_k(retrieved_ids, relevant_ids, k=None):
    """Fraction of top-K retrieved results that are relevant."""
    if k is not None:
        retrieved_ids = retrieved_ids[:k]
    if not retrieved_ids:
        return 0.0
    return len(set(retrieved_ids) & set(relevant_ids)) / len(retrieved_ids)


def mrr(retrieved_ids, relevant_ids):
    """Mean Reciprocal Rank — 1/rank of the first relevant result."""
    relevant_set = set(relevant_ids)
    for i, doc_id in enumerate(retrieved_ids):
        if doc_id in relevant_set:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(retrieved_ids, relevant_ids, k=None):
    """Normalized Discounted Cumulative Gain at K."""
    if k is not None:
        retrieved_ids = retrieved_ids[:k]
    relevant_set = set(relevant_ids)

    # DCG
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids):
        if doc_id in relevant_set:
            dcg += 1.0 / np.log2(i + 2)  # i+2 because rank starts at 1, log2(1)=0

    # Ideal DCG
    ideal_length = min(len(relevant_ids), len(retrieved_ids))
    idcg = sum(1.0 / np.log2(i + 2) for i in range(ideal_length))

    if idcg == 0:
        return 0.0
    return dcg / idcg


def evaluate_query(retrieved_ids, relevant_ids, k_values=(3, 5, 10)):
    """Run all retrieval metrics for a single query at multiple K values.

    Returns a dict of metric names to values.
    """
    results = {"mrr": mrr(retrieved_ids, relevant_ids)}
    for k in k_values:
        results[f"recall@{k}"] = recall_at_k(retrieved_ids, relevant_ids, k)
        results[f"precision@{k}"] = precision_at_k(retrieved_ids, relevant_ids, k)
        results[f"ndcg@{k}"] = ndcg_at_k(retrieved_ids, relevant_ids, k)
    return results


def evaluate_dataset(eval_results):
    """Aggregate per-query metrics into dataset-level averages.

    eval_results: list of dicts from evaluate_query().
    Returns a dict of averaged metrics.
    """
    if not eval_results:
        return {}
    keys = eval_results[0].keys()
    return {key: np.mean([r[key] for r in eval_results]) for key in keys}
