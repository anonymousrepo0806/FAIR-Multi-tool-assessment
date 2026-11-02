import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("Merging raw tool outputs", "merge.py"),
    ("Running agreement analysis", "raw_analysis.py"),
    ("Computing score distributions", "rq_figures.py"),
    ("Computing consensus analysis", "consensus_figures.py"),
    ("Testing hypotheses H1-H4", "hypotheses.py"),
    ("Generating paper figures", "paper_figures.py"),
]


def main():
    for i, (label, script) in enumerate(STEPS, 1):
        path = os.path.join(HERE, script)
        if not os.path.exists(path):
            sys.exit(f"{script} not found in {HERE}")
        print(f"\n=== Step {i}/{len(STEPS)}: {label} ===", flush=True)
        start = time.time()
        result = subprocess.run([sys.executable, path] + (sys.argv[1:] if script == "merge.py" else []), cwd=HERE)
        if result.returncode != 0:
            sys.exit(f"\nStopped: {script} failed with exit code {result.returncode}")
        print(f"--- done in {time.time() - start:.1f}s", flush=True)
    print(f"\nAll steps finished. Figures are in {os.path.join(HERE, 'figures')}, tables in {os.path.join(HERE, 'results')}")


if __name__ == "__main__":
    main()
