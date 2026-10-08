from backend.tools.registry import registry, ToolMetadata

def add(a: float, b: float) -> float:
    """A simple tool to add two numbers."""
    return a + b

def subtract(a: float, b: float) -> float:
    """A simple tool to subtract two numbers."""
    return a - b

registry.register(
    ToolMetadata(
        name="add",
        description="A simple tool to add two numbers.",
        input_schema={"a": "float", "b": "float"},
        requires_approval=False
    ),
    add
)

registry.register(
    ToolMetadata(
        name="subtract",
        description="A simple tool to subtract two numbers.",
        input_schema={"a": "float", "b": "float"},
        requires_approval=False
    ),
    subtract
)
