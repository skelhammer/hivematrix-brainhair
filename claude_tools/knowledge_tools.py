"""
KnowledgeTree Service Tools

Tools for searching and browsing the knowledge base.
"""

import os
import sys

# Add parent directory to path to import service_client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.service_client import call_service


def search_knowledge(query: str, limit: int = 10) -> dict:
    """
    Search the knowledge base for articles.

    Args:
        query: Search query
        limit: Maximum number of results to return

    Returns:
        {
            "results": [
                {
                    "id": "article-123",
                    "title": "How to Reset Password",
                    "summary": "Step-by-step guide...",
                    "category": "User Management",
                    "relevance": 0.95
                },
                ...
            ],
            "count": 5
        }

    Example:
        >>> results = search_knowledge("password reset")
        >>> for article in results['results']:
        ...     print(f"{article['title']} - {article['relevance']}")
    """
    try:
        response = call_service(
            'knowledgetree',
            f'/api/search?query={query}&limit={limit}'
        )
        return response.json()
    except Exception as e:
        return {
            'error': 'Failed to search knowledge base',
            'results': [],
            'count': 0
        }


def browse_knowledge(path: str = '/') -> dict:
    """
    Browse the knowledge base by category/folder.

    Args:
        path: Category path to browse (default: root)

    Returns:
        {
            "path": "/troubleshooting/printers",
            "categories": [
                {"name": "HP Printers", "path": "/troubleshooting/printers/hp"},
                ...
            ],
            "articles": [
                {
                    "id": "article-456",
                    "title": "Printer Offline Error",
                    "summary": "...",
                },
                ...
            ]
        }

    Example:
        >>> kb = browse_knowledge("/troubleshooting")
        >>> print(f"Categories: {[c['name'] for c in kb['categories']]}")
    """
    try:
        response = call_service('knowledgetree', f'/api/browse?path={path}')
        return response.json()
    except Exception as e:
        return {
            'error': 'Failed to browse knowledge base',
            'path': path,
            'categories': [],
            'articles': []
        }


def get_article(article_id: str) -> dict:
    """
    Get full content of a knowledge base article.

    Args:
        article_id: Article identifier

    Returns:
        {
            "id": "article-123",
            "title": "How to Reset Password",
            "category": "User Management",
            "content": "Full article content in markdown...",
            "created_at": "2025-01-15T10:00:00",
            "updated_at": "2025-02-20T14:30:00",
            "tags": ["password", "reset", "user"],
            "related_articles": [
                {"id": "article-124", "title": "Password Policy"},
                ...
            ]
        }

    Example:
        >>> article = get_article("article-123")
        >>> print(f"Title: {article['title']}")
        >>> print(f"Content: {article['content']}")
    """
    try:
        response = call_service('knowledgetree', f'/api/node/{article_id}')
        return response.json()
    except Exception as e:
        return {
            'error': 'Failed to retrieve article',
            'id': article_id
        }
