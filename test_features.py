#!/usr/bin/env python3
"""Quick test script for new features."""

import os
from dotenv import load_dotenv

# Load environment variables FIRST (before importing obsidian module)
load_dotenv()

from src.mcp_obsidian.obsidian import Obsidian

api_key = os.getenv("OBSIDIAN_API_KEY")
host = os.getenv("OBSIDIAN_HOST", "127.0.0.1")

if not api_key:
    print("Error: OBSIDIAN_API_KEY not set in .env file")
    exit(1)

# Create API instance
api = Obsidian(api_key=api_key, host=host)

print("=" * 60)
print("Testing MCP Obsidian Thinking Partner Features")
print("=" * 60)

# Test 1: Create a test project
print("\n1. Testing project creation...")
try:
    result = api.create_folder_structure(
        base_path="Test Project",
        template="research_project"
    )
    print(f"✓ Created project structure: {result}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: Add frontmatter to a test file
print("\n2. Testing frontmatter management...")
try:
    # Create a test file
    api.put_content("Test Project/test.md", "# Test Note\n\nThis is a test.")
    
    # Add frontmatter
    api.update_frontmatter("Test Project/test.md", {
        "status": "active",
        "mode": "thinking",
        "tags": ["test", "research"]
    })
    
    # Read it back
    fm = api.get_frontmatter("Test Project/test.md")
    print(f"✓ Frontmatter: {fm}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: Tag operations
print("\n3. Testing tag operations...")
try:
    # Get tags from file
    tags = api.get_tags_from_file("Test Project/test.md")
    print(f"✓ Tags from file: {tags}")
    
    # Get all tags in vault
    all_tags = api.get_all_tags()
    print(f"✓ Total unique tags in vault: {len(all_tags)}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 4: Date range queries
print("\n4. Testing date range queries...")
try:
    files = api.get_files_by_date_range(
        days_back=7,
        folder_path="Test Project",
        include_content=False
    )
    print(f"✓ Files modified in last 7 days: {len(files)}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 5: Progress summary
print("\n5. Testing progress summary...")
try:
    progress = api.get_folder_progress(
        folder_path="Test Project",
        days_back=3,
        include_content=False
    )
    print(f"✓ Progress summary: {progress['file_count']} files changed in last 3 days")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 6: Links
print("\n6. Testing link extraction...")
try:
    # Add some links to test file
    content = """---
status: active
mode: thinking
tags: [test, research]
---

# Test Note

This links to [[Other Note]] and [markdown link](another.md).
"""
    api.put_content("Test Project/test.md", content)
    
    links = api.get_links_in_file("Test Project/test.md")
    print(f"✓ Links found: {links}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "=" * 60)
print("Testing complete!")
print("=" * 60)
print("\nTo clean up, you can delete the 'Test Project' folder in Obsidian.")

