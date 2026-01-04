# MCP Obsidian - Your AI Thinking Partner

Connect Claude to your Obsidian vault for deep research and thinking work. No Dataview plugin required - uses native Obsidian features only.

---

## Quick Start

### Prerequisites
1. **Obsidian** with [Local REST API plugin](https://github.com/coddingtonbear/obsidian-local-rest-api) installed and enabled
2. **Python 3.11+**
3. **uv** package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Installation

```bash
# Clone or download this repo
cd /path/to/mcp-obsidian-thinking

# Create virtual environment and install
python3 -m venv .venv
.venv/bin/pip install -e .
```

### Configuration

#### For Raycast

Create `~/.config/raycast/mcp_servers.json`:

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
