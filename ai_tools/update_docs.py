#!/home/david/Work/hivematrix/hivematrix-brainhair/pyenv/bin/python
"""
Update Documentation

Smart tool to update any document in KnowledgeTree. Searches for documents
and folders intelligently, creates if missing, updates if exists.

Usage:
    # Update any document by path
    python update_docs.py "/Companies/Example Company/overview.md" "Content here..."

    # Or just search by keywords - tool finds the best match
    python update_docs.py "Example Company overview" "Content here..."

    # Works with any folder structure
    python update_docs.py "IT/Windows/password-reset.md" "Reset steps..."
    python update_docs.py "/Support/Ticket Templates/email-template.md" "Template..."

The tool is smart:
- Searches if you don't provide exact path
- Creates missing folders automatically
- Updates if document exists, creates if it doesn't
- Shows you what it found before making changes
"""

import sys
import os

# Import from manage_knowledge
sys.path.insert(0, os.path.dirname(__file__))
from manage_knowledge import (
    get_service_token, search_knowledge, browse_knowledge,
    create_node, update_node, get_node_details, get_node_id_from_path
)
from approval_helper import request_approval


def find_or_create_path(path_parts, skip_approval=False):
    """
    Walk through path parts, creating folders as needed.
    Returns the final folder ID, or None if failed.

    Args:
        path_parts: List like ['Companies', 'Example Company', 'overview.md']
        skip_approval: If True, skip approval prompts (debug mode)

    Returns:
        (parent_id, filename) tuple
    """
    if not path_parts:
        return None, None

    filename = path_parts[-1]
    folder_parts = path_parts[:-1]

    # Start at root
    current_path = "/"
    current_id = "root"

    print(f"📂 Navigating path: /{'/'.join(folder_parts)}")

    # Walk through each folder
    for folder_name in folder_parts:
        next_path = f"{current_path}{folder_name}".replace('//', '/')
        print(f"   Checking: {next_path}")

        # Try to browse to this folder
        browse_result = browse_knowledge(next_path)

        if browse_result and browse_result.get('current_node', {}).get('id'):
            # Folder exists
            current_id = browse_result['current_node']['id']
            current_path = next_path + "/"
            print(f"   ✓ Found")
        else:
            # Folder doesn't exist - create it
            print(f"   ✗ Not found, creating folder: {folder_name}")

            if not skip_approval:
                approved = request_approval(
                    f"Create folder: {folder_name}",
                    {
                        'Path': current_path,
                        'Folder': folder_name,
                        'Action': 'Create missing folder in path'
                    }
                )

                if not approved:
                    print("✗ User denied folder creation")
                    return None, None

            new_id = create_node(current_path.rstrip('/') or '/', folder_name, is_folder=True)
            if not new_id:
                print(f"ERROR: Failed to create folder: {folder_name}")
                return None, None

            current_id = new_id
            current_path = next_path + "/"
            print(f"   ✓ Created")

    return current_id, filename


def update_docs(path_or_search: str, content: str, skip_approval: bool = False) -> bool:
    """
    Update or create a document.

    Args:
        path_or_search: Either exact path like "/Companies/Example Company/overview.md"
                       or search terms like "Example Company overview"
        content: Document content
        skip_approval: If True, skip approval prompts (debug mode)

    Returns:
        True if successful
    """
    print(f"📝 Updating document")
    print(f"   Target: {path_or_search}")
    print(f"   Content: {len(content)} characters")
    print()

    # Determine if it's a path or search term
    is_path = path_or_search.startswith('/') or '/' in path_or_search

    parent_id = None
    filename = None
    existing_doc = None

    if is_path:
        # It's a path - parse it
        path = path_or_search.strip('/')
        path_parts = path.split('/')

        parent_id, filename = find_or_create_path(path_parts, skip_approval=skip_approval)
        if not parent_id:
            return False

        # Check if document already exists
        parent_path = '/' + '/'.join(path_parts[:-1]) if len(path_parts) > 1 else '/'
        browse_result = browse_knowledge(parent_path)

        if browse_result:
            for article in browse_result.get('articles', []):
                if article['title'] == filename or article['title'] == filename.replace('.md', ''):
                    existing_doc = article
                    print(f"✓ Found existing document: {article['title']}")
                    break

    else:
        # It's a search term - find the document
        print(f"🔍 Searching for: {path_or_search}")
        results = search_knowledge(path_or_search)

        if not results:
            print(f"❌ No documents found matching: {path_or_search}")
            print(f"   Try using an exact path like: /Folder/Subfolder/document.md")
            return False

        # Filter to articles only
        articles = [r for r in results if not r.get('is_folder')]

        if not articles:
            print(f"❌ Search found folders but no documents")
            print(f"   Try using an exact path to create a new document")
            return False

        if len(articles) > 1:
            print(f"⚠️  Found {len(articles)} documents:")
            for i, art in enumerate(articles[:5], 1):
                print(f"   {i}. {art['name']} in /{art.get('folder_path', '')}")
            print(f"   Using first match: {articles[0]['name']}")

        existing_doc = articles[0]
        print(f"✓ Found: {existing_doc['name']} in /{existing_doc.get('folder_path', '')}")

    # Now either update or create
    if existing_doc:
        # Update existing document
        print(f"📝 Updating existing document...")

        if not skip_approval:
            approved = request_approval(
                f"Update document: {existing_doc.get('name', filename)}",
                {
                    'Document': existing_doc.get('name', filename),
                    'Path': f"/{existing_doc.get('folder_path', '')}",
                    'Action': 'Update content',
                    'Content Length': f"{len(content)} characters"
                }
            )

            if not approved:
                print("✗ User denied the change")
                return False

        success = update_node(existing_doc['id'], content=content)
        if success:
            print(f"✅ Successfully updated document")
            return True
        else:
            print(f"❌ Failed to update document")
            return False

    elif parent_id and filename:
        # Create new document
        print(f"📝 Creating new document: {filename}")

        # Reconstruct parent path from the path_parts we used
        if is_path:
            path = path_or_search.strip('/')
            path_parts = path.split('/')
            parent_path = '/' + '/'.join(path_parts[:-1]) if len(path_parts) > 1 else '/'
        else:
            parent_path = '/'  # Fallback

        if not skip_approval:
            approved = request_approval(
                f"Create document: {filename}",
                {
                    'Document': filename,
                    'Parent Path': parent_path,
                    'Action': 'Create new document',
                    'Content Length': f"{len(content)} characters"
                }
            )

            if not approved:
                print("✗ User denied the change")
                return False

        node_id = create_node(
            parent_path=parent_path,
            name=filename,
            content=content,
            is_folder=False
        )

        if node_id:
            print(f"✅ Successfully created document")
            return True
        else:
            print(f"❌ Failed to create document")
            return False

    else:
        print(f"❌ Could not determine how to update document")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Update or create documents in KnowledgeTree',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('path_or_search', help='Path or search terms for document')
    parser.add_argument('content', help='Document content')
    parser.add_argument('--debug-dont-ask-permission', action='store_true',
                       help='Skip approval prompts (for testing only)')

    args = parser.parse_args()

    # Set session ID if debug mode
    if args.debug_dont_ask_permission:
        print("⚠️  DEBUG MODE: Skipping approval prompts")
        os.environ['BRAINHAIR_SESSION_ID'] = 'debug_mode'

    success = update_docs(args.path_or_search, args.content, skip_approval=args.debug_dont_ask_permission)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
