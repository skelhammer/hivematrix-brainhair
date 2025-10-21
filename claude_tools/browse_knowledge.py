#!/usr/bin/env python3
"""
Browse Knowledge Base

Usage:
    python browse_knowledge.py [path]

Example:
    python browse_knowledge.py /
    python browse_knowledge.py /troubleshooting
"""

import sys
import os
import json
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app
from knowledge_tools import browse_knowledge

def main():
    parser = argparse.ArgumentParser(description='Browse the knowledge base')
    parser.add_argument('path', nargs='?', default='/', help='Path to browse (default: /)')
    parser.add_argument('--json', action='store_true', help='Output raw JSON')

    args = parser.parse_args()

    # Use Flask app context
    with app.app_context():
        result = browse_knowledge(args.path)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            # Pretty print
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
                return 1

            print(f"\n📁 Knowledge Base: {result['path']}")
            print("=" * 60)

            if result.get('categories'):
                print("\n📂 Categories:")
                for cat in result['categories']:
                    print(f"  - {cat['name']}")
                    if 'path' in cat:
                        print(f"    Path: {cat['path']}")

            if result.get('articles'):
                print("\n📄 Articles:")
                for article in result['articles']:
                    print(f"\n  • {article['title']}")
                    print(f"    ID: {article['id']}")
                    if 'summary' in article and article['summary']:
                        print(f"    Summary: {article['summary'][:100]}...")

            if not result.get('categories') and not result.get('articles'):
                print("\n(Empty)")

    return 0

if __name__ == '__main__':
    sys.exit(main())
