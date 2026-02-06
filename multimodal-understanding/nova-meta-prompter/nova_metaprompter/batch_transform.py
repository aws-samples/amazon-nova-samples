"""
Batch transform prompts to align with Amazon Nova guidelines.

Supports multiple input formats:
- JSON: Array of prompts or array of objects with 'prompt' field
- JSONL: One JSON object per line with 'prompt' field
- TXT: One prompt per line (or custom delimiter)

Usage:
    python -m nova_metaprompter.batch_transform input.json -o output.json
    python -m nova_metaprompter.batch_transform input.jsonl -o output.jsonl
    python -m nova_metaprompter.batch_transform input.txt -o output.json --delimiter "---"
"""

import argparse
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from nova_metaprompter.transform import (
    transform_prompt,
    transform_with_intent_classification,
)


def load_prompts(input_path: Path, delimiter: str | None = None) -> list[dict]:
    """Load prompts from various file formats.

    Returns list of dicts with at least 'prompt' key. Additional keys are preserved.
    """
    suffix = input_path.suffix.lower()
    content = input_path.read_text(encoding='utf-8')

    if suffix == '.json':
        data = json.loads(content)
        if isinstance(data, list):
            # Could be list of strings or list of objects
            prompts = []
            for i, item in enumerate(data):
                if isinstance(item, str):
                    prompts.append({'id': i, 'prompt': item})
                elif isinstance(item, dict) and 'prompt' in item:
                    if 'id' not in item:
                        item['id'] = i
                    prompts.append(item)
                else:
                    raise ValueError(f"Item {i} must be a string or object with 'prompt' field")
            return prompts
        else:
            raise ValueError("JSON file must contain an array")

    elif suffix == '.jsonl':
        prompts = []
        for i, line in enumerate(content.strip().split('\n')):
            if not line.strip():
                continue
            item = json.loads(line)
            if 'prompt' not in item:
                raise ValueError(f"Line {i+1} must have 'prompt' field")
            if 'id' not in item:
                item['id'] = i
            prompts.append(item)
        return prompts

    else:  # Plain text
        if delimiter:
            parts = content.split(delimiter)
        else:
            parts = content.strip().split('\n')

        prompts = []
        for i, part in enumerate(parts):
            text = part.strip()
            if text:
                prompts.append({'id': i, 'prompt': text})
        return prompts


def save_results(results: list[dict], output_path: Path):
    """Save results to file based on extension."""
    suffix = output_path.suffix.lower()

    if suffix == '.jsonl':
        with open(output_path, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
    else:  # Default to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)


def transform_single(item: dict, use_intent_classification: bool, model_id: str,
                     reasoning_mode: bool, tool_use: bool, image: bool, video: bool) -> dict:
    """Transform a single prompt and return result dict."""
    prompt = item['prompt']

    try:
        if use_intent_classification:
            result = transform_with_intent_classification(
                prompt,
                transform_model_id=model_id,
                reasoning_mode=reasoning_mode,
                tool_use=tool_use,
                image=image,
                video=video,
            )
        else:
            result = transform_prompt(
                prompt,
                model_id=model_id,
                reasoning_mode=reasoning_mode,
                tool_use=tool_use,
                image=image,
                video=video,
            )

        return {
            **item,
            'status': 'success',
            'result': result,
        }
    except Exception as e:
        return {
            **item,
            'status': 'error',
            'error': str(e),
        }


def main():
    parser = argparse.ArgumentParser(
        description='Batch transform prompts to align with Amazon Nova guidelines.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Transform prompts from JSON array
  python -m nova_metaprompter.batch_transform prompts.json -o results.json

  # Transform from JSONL with intent classification
  python -m nova_metaprompter.batch_transform prompts.jsonl -o results.jsonl --classify-intent

  # Transform from text file with custom delimiter
  python -m nova_metaprompter.batch_transform prompts.txt -o results.json --delimiter "---"

  # Run with parallel processing
  python -m nova_metaprompter.batch_transform prompts.json -o results.json --workers 4

Input formats:
  JSON:  [{"prompt": "...", "id": "optional"}, ...] or ["prompt1", "prompt2", ...]
  JSONL: {"prompt": "...", "id": "optional"}\\n{"prompt": "...", "id": "optional"}
  TXT:   One prompt per line (or use --delimiter for multi-line prompts)
        """
    )

    parser.add_argument('input', type=Path, help='Input file containing prompts')
    parser.add_argument('-o', '--output', type=Path, required=True,
                        help='Output file for results (.json or .jsonl)')
    parser.add_argument('--delimiter', type=str, default=None,
                        help='Delimiter for splitting text files (default: newline)')
    parser.add_argument('--model-id', type=str, default=None,
                        help='Model ID for transformation (default: us.amazon.nova-2-lite-v1:0)')
    parser.add_argument('--classify-intent', action='store_true',
                        help='Use intent classification to optimize guidance loading')
    parser.add_argument('--reasoning-mode', action='store_true',
                        help='Enable reasoning mode guidance')
    parser.add_argument('--tool-use', action='store_true',
                        help='Enable tool use guidance')
    parser.add_argument('--image', action='store_true',
                        help='Enable image understanding guidance')
    parser.add_argument('--video', action='store_true',
                        help='Enable video understanding guidance')
    parser.add_argument('--workers', type=int, default=1,
                        help='Number of parallel workers (default: 1)')

    args = parser.parse_args()

    # Validate input file exists
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Load prompts
    print(f"Loading prompts from {args.input}...")
    try:
        prompts = load_prompts(args.input, args.delimiter)
    except Exception as e:
        print(f"Error loading prompts: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(prompts)} prompts")

    # Transform prompts
    results = []

    if args.workers > 1:
        print(f"Processing with {args.workers} parallel workers...")
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    transform_single,
                    item,
                    args.classify_intent,
                    args.model_id,
                    args.reasoning_mode,
                    args.tool_use,
                    args.image,
                    args.video,
                ): item['id']
                for item in prompts
            }

            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                results.append(result)
                status = result['status']
                print(f"[{i}/{len(prompts)}] ID={result['id']}: {status}")
    else:
        print("Processing sequentially...")
        for i, item in enumerate(prompts, 1):
            print(f"[{i}/{len(prompts)}] Processing ID={item['id']}...")
            result = transform_single(
                item,
                args.classify_intent,
                args.model_id,
                args.reasoning_mode,
                args.tool_use,
                args.image,
                args.video,
            )
            results.append(result)
            print(f"  Status: {result['status']}")

    # Sort results by original order
    results.sort(key=lambda x: x['id'] if isinstance(x['id'], int) else 0)

    # Save results
    print(f"\nSaving results to {args.output}...")
    save_results(results, args.output)

    # Summary
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = len(results) - success_count
    print(f"\nComplete: {success_count} succeeded, {error_count} failed")

    if error_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
