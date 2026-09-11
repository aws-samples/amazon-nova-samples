import json
import re
from difflib import SequenceMatcher

def normalize_text(text):
    """Normalize text for ANLS calculation."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def anls_score(prediction, ground_truth, threshold=0.5):
    """Calculate ANLS (Average Normalized Levenshtein Similarity) score."""
    pred_norm = normalize_text(prediction)
    gt_norm = normalize_text(ground_truth)
    
    if len(gt_norm) == 0:
        return 1.0 if len(pred_norm) == 0 else 0.0
    
    similarity = SequenceMatcher(None, pred_norm, gt_norm).ratio()
    
    if similarity < threshold:
        return 0.0
    else:
        return similarity

def calculate_anls_from_file(results_file):
    """Calculate ANLS metric from results file."""
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    predictions = [r['model_response'] for r in results if 'model_response' in r]
    ground_truths = [r['expected'] for r in results if 'expected' in r]
    
    scores = []
    for pred, gt in zip(predictions, ground_truths):
        score = anls_score(pred, gt)
        scores.append(score)
    
    anls_star = sum(scores) / len(scores) if scores else 0.0
    
    print(f"ANLS* Score: {anls_star:.4f}")
    print(f"Total samples: {len(predictions)}")
    
    # Save ANLS score
    with open('anls_results.txt', 'w') as f:
        f.write(f"ANLS* Score: {anls_star:.4f}\n")
        f.write(f"Total samples: {len(predictions)}\n")
    
    return anls_star