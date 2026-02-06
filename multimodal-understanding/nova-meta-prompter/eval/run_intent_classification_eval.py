"""
Intent Classification Evaluation Script

Runs the intent classifier against ground truth data and measures accuracy.
"""

import json
import os
from datetime import datetime
from collections import defaultdict
from nova_metaprompter import classify_intent, VALID_INTENTS


def load_ground_truth(filepath):
    """Load ground truth data from JSONL file."""
    examples = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))
    return examples


def calculate_metrics(y_true, y_pred):
    """Calculate precision, recall, and F1 for multi-label classification.

    Args:
        y_true: Set of true labels
        y_pred: Set of predicted labels

    Returns:
        dict with precision, recall, f1
    """
    if len(y_pred) == 0 and len(y_true) == 0:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    if len(y_pred) == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    if len(y_true) == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    true_positives = len(y_true & y_pred)
    precision = true_positives / len(y_pred) if len(y_pred) > 0 else 0.0
    recall = true_positives / len(y_true) if len(y_true) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1}


def run_evaluation(ground_truth_path, model_id=None, verbose=True):
    """Run evaluation against ground truth.

    Args:
        ground_truth_path: Path to ground truth JSONL file
        model_id: Optional model ID for classification
        verbose: Print progress and details

    Returns:
        dict with evaluation results
    """
    examples = load_ground_truth(ground_truth_path)

    results = []
    exact_matches = 0
    total_precision = 0.0
    total_recall = 0.0
    total_f1 = 0.0

    # Per-intent tracking
    intent_true_positives = defaultdict(int)
    intent_false_positives = defaultdict(int)
    intent_false_negatives = defaultdict(int)

    if verbose:
        print(f"Running evaluation on {len(examples)} examples...")
        print(f"Model: {model_id or 'default (nova-micro)'}")
        print("-" * 80)

    for i, example in enumerate(examples):
        prompt = example["prompt"]
        expected = set(example["intents"])

        # Run classification
        try:
            result = classify_intent(prompt, model_id=model_id)
            predicted = set(result.get("intents", []))
            reasoning = result.get("reasoning", "")
            error = None
        except Exception as e:
            predicted = set()
            reasoning = ""
            error = str(e)

        # Calculate metrics for this example
        metrics = calculate_metrics(expected, predicted)
        is_exact_match = expected == predicted

        if is_exact_match:
            exact_matches += 1

        total_precision += metrics["precision"]
        total_recall += metrics["recall"]
        total_f1 += metrics["f1"]

        # Per-intent tracking
        for intent in expected & predicted:
            intent_true_positives[intent] += 1
        for intent in predicted - expected:
            intent_false_positives[intent] += 1
        for intent in expected - predicted:
            intent_false_negatives[intent] += 1

        result_entry = {
            "index": i,
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "expected": sorted(list(expected)),
            "predicted": sorted(list(predicted)),
            "exact_match": is_exact_match,
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "reasoning": reasoning,
            "error": error
        }
        results.append(result_entry)

        if verbose:
            status = "✓" if is_exact_match else "✗"
            print(f"[{i+1:3d}/{len(examples)}] {status} Expected: {sorted(list(expected))}")
            print(f"              Predicted: {sorted(list(predicted))}")
            if not is_exact_match:
                missing = expected - predicted
                extra = predicted - expected
                if missing:
                    print(f"              Missing: {sorted(list(missing))}")
                if extra:
                    print(f"              Extra: {sorted(list(extra))}")
            print()

    # Calculate aggregate metrics
    n = len(examples)
    aggregate = {
        "total_examples": n,
        "exact_match_accuracy": exact_matches / n if n > 0 else 0.0,
        "exact_matches": exact_matches,
        "macro_precision": total_precision / n if n > 0 else 0.0,
        "macro_recall": total_recall / n if n > 0 else 0.0,
        "macro_f1": total_f1 / n if n > 0 else 0.0,
    }

    # Per-intent metrics
    per_intent_metrics = {}
    all_intents = set(VALID_INTENTS) | set(intent_true_positives.keys()) | set(intent_false_positives.keys()) | set(intent_false_negatives.keys())

    for intent in sorted(all_intents):
        tp = intent_true_positives[intent]
        fp = intent_false_positives[intent]
        fn = intent_false_negatives[intent]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_intent_metrics[intent] = {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1
        }

    return {
        "aggregate": aggregate,
        "per_intent": per_intent_metrics,
        "results": results
    }


def print_summary(eval_results):
    """Print a summary of evaluation results."""
    agg = eval_results["aggregate"]
    per_intent = eval_results["per_intent"]

    print("=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Total Examples:      {agg['total_examples']}")
    print(f"Exact Matches:       {agg['exact_matches']} ({agg['exact_match_accuracy']:.1%})")
    print(f"Macro Precision:     {agg['macro_precision']:.3f}")
    print(f"Macro Recall:        {agg['macro_recall']:.3f}")
    print(f"Macro F1:            {agg['macro_f1']:.3f}")

    print("\n" + "-" * 80)
    print("PER-INTENT METRICS")
    print("-" * 80)
    print(f"{'Intent':<25} {'Prec':>8} {'Recall':>8} {'F1':>8} {'TP':>6} {'FP':>6} {'FN':>6}")
    print("-" * 80)

    for intent in sorted(per_intent.keys()):
        m = per_intent[intent]
        print(f"{intent:<25} {m['precision']:>8.3f} {m['recall']:>8.3f} {m['f1']:>8.3f} "
              f"{m['true_positives']:>6} {m['false_positives']:>6} {m['false_negatives']:>6}")

    print("=" * 80)


def save_results(eval_results, output_path):
    """Save evaluation results to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(eval_results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run intent classification evaluation")
    parser.add_argument(
        "--ground-truth",
        default=os.path.join(os.path.dirname(__file__), "intent_classification_ground_truth.jsonl"),
        help="Path to ground truth JSONL file"
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help="Model ID for classification (default: nova-micro)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path for results JSON (default: auto-generated with timestamp)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )

    args = parser.parse_args()
    print(args.model_id)
    # Run evaluation
    eval_results = run_evaluation(
        args.ground_truth,
        model_id=args.model_id,
        verbose=not args.quiet
    )

    # Print summary
    print_summary(eval_results)

    # Save results
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            os.path.dirname(__file__),
            f"intent_classification_results_{timestamp}.json"
        )

    save_results(eval_results, output_path)

    return eval_results


if __name__ == "__main__":
    main()
