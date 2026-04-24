# Multi-Agent AI Task Automation System

## Overview
This project is an enterprise-ready multi-agent AI system that decomposes a complex user request into subtasks, executes them with worker agents, and stores intermediate outputs in memory.

## Architecture
- **Planner Agent**: Uses the OpenAI API to transform a single user task into a structured JSON plan with ordered steps.
- **Executor**: Orchestrates the workflow by executing each step sequentially, applying retries, and handling errors.
- **Worker Agent**: Executes subtasks by invoking tools and writing step outputs back to memory.
- **Tools**: Contains text utilities for summarization, LinkedIn post generation, and email drafting.
- **Memory**: A dictionary-based in-memory store to pass intermediate outputs across agent steps.
- **Logging**: Logs planner decisions and worker execution to `logs/app.log`.
- **Interface**: Includes both CLI and Streamlit UI interfaces.

## How Agents Interact
1. The CLI or Streamlit UI accepts a complex task from the user.
2. The **Planner Agent** converts the task into a plan with ordered steps.
3. The **Executor** reads the plan and executes each step in order.
4. The **Worker Agent** uses tools to complete the task and stores results in memory.
5. All intermediate outputs are collected in memory and used by dependent steps.

## Setup
1. Create a Python environment.
2. Install dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set your OpenAI API key.

## Run CLI
```bash
cd multi_agent_ai_system
python interface/cli.py "Summarize article, create LinkedIn post, draft email"
```

## Run Streamlit UI
```bash
cd multi_agent_ai_system
streamlit run interface/app.py
```

## Example Usage
- Input: `Summarize article, create LinkedIn post, draft email`
- Plan output includes steps for summarization, LinkedIn post creation, and email drafting.
- Execution trace includes status, retry attempts, and results for each step.

## Sample Outputs
- `step1`: Summarized content
- `step2`: LinkedIn post draft
- `step3`: Email draft

## Project Structure
```
multi_agent_ai_system/
├── agents/
│   ├── planner.py
│   ├── worker.py
├── tools/
│   ├── text_tools.py
│   ├── file_tools.py
├── core/
│   ├── executor.py
│   ├── memory.py
│   ├── logger.py
├── interface/
│   ├── cli.py
│   └── app.py
├── examples/
│   └── sample_tasks.txt
├── logs/
├── .env.example
├── requirements.txt
├── README.md
└── .gitignore
```
