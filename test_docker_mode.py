#!/usr/bin/env python3
"""
Test script to verify Docker mode works with Harbor parity.
"""

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from codexlm import CodexLM

def test_docker_single_sample():
    """Test Docker mode with a single sample."""
    
    print("=" * 80)
    print("Testing Docker Mode - Single Sample")
    print("=" * 80)
    
    # Sample from Taiwan bankruptcy dataset
    sample_doc = {
        "id": "taiwan000000",
        "query": "Based on the following financial report, predict whether the company will go bankrupt.\nOUTPUT EXACTLY 'yes' or 'no'.\n\nFinancial Report:\nROA(C) before interest and depreciation before interest: 0.370594\nROA(A) before interest and % after tax: 0.424389\nROA(B) before interest and depreciation after tax: 0.405750\nOperating Gross Margin: 0.601457\nRealized Sales Gross Margin: 0.601457\nOperating Profit Rate: 0.998969\nPre-tax net Interest Rate: 0.998969\nAfter-tax net Interest Rate: 0.998969\nNon-industry income and expenditure/revenue: 0.000000\nContinuous interest rate (after tax): 0.002620\nOperating Expense Rate: 0.601888\nResearch and development expense rate: 0.000000\nCash flow rate: 0.146920\nInterest-bearing debt interest rate: 0.000000\nTax rate (A): 0.000000\nNet Value Per Share (B): 0.279557\nNet Value Per Share (A): 0.283846\nNet Value Per Share (C): 0.281712\nPersistent EPS in the Last Four Seasons: 0.351480\nCash Flow Per Share: 0.041116\nRevenue Per Share (Yuan ¥): 0.188713\nOperating Profit Per Share (Yuan ¥): 0.188520\nPer Share Net profit before tax (Yuan ¥): 0.188520\nRealized Sales Gross Profit Growth Rate: 0.000000\nOperating Profit Growth Rate: -0.569706\nAfter-tax Net Profit Growth Rate: -0.569706\nRegular Net Profit Growth Rate: -0.569706\nContinuous Net Profit Growth Rate: -0.569706\nTotal Asset Growth Rate: -0.016674\nNet Value Growth Rate: -0.026801\nTotal Asset Return Growth Rate Ratio: 17.916194\nCash Reinvestment %: 0.005787\nCurrent Ratio: 1.014601\nQuick Ratio: 0.962302\nInterest Expense Ratio: 1.000000\nTotal debt/Total net worth: 0.306486\nDebt ratio %: 0.234389\nNet worth/Assets: 0.765611\nLong-term fund suitability ratio (A): 0.647188\nBorrowing dependency: 0.000046\nContingent liabilities/Net worth: 0.000000\nOperating profit/Paid-in capital: 0.675000\nNet profit before tax/Paid-in capital: 0.675000\nInventory and accounts receivable/Net value: 0.117155\nTotal Asset Turnover: 0.188806\nAccounts Receivable Turnover: 9.013621\nAverage Collection Days: 40.485597\nInventory Turnover Rate (times): 28.457514\nFixed Assets Turnover Frequency: 29.202290\nNet Worth Turnover Rate (times): 0.246631\nRevenue per person: 0.057790\nOperating profit per person: 0.057716\nAllocation rate per person: 0.002425\nWorking Capital to Total Assets: 0.019180\nQuick Assets/Total Assets: 0.633716\nCurrent Assets/Total Assets: 0.668120\nCash/Total Assets: 0.032663\nQuick Assets/Current Liability: 0.962302\nCash/Current Liability: 0.032662\nCurrent Liability to Assets: 0.658572\nOperating Funds to Liability: 0.029126\nInventory/Working Capital: 2.383297\nInventory/Current Liability: 0.051759\nCurrent Liabilities/Liability: 0.999912\nWorking Capital/Equity: 0.025052\nCurrent Liabilities/Equity: 0.860226\nLong-term Liability to Current Assets: 0.000132\nRetained Earnings to Total Assets: 0.177342\nTotal income/Total expense: 1.041858\nTotal expense/Assets: 0.608389\nCurrent Asset Turnover Rate: 0.282606\nQuick Asset Turnover Rate: 0.298027\nWorking capitcal Turnover Rate: 9.840632\nCash Turnover Rate: 5.778928\nCash Flow to Sales: 0.217886\nFixed Assets to Assets: 0.006469\nCurrent Liability to Liability: 0.999912\nCurrent Liability to Equity: 0.860226\nEquity to Long-term Liability: 874.909539\nCash Flow to Total Assets: 0.041116\nCash Flow to Liability: 0.175416\nCFO to Assets: 0.026601\nCash Flow to Equity: 0.053709\nCurrent Liability to Current Assets: 1.014385\nLiability-Assets Flag: 0.000000\nNet Income to Total Assets: 0.190839\nTotal assets to GNP price: 0.000002\nNo-credit Interval: 0.160099\nGross Profit to Sales: 0.601457\nNet Income to Stockholder's Equity: 0.249281\nLiability to Equity: 0.306486\nDegree of Financial Leverage (DFL): 0.000000\nInterest Coverage Ratio (Interest expense to EBIT): 0.000000",
        "choices": ["yes", "no"],
        "gold": 1  # Index of "no"
    }
    
    try:
        # Create CodexLM with Docker mode
        lm = CodexLM(model="gpt-4o-mini", harbor_mode=True, use_docker=True)
        
        # Set up agent details saving
        results_dir = Path(__file__).parent / "results" / "docker_test"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        agent_details_dir = results_dir / "agent_details"
        agent_details_dir.mkdir(parents=True, exist_ok=True)
        
        lm._save_agent_details = True
        lm._agent_log_base_dir = str(agent_details_dir)
        
        # Set current doc
        lm.current_doc = sample_doc
        
        print("\nRunning prediction with Docker mode...")
        print(f"Query: {sample_doc['query'][:200]}...")
        
        # Run prediction
        contexts_labels = [("", "until")]
        predictions = lm.greedy_until(contexts_labels)
        
        prediction = predictions[0].strip().lower()
        gold_answer = sample_doc["choices"][sample_doc["gold"]]
        
        print(f"\nPrediction: {prediction}")
        print(f"Gold answer: {gold_answer}")
        print(f"Correct: {prediction == gold_answer}")
        
        print("\n" + "=" * 80)
        print("Docker Mode Test Completed Successfully")
        print("=" * 80)
        
        return prediction == gold_answer
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_docker_single_sample()
    sys.exit(0 if success else 1)
