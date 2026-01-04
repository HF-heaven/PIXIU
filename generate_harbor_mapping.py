#!/usr/bin/env python3
"""
Generate a mapping between Harbor Taiwan dataset samples and HuggingFace indices.
This ensures PIXIU can evaluate the exact same samples as Harbor for parity experiments.
"""

import json
import os
from pathlib import Path
from datasets import load_dataset
from tqdm import tqdm

def extract_bankrupt_value(text):
    """Extract Bankrupt? value from financial text."""
    try:
        return text.split('Bankrupt?: ')[1].split(',')[0]
    except IndexError:
        return None

def main():
    print("Loading HuggingFace dataset...")
    hf_dataset = load_dataset("TheFinAI/cra-taiwan", split="test")
    
    # Build a lookup dict: bankrupt_value -> hf_index
    print("Building HuggingFace lookup...")
    hf_lookup = {}
    for idx in tqdm(range(len(hf_dataset))):
        text = hf_dataset[idx]['text']
        bankrupt = extract_bankrupt_value(text)
        if bankrupt and bankrupt not in hf_lookup:
            hf_lookup[bankrupt] = idx
    
    print(f"HuggingFace dataset has {len(hf_dataset)} samples")
    print(f"Unique Bankrupt? values: {len(hf_lookup)}")
    
    # Find all Harbor samples
    harbor_dir = Path("/home/hefan/harbor/datasets/pixiu/taiwan")
    harbor_samples = sorted(harbor_dir.glob("pixiu-taiwan-taiwan*/tests/data/item.json"))
    
    print(f"\nFound {len(harbor_samples)} Harbor samples")
    
    # Create mapping
    mapping = {}
    missing = []
    
    print("\nMapping Harbor samples to HuggingFace indices...")
    for harbor_path in tqdm(harbor_samples):
        # Extract harbor sample number from path (e.g., taiwan000012 -> 12)
        harbor_name = harbor_path.parent.parent.parent.name
        harbor_idx = int(harbor_name.replace("pixiu-taiwan-taiwan", ""))
        
        # Load Harbor sample
        with open(harbor_path) as f:
            harbor_data = json.load(f)
        
        bankrupt = extract_bankrupt_value(harbor_data.get('query', ''))
        
        if bankrupt and bankrupt in hf_lookup:
            hf_idx = hf_lookup[bankrupt]
            mapping[harbor_idx] = hf_idx
        else:
            missing.append(harbor_idx)
            print(f"\n  WARNING: Harbor sample {harbor_idx} not found in HuggingFace")
    
    # Save mapping
    output_file = "/home/hefan/PIXIU/harbor_taiwan_index_mapping.json"
    with open(output_file, 'w') as f:
        json.dump({
            "description": "Mapping from Harbor taiwan sample indices to HuggingFace dataset indices",
            "harbor_dataset_path": str(harbor_dir),
            "hf_dataset": "TheFinAI/cra-taiwan",
            "hf_split": "test",
            "total_samples": len(mapping),
            "missing_samples": len(missing),
            "mapping": {str(k): v for k, v in sorted(mapping.items())}
        }, f, indent=2)
    
    print(f"\n✅ Mapping saved to: {output_file}")
    print(f"   Total mapped: {len(mapping)}")
    print(f"   Missing: {len(missing)}")
    
    if missing:
        print(f"   Missing indices: {missing}")
    
    # Print first 15 mappings
    print("\nFirst 15 mappings:")
    for harbor_idx in sorted(mapping.keys())[:15]:
        hf_idx = mapping[harbor_idx]
        print(f"  Harbor {harbor_idx:06d} → HuggingFace index {hf_idx}")
    
    # Verify a sample
    print("\nVerifying sample 0...")
    harbor_path = harbor_dir / "pixiu-taiwan-taiwan000000" / "tests" / "data" / "item.json"
    with open(harbor_path) as f:
        harbor_data = json.load(f)
    harbor_bankrupt = extract_bankrupt_value(harbor_data['query'])
    
    hf_idx = mapping[0]
    hf_bankrupt = extract_bankrupt_value(hf_dataset[hf_idx]['text'])
    
    print(f"  Harbor 000000: Bankrupt?={harbor_bankrupt}")
    print(f"  HuggingFace {hf_idx}: Bankrupt?={hf_bankrupt}")
    print(f"  Match: {harbor_bankrupt == hf_bankrupt} ✅" if harbor_bankrupt == hf_bankrupt else "  Match: FAILED ❌")

if __name__ == "__main__":
    main()
