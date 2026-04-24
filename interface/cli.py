import argparse
from core.executor import ExecutionEngine


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="Multi-Agent AI Task Automation CLI")
    parser.add_argument("task", nargs="*", help="Complex user task to execute")
    args = parser.parse_args()
    if not args.task:
        task = input("Enter a complex task: ")
    else:
        task = " ".join(args.task)

    engine = ExecutionEngine()
    results = engine.run(task)
    print("\n=== Plan ===")
    for step in results["plan"].get("steps", []):
        print(f"- {step['id']}: {step['description']} (tool={step['tool']})")

    print("\n=== Execution Trace ===")
    for entry in results["trace"]:
        print(f"{entry['id']} | status={entry['status']} | attempt={entry['attempt']} | confidence={entry['confidence']}\n  result: {entry['result'][:300]}\n")

    print("=== Final Outputs ===")
    for step_id, output in results["final_output"].items():
        if isinstance(output, dict):
            print(f"{step_id}: {output.get('status')} - {output.get('result')[:300]}")


if __name__ == "__main__":
    run_cli()
