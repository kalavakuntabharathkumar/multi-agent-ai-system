import streamlit as st
from core.executor import ExecutionEngine

st.set_page_config(page_title="Multi-Agent AI Task Automation", layout="wide")
st.title("Multi-Agent AI Task Automation System")
st.markdown(
    "Enter a complex task, then watch the planner create subtasks and worker agents execute them sequentially."
)

user_task = st.text_area("User task", value="Summarize article, create LinkedIn post, draft email")
if st.button("Run Task"):
    if not user_task.strip():
        st.warning("Please add a task before running.")
    else:
        engine = ExecutionEngine()
        with st.spinner("Running agents..."):
            results = engine.run(user_task)

        st.subheader("Planner Output")
        for step in results["plan"].get("steps", []):
            st.write(f"**{step['id']}**: {step['description']} (tool={step['tool']})")

        st.subheader("Execution Trace")
        for entry in results["trace"]:
            st.write(
                f"**{entry['id']}** | status={entry['status']} | attempt={entry['attempt']} | confidence={entry['confidence']}"
            )
            st.write(entry["result"])

        st.subheader("Final Outputs")
        for step_id, output in results["final_output"].items():
            if isinstance(output, dict):
                st.write(f"**{step_id}**: {output.get('status')}\n{output.get('result')}" )
