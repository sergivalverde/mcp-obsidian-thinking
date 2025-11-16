from collections.abc import Sequence
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import json
import os
from . import obsidian

api_key = os.getenv("OBSIDIAN_API_KEY", "")
obsidian_host = os.getenv("OBSIDIAN_HOST", "127.0.0.1")

if api_key == "":
    raise ValueError(f"OBSIDIAN_API_KEY environment variable required. Working directory: {os.getcwd()}")

TOOL_LIST_FILES_IN_VAULT = "obsidian_list_files_in_vault"
TOOL_LIST_FILES_IN_DIR = "obsidian_list_files_in_dir"

def _format_frontmatter_instructions(frontmatter: dict) -> str:
    """Format frontmatter instructions as a prominent header.
    
    Args:
        frontmatter: Dictionary of frontmatter fields
        
    Returns:
        Formatted instruction header string, or empty string if no instructions
    """
    # Check for behavioral instructions in frontmatter
    has_instructions = any(key in frontmatter for key in ['mode', 'instructions', 'ai_instructions', 'behavior'])
    
    if not has_instructions:
        return ""
    
    # Build prominent instruction header
    instruction_parts = []
    instruction_parts.append("=" * 80)
    instruction_parts.append("⚠️  CRITICAL: FRONTMATTER INSTRUCTIONS DETECTED")
    instruction_parts.append("=" * 80)
    
    if 'mode' in frontmatter:
        mode = frontmatter['mode']
        instruction_parts.append(f"\n🎯 MODE: {mode.upper()}")
        
        if mode == 'thinking':
            instruction_parts.append("\n⚠️  YOU ARE IN THINKING MODE - DO NOT CREATE CONTENT!")
            instruction_parts.append("Your role: Ask questions, explore ideas, organize research.")
            instruction_parts.append("NOT your role: Write drafts, create outlines, generate artifacts.")
    
    if 'instructions' in frontmatter:
        instruction_parts.append(f"\n📋 INSTRUCTIONS:\n{frontmatter['instructions']}")
    
    if 'ai_instructions' in frontmatter:
        instruction_parts.append(f"\n📋 AI INSTRUCTIONS:\n{frontmatter['ai_instructions']}")
    
    if 'behavior' in frontmatter:
        instruction_parts.append(f"\n🤖 BEHAVIOR:\n{frontmatter['behavior']}")
    
    # Add other relevant frontmatter fields
    if 'stage' in frontmatter:
        instruction_parts.append(f"\n📊 STAGE: {frontmatter['stage']}")
    
    if 'status' in frontmatter:
        instruction_parts.append(f"\n📌 STATUS: {frontmatter['status']}")
    
    instruction_parts.append("\n" + "=" * 80)
    instruction_parts.append("END OF INSTRUCTIONS - FOLLOW THEM STRICTLY")
    instruction_parts.append("=" * 80)
    
    return "\n".join(instruction_parts)

class ToolHandler():
    def __init__(self, tool_name: str):
        self.name = tool_name

    def get_tool_description(self) -> Tool:
        raise NotImplementedError()

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        raise NotImplementedError()
    
class ListFilesInVaultToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(TOOL_LIST_FILES_IN_VAULT)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all files and directories in the root directory of your Obsidian vault.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            },
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        files = api.list_files_in_vault()

        return [
            TextContent(
                type="text",
                text=json.dumps(files, indent=2)
            )
        ]
    
class ListFilesInDirToolHandler(ToolHandler):
    def __init__(self):
        super().__init__(TOOL_LIST_FILES_IN_DIR)

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Lists all files and directories that exist in a specific Obsidian directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dirpath": {
                        "type": "string",
                        "description": "Path to list files from (relative to your vault root). Note that empty directories will not be returned."
                    },
                },
                "required": ["dirpath"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:

        if "dirpath" not in args:
            raise RuntimeError("dirpath argument missing in arguments")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        files = api.list_files_in_dir(args["dirpath"])

        return [
            TextContent(
                type="text",
                text=json.dumps(files, indent=2)
            )
        ]
    
class GetFileContentsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_file_contents")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Return the content of a single file in your vault. IMPORTANT: If the file contains frontmatter with 'mode', 'instructions', or behavioral directives, these will be prominently displayed at the top of the response. You MUST follow these instructions strictly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the relevant file (relative to your vault root).",
                        "format": "path"
                    },
                },
                "required": ["filepath"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepath" not in args:
            raise RuntimeError("filepath argument missing in arguments")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        content = api.get_file_contents(args["filepath"])
        
        # Extract and highlight frontmatter instructions
        try:
            frontmatter = api.get_frontmatter(args["filepath"])
            instruction_header = _format_frontmatter_instructions(frontmatter)
            
            if instruction_header:
                # Combine instructions with content
                formatted_output = instruction_header + "\n\n" + content
                
                return [
                    TextContent(
                        type="text",
                        text=formatted_output
                    )
                ]
        except:
            # If frontmatter extraction fails, just return content
            pass

        return [
            TextContent(
                type="text",
                text=content
            )
        ]
    
class SearchToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_simple_search")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="""Simple search for documents matching a specified text query across all files in the vault. 
            Use this tool when you want to do a simple text search""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to a simple search for in the vault."
                    },
                    "context_length": {
                        "type": "integer",
                        "description": "How much context to return around the matching string (default: 100)",
                        "default": 100
                    }
                },
                "required": ["query"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "query" not in args:
            raise RuntimeError("query argument missing in arguments")

        context_length = args.get("context_length", 100)
        
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.search(args["query"], context_length)
        
        formatted_results = []
        for result in results:
            formatted_matches = []
            for match in result.get('matches', []):
                context = match.get('context', '')
                match_pos = match.get('match', {})
                start = match_pos.get('start', 0)
                end = match_pos.get('end', 0)
                
                formatted_matches.append({
                    'context': context,
                    'match_position': {'start': start, 'end': end}
                })
                
            formatted_results.append({
                'filename': result.get('filename', ''),
                'score': result.get('score', 0),
                'matches': formatted_matches
            })

        return [
            TextContent(
                type="text",
                text=json.dumps(formatted_results, indent=2)
            )
        ]
    
class AppendContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_append_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Append content to a new or existing file in the vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file (relative to vault root)",
                       "format": "path"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content to append to the file"
                   }
               },
               "required": ["filepath", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args or "content" not in args:
           raise RuntimeError("filepath and content arguments required")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.append_content(args.get("filepath", ""), args["content"])

       return [
           TextContent(
               type="text",
               text=f"Successfully appended content to {args['filepath']}"
           )
       ]
   
class PatchContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_patch_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Insert content into an existing note relative to a heading, block reference, or frontmatter field.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file (relative to vault root)",
                       "format": "path"
                   },
                   "operation": {
                       "type": "string",
                       "description": "Operation to perform (append, prepend, or replace)",
                       "enum": ["append", "prepend", "replace"]
                   },
                   "target_type": {
                       "type": "string",
                       "description": "Type of target to patch",
                       "enum": ["heading", "block", "frontmatter"]
                   },
                   "target": {
                       "type": "string", 
                       "description": "Target identifier (heading path, block reference, or frontmatter field)"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content to insert"
                   }
               },
               "required": ["filepath", "operation", "target_type", "target", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if not all(k in args for k in ["filepath", "operation", "target_type", "target", "content"]):
           raise RuntimeError("filepath, operation, target_type, target and content arguments required")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.patch_content(
           args.get("filepath", ""),
           args.get("operation", ""),
           args.get("target_type", ""),
           args.get("target", ""),
           args.get("content", "")
       )

       return [
           TextContent(
               type="text",
               text=f"Successfully patched content in {args['filepath']}"
           )
       ]
       
class PutContentToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_put_content")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Create a new file in your vault or update the content of an existing one in your vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the relevant file (relative to your vault root)",
                       "format": "path"
                   },
                   "content": {
                       "type": "string",
                       "description": "Content of the file you would like to upload"
                   }
               },
               "required": ["filepath", "content"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args or "content" not in args:
           raise RuntimeError("filepath and content arguments required")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.put_content(args.get("filepath", ""), args["content"])

       return [
           TextContent(
               type="text",
               text=f"Successfully uploaded content to {args['filepath']}"
           )
       ]
   

class DeleteFileToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_delete_file")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="Delete a file or directory from the vault.",
           inputSchema={
               "type": "object",
               "properties": {
                   "filepath": {
                       "type": "string",
                       "description": "Path to the file or directory to delete (relative to vault root)",
                       "format": "path"
                   },
                   "confirm": {
                       "type": "boolean",
                       "description": "Confirmation to delete the file (must be true)",
                       "default": False
                   }
               },
               "required": ["filepath", "confirm"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "filepath" not in args:
           raise RuntimeError("filepath argument missing in arguments")
       
       if not args.get("confirm", False):
           raise RuntimeError("confirm must be set to true to delete a file")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       api.delete_file(args["filepath"])

       return [
           TextContent(
               type="text",
               text=f"Successfully deleted {args['filepath']}"
           )
       ]
   
class ComplexSearchToolHandler(ToolHandler):
   def __init__(self):
       super().__init__("obsidian_complex_search")

   def get_tool_description(self):
       return Tool(
           name=self.name,
           description="""Complex search for documents using a JsonLogic query. 
           Supports standard JsonLogic operators plus 'glob' and 'regexp' for pattern matching. Results must be non-falsy.

           Use this tool when you want to do a complex search, e.g. for all documents with certain tags etc.
           ALWAYS follow query syntax in examples.

           Examples
            1. Match all markdown files
            {"glob": ["*.md", {"var": "path"}]}

            2. Match all markdown files with 1221 substring inside them
            {
              "and": [
                { "glob": ["*.md", {"var": "path"}] },
                { "regexp": [".*1221.*", {"var": "content"}] }
              ]
            }

            3. Match all markdown files in Work folder containing name Keaton
            {
              "and": [
                { "glob": ["*.md", {"var": "path"}] },
                { "regexp": [".*Work.*", {"var": "path"}] },
                { "regexp": ["Keaton", {"var": "content"}] }
              ]
            }
           """,
           inputSchema={
               "type": "object",
               "properties": {
                   "query": {
                       "type": "object",
                       "description": "JsonLogic query object. ALWAYS follow query syntax in examples. \
                            Example 1: {\"glob\": [\"*.md\", {\"var\": \"path\"}]} matches all markdown files \
                            Example 2: {\"and\": [{\"glob\": [\"*.md\", {\"var\": \"path\"}]}, {\"regexp\": [\".*1221.*\", {\"var\": \"content\"}]}]} matches all markdown files with 1221 substring inside them \
                            Example 3: {\"and\": [{\"glob\": [\"*.md\", {\"var\": \"path\"}]}, {\"regexp\": [\".*Work.*\", {\"var\": \"path\"}]}, {\"regexp\": [\"Keaton\", {\"var\": \"content\"}]}]} matches all markdown files in Work folder containing name Keaton \
                        "
                   }
               },
               "required": ["query"]
           }
       )

   def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
       if "query" not in args:
           raise RuntimeError("query argument missing in arguments")

       api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
       results = api.search_json(args.get("query", ""))

       return [
           TextContent(
               type="text",
               text=json.dumps(results, indent=2)
           )
       ]

class BatchGetFileContentsToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_batch_get_file_contents")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Return the contents of multiple files in your vault, concatenated with headers. IMPORTANT: If any file contains frontmatter with 'mode', 'instructions', or behavioral directives, these will be prominently displayed for that file. You MUST follow these instructions strictly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepaths": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Path to a file (relative to your vault root)",
                            "format": "path"
                        },
                        "description": "List of file paths to read"
                    },
                },
                "required": ["filepaths"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "filepaths" not in args:
            raise RuntimeError("filepaths argument missing in arguments")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        
        # Process each file individually to extract frontmatter instructions
        all_contents = []
        for filepath in args["filepaths"]:
            try:
                content = api.get_file_contents(filepath)
                
                # Try to extract frontmatter instructions
                try:
                    frontmatter = api.get_frontmatter(filepath)
                    instruction_header = _format_frontmatter_instructions(frontmatter)
                    
                    if instruction_header:
                        # Add file header with instructions
                        all_contents.append(f"\n{'=' * 80}")
                        all_contents.append(f"FILE: {filepath}")
                        all_contents.append('=' * 80)
                        all_contents.append(instruction_header)
                        all_contents.append(content)
                    else:
                        # Add file header without instructions
                        all_contents.append(f"\n{'=' * 80}")
                        all_contents.append(f"FILE: {filepath}")
                        all_contents.append('=' * 80)
                        all_contents.append(content)
                except:
                    # If frontmatter extraction fails, just add content with header
                    all_contents.append(f"\n{'=' * 80}")
                    all_contents.append(f"FILE: {filepath}")
                    all_contents.append('=' * 80)
                    all_contents.append(content)
            except Exception as e:
                all_contents.append(f"\n{'=' * 80}")
                all_contents.append(f"FILE: {filepath}")
                all_contents.append('=' * 80)
                all_contents.append(f"Error reading file: {str(e)}")
        
        combined_content = "\n".join(all_contents)

        return [
            TextContent(
                type="text",
                text=combined_content
            )
        ]

class PeriodicNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_periodic_note")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get current periodic note for the specified period.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "The period type (daily, weekly, monthly, quarterly, yearly)",
                        "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]
                    },
                    "type": {
                        "type": "string",
                        "description": "The type of data to get ('content' or 'metadata'). 'content' returns just the content in Markdown format. 'metadata' includes note metadata (including paths, tags, etc.) and the content.",
                        "default": "content",
                        "enum": ["content", "metadata"]
                    }
                },
                "required": ["period"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "period" not in args:
            raise RuntimeError("period argument missing in arguments")

        period = args["period"]
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if period not in valid_periods:
            raise RuntimeError(f"Invalid period: {period}. Must be one of: {', '.join(valid_periods)}")
        
        type = args["type"] if "type" in args else "content"
        valid_types = ["content", "metadata"]
        if type not in valid_types:
            raise RuntimeError(f"Invalid type: {type}. Must be one of: {', '.join(valid_types)}")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        content = api.get_periodic_note(period,type)

        return [
            TextContent(
                type="text",
                text=content
            )
        ]
        
class RecentPeriodicNotesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_recent_periodic_notes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get most recent periodic notes for the specified period type.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "The period type (daily, weekly, monthly, quarterly, yearly)",
                        "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of notes to return (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "Whether to include note content (default: false)",
                        "default": False
                    }
                },
                "required": ["period"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "period" not in args:
            raise RuntimeError("period argument missing in arguments")

        period = args["period"]
        valid_periods = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if period not in valid_periods:
            raise RuntimeError(f"Invalid period: {period}. Must be one of: {', '.join(valid_periods)}")

        limit = args.get("limit", 5)
        if not isinstance(limit, int) or limit < 1:
            raise RuntimeError(f"Invalid limit: {limit}. Must be a positive integer")
            
        include_content = args.get("include_content", False)
        if not isinstance(include_content, bool):
            raise RuntimeError(f"Invalid include_content: {include_content}. Must be a boolean")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.get_recent_periodic_notes(period, limit, include_content)

        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )
        ]
        
class RecentChangesToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_get_recent_changes")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get recently modified files in the vault.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of files to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "days": {
                        "type": "integer",
                        "description": "Only include files modified within this many days (default: 90)",
                        "minimum": 1,
                        "default": 90
                    }
                }
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        limit = args.get("limit", 10)
        if not isinstance(limit, int) or limit < 1:
            raise RuntimeError(f"Invalid limit: {limit}. Must be a positive integer")
            
        days = args.get("days", 90)
        if not isinstance(days, int) or days < 1:
            raise RuntimeError(f"Invalid days: {days}. Must be a positive integer")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        results = api.get_recent_changes(limit, days)

        return [
            TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )
        ]

class FrontmatterToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_frontmatter")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Manage frontmatter in Obsidian notes. Operations: read (get all frontmatter), update (merge fields), delete (remove field).",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform: read, update, or delete",
                        "enum": ["read", "update", "delete"]
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file (relative to vault root)",
                        "format": "path"
                    },
                    "updates": {
                        "type": "object",
                        "description": "For 'update' operation: dictionary of fields to update"
                    },
                    "field": {
                        "type": "string",
                        "description": "For 'delete' operation: field name to delete"
                    }
                },
                "required": ["operation", "filepath"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "operation" not in args or "filepath" not in args:
            raise RuntimeError("operation and filepath arguments required")

        operation = args["operation"]
        filepath = args["filepath"]
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        if operation == "read":
            frontmatter = api.get_frontmatter(filepath)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(frontmatter, indent=2)
                )
            ]
        elif operation == "update":
            if "updates" not in args:
                raise RuntimeError("updates argument required for update operation")
            api.update_frontmatter(filepath, args["updates"])
            return [
                TextContent(
                    type="text",
                    text=f"Successfully updated frontmatter in {filepath}"
                )
            ]
        elif operation == "delete":
            if "field" not in args:
                raise RuntimeError("field argument required for delete operation")
            api.delete_frontmatter_field(filepath, args["field"])
            return [
                TextContent(
                    type="text",
                    text=f"Successfully deleted field '{args['field']}' from {filepath}"
                )
            ]
        else:
            raise RuntimeError(f"Unknown operation: {operation}")

class TagToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_tags")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Work with tags in Obsidian. Operations: get_all (all unique tags), get_file_tags (tags from specific file), find_by_tags (files matching tags).",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform",
                        "enum": ["get_all", "get_file_tags", "find_by_tags"]
                    },
                    "filepath": {
                        "type": "string",
                        "description": "For 'get_file_tags': path to the file",
                        "format": "path"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "For 'find_by_tags': list of tags to search for"
                    },
                    "match_all": {
                        "type": "boolean",
                        "description": "For 'find_by_tags': if true, file must have all tags (AND), if false any tag (OR)",
                        "default": False
                    }
                },
                "required": ["operation"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "operation" not in args:
            raise RuntimeError("operation argument required")

        operation = args["operation"]
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        if operation == "get_all":
            tags = api.get_all_tags()
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"tags": tags}, indent=2)
                )
            ]
        elif operation == "get_file_tags":
            if "filepath" not in args:
                raise RuntimeError("filepath argument required for get_file_tags operation")
            tags = api.get_tags_from_file(args["filepath"])
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"filepath": args["filepath"], "tags": tags}, indent=2)
                )
            ]
        elif operation == "find_by_tags":
            if "tags" not in args:
                raise RuntimeError("tags argument required for find_by_tags operation")
            match_all = args.get("match_all", False)
            files = api.find_files_by_tags(args["tags"], match_all)
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"files": files, "tags": args["tags"], "match_all": match_all}, indent=2)
                )
            ]
        else:
            raise RuntimeError(f"Unknown operation: {operation}")

class AttachmentManagementToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_attachments")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Manage attachments in Obsidian. Operations: list (list files in attachments folder), rename (rename and update references), find_references (find files referencing an attachment).",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform",
                        "enum": ["list", "rename", "find_references"]
                    },
                    "folder_path": {
                        "type": "string",
                        "description": "For 'list': path to attachments folder",
                        "default": "attachments"
                    },
                    "filepath": {
                        "type": "string",
                        "description": "For 'rename' or 'find_references': path to the attachment"
                    },
                    "new_name": {
                        "type": "string",
                        "description": "For 'rename': new filename"
                    }
                },
                "required": ["operation"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "operation" not in args:
            raise RuntimeError("operation argument required")

        operation = args["operation"]
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        if operation == "list":
            folder_path = args.get("folder_path", "attachments")
            attachments = api.list_attachments(folder_path)
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"folder": folder_path, "attachments": attachments}, indent=2)
                )
            ]
        elif operation == "rename":
            if "filepath" not in args or "new_name" not in args:
                raise RuntimeError("filepath and new_name arguments required for rename operation")
            api.rename_attachment(args["filepath"], args["new_name"])
            return [
                TextContent(
                    type="text",
                    text=f"Successfully renamed {args['filepath']} to {args['new_name']}"
                )
            ]
        elif operation == "find_references":
            if "filepath" not in args:
                raise RuntimeError("filepath argument required for find_references operation")
            references = api.find_attachment_references(args["filepath"])
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"attachment": args["filepath"], "references": references}, indent=2)
                )
            ]
        else:
            raise RuntimeError(f"Unknown operation: {operation}")

class LinkManagementToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_links")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Manage links in Obsidian. Operations: get_links (extract links from file), get_backlinks (find files linking to this file), update_links (update links when file is renamed).",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform",
                        "enum": ["get_links", "get_backlinks", "update_links"]
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file",
                        "format": "path"
                    },
                    "old_path": {
                        "type": "string",
                        "description": "For 'update_links': old file path"
                    },
                    "new_path": {
                        "type": "string",
                        "description": "For 'update_links': new file path"
                    }
                },
                "required": ["operation"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "operation" not in args:
            raise RuntimeError("operation argument required")

        operation = args["operation"]
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)

        if operation == "get_links":
            if "filepath" not in args:
                raise RuntimeError("filepath argument required for get_links operation")
            links = api.get_links_in_file(args["filepath"])
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"filepath": args["filepath"], "links": links}, indent=2)
                )
            ]
        elif operation == "get_backlinks":
            if "filepath" not in args:
                raise RuntimeError("filepath argument required for get_backlinks operation")
            backlinks = api.get_backlinks(args["filepath"])
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"filepath": args["filepath"], "backlinks": backlinks}, indent=2)
                )
            ]
        elif operation == "update_links":
            if "old_path" not in args or "new_path" not in args:
                raise RuntimeError("old_path and new_path arguments required for update_links operation")
            count = api.update_links(args["old_path"], args["new_path"])
            return [
                TextContent(
                    type="text",
                    text=f"Successfully updated links in {count} files"
                )
            ]
        else:
            raise RuntimeError(f"Unknown operation: {operation}")

class DateRangeToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_files_by_date")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get files by date range. Supports relative dates like 'last 3 days' via days_back parameter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_back": {
                        "type": "integer",
                        "description": "Get files from last N days (alternative to start_date/end_date)",
                        "minimum": 1
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in ISO format (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in ISO format (YYYY-MM-DD)"
                    },
                    "folder_path": {
                        "type": "string",
                        "description": "Filter by folder path (empty for all)",
                        "default": ""
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "Whether to include file content",
                        "default": False
                    }
                }
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        
        files = api.get_files_by_date_range(
            start_date=args.get("start_date"),
            end_date=args.get("end_date"),
            folder_path=args.get("folder_path", ""),
            days_back=args.get("days_back"),
            include_content=args.get("include_content", False)
        )

        return [
            TextContent(
                type="text",
                text=json.dumps(files, indent=2)
            )
        ]

class ProgressSummaryToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_folder_progress")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Get progress summary for a folder. Shows all files changed in the last N days. Great for 'catch me up on last 3 days' queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Path to the folder"
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 3)",
                        "default": 3,
                        "minimum": 1
                    },
                    "include_content": {
                        "type": "boolean",
                        "description": "Whether to include file content (default: false)",
                        "default": False
                    }
                },
                "required": ["folder_path"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "folder_path" not in args:
            raise RuntimeError("folder_path argument required")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        
        progress = api.get_folder_progress(
            folder_path=args["folder_path"],
            days_back=args.get("days_back", 3),
            include_content=args.get("include_content", False)
        )

        return [
            TextContent(
                type="text",
                text=json.dumps(progress, indent=2)
            )
        ]

class FolderTemplateToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_create_project")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Create a project folder with standardized structure inside the Projects/ folder. Templates: 'research_project' (creates Chats/, Research/, Daily Progress/ subfolders) or 'simple' (just index file).",
            inputSchema={
                "type": "object",
                "properties": {
                    "base_path": {
                        "type": "string",
                        "description": "Project name or path. If it doesn't start with 'Projects/', it will be automatically prepended (e.g., 'My Research' becomes 'Projects/My Research')"
                    },
                    "template": {
                        "type": "string",
                        "description": "Template to use",
                        "enum": ["research_project", "simple"],
                        "default": "research_project"
                    }
                },
                "required": ["base_path"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "base_path" not in args:
            raise RuntimeError("base_path argument required")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        
        # Automatically prepend "Projects/" if not already present
        base_path = args["base_path"]
        if not base_path.startswith("Projects/"):
            base_path = f"Projects/{base_path}"
        
        created = api.create_folder_structure(
            base_path=base_path,
            template=args.get("template", "research_project")
        )

        return [
            TextContent(
                type="text",
                text=json.dumps(created, indent=2)
            )
        ]

class DailyProgressNoteToolHandler(ToolHandler):
    def __init__(self):
        super().__init__("obsidian_create_daily_progress")

    def get_tool_description(self):
        return Tool(
            name=self.name,
            description="Create a daily progress note in a project's Daily Progress folder with the naming format daily_progress_YYYY_MM_DD.md. Perfect for tracking daily learnings and progress on a project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project (e.g., 'Projects/My Research' or just 'My Research' if it's in Projects/)"
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional date in YYYY-MM-DD format. Defaults to today if not provided.",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                    }
                },
                "required": ["project_path"]
            }
        )

    def run_tool(self, args: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if "project_path" not in args:
            raise RuntimeError("project_path argument required")

        api = obsidian.Obsidian(api_key=api_key, host=obsidian_host)
        
        # Automatically prepend "Projects/" if not already present
        project_path = args["project_path"]
        if not project_path.startswith("Projects/"):
            project_path = f"Projects/{project_path}"
        
        file_path = api.create_daily_progress_note(
            project_path=project_path,
            date=args.get("date")
        )

        return [
            TextContent(
                type="text",
                text=f"Created daily progress note: {file_path}"
            )
        ]
