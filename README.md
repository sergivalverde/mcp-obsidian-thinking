# MCP Obsidian - Your AI Thinking Partner

Connect Claude to your Obsidian vault for deep research and thinking work. No Dataview plugin required - uses native Obsidian features only.

---

## Quick Start

### Prerequisites
1. **Obsidian** with [Local REST API plugin](https://github.com/coddingtonbear/obsidian-local-rest-api) installed and enabled
2. **Python 3.11+**
3. **uv** package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Installation

**File Operations:**
- list_files_in_vault: Lists all files and directories in the root directory of your Obsidian vault
- list_files_in_dir: Lists all files and directories in a specific Obsidian directory
- get_file_contents: Return the content of a single file in your vault
- batch_get_file_contents: Return the contents of multiple files
- search: Search for documents matching a specified text query across all files in the vault
- complex_search: Complex search using JsonLogic queries
- patch_content: Insert content into an existing note relative to a heading, block reference, or frontmatter field
- append_content: Append content to a new or existing file in the vault
- put_content: Create or update a file in the vault
- delete_file: Delete a file or directory from your vault

**Frontmatter Management:**
- obsidian_frontmatter: Read, update, or delete frontmatter fields in notes

**Tag Operations:**
- obsidian_tags: Get all tags, get tags from a file, or find files by tags

**Link Management:**
- obsidian_links: Extract links from files, find backlinks, or update links when files are renamed

**Attachment Management:**
- obsidian_attachments: List attachments, rename attachments and update references, find files referencing an attachment

**Date & Progress Tracking:**
- obsidian_files_by_date: Get files by date range with flexible date queries
- obsidian_folder_progress: Get progress summary for a folder (great for "catch me up on last 3 days")
- get_recent_changes: Get recently modified files
- get_periodic_note: Get current periodic note (daily, weekly, monthly, etc.)
- get_recent_periodic_notes: Get most recent periodic notes

**Project Management:**
- obsidian_create_project: Create project folders with standardized structure (research_project template includes Chats/, Research/, Daily Progress/ subfolders)
- obsidian_create_daily_progress: Create daily progress notes with format `daily_progress_YYYY_MM_DD.md` in a project's Daily Progress folder

**Automatic Features:**
- **Automatic Internal Linking**: When writing content, file path mentions are automatically converted to Obsidian wiki-links (e.g., `Research/article.md` becomes `[[article]]`)
- **Backtick File Path Conversion**: File paths in backticks (like `` `Shane Parrish - Article.md` ``) are automatically converted to wiki-links if the file exists anywhere in your vault
- **Smart Filename Search**: When checking if a file exists, searches the entire vault by filename - works even if Claude references `article.md` but the file is actually in `Clippings/article.md`
- **Frontmatter Instruction Injection**: When reading files, frontmatter instructions (like `mode: thinking`) are automatically highlighted and enforced
- **Smart Link Normalization**: Wiki-links to EXISTING files are automatically normalized to clean filename-only format (`[[filename]]`), removing relative paths like `../../` and full paths. Works even if Claude writes `[[../../path/to/file]]` - it gets auto-corrected to `[[file]]` (only if the file exists)
- **Frontmatter Link Normalization**: Wiki-links in frontmatter YAML (category, related, etc.) are automatically normalized just like content links. Preserves display text in links like `[[file|Display Text]]`
- **No False Positives**: Links to non-existent files are NEVER normalized or created. If you write `[[Blue Ocean Strategy]]` and that file doesn't exist, it stays exactly as-is. This prevents false positive links in your vault.

# Create virtual environment and install
python3 -m venv .venv
.venv/bin/pip install -e .
```

### Configuration

#### For Raycast

## Thinking Partner Setup

Inspired by Noah Brier's workflow (featured on the AI & I podcast), this MCP server is designed to work as a "thinking partner" for deep research and project work in Obsidian. The key insight: AI is not just for generating artifacts—it's incredible at *reading* and helping you *think*.

### The Thinking Mode vs Writing Mode Distinction

One of the most common frustrations with AI models is that they immediately jump to creating artifacts when you're just trying to think through a problem. Noah's solution is to explicitly set the AI into "thinking mode" using frontmatter:

```yaml
---
mode: thinking
instructions: |
  CRITICAL: I am in THINKING mode, not WRITING mode.
  
  DO NOT under any circumstances try to write the artifact for me.
  Take this literally: do not create outlines, drafts, or any versions of the talk/writing.
  
  Only gather and organize the requested materials.
  
  Your role is to:
  - Help me explore ideas by asking questions
  - Gather relevant materials from my vault
  - Organize research notes
  - Summarize what I've learned
  - Challenge my thinking
  
  You are my thinking partner, not my ghostwriter.
---
```

### 🚨 How Thinking Mode Actually Works

**The MCP server automatically injects frontmatter instructions into every file read!**

When Claude reads a file using `obsidian_get_file_contents` or `obsidian_batch_get_file_contents`, the server:

1. **Extracts** the frontmatter from the file
2. **Checks** for behavioral instructions (`mode`, `instructions`, `ai_instructions`, `behavior`)
3. **Injects** a prominent warning banner at the top of the response
4. **Highlights** critical directives like "THINKING MODE" and "DO NOT CREATE CONTENT"

**What Claude sees when reading a file with `mode: thinking`:**

```
⚠️  CRITICAL: FRONTMATTER INSTRUCTIONS DETECTED

🎯 MODE: THINKING

⚠️  YOU ARE IN THINKING MODE - DO NOT CREATE CONTENT!
Your role: Ask questions, explore ideas, organize research.
NOT your role: Write drafts, create outlines, generate artifacts.

📋 INSTRUCTIONS:
[Your full instructions from frontmatter here]

📊 STAGE: exploration
📌 STATUS: active

END OF INSTRUCTIONS - FOLLOW THEM STRICTLY

[Then the actual file content follows...]
```

This means:
- ✅ **No manual reminders needed** - Instructions are automatically surfaced
- ✅ **Impossible to miss** - Prominent warning banners with emojis
- ✅ **Always enforced** - Every file read includes the instructions
- ✅ **Context-aware** - Different modes get different warnings

### Setting Up a Research Project

Create a new project with the standardized structure:

```
Use obsidian_create_project tool:
{
  "base_path": "My Research Topic",
  "template": "research_project"
}
```

This creates:
- `Projects/My Research Topic/` folder
- `index.md` with thinking mode frontmatter and basic structure sections
- Empty `README.md` for you to populate
- Folder structure: `Chats/`, `Research/`, `Daily Progress/`

**What's Pre-filled:**
- `index.md` includes critical thinking mode instructions in frontmatter
- Basic structure sections (Overview, Key Questions, Resources, Next Steps)
- This ensures the AI always enters thinking mode for your project

**What's Empty:**
- `README.md` - for you to add project overview/documentation as needed
- All subfolders start empty

**Note:** Projects are automatically created inside the `Projects/` folder. You can just provide the project name (e.g., "My Research Topic") and it will be created at `Projects/My Research Topic/`. If you explicitly include "Projects/" in the path, it won't be doubled.

### Key Workflow Patterns

#### 1. Starting a New Session

**Prompt:** "Can you catch me up on the last 3 days of work on this project?"

This uses `obsidian_folder_progress` to show all files changed recently:

```json
{
  "folder_path": "Projects/My Research Topic",
  "days_back": 3,
  "include_content": true
}
```

#### 2. Organizing with Tags

**Frontmatter tags for research states:**
```yaml
---
status: active
stage: thinking  # or: researching, writing, reviewing, complete
tags: [research, transformers, AI]
---
```

**Find all active research:**
```
Use obsidian_tags tool:
{
  "operation": "find_by_tags",
  "tags": ["research", "active"],
  "match_all": true
}
```

#### 3. Creating Daily Progress Notes

**Prompt:** "Create a daily progress note for today"

This uses `obsidian_create_daily_progress` to create a structured note:

```json
{
  "project_path": "My Research Topic"
}
```

Creates: `Projects/My Research Topic/Daily Progress/daily_progress_2025_11_16.md`

The note includes:
- Frontmatter with date (as wiki-link: `[[YYYY-MM-DD]]`), type, project (as wiki-link), and tags in inline format
- Heading with linked date for easy navigation
- Sections for: What I Learned, Key Insights, Questions & Challenges, Next Steps, Resources Referenced

**Example generated content:**
```yaml
---
date: [[2025-11-16]]
type: daily_progress
project: "[[My Research]]"
tags: [daily-progress, research-planning]
---

# Daily Progress - [[2025-11-16]]

## What I Learned Today
...
```

**For a specific date:**
```json
{
  "project_path": "My Research Topic",
  "date": "2025-11-15"
}
```

#### 4. Daily Progress Summaries

At the end of each work session, have the AI create a summary:

**Prompt:** "Review everything I worked on today in this project and create a summary in Daily Progress/[today's date].md"

The AI will:
1. Use `obsidian_files_by_date` to find today's changes
2. Read the modified files
3. Create a summary with key learnings and next steps

#### 4. Managing Research Materials

When you save a chat or article:

**Prompt:** "I've just added this article to Research/. Can you extract the key ideas and update the main index?"

The AI can:
- Read the new content
- Extract tags and add them to frontmatter
- Update the project index with a link and summary

### Example Agent Configuration

For Claude Code or similar tools, you can create a dedicated "thinking partner" agent:

```yaml
name: Thinking Partner
description: Helps explore complex problems without jumping to solutions

instructions: |
  You are a collaborative thinking partner specializing in helping people 
  explore complex problems through questions and dialogue.
  
  Your role is to facilitate thinking, NOT to do the thinking or create artifacts.
  
  Core principles:
  1. Ask clarifying questions before making suggestions
  2. Help organize thoughts, don't organize them yourself
  3. Surface connections between ideas
  4. Challenge assumptions constructively
  5. NEVER write the artifact unless explicitly asked
  
  When the user is researching:
  - Help them find relevant materials in their vault
  - Summarize what they've gathered so far
  - Suggest gaps in their research
  - Help them see patterns across sources
  
  When the user is thinking:
  - Ask "What if?" questions
  - Play devil's advocate
  - Help them articulate unclear ideas
  - Connect to previous work in their vault
  
  Remember: You're a thinking partner, not a ghostwriter.
```

### Useful Prompts for Thinking Partnership

**Starting a session:**
- "What's new in [project folder] over the last 3 days?"
- "Help me think through [topic]. Ask me questions to clarify my thinking."
- "What are the main themes emerging from my research in [folder]?"

**During research:**
- "Find all my notes related to [concept] and summarize the key points."
- "What's missing from my research on [topic]?"
- "Are there any contradictions in what I've gathered so far?"

**Organizing:**
- "Look through [folder] and suggest a better organization structure."
- "Extract all the key concepts from my research and create a tag structure."
- "Find all the files where I mention [concept] and show me how I'm thinking about it."

**Wrapping up:**
- "Create a progress summary for today's work."
- "What are the most important open questions I should tackle next?"
- "Update the project index with today's insights."

## Advanced Workflows

### Project-Based Research Workflow

This workflow is ideal for long-form research projects (talks, papers, consulting projects):

**Phase 1: Setup**
1. Create project structure with `obsidian_create_project` (automatically includes thinking mode frontmatter)
2. Review and customize the index.md structure sections as needed
3. Start working - thinking mode is already configured

**Phase 2: Research Collection**
1. Save articles, conversations, and notes to Research/ folder
2. Use web clipper or copy-paste for external sources
3. Save relevant AI conversations to Chats/ folder
4. Tag everything as you go

**Phase 3: Synthesis**
1. Use `obsidian_folder_progress` to review recent additions
2. Have AI identify themes and patterns
3. Create synthesis notes linking ideas together
4. Update project index with emerging structure

**Phase 4: Production**
1. Switch from "thinking mode" to "writing mode" in frontmatter
2. Create outline based on synthesis
3. Write in focused sessions with AI support
4. Keep daily progress notes

**Phase 5: Review**
1. Use `obsidian_links` to find all connected ideas
2. Ensure all key research is incorporated
3. Create final summary

### Using Attachments Effectively

**Organize attachments with meaningful names:**
```
Use obsidian_attachments tool to rename:
{
  "operation": "rename",
  "filepath": "attachments/IMG_1234.jpg",
  "new_name": "transformer-architecture-diagram.jpg"
}
```

This automatically updates all references across your vault.

**Find orphaned attachments:**
```
1. List all attachments
2. For each attachment, find references
3. Flag attachments with zero references for cleanup
```

### Tag-Based Organization

**Hierarchical tags for research stages:**
- `#research/collecting` - Still gathering materials
- `#research/synthesizing` - Finding patterns
- `#research/writing` - Creating artifacts
- `#research/complete` - Finished

**Content type tags:**
- `#source/article` - Web articles
- `#source/paper` - Academic papers
- `#source/conversation` - AI chats or interviews
- `#source/idea` - Original thoughts

**Project tags:**
- `#project/[name]` - Associate with specific project

**Query examples:**
```
Find all articles I'm still researching:
{
  "operation": "find_by_tags",
  "tags": ["source/article", "research/collecting"],
  "match_all": true
}

Find all completed research across projects:
{
  "operation": "find_by_tags",
  "tags": ["research/complete"],
  "match_all": false
}
```

### Date-Based Progress Tracking

**Weekly review workflow:**

1. **Get this week's work:**
```json
{
  "days_back": 7,
  "folder_path": "Projects",
  "include_content": false
}
```

2. **Review each project's progress:**
```json
{
  "folder_path": "Projects/Project Name",
  "days_back": 7,
  "include_content": true
}
```

3. **Create weekly summary:**
Have AI compile:
- Files created/modified
- Key insights from daily progress notes
- Next week's priorities

**Monthly review:**
- Use 30-day lookback
- Review all project indexes
- Identify stalled projects
- Archive completed work

### Link Management for Refactoring

When reorganizing your vault:

**Before moving files:**
1. Get all backlinks: `obsidian_links` with operation "get_backlinks"
2. Note files that will be affected

**After moving files:**
1. Use `obsidian_links` with operation "update_links"
2. Provide old and new paths
3. All wiki-links and markdown links are updated automatically

**Finding broken links:**
Run a check to find files referenced but not found (can be built as a workflow using the link tools).

### PARA Method Integration

This server works great with Tiago Forte's PARA method:

**Structure:**
- Projects/ (active projects)
- Areas/ (ongoing responsibilities)
- Resources/ (reference materials)
- Archives/ (inactive items)

**Project workflow:**
1. Create new project in Projects/ with `obsidian_create_project`
2. Use frontmatter to track project status
3. Use tags for cross-cutting concerns
4. When complete, move to Archives/ and update links

**Finding work in progress:**
```
Find all active projects:
{
  "operation": "find_by_tags",
  "tags": ["status/active"],
  "match_all": true
}
```

**Regular cleanup:**
Use date queries to find stale projects:
```
{
  "folder_path": "Projects",
  "days_back": 90,
  "include_content": false
}
```

Any project not touched in 90 days is a candidate for archiving.

## Frontmatter Link Normalization

The MCP automatically normalizes ALL wiki-links in both frontmatter and content when writing files. This ensures clean, consistent links throughout your vault.

### What Gets Normalized

**In Frontmatter:**
```yaml
# Before (problematic)
---
category: "[[../index|Red Ocean New Entrants]]"
related: "[[../../Research/mental_models.md]]"
tags:
  - daily-progress
  - research-planning
date: 2025-11-16
---

# After (normalized)
---
category: "[[index|Red Ocean New Entrants]]"
related: "[[mental_models]]"
tags: [daily-progress, research-planning]
date: [[2025-11-16]]
---
```

**In Content:**
```markdown
# Before
This is based on [[../some/path/file.md]] and [[../../Research/article.md]].

# After
This is based on [[file]] and [[article]].
```

### How It Works

1. **Checks file existence**: Only normalizes links to files that actually exist in your vault
2. **Removes relative paths**: `../` and `./` are stripped
3. **Extracts filename**: `path/to/file.md` becomes `file`
4. **Removes .md extension**: Obsidian convention
5. **Preserves display text**: `[[file|Display Text]]` stays intact
6. **Works everywhere**: Frontmatter fields, list items, content body
7. **No false positives**: Links to non-existent files remain unchanged

### Benefits

- **No false positives**: Only links to existing files are normalized - prevents broken links
- **Consistent links**: No more `[[../../path]]` vs `[[path]]` confusion
- **Vault portability**: Links work regardless of folder structure
- **Obsidian native**: Matches how Obsidian resolves links internally
- **Automatic**: Happens transparently when writing content
- **Safe**: Display text and link semantics are preserved
- **Clean reading lists**: Book/article titles that don't exist as files stay as plain text, not broken links

### Example: Daily Progress Notes

When you create a daily progress note, the template automatically uses wiki-links:

```yaml
---
date: [[2025-11-16]]
type: daily_progress
project: "[[My Research]]"
tags: [daily-progress, research-planning]
---

# Daily Progress - [[2025-11-16]]
```

All dates and project names are clickable wiki-links that work with Obsidian's graph view, backlinks, and navigation.

## Configuration

```json
{
  "mcpServers": {
    "mcp-obsidian-thinking": {
      "command": "/path/to/mcp-obsidian-thinking/.venv/bin/python",
      "args": ["-m", "mcp_obsidian"],
      "env": {
        "OBSIDIAN_MODE": "api",
        "OBSIDIAN_API_KEY": "your-api-key-here",
        "OBSIDIAN_HOST": "127.0.0.1",
        "OBSIDIAN_PORT": "27124"
      }
    }
  }
}
```

#### For Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-obsidian-thinking": {
      "command": "/path/to/mcp-obsidian-thinking/.venv/bin/python",
      "args": ["-m", "mcp_obsidian"],
      "env": {
        "OBSIDIAN_MODE": "api",
        "OBSIDIAN_API_KEY": "your-api-key-here",
        "OBSIDIAN_HOST": "127.0.0.1",
        "OBSIDIAN_PORT": "27124"
      }
    }
  }
}
```

**Get your API key:** Open Obsidian → Settings → Local REST API → Copy the API key

**Restart** Raycast or Claude Desktop after configuration.

---

## How to Use

### Basic Commands

```
@mcp-obsidian-thinking what did I work on this week?
@mcp-obsidian-thinking search for all notes about "machine learning"
@mcp-obsidian-thinking create a new project called "AI Research"
@mcp-obsidian-thinking summarize my recent changes
```

### Key Features

**File Operations**
- Read, write, search, and organize files
- Automatic wiki-link creation for file mentions
- Smart filename search across entire vault

**Research Projects**
- Create structured project folders (Chats/, Research/, Daily Progress/)
- Track daily progress with dated notes
- Organize research materials

**Thinking Mode** 
- Add frontmatter to control AI behavior:
  ```yaml
  ---
  mode: thinking
  instructions: |
    You are my thinking partner, not my ghostwriter.
    Help me explore ideas, don't write artifacts for me.
  ---
  ```
- AI automatically reads and follows these instructions

**Recent Activity**
- Get recent changes: "what changed this week?"
- Track folder progress: "catch me up on my Projects folder"
- Find files by date range

---

## GitHub Mode (Optional)

Work with your vault as a Git repository instead of using the Obsidian API.

### Setup

```bash
# Clone your vault repository
git clone git@github.com:username/vault.git /path/to/vault
```

### Configuration

```json
{
  "mcpServers": {
    "mcp-obsidian-thinking": {
      "command": "/path/to/mcp-obsidian-thinking/.venv/bin/python",
      "args": ["-m", "mcp_obsidian"],
      "env": {
        "OBSIDIAN_MODE": "github",
        "VAULT_PATH": "/path/to/vault",
        "GITHUB_REPO": "git@github.com:username/vault.git"
      }
    }
  }
}
```

**Sync changes:** `@mcp-obsidian-thinking sync my vault`

---

## Troubleshooting

### "API key required" error
- Check Obsidian → Settings → Local REST API → Ensure plugin is enabled
- Copy the API key and update your config file
- Restart Raycast/Claude Desktop

### "Connection refused" error
- Ensure Obsidian is running
- Check the port number in Settings → Local REST API (default: 27124)
- Update `OBSIDIAN_PORT` in your config if different

### Tools timing out
- This is normal for large vaults (100+ files)
- The server limits queries to avoid timeouts
- Use specific folder searches when possible

### After updating code
```bash
cd /path/to/mcp-obsidian-thinking
.venv/bin/pip install -e .
# Restart Raycast or Claude Desktop
```

---

## All Available Tools

**File Operations**
- `list_files_in_vault` - List all files in vault root
- `list_files_in_dir` - List files in specific folder
- `get_file_contents` - Read a single file
- `batch_get_file_contents` - Read multiple files
- `simple_search` - Search vault by text
- `complex_search` - Advanced JsonLogic queries
- `put_content` - Create or update file
- `append_content` - Append to file
- `patch_content` - Insert at heading/block
- `delete_file` - Delete file or folder

**Metadata & Organization**
- `frontmatter` - Read/update/delete frontmatter
- `tags` - Work with tags
- `links` - Manage internal links
- `attachments` - Handle attachments

**Date & Progress**
- `get_recent_changes` - Recently modified files
- `files_by_date` - Files in date range
- `folder_progress` - Folder activity summary
- `get_periodic_note` - Current daily/weekly note
- `get_recent_periodic_notes` - Recent periodic notes

**Projects**
- `create_project` - New project structure
- `create_daily_progress` - Daily progress note

**Git (GitHub mode only)**
- `git_sync` - Commit and push changes

---

## Tips

1. **Start conversations with context**: "@mcp-obsidian-thinking" tells Claude to use your vault
2. **Use thinking mode**: Add frontmatter to control AI behavior in research notes
3. **Organize with projects**: Use `create_project` for structured research
4. **Track progress**: Use daily progress notes to document learning
5. **Search effectively**: Use simple search for text, complex search for metadata

---

## Credits

Inspired by Noah Brier's "thinking partner" workflow from the AI & I podcast.

Built with [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic.

---

## License

MIT
