import os
import sys
import json

# Add backend to PYTHONPATH so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.analysis.classifier import classify_article

def run_evaluation():
    dataset_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'evaluation_dataset.json')
    with open(dataset_path, 'r') as f:
        dataset = json.load(f)

    correct = 0
    total = len(dataset)
    results = []

    print(f"Starting evaluation of {total} test cases...")
    print("-" * 50)

    for i, case in enumerate(dataset):
        headline = case["headline"]
        desc = case.get("description", "")
        expected = case["expected_oil_impact"]

        # Call the actual classifier
        try:
            output = classify_article(headline, desc)
            actual = output.get("oil_impact", "Error")
        except Exception as e:
            actual = f"Error: {e}"

        is_correct = actual == expected
        if is_correct:
            correct += 1

        results.append({
            "headline": headline,
            "expected": expected,
            "actual": actual,
            "is_correct": is_correct
        })

        marker = "✅" if is_correct else "❌"
        print(f"[{i+1}/{total}] {marker} Headline: {headline}")
        print(f"    Expected: {expected} | Actual: {actual}")

    print("-" * 50)
    accuracy = (correct / total) * 100
    print(f"Evaluation Complete!")
    print(f"Accuracy: {accuracy:.2f}% ({correct}/{total})")
    
    if accuracy < 80.0:
        print("\n⚠️ WARNING: Accuracy is below 80%. Consider tuning the prompt in app/analysis/classifier.py.")

if __name__ == "__main__":
    # Ensure keys are loaded if not in env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
        
    run_evaluation()
