import json
import re
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, Any


def _strip_html(text: str) -> str:
    """Remove HTML tags from search snippets."""
    return re.sub(r"<[^>]+>", "", text).strip()


def search_information(query: str, timeout: int = 6) -> Dict[str, Any]:
    """
    Perform a real information search using Wikipedia's public API.
    Does not fake results. Returns structured facts, snippets, and URLs.
    Handles network errors, timeouts, and empty queries cleanly.
    """
    clean_query = query.strip() if query else ""
    if not clean_query:
        return {
            "success": False,
            "query": query,
            "error": "Search query cannot be empty."
        }

    try:
        encoded_query = urllib.parse.quote(clean_query)
        search_url = (
            f"https://en.wikipedia.org/w/api.php?"
            f"action=query&list=search&srsearch={encoded_query}&format=json&utf8=1&srlimit=3"
        )

        request = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": "TaskPilotAgent/1.0 (Autonomous-Task-Agent; contact@example.com)"
            }
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return {
                    "success": False,
                    "query": clean_query,
                    "error": f"Search service returned status {response.status}."
                }
            raw_data = response.read().decode("utf-8")
            data = json.loads(raw_data)

        items = data.get("query", {}).get("search", [])
        if not items:
            return {
                "success": True,
                "query": clean_query,
                "results": [],
                "message": f"No direct information found for '{clean_query}'."
            }

        results = []
        for item in items:
            title = item.get("title", "")
            snippet = _strip_html(item.get("snippet", ""))
            encoded_title = urllib.parse.quote(title.replace(" ", "_"))
            results.append({
                "title": title,
                "snippet": snippet,
                "url": f"https://en.wikipedia.org/wiki/{encoded_title}"
            })

        # Provide a synthesized top summary
        top_snippet = results[0]["snippet"]
        return {
            "success": True,
            "query": clean_query,
            "results": results,
            "summary": f"{results[0]['title']}: {top_snippet}"
        }

    except urllib.error.HTTPError as e:
        return {
            "success": False,
            "query": clean_query,
            "error": f"Search HTTP error: {e.code} - {e.reason}"
        }
    except urllib.error.URLError as e:
        return {
            "success": False,
            "query": clean_query,
            "error": f"Search network error: {e.reason}"
        }
    except TimeoutError:
        return {
            "success": False,
            "query": clean_query,
            "error": "Search timed out. Please try again."
        }
    except Exception as e:
        return {
            "success": False,
            "query": clean_query,
            "error": f"Search unexpected error: {str(e)}"
        }