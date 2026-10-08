# AI Personal Assistant & Autonomous Agents

An AI-powered personal assistant that can understand user requests, break them into structured tasks, select safe tools, execute workflows, and request human approval for sensitive actions.

## Problem

Traditional AI assistants mainly answer questions. They often cannot safely perform multi-step tasks or use tools to complete workflows.

This project demonstrates an autonomous agent architecture where the assistant can:

- Understand user intent
- Create structured task plans
- Select registered tools
- Validate tool arguments
- Execute tasks step-by-step
- Request human approval for sensitive operations
- Maintain task history
- Display an execution trace
- Handle failures safely

## Architecture

User Request
    ↓
Planner
    ↓
Validated Task Plan
    ↓
Tool Registry
    ↓
Orchestrator
    ↓
Human Approval (when required)
    ↓
Tool Execution
    ↓
Result + Execution Trace
    ↓
Persistent Task History

## Key Features

### 1. Intelligent Task Planning

The assistant converts natural-language requests into structured task plans.

Example:

"Add 25 and 75"

becomes a calculation task using the registered `add` tool.

### 2. Tool Registry

All tools are registered in a controlled registry.

Current tools include:

- Calculator
- Notes
- Web Research

The assistant cannot directly execute arbitrary Python, shell commands, or unknown tools.

### 3. Tool Validation

Before execution, the system verifies:

- Tool exists
- Arguments are valid
- Required arguments are present
- Argument types are correct
- Unknown arguments are rejected

### 4. Human Approval

Sensitive operations require explicit user approval.

Example:

"Delete notes"

The system pauses and asks:

> Approval Required

The user can choose:

- Approve
- Reject

### 5. Execution Trace

The application displays how the agent processed a request, including planning, validation, approval, and execution.

### 6. Persistent Task History

Completed and failed tasks are stored in SQLite so previous workflows can be reviewed.

### 7. Health Monitoring

The backend provides a health endpoint for checking whether the assistant service is running.

## Technology Stack

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- SQLite

### Frontend

- HTML
- CSS
- JavaScript

### Testing

- Pytest
- Automated API and security tests

### AI Integration

The architecture supports an OpenAI-compatible LLM endpoint.

If an external LLM is unavailable, the application uses a safe fallback planner.

## Security Design

The LLM does not directly execute tools.

Instead:

LLM
 ↓
Structured Plan
 ↓
Validation
 ↓
Tool Registry
 ↓
Orchestrator
 ↓
Execution

This prevents the model from directly executing arbitrary code or unknown tools.

Sensitive operations also require human approval.

API keys are stored locally using environment variables and are never hardcoded into the application.

## Testing

The project includes automated tests covering:

- Basic API functionality
- Task planning
- Tool execution
- Tool validation
- Invalid tool rejection
- Invalid argument rejection
- LLM plan validation
- Web research
- Approval workflow
- API security
- Health endpoint

Current test result:

**33 tests passing**

## Project Structure

```text
AI-PERSONAL-ASSISTANT-AND-AUTONOMOUS-AGENTS/
│
├── backend/
│   ├── agents/
│   │   ├── llm_service.py
│   │   └── orchestrator.py
│   │
│   ├── database/
│   │   └── db.py
│   │
│   ├── tests/
│   │   ├── test_basic.py
│   │   ├── test_llm.py
│   │   └── test_web_research.py
│   │
│   ├── tools/
│   │   ├── calculator.py
│   │   ├── notes.py
│   │   ├── registry.py
│   │   └── web_research.py
│   │
│   ├── config.py
│   └── main.py
│
├── frontend/
│   ├── app.js
│   └── index.html
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md