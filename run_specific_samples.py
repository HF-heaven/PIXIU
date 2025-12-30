#!/usr/bin/env python3
"""
Run PIXIU evaluation on specific samples that match Harbor's generated tasks.

This script allows running specific samples by their IDs, matching the samples
generated in Harbor's datasets/pixiu directory.
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "src" / "financial-evaluation"))

from evaluator import simple_evaluate
from tasks import flare
import tasks as ta


def get_harbor_sample_ids(dataset_name: str, harbor_datasets_path: Path) -> list[str]:
    """Extract sample IDs from Harbor's generated tasks."""
    # Map dataset names
    dataset_map = {
        "en-fpb": "flare-fpb",
        "flare-fpb": "flare-fpb",
        "TheFinAI/en-fpb": "flare-fpb",
        "TheFinAI/flare-fpb": "flare-fpb",
    }
    
    # Find the short name
    short_name = None
    for key, value in dataset_map.items():
        if key in dataset_name.lower():
            short_name = value
            break
    
    if not short_name:
        # Try to infer from path
        if "fpb" in dataset_name.lower():
            short_name = "flare-fpb"
        else:
            raise ValueError(f"Unknown dataset: {dataset_name}")
    
    # Find the dataset directory
    dataset_dir = None
    for possible_name in ["en-fpb", "flare-fpb"]:
        possible_dir = harbor_datasets_path / possible_name
        if possible_dir.exists():
            dataset_dir = possible_dir
            break
    
    if not dataset_dir:
        raise ValueError(f"Dataset directory not found for {dataset_name} in {harbor_datasets_path}")
    
    # Extract sample IDs
    sample_ids = []
    for task_dir in dataset_dir.iterdir():
        if task_dir.is_dir():
            # Try different prefix patterns
            prefixes = [
                f"pixiu-{short_name}-",
                f"pixiu-{short_name.replace('flare-', '')}-",  # e.g., pixiu-fpb-
            ]
            for prefix in prefixes:
                if task_dir.name.startswith(prefix):
                    sample_id = task_dir.name.replace(prefix, "")
                    sample_ids.append(sample_id)
                    break
    
    return sorted(sample_ids)


def create_filtered_task(task_class, sample_ids: list[str]):
    """Create a filtered version of a task that only includes specific sample IDs."""
    
    class FilteredTask(task_class):
        def test_docs(self):
            """Filter test docs to only include specified sample IDs."""
            all_docs = super().test_docs()
            filtered = [doc for doc in all_docs if doc.get("id") in sample_ids]
            return filtered
    
    # Copy class attributes
    FilteredTask.__name__ = f"Filtered{task_class.__name__}"
    FilteredTask.DATASET_PATH = task_class.DATASET_PATH
    if hasattr(task_class, "DATASET_NAME"):
        FilteredTask.DATASET_NAME = task_class.DATASET_NAME
    
    return FilteredTask


def main():
    parser = argparse.ArgumentParser(description="Run PIXIU evaluation on specific Harbor samples")
    parser.add_argument(
        "--dataset",
        type=str,
        default="en-fpb",
        help="Dataset name (e.g., en-fpb, flare-fpb)",
    )
    parser.add_argument(
        "--harbor-datasets-path",
        type=Path,
        default=Path("/home/hefan/harbor/datasets/pixiu"),
        help="Path to Harbor's datasets/pixiu directory",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="codex",
        help="Model type (codex, gpt-*, or other lm_eval model names)",
    )
    parser.add_argument(
        "--model-args",
        type=str,
        default="",
        help="Model arguments (e.g., 'model=gpt-5-mini')",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default=None,
        help="Output path for results JSON",
    )
    parser.add_argument(
        "--output-base-path",
        type=str,
        default=None,
        help="Base path for detailed outputs",
    )
    parser.add_argument(
        "--write-out",
        action="store_true",
        help="Write detailed outputs",
    )
    
    args = parser.parse_args()
    
    # Get sample IDs from Harbor
    print(f"Extracting sample IDs from {args.harbor_datasets_path}...")
    try:
        sample_ids = get_harbor_sample_ids(args.dataset, args.harbor_datasets_path)
        print(f"Found {len(sample_ids)} samples: {sample_ids[:5]}... (showing first 5)")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get the task class
    task_name_map = {
        "en-fpb": "flare_fpb",
        "flare-fpb": "flare_fpb",
    }
    
    task_name = task_name_map.get(args.dataset.lower(), args.dataset.lower())
    
    # Get task from registry
    if hasattr(ta, "TASK_REGISTRY"):
        if task_name not in ta.TASK_REGISTRY:
            print(f"Error: Task '{task_name}' not found in TASK_REGISTRY", file=sys.stderr)
            print(f"Available tasks: {list(ta.TASK_REGISTRY.keys())[:10]}...", file=sys.stderr)
            sys.exit(1)
        
        original_task_class = ta.TASK_REGISTRY[task_name]
    else:
        # Fallback: try to get from flare module
        if hasattr(flare, "FPB"):
            original_task_class = flare.FPB
        else:
            print(f"Error: Could not find task class for {args.dataset}", file=sys.stderr)
            sys.exit(1)
    
    # Create filtered task
    filtered_task_class = create_filtered_task(original_task_class, sample_ids)
    filtered_task = filtered_task_class()
    
    print(f"Running evaluation on {len(sample_ids)} samples...")
    print(f"Model: {args.model}")
    if args.model_args:
        print(f"Model args: {args.model_args}")
    
    # Prepare model args
    model_args_str = args.model_args
    
    # Run evaluation
    results = simple_evaluate(
        model=args.model,
        model_args=model_args_str if model_args_str else None,
        tasks=[filtered_task],
        num_fewshot=0,
        limit=None,  # We filter in test_docs, so no need for limit
        write_out=args.write_out,
        output_base_path=args.output_base_path,
    )
    
    # Save results
    if args.output_path:
        import json
        output_path = Path(args.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to {args.output_path}")
    else:
        import json
        print("\nResults:")
        print(json.dumps(results, indent=2))
    
    return results


if __name__ == "__main__":
    main()

