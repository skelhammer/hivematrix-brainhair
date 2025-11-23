#!/usr/bin/env python3
"""
Search KnowledgeTree

Search the knowledge base and display results.
"""

import json
import sys
from brainhair_auth import get_auth


def search_knowledge(query):
    """
    Search KnowledgeTree with PHI/CJIS filtering.

    Args:
        query: Search query string
        filter_type: Type of filter to apply ("phi" or "cjis")

    Returns:
        Search results
    """
    auth = get_auth()

    response = auth.get("/api/knowledge/search", params={"q": query, "filter": filter_type})

    if response.status_code == 200:
        try:
            data = response.json()
            return data
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            print(f"Response text: {response.text}")
            return {}
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return {}


def browse_knowledge(path=""):
    """
    Browse KnowledgeTree nodes.

    Args:
        path: Path to browse (empty for root)
        filter_type: Type of filter to apply ("phi" or "cjis")

    Returns:
        Browse results
    """
    auth = get_auth()

    if path:
        params["path"] = path

    response = auth.get("/api/knowledge/browse", params=params)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return {}


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Search: python search_knowledge.py search <query> [filter]")
        print("  Browse: python search_knowledge.py browse [path] [filter]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "search":
        if len(sys.argv) < 3:
            print("Error: Search query required")
            sys.exit(1)

        query = sys.argv[2]
        if len(sys.argv) > 3:

        results = search_knowledge(query)

        print(f"\n=== Search Results for '{query}' (Filter: {filter_type}) ===\n")
        print(json.dumps(results, indent=2))

    elif command == "browse":
        path = sys.argv[2] if len(sys.argv) > 2 else ""
        if len(sys.argv) > 3:

        results = browse_knowledge(path)

        print(f"\n=== Browse '{path or '/'}' (Filter: {filter_type}) ===\n")
        print(json.dumps(results, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
