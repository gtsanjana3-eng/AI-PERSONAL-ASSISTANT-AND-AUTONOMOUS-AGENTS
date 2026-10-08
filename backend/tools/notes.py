from backend.tools.registry import registry, ToolMetadata
from backend.database.db import get_connection

def create_note(content: str) -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, content TEXT)")
    c.execute("INSERT INTO notes (content) VALUES (?)", (content,))
    conn.commit()
    conn.close()
    return "Note created successfully."

def delete_all_notes() -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, content TEXT)")
    c.execute("DELETE FROM notes")
    conn.commit()
    conn.close()
    return "All notes deleted."

registry.register(
    ToolMetadata(
        name="create_note",
        description="Creates an internal note.",
        input_schema={"content": "str"},
        requires_approval=False
    ),
    create_note
)

registry.register(
    ToolMetadata(
        name="delete_all_notes",
        description="Deletes all internal notes.",
        input_schema={},
        requires_approval=True
    ),
    delete_all_notes
)
