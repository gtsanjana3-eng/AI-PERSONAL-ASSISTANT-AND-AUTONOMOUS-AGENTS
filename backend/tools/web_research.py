import httpx
from typing import Dict, Any
from backend.tools.registry import registry, ToolMetadata
from backend.config import settings

def web_search(query: str) -> str:
    """Searches the web for information based on a query."""
    if not query or not query.strip():
        return "Error: Empty search query provided."
        
    provider = settings.SEARCH_PROVIDER.lower() if settings.SEARCH_PROVIDER else ""
    
    if not provider:
        return "Research unavailable: No search provider configured."
        
    try:
        if provider == "wikipedia":
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "utf8": "1",
                "format": "json"
            }
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                results = data.get("query", {}).get("search", [])
                if not results:
                    return f"No results found for '{query}'."
                    
                # Extract top 3 results
                snippets = []
                for r in results[:3]:
                    snippets.append(f"Title: {r.get('title', 'Unknown')}\nSnippet: {r.get('snippet', '')}")
                    
                return "\n\n".join(snippets)
                
        elif provider == "tavily":
            # Example placeholder for a generic provider requiring a key
            if not settings.SEARCH_API_KEY:
                return "Research unavailable: Search API key not configured."
            return "Research unavailable: Provider 'tavily' not fully implemented yet."
        else:
            return f"Research unavailable: Unknown provider '{provider}'."
            
    except httpx.TimeoutException:
        return "Error: Search request timed out."
    except Exception as e:
        return f"Error: Search request failed ({str(e)})."

registry.register(
    ToolMetadata(
        name="web_search",
        description="Searches the web for information based on a text query.",
        input_schema={"query": "str"},
        requires_approval=False
    ),
    web_search
)
