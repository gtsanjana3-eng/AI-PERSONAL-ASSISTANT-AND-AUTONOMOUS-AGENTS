import enum
import uuid
import re

from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field

from backend.tools.registry import registry
from backend.config import settings
from backend.database.db import save_task_history


# Import tools so they register themselves
import backend.tools.calculator
import backend.tools.notes
import backend.tools.web_research


class AgentState(str, enum.Enum):
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class Task(BaseModel):
    id: int
    description: str
    tool_name: Optional[str] = None
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    requires_approval: bool = False


class TaskPlan(BaseModel):
    id: str
    original_request: str
    intent: str
    tasks: List[Task]
    state: AgentState
    final_result: Optional[str] = None
    error: Optional[str] = None
    planner_source: str = "fallback"

    # New: transparent execution trace
    execution_trace: List[str] = Field(default_factory=list)


# Active plans are kept in memory.
# Persistent completed history is stored in SQLite.
_plans_db: Dict[str, TaskPlan] = {}


class AgentOrchestrator:

    # ==========================================
    # FALLBACK PLANNER
    # ==========================================

    def _mock_planner(self, user_input: str) -> TaskPlan:

        user_input_lower = user_input.lower().strip()
        plan_id = str(uuid.uuid4())

        if not user_input_lower:
            return TaskPlan(
                id=plan_id,
                original_request=user_input,
                intent="unknown",
                tasks=[],
                state=AgentState.FAILED,
                error="Invalid input",
                execution_trace=["Request rejected: empty input."]
            )

        if "fail" in user_input_lower:
            return TaskPlan(
                id=plan_id,
                original_request=user_input,
                intent="test_failure",
                tasks=[
                    Task(
                        id=1,
                        description="Trigger failure",
                        tool_name="unknown_tool"
                    )
                ],
                state=AgentState.PLANNING,
                execution_trace=[
                    "Planner created a failure-test task."
                ]
            )

        if "delete notes" in user_input_lower:
            return TaskPlan(
                id=plan_id,
                original_request=user_input,
                intent="delete_notes",
                tasks=[
                    Task(
                        id=1,
                        description="Delete all notes",
                        tool_name="delete_all_notes"
                    )
                ],
                state=AgentState.PLANNING,
                execution_trace=[
                    "Planner identified a note deletion request."
                ]
            )

        if "create note" in user_input_lower:
            return TaskPlan(
                id=plan_id,
                original_request=user_input,
                intent="create_note",
                tasks=[
                    Task(
                        id=1,
                        description="Create note",
                        tool_name="create_note",
                        tool_args={
                            "content": "test note"
                        }
                    )
                ],
                state=AgentState.PLANNING,
                execution_trace=[
                    "Planner identified a note creation request."
                ]
            )

        if "research" in user_input_lower:
            return TaskPlan(
                id=plan_id,
                original_request=user_input,
                intent="research",
                tasks=[
                    Task(
                        id=1,
                        description="Research topic",
                        tool_name="web_search",
                        tool_args={
                            "query": user_input
                        }
                    )
                ],
                state=AgentState.PLANNING,
                execution_trace=[
                    "Planner identified a research request."
                ]
            )

        if "add" in user_input_lower:

            numbers = re.findall(
                r"-?\d+(?:\.\d+)?",
                user_input
            )

            if len(numbers) >= 2:

                a = float(numbers[0])
                b = float(numbers[1])

                if a.is_integer():
                    a = int(a)

                if b.is_integer():
                    b = int(b)

                return TaskPlan(
                    id=plan_id,
                    original_request=user_input,
                    intent="calculation",
                    tasks=[
                        Task(
                            id=1,
                            description=f"Add {a} and {b}",
                            tool_name="add",
                            tool_args={
                                "a": a,
                                "b": b
                            }
                        )
                    ],
                    state=AgentState.PLANNING,
                    execution_trace=[
                        f"Planner identified an addition task: {a} + {b}."
                    ]
                )

        if "subtract" in user_input_lower:

            numbers = re.findall(
                r"-?\d+(?:\.\d+)?",
                user_input
            )

            if len(numbers) >= 2:

                a = float(numbers[0])
                b = float(numbers[1])

                if a.is_integer():
                    a = int(a)

                if b.is_integer():
                    b = int(b)

                return TaskPlan(
                    id=plan_id,
                    original_request=user_input,
                    intent="calculation",
                    tasks=[
                        Task(
                            id=1,
                            description=f"Subtract {b} from {a}",
                            tool_name="subtract",
                            tool_args={
                                "a": a,
                                "b": b
                            }
                        )
                    ],
                    state=AgentState.PLANNING,
                    execution_trace=[
                        f"Planner identified a subtraction task: {a} - {b}."
                    ]
                )

        return TaskPlan(
            id=plan_id,
            original_request=user_input,
            intent="general_chat",
            tasks=[
                Task(
                    id=1,
                    description="Process general input",
                    tool_name=None
                )
            ],
            state=AgentState.PLANNING,
            execution_trace=[
                "Planner classified the request as general chat."
            ]
        )

    # ==========================================
    # AI PLANNER
    # ==========================================

    def _llm_planner_call(
        self,
        user_input: str
    ) -> Optional[TaskPlan]:

        from backend.agents.llm_service import call_llm_planner

        plan_data = call_llm_planner(user_input)

        if not plan_data:
            return None

        plan_id = str(uuid.uuid4())

        tasks = []

        for t in plan_data.get("tasks", []):

            task = Task(
                id=t.get("id", len(tasks) + 1),
                description=t.get("description", ""),
                tool_name=t.get("tool_name"),
                tool_args=t.get("tool_args", {})
            )

            tasks.append(task)

        return TaskPlan(
            id=plan_id,
            original_request=user_input,
            intent=plan_data.get("intent", "LLM Intent"),
            tasks=tasks,
            state=AgentState.PLANNING,
            planner_source="ai",
            execution_trace=[
                "AI planner generated and validated the task plan."
            ]
        )

    # ==========================================
    # PROCESS REQUEST
    # ==========================================

    def process_request(
        self,
        user_input: str
    ) -> dict:

        plan = None

        if settings.LLM_ENABLED:
            plan = self._llm_planner_call(user_input)

        if not plan:
            plan = self._mock_planner(user_input)

        _plans_db[plan.id] = plan

        plan.execution_trace.append(
            f"Planner source: {plan.planner_source}."
        )

        if plan.state == AgentState.FAILED:
            save_task_history(plan)
            return plan.model_dump()

        for task in plan.tasks:

            if task.tool_name:

                tool = registry.get_tool(task.tool_name)

                if tool and tool.metadata.requires_approval:
                    task.requires_approval = True

                    plan.execution_trace.append(
                        f"Task {task.id} requires human approval."
                    )

        return self._resume_plan(plan.id)

    # ==========================================
    # EXECUTION
    # ==========================================

    def _resume_plan(
        self,
        plan_id: str
    ) -> dict:

        plan = _plans_db.get(plan_id)

        if not plan:
            raise ValueError("Plan not found")

        if plan.state in [
            AgentState.COMPLETED,
            AgentState.FAILED
        ]:
            return plan.model_dump()

        plan.state = AgentState.EXECUTING

        plan.execution_trace.append(
            "Execution started."
        )

        try:

            for task in plan.tasks:

                if task.status in [
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.REJECTED
                ]:
                    continue

                if (
                    task.requires_approval
                    and task.status == TaskStatus.PENDING
                ):

                    plan.state = AgentState.WAITING_FOR_APPROVAL

                    plan.execution_trace.append(
                        f"Execution paused: waiting for approval for task {task.id}."
                    )

                    save_task_history(plan)

                    return plan.model_dump()

                task.status = TaskStatus.IN_PROGRESS

                plan.execution_trace.append(
                    f"Task {task.id} started: {task.description}."
                )

                if task.tool_name:

                    tool = registry.get_tool(task.tool_name)

                    if not tool:

                        task.error = (
                            f"Tool '{task.tool_name}' is not registered."
                        )

                        task.status = TaskStatus.FAILED

                        plan.execution_trace.append(
                            f"Task {task.id} failed: unregistered tool."
                        )

                        raise ValueError(task.error)

                    if not registry.validate_tool_call(
                        task.tool_name,
                        task.tool_args
                    ):

                        task.error = (
                            f"Invalid arguments for tool "
                            f"'{task.tool_name}'."
                        )

                        task.status = TaskStatus.FAILED

                        plan.execution_trace.append(
                            f"Task {task.id} failed: invalid tool arguments."
                        )

                        raise ValueError(task.error)

                    plan.execution_trace.append(
                        f"Validated tool call: {task.tool_name}."
                    )

                    try:

                        task.result = tool.execute(
                            **task.tool_args
                        )

                        task.status = TaskStatus.COMPLETED

                        plan.execution_trace.append(
                            f"Task {task.id} completed successfully."
                        )

                    except Exception as e:

                        task.error = str(e)

                        task.status = TaskStatus.FAILED

                        plan.execution_trace.append(
                            f"Task {task.id} failed during tool execution: {e}"
                        )

                        raise e

                else:

                    task.result = "Processed without tool"

                    task.status = TaskStatus.COMPLETED

                    plan.execution_trace.append(
                        f"Task {task.id} completed without a tool."
                    )

            plan.state = AgentState.COMPLETED

            if plan.tasks:

                plan.final_result = (
                    "Completed successfully. "
                    f"Last result: "
                    f"{plan.tasks[-1].result}"
                )

            else:

                plan.final_result = "No tasks to execute."

            plan.execution_trace.append(
                "All tasks completed. Agent workflow finished."
            )

        except Exception as e:

            plan.state = AgentState.FAILED
            plan.error = str(e)

            plan.execution_trace.append(
                f"Agent workflow failed: {e}"
            )

        save_task_history(plan)

        return plan.model_dump()

    # ==========================================
    # APPROVE TASK
    # ==========================================

    def approve_task(
        self,
        plan_id: str,
        task_id: int
    ) -> dict:

        plan = _plans_db.get(plan_id)

        if not plan:
            raise ValueError("Plan not found")

        for task in plan.tasks:

            if (
                task.id == task_id
                and task.requires_approval
                and task.status == TaskStatus.PENDING
            ):

                task.requires_approval = False

                plan.execution_trace.append(
                    f"User approved task {task_id}."
                )

                break

        return self._resume_plan(plan_id)

    # ==========================================
    # REJECT TASK
    # ==========================================

    def reject_task(
        self,
        plan_id: str,
        task_id: int
    ) -> dict:

        plan = _plans_db.get(plan_id)

        if not plan:
            raise ValueError("Plan not found")

        for task in plan.tasks:

            if (
                task.id == task_id
                and task.status == TaskStatus.PENDING
            ):

                task.status = TaskStatus.REJECTED

                task.error = "User rejected execution."

                plan.state = AgentState.FAILED

                plan.error = "Task rejected by user."

                plan.execution_trace.append(
                    f"User rejected task {task_id}. Workflow stopped."
                )

                break

        save_task_history(plan)

        return plan.model_dump()