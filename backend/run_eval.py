"""
Stand-alone runner script to exercise the Information Sufficiency Evaluator pipeline.
Demonstrates end-to-end execution of all 4 methods across the HotpotQA-style samples.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from sufficiency import llm, pipeline, samples

def main():
    print("=" * 70)
    print(" INFORMATION SUFFICIENCY EVALUATOR - PIPELINE RUNNER")
    print(f" LLM Mode: {llm.mode().upper()}")
    print("=" * 70)

    summary, cases = pipeline.run(samples.SAMPLES, pipeline.METHODS)

    print(f"\nTotal Cases Evaluated: {summary['n_cases']}")
    print("-" * 70)
    print(f"{'Method':<25} | {'Accuracy (%)':<15}")
    print("-" * 70)
    for method, acc in summary["accuracy"].items():
        print(f"{method:<25} | {acc:>6.1f}%")
    print("-" * 70)

    print("\nDETAILED CASE RESULTS:")
    for idx, case in enumerate(cases, 1):
        print(f"\n[Case {idx}] Question: {case['question']}")
        print(f"       Setting:  {case['setting']}")
        print(f"       Expected: {case['gold_label']}")
        print("       Predictions:")
        for method, res in case["results"].items():
            mark = "[OK]" if res["correct"] else "[FAIL]"
            print(f"         - {method:<16}: {res['pred']:<12} {mark}")
            if "hypotheses" in res:
                print(f"           * Consensus: {res.get('consensus')} (score: {res.get('similarity')})")
            if "verification" in res:
                print(f"           * Verify:    {res.get('verification')}")
            if "detail" in res and res["detail"]:
                print(f"           * Detail:    {res['detail']}")

    print("\n" + "=" * 70)
    print(" RUN COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
