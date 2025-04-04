#!/usr/bin/env python3
from pathlib import Path
import json
import requests
import argparse
import pandas as pd
import time
import os
from sklearn.metrics import classification_report, confusion_matrix, precision_score, recall_score, f1_score, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns

def evaluate_combined(test_file, api_url, output_dir):
    """Evaluate the combined approach."""
    y_true, y_pred = [], []
    results = []

    with open(test_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                code = data["code"]
                expected = data["expected"]
                payload = {"code": code, "top_k": 10}

                try:
                    start_time = time.time()
                    res = requests.post(api_url, json=payload, timeout=30)
                    res.raise_for_status()
                    response_time = time.time() - start_time
                    
                    result = res.json()
                    predicted = result.get("plagiarism_detected", False)
                    
                    y_true.append(expected)
                    y_pred.append(predicted)
                    
                    results.append({
                        "line_num": line_num,
                        "method": "combined",
                        "expected": expected,
                        "predicted": predicted,
                        "correct": expected == predicted,
                        "response_time": response_time
                    })
                    
                except requests.exceptions.RequestException as e:
                    print(f"❌ Combined API request failed (line {line_num}): {e}")
                    results.append({
                        "line_num": line_num,
                        "method": "combined",
                        "expected": expected,
                        "predicted": None,
                        "correct": None,
                        "error": str(e),
                        "response_time": None
                    })
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON at line {line_num}: {e}")

    # Generate metrics
    if y_true and y_pred:
        metrics = calculate_metrics(y_true, y_pred, "Combined")
        
        # Save confusion matrix
        plt.figure(figsize=(8, 6))
        cm = confusion_matrix(y_true, y_pred, labels=[True, False])
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")
        plt.title("Combined Approach Confusion Matrix")
        plt.xlabel("Predicted")
        plt.ylabel("Actual")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "combined_confusion_matrix.png"))
        plt.close()
        
        return results, metrics
    
    return results, None

def evaluate_llm(test_file, api_url, output_dir):
    """Evaluate the LLM-only approach."""
    y_true, y_pred = [], []
    results = []

    with open(test_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                code = data["code"]
                expected = data["expected"]
                payload = {"code": code}

                try:
                    start_time = time.time()
                    res = requests.post(api_url, json=payload, timeout=30)
                    res.raise_for_status()
                    response_time = time.time() - start_time
                    
                    result_text = res.text.strip().lower()
                    predicted = result_text == "yes"  # True if "yes", else False
                    
                    y_true.append(expected)
                    y_pred.append(predicted)
                    
                    results.append({
                        "line_num": line_num,
                        "method": "llm",
                        "expected": expected,
                        "predicted": predicted,
                        "correct": expected == predicted,
                        "response_time": response_time
                    })
                    
                except requests.exceptions.RequestException as e:
                    print(f"❌ LLM API request failed (line {line_num}): {e}")
                    results.append({
                        "line_num": line_num,
                        "method": "llm",
                        "expected": expected,
                        "predicted": None,
                        "correct": None,
                        "error": str(e),
                        "response_time": None
                    })
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON at line {line_num}: {e}")

    # Generate metrics
    if y_true and y_pred:
        metrics = calculate_metrics(y_true, y_pred, "LLM")
        
        # Save confusion matrix
        plt.figure(figsize=(8, 6))
        cm = confusion_matrix(y_true, y_pred, labels=[True, False])
        sns.heatmap(cm, annot=True, fmt="d", cmap="Oranges")
        plt.title("LLM-Only Approach Confusion Matrix")
        plt.xlabel("Predicted")
        plt.ylabel("Actual")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "llm_confusion_matrix.png"))
        plt.close()
        
        return results, metrics
    
    return results, None

def evaluate_threshold(test_file, api_url, output_dir):
    """Evaluate the threshold approach."""
    y_true, y_pred = [], []
    results = []

    with open(test_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                code = data["code"]
                expected = data["expected"]
                payload = {"code": code, "top_k": 10, "analyze_plagiarism": True}

                try:
                    start_time = time.time()
                    res = requests.post(api_url, json=payload, timeout=30)
                    res.raise_for_status()
                    response_time = time.time() - start_time
                    
                    result = res.json()
                    predicted = result.get("plagiarism_detected", False)
                    
                    y_true.append(expected)
                    y_pred.append(predicted)
                    
                    results.append({
                        "line_num": line_num,
                        "method": "threshold",
                        "expected": expected,
                        "predicted": predicted,
                        "correct": expected == predicted,
                        "response_time": response_time
                    })
                    
                except requests.exceptions.RequestException as e:
                    print(f"❌ Threshold API request failed (line {line_num}): {e}")
                    results.append({
                        "line_num": line_num,
                        "method": "threshold",
                        "expected": expected,
                        "predicted": None,
                        "correct": None,
                        "error": str(e),
                        "response_time": None
                    })
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON at line {line_num}: {e}")

    # Generate metrics
    if y_true and y_pred:
        metrics = calculate_metrics(y_true, y_pred, "Threshold")
        
        # Save confusion matrix
        plt.figure(figsize=(8, 6))
        cm = confusion_matrix(y_true, y_pred, labels=[True, False])
        sns.heatmap(cm, annot=True, fmt="d", cmap="Greens")
        plt.title("Threshold Approach Confusion Matrix")
        plt.xlabel("Predicted")
        plt.ylabel("Actual")
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "threshold_confusion_matrix.png"))
        plt.close()
        
        return results, metrics
    
    return results, None

def calculate_metrics(y_true, y_pred, method_name):
    """Calculate evaluation metrics."""
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    # Print report to console
    print(f"\n📊 {method_name} Approach Metrics:")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1 Score: {f1:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_true, y_pred, zero_division=0))
    
    return {
        "method": method_name.lower(),
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "total_samples": len(y_true),
        "positive_samples": sum(y_true),
        "negative_samples": len(y_true) - sum(y_true)
    }

def main():
    parser = argparse.ArgumentParser(description="Evaluate plagiarism detection methods")
    parser.add_argument("--test-file", type=str, default="/data/test_cases.jsonl",
                        help="Path to test cases JSONL file")
    parser.add_argument("--combined-api", type=str, default="http://combined-api:8001/check-plagiarism",
                        help="URL for combined approach API")
    parser.add_argument("--llm-api", type=str, default="http://llm-api:8002/check",
                        help="URL for LLM-only approach API")
    parser.add_argument("--threshold-api", type=str, default="http://threshold-api:8003/search-similar",
                        help="URL for threshold approach API")
    parser.add_argument("--output-dir", type=str, default="/results",
                        help="Directory to save results")
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize timestamp
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    
    # Run evaluations
    print("Starting evaluation...")
    
    combined_results, combined_metrics = evaluate_combined(args.test_file, args.combined_api, args.output_dir)
    llm_results, llm_metrics = evaluate_llm(args.test_file, args.llm_api, args.output_dir)
    threshold_results, threshold_metrics = evaluate_threshold(args.test_file, args.threshold_api, args.output_dir)
    
    # Combine all results
    all_results = combined_results + llm_results + threshold_results
    
    # Save detailed results
    results_df = pd.DataFrame(all_results)
    results_csv_path = os.path.join(args.output_dir, f"detailed_results_{timestamp}.csv")
    results_df.to_csv(results_csv_path, index=False)
    print(f"✅ Detailed results saved to {results_csv_path}")
    
    # Save summary metrics
    metrics_list = []
    if combined_metrics:
        metrics_list.append(combined_metrics)
    if llm_metrics:
        metrics_list.append(llm_metrics)
    if threshold_metrics:
        metrics_list.append(threshold_metrics)
    
    if metrics_list:
        metrics_df = pd.DataFrame(metrics_list)
        metrics_csv_path = os.path.join(args.output_dir, f"metrics_summary_{timestamp}.csv")
        metrics_df.to_csv(metrics_csv_path, index=False)
        print(f"✅ Metrics summary saved to {metrics_csv_path}")
    
    # Generate comparison visualization
    if metrics_list:
        plt.figure(figsize=(12, 8))
        
        # Metrics comparison
        methods = [m["method"] for m in metrics_list]
        metrics = ["accuracy", "precision", "recall", "f1"]
        
        x = range(len(methods))
        width = 0.2
        
        for i, metric in enumerate(metrics):
            values = [m[metric] for m in metrics_list]
            plt.bar([p + width*i for p in x], values, width, label=metric.capitalize())
        
        plt.xlabel('Method')
        plt.ylabel('Score')
        plt.title('Comparison of Plagiarism Detection Methods')
        plt.xticks([p + width for p in x], methods)
        plt.ylim(0, 1)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        comparison_path = os.path.join(args.output_dir, f"methods_comparison_{timestamp}.png")
        plt.savefig(comparison_path)
        plt.close()
        print(f"✅ Comparison visualization saved to {comparison_path}")
    
    print("\n🎉 Evaluation completed successfully!")

if __name__ == "__main__":
    main()