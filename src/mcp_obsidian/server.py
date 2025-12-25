import json
import logging
from collections.abc import Sequence
from functools import lru_cache
from typing import Any
import os
from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

load_dotenv()

from . import tools
from .backend import VaultBackend
from .obsidian import ObsidianAPIBackend
from .github_backend import GitHubBackend

# Load environment variables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-obsidian")

# Backend factory
_backend_instance = None

def get_backend() -> VaultBackend:
    """Get the configured backend instance (singleton)."""
    global _backend_instance
    
    if _backend_instance is None:
        obsidian_mode = os.getenv("OBSIDIAN_MODE", "api").lower()
        
        if obsidian_mode == "github":
            # GitHub mode
            vault_path = os.getenv("VAULT_PATH")
            github_repo = os.getenv("GITHUB_REPO")
            github_token = os.getenv("GITHUB_TOKEN")
            
            if not vault_path:
                raise ValueError("VAULT_PATH required for GitHub mode")
            if not github_repo:
                raise ValueError("GITHUB_REPO required for GitHub mode")
            
            logger.info(f"Initializing GitHub backend: {vault_path}")
            _backend_instance = GitHubBackend(vault_path, github_repo, github_token)
        else:
            # API mode (default)
            api_key = os.getenv("OBSIDIAN_API_KEY")
            if not api_key:
                raise ValueError(f"OBSIDIAN_API_KEY required for API mode. Working directory: {os.getcwd()}")
            
            logger.info("Initializing Obsidian API backend")
            _backend_instance = ObsidianAPIBackend(
                api_key=api_key,
                protocol=os.getenv('OBSIDIAN_PROTOCOL', 'https'),
                host=os.getenv('OBSIDIAN_HOST', '127.0.0.1'),
                port=int(os.getenv('OBSIDIAN_PORT', '27124')),
                verify_ssl=False
            )
    
    return _backend_instance

app = Server("mcp-obsidian")

# Export get_backend for use in tools
__all__ = ['get_backend']

tool_handlers = {}
def add_tool_handler(tool_class: tools.ToolHandler):
    global tool_handlers

    tool_handlers[tool_class.name] = tool_class

def get_tool_handler(name: str) -> tools.ToolHandler | None:
    if name not in tool_handlers:
        return None
    
    return tool_handlers[name]

add_tool_handler(tools.ListFilesInDirToolHandler())
add_tool_handler(tools.ListFilesInVaultToolHandler())
add_tool_handler(tools.GetFileContentsToolHandler())
add_tool_handler(tools.SearchToolHandler())
add_tool_handler(tools.PatchContentToolHandler())
add_tool_handler(tools.AppendContentToolHandler())
add_tool_handler(tools.PutContentToolHandler())
add_tool_handler(tools.DeleteFileToolHandler())
add_tool_handler(tools.ComplexSearchToolHandler())
add_tool_handler(tools.BatchGetFileContentsToolHandler())
add_tool_handler(tools.PeriodicNotesToolHandler())
add_tool_handler(tools.RecentPeriodicNotesToolHandler())
add_tool_handler(tools.RecentChangesToolHandler())
add_tool_handler(tools.FrontmatterToolHandler())
add_tool_handler(tools.TagToolHandler())
add_tool_handler(tools.AttachmentManagementToolHandler())
add_tool_handler(tools.LinkManagementToolHandler())
add_tool_handler(tools.DateRangeToolHandler())
add_tool_handler(tools.ProgressSummaryToolHandler())
add_tool_handler(tools.FolderTemplateToolHandler())
add_tool_handler(tools.DailyProgressNoteToolHandler())
add_tool_handler(tools.GitSyncToolHandler())

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""

    return [th.get_tool_description() for th in tool_handlers.values()]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls for command line run."""
    
    if not isinstance(arguments, dict):
        raise RuntimeError("arguments must be dictionary")


    tool_handler = get_tool_handler(name)
    if not tool_handler:
        raise ValueError(f"Unknown tool: {name}")

    try:
        return tool_handler.run_tool(arguments)
    except Exception as e:
        logger.error(str(e))
        raise RuntimeError(f"Caught Exception. Error: {str(e)}")


async def main():

    # Import here to avoid issues with event loops
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )
