import requests
import urllib.parse
import os
import re
import yaml
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

class Obsidian():
    def __init__(
            self, 
            api_key: str,
            protocol: str = os.getenv('OBSIDIAN_PROTOCOL', 'https').lower(),
            host: str = str(os.getenv('OBSIDIAN_HOST', '127.0.0.1')),
            port: int = int(os.getenv('OBSIDIAN_PORT', '27124')),
            verify_ssl: bool = False,
        ):
        self.api_key = api_key
        
        if protocol == 'http':
            self.protocol = 'http'
        else:
            self.protocol = 'https' # Default to https for any other value, including 'https'

        self.host = host
        self.port = port
        self.verify_ssl = verify_ssl
        self.timeout = (3, 6)
        self._file_existence_cache = {}  # Cache for file existence checks

    def get_base_url(self) -> str:
        return f'{self.protocol}://{self.host}:{self.port}'
    
    def _get_headers(self) -> dict:
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        return headers

    def _safe_call(self, f) -> Any:
        try:
            return f()
        except requests.HTTPError as e:
            error_data = e.response.json() if e.response.content else {}
            code = error_data.get('errorCode', -1) 
            message = error_data.get('message', '<unknown>')
            raise Exception(f"Error {code}: {message}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    def list_files_in_vault(self) -> Any:
        url = f"{self.get_base_url()}/vault/"
        
        def call_fn():
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()['files']

        return self._safe_call(call_fn)

        
    def list_files_in_dir(self, dirpath: str) -> Any:
        url = f"{self.get_base_url()}/vault/{dirpath}/"
        
        def call_fn():
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()['files']

        return self._safe_call(call_fn)

    def get_file_contents(self, filepath: str) -> Any:
        url = f"{self.get_base_url()}/vault/{filepath}"
    
        def call_fn():
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            
            return response.text

        return self._safe_call(call_fn)
    
    def get_batch_file_contents(self, filepaths: list[str]) -> str:
        """Get contents of multiple files and concatenate them with headers.
        
        Args:
            filepaths: List of file paths to read
            
        Returns:
            String containing all file contents with headers
        """
        result = []
        
        for filepath in filepaths:
            try:
                content = self.get_file_contents(filepath)
                result.append(f"# {filepath}\n\n{content}\n\n---\n\n")
            except Exception as e:
                # Add error message but continue processing other files
                result.append(f"# {filepath}\n\nError reading file: {str(e)}\n\n---\n\n")
                
        return "".join(result)

    def search(self, query: str, context_length: int = 100) -> Any:
        url = f"{self.get_base_url()}/search/simple/"
        params = {
            'query': query,
            'contextLength': context_length
        }
        
        def call_fn():
            response = requests.post(url, headers=self._get_headers(), params=params, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            return response.json()

        return self._safe_call(call_fn)
    
    def append_content(self, filepath: str, content: str) -> Any:
        # AUTO-LINK: Process content before appending
        content = self._auto_link_content(content)
        
        url = f"{self.get_base_url()}/vault/{filepath}"
        
        def call_fn():
            response = requests.post(
                url, 
                headers=self._get_headers() | {'Content-Type': 'text/markdown'}, 
                data=content,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return None

        return self._safe_call(call_fn)
    
    def patch_content(self, filepath: str, operation: str, target_type: str, target: str, content: str) -> Any:
        # AUTO-LINK: Process content before patching
        content = self._auto_link_content(content)
        
        url = f"{self.get_base_url()}/vault/{filepath}"
        
        headers = self._get_headers() | {
            'Content-Type': 'text/markdown',
            'Operation': operation,
            'Target-Type': target_type,
            'Target': urllib.parse.quote(target)
        }
        
        def call_fn():
            response = requests.patch(url, headers=headers, data=content, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            return None

        return self._safe_call(call_fn)

    def put_content(self, filepath: str, content: str) -> Any:
        # AUTO-LINK: Process content before writing
        content = self._auto_link_content(content)
        
        url = f"{self.get_base_url()}/vault/{filepath}"
        
        def call_fn():
            response = requests.put(
                url, 
                headers=self._get_headers() | {'Content-Type': 'text/markdown'}, 
                data=content,
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return None

        return self._safe_call(call_fn)
    
    def delete_file(self, filepath: str) -> Any:
        """Delete a file or directory from the vault.
        
        Args:
            filepath: Path to the file to delete (relative to vault root)
            
        Returns:
            None on success
        """
        url = f"{self.get_base_url()}/vault/{filepath}"
        
        def call_fn():
            response = requests.delete(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            return None
            
        return self._safe_call(call_fn)
    
    def search_json(self, query: dict) -> Any:
        url = f"{self.get_base_url()}/search/"
        
        headers = self._get_headers() | {
            'Content-Type': 'application/vnd.olrapi.jsonlogic+json'
        }
        
        def call_fn():
            response = requests.post(url, headers=headers, json=query, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            return response.json()

        return self._safe_call(call_fn)
    
    def get_periodic_note(self, period: str, type: str = "content") -> Any:
        """Get current periodic note for the specified period.
        
        Args:
            period: The period type (daily, weekly, monthly, quarterly, yearly)
            type: Type of the data to get ('content' or 'metadata'). 
                'content' returns just the content in Markdown format. 
                'metadata' includes note metadata (including paths, tags, etc.) and the content.. 
            
        Returns:
            Content of the periodic note
        """
        url = f"{self.get_base_url()}/periodic/{period}/"
        
        def call_fn():
            headers = self._get_headers()
            if type == "metadata":
                headers['Accept'] = 'application/vnd.olrapi.note+json'
            response = requests.get(url, headers=headers, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            
            return response.text

        return self._safe_call(call_fn)
    
    def get_recent_periodic_notes(self, period: str, limit: int = 5, include_content: bool = False) -> Any:
        """Get most recent periodic notes for the specified period type.
        
        Args:
            period: The period type (daily, weekly, monthly, quarterly, yearly)
            limit: Maximum number of notes to return (default: 5)
            include_content: Whether to include note content (default: False)
            
        Returns:
            List of recent periodic notes
        """
        url = f"{self.get_base_url()}/periodic/{period}/recent"
        params = {
            "limit": limit,
            "includeContent": include_content
        }
        
        def call_fn():
            response = requests.get(
                url, 
                headers=self._get_headers(), 
                params=params,
                verify=self.verify_ssl, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json()

        return self._safe_call(call_fn)
    
    def get_recent_changes(self, limit: int = 10, days: int = 90) -> Any:
        """Get recently modified files in the vault.
        
        Args:
            limit: Maximum number of files to return (default: 10)
            days: Only include files modified within this many days (default: 90)
            
        Returns:
            List of recently modified files with metadata
        """
        # Build the DQL query
        query_lines = [
            "TABLE file.mtime",
            f"WHERE file.mtime >= date(today) - dur({days} days)",
            "SORT file.mtime DESC",
            f"LIMIT {limit}"
        ]
        
        # Join with proper DQL line breaks
        dql_query = "\n".join(query_lines)
        
        # Make the request to search endpoint
        url = f"{self.get_base_url()}/search/"
        headers = self._get_headers() | {
            'Content-Type': 'application/vnd.olrapi.dataview.dql+txt'
        }
        
        def call_fn():
            response = requests.post(
                url,
                headers=headers,
                data=dql_query.encode('utf-8'),
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        return self._safe_call(call_fn)
    
    def get_frontmatter(self, filepath: str) -> Dict[str, Any]:
        """Extract frontmatter from a file.
        
        Args:
            filepath: Path to the file (relative to vault root)
            
        Returns:
            Dictionary of frontmatter fields, empty dict if no frontmatter
        """
        content = self.get_file_contents(filepath)
        
        # Match YAML frontmatter (--- at start, --- at end)
        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(pattern, content, re.DOTALL)
        
        if not match:
            return {}
        
        try:
            frontmatter = yaml.safe_load(match.group(1))
            return frontmatter if isinstance(frontmatter, dict) else {}
        except yaml.YAMLError:
            return {}
    
    def update_frontmatter(self, filepath: str, updates: Dict[str, Any]) -> None:
        """Update frontmatter fields in a file, merging with existing.
        
        Args:
            filepath: Path to the file (relative to vault root)
            updates: Dictionary of fields to update
        """
        content = self.get_file_contents(filepath)
        
        # Extract existing frontmatter and content
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)'
        match = re.match(pattern, content, re.DOTALL)
        
        if match:
            # File has existing frontmatter
            try:
                existing_fm = yaml.safe_load(match.group(1))
                existing_fm = existing_fm if isinstance(existing_fm, dict) else {}
            except yaml.YAMLError:
                existing_fm = {}
            
            body_content = match.group(2)
        else:
            # No existing frontmatter
            existing_fm = {}
            body_content = content
        
        # Merge updates
        existing_fm.update(updates)
        
        # Rebuild file content
        fm_yaml = yaml.dump(existing_fm, default_flow_style=False, allow_unicode=True)
        new_content = f"---\n{fm_yaml}---\n{body_content}"
        
        self.put_content(filepath, new_content)
    
    def delete_frontmatter_field(self, filepath: str, field: str) -> None:
        """Delete a specific field from frontmatter.
        
        Args:
            filepath: Path to the file (relative to vault root)
            field: Field name to delete
        """
        content = self.get_file_contents(filepath)
        
        # Extract existing frontmatter and content
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)'
        match = re.match(pattern, content, re.DOTALL)
        
        if not match:
            # No frontmatter, nothing to delete
            return
        
        try:
            existing_fm = yaml.safe_load(match.group(1))
            existing_fm = existing_fm if isinstance(existing_fm, dict) else {}
        except yaml.YAMLError:
            return
        
        body_content = match.group(2)
        
        # Remove the field if it exists
        if field in existing_fm:
            del existing_fm[field]
        
        # Rebuild file content
        if existing_fm:
            fm_yaml = yaml.dump(existing_fm, default_flow_style=False, allow_unicode=True)
            new_content = f"---\n{fm_yaml}---\n{body_content}"
        else:
            # No frontmatter left, just use body
            new_content = body_content
        
        self.put_content(filepath, new_content)
    
    def get_all_tags(self) -> list[str]:
        """Extract all unique tags from the vault.
        
        Returns:
            List of unique tags (without # prefix)
        """
        # Use complex search to find all markdown files
        query = {"glob": ["*.md", {"var": "path"}]}
        results = self.search_json(query)
        
        tags = set()
        for file_info in results:
            filepath = file_info.get('path', '')
            try:
                # Get tags from this file
                file_tags = self.get_tags_from_file(filepath)
                tags.update(file_tags)
            except:
                pass
        
        return sorted(list(tags))
    
    def get_tags_from_file(self, filepath: str) -> list[str]:
        """Extract tags from a specific file (frontmatter + inline).
        
        Args:
            filepath: Path to the file (relative to vault root)
            
        Returns:
            List of tags (without # prefix)
        """
        tags = set()
        content = self.get_file_contents(filepath)
        
        # Get tags from frontmatter
        frontmatter = self.get_frontmatter(filepath)
        if 'tags' in frontmatter:
            fm_tags = frontmatter['tags']
            if isinstance(fm_tags, list):
                tags.update(str(tag).lstrip('#') for tag in fm_tags)
            elif isinstance(fm_tags, str):
                tags.add(fm_tags.lstrip('#'))
        
        # Get inline tags (e.g., #tag or #nested/tag)
        inline_tag_pattern = r'#([a-zA-Z][a-zA-Z0-9/_-]*)'
        inline_tags = re.findall(inline_tag_pattern, content)
        tags.update(inline_tags)
        
        return sorted(list(tags))
    
    def find_files_by_tags(self, tags: list[str], match_all: bool = False) -> list[str]:
        """Find files matching tag query.
        
        Args:
            tags: List of tags to search for (without # prefix)
            match_all: If True, file must have all tags (AND). If False, any tag (OR)
            
        Returns:
            List of file paths matching the tag criteria
        """
        # Get all markdown files
        query = {"glob": ["*.md", {"var": "path"}]}
        results = self.search_json(query)
        
        matching_files = []
        for file_info in results:
            filepath = file_info.get('path', '')
            try:
                file_tags = set(self.get_tags_from_file(filepath))
                search_tags = set(tag.lstrip('#') for tag in tags)
                
                if match_all:
                    # All tags must be present
                    if search_tags.issubset(file_tags):
                        matching_files.append(filepath)
                else:
                    # Any tag can be present
                    if search_tags.intersection(file_tags):
                        matching_files.append(filepath)
            except:
                pass
        
        return matching_files
    
    def list_attachments(self, folder_path: str = "attachments") -> list[Dict[str, Any]]:
        """List all files in attachments folder with metadata.
        
        Args:
            folder_path: Path to attachments folder (default: "attachments")
            
        Returns:
            List of file info dictionaries with path, size, and type
        """
        try:
            files = self.list_files_in_dir(folder_path)
            attachment_list = []
            
            for file_path in files:
                if file_path.endswith('/'):
                    continue  # Skip directories
                    
                # Get basic file info
                file_info = {
                    'path': file_path,
                    'name': file_path.split('/')[-1],
                    'extension': file_path.split('.')[-1] if '.' in file_path else ''
                }
                attachment_list.append(file_info)
            
            return attachment_list
        except:
            return []
    
    def find_attachment_references(self, filepath: str) -> list[str]:
        """Find all files that reference a specific attachment.
        
        Args:
            filepath: Path to the attachment file
            
        Returns:
            List of file paths that reference this attachment
        """
        filename = filepath.split('/')[-1]
        # Search for files containing this filename
        results = self.search(filename, context_length=50)
        
        referencing_files = []
        for result in results:
            ref_file = result.get('filename', '')
            if ref_file and ref_file != filepath:
                referencing_files.append(ref_file)
        
        return referencing_files
    
    def rename_attachment(self, old_path: str, new_name: str) -> None:
        """Rename an attachment and update all references.
        
        Args:
            old_path: Current path to the attachment
            new_name: New filename (without directory path)
        """
        # Get directory from old path
        old_filename = old_path.split('/')[-1]
        directory = '/'.join(old_path.split('/')[:-1])
        new_path = f"{directory}/{new_name}" if directory else new_name
        
        # Find all files that reference this attachment
        referencing_files = self.find_attachment_references(old_path)
        
        # Get the attachment content
        try:
            content = self.get_file_contents(old_path)
            
            # Create file with new name
            self.put_content(new_path, content)
            
            # Update all references
            for ref_file in referencing_files:
                try:
                    file_content = self.get_file_contents(ref_file)
                    # Replace old filename with new filename
                    updated_content = file_content.replace(old_filename, new_name)
                    self.put_content(ref_file, updated_content)
                except:
                    pass
            
            # Delete old file
            self.delete_file(old_path)
        except Exception as e:
            raise Exception(f"Failed to rename attachment: {str(e)}")
    
    def get_links_in_file(self, filepath: str) -> Dict[str, list[str]]:
        """Extract all links from a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Dictionary with 'wiki_links' and 'markdown_links' lists
        """
        content = self.get_file_contents(filepath)
        
        # Wiki-style links: [[Link]] or [[Link|Display]]
        wiki_pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
        wiki_links = re.findall(wiki_pattern, content)
        
        # Markdown links: [Display](url)
        md_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        md_links = re.findall(md_pattern, content)
        md_links = [url for _, url in md_links if not url.startswith('http')]
        
        return {
            'wiki_links': wiki_links,
            'markdown_links': md_links
        }
    
    def get_backlinks(self, filepath: str) -> list[str]:
        """Find all files that link to a specific file.
        
        Args:
            filepath: Path to the target file
            
        Returns:
            List of file paths that link to this file
        """
        # Get filename without extension for wiki links
        filename = filepath.split('/')[-1]
        basename = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # Search for references to this file
        results = self.search(basename, context_length=100)
        
        backlinks = []
        for result in results:
            ref_file = result.get('filename', '')
            if ref_file and ref_file != filepath:
                # Check if it actually contains a link
                try:
                    links = self.get_links_in_file(ref_file)
                    all_links = links['wiki_links'] + links['markdown_links']
                    if any(basename in link or filepath in link for link in all_links):
                        backlinks.append(ref_file)
                except:
                    pass
        
        return list(set(backlinks))
    
    def update_links(self, old_path: str, new_path: str) -> int:
        """Update all links when a file is renamed/moved.
        
        Args:
            old_path: Old file path
            new_path: New file path
            
        Returns:
            Number of files updated
        """
        old_basename = old_path.split('/')[-1].rsplit('.', 1)[0] if '.' in old_path else old_path.split('/')[-1]
        new_basename = new_path.split('/')[-1].rsplit('.', 1)[0] if '.' in new_path else new_path.split('/')[-1]
        
        # Find files that link to the old path
        backlinks = self.get_backlinks(old_path)
        
        updated_count = 0
        for ref_file in backlinks:
            try:
                content = self.get_file_contents(ref_file)
                
                # Update wiki links
                content = re.sub(
                    r'\[\[' + re.escape(old_basename) + r'(\|[^\]]+)?\]\]',
                    f'[[{new_basename}\\1]]',
                    content
                )
                
                # Update markdown links
                content = re.sub(
                    r'\[([^\]]+)\]\(' + re.escape(old_path) + r'\)',
                    f'[\\1]({new_path})',
                    content
                )
                
                self.put_content(ref_file, content)
                updated_count += 1
            except:
                pass
        
        return updated_count
    
    def get_files_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        folder_path: str = "",
        days_back: Optional[int] = None,
        include_content: bool = False
    ) -> list[Dict[str, Any]]:
        """Get files created/modified in date range.
        
        Args:
            start_date: Start date in ISO format (YYYY-MM-DD) or None
            end_date: End date in ISO format (YYYY-MM-DD) or None
            folder_path: Filter by folder path (empty string for all)
            days_back: Alternative to start_date - get files from last N days
            include_content: Whether to include file content
            
        Returns:
            List of file info dictionaries
        """
        # Calculate date range
        if days_back is not None:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=days_back)
        else:
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime.min
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime.max
        
        # Use DQL query to get files
        days_val = days_back if days_back else 365
        dql_query = f"""
TABLE file.mtime, file.ctime
WHERE file.mtime >= date(today) - dur({days_val} days)
SORT file.mtime DESC
"""
        
        url = f"{self.get_base_url()}/search/"
        headers = self._get_headers() | {
            'Content-Type': 'application/vnd.olrapi.dataview.dql+txt'
        }
        
        def call_fn():
            response = requests.post(
                url,
                headers=headers,
                data=dql_query.encode('utf-8'),
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        
        results = self._safe_call(call_fn)
        
        # Filter by folder if specified
        filtered_results = []
        for result in results:
            path = result.get('path', '')
            if folder_path and not path.startswith(folder_path):
                continue
            
            if include_content:
                try:
                    result['content'] = self.get_file_contents(path)
                except:
                    result['content'] = None
            
            filtered_results.append(result)
        
        return filtered_results
    
    def get_folder_progress(
        self,
        folder_path: str,
        days_back: int = 3,
        include_content: bool = False
    ) -> Dict[str, Any]:
        """Get progress summary for a folder.
        
        Args:
            folder_path: Path to the folder
            days_back: Number of days to look back
            include_content: Whether to include file content
            
        Returns:
            Dictionary with progress information
        """
        files = self.get_files_by_date_range(
            folder_path=folder_path,
            days_back=days_back,
            include_content=include_content
        )
        
        return {
            'folder': folder_path,
            'days_back': days_back,
            'file_count': len(files),
            'files': files
        }
    
    def create_folder_structure(
        self,
        base_path: str,
        template: str = "research_project"
    ) -> Dict[str, Any]:
        """Create a folder structure from a template.
        
        Args:
            base_path: Base path for the project
            template: Template name (default: "research_project")
            
        Returns:
            Dictionary with created paths
        """
        templates = {
            "research_project": {
                "folders": ["Chats", "Research", "Daily Progress"],
                "files": {
                    "README.md": "",
                    "index.md": f"""---
project: {base_path}
status: active
stage: exploration
mode: thinking
instructions: |
  CRITICAL: I am in THINKING mode, not WRITING mode.
  
  DO NOT write articles, guides, or drafts for me.
  Only help me explore and deepen my thinking about this project.
  
  Your role is to:
  - Ask me probing questions to clarify my thoughts
  - Help me identify patterns and connections
  - Challenge my assumptions constructively
  - Suggest areas to explore further
  - Summarize what I've learned so far
  - Organize research materials
  
  You are my thinking partner, not my ghostwriter.
---

# {base_path}

## Overview

## Key Questions

## Resources

## Next Steps
"""
                }
            },
            "simple": {
                "folders": [],
                "files": {
                    "index.md": f"# {base_path}\n\nCreated on {datetime.now().strftime('%Y-%m-%d')}\n"
                }
            }
        }
        
        if template not in templates:
            template = "research_project"
        
        template_config = templates[template]
        created_paths = {
            'folders': [],
            'files': []
        }
        
        # Create subfolders
        for folder in template_config["folders"]:
            folder_path = f"{base_path}/{folder}"
            # Create a placeholder file to ensure folder exists
            placeholder_path = f"{folder_path}/.placeholder"
            try:
                self.put_content(placeholder_path, "")
                created_paths['folders'].append(folder_path)
            except:
                pass
        
        # Create initial files
        for filename, content in template_config["files"].items():
            file_path = f"{base_path}/{filename}"
            try:
                self.put_content(file_path, content)
                created_paths['files'].append(file_path)
            except:
                pass
        
        return created_paths
    
    def create_daily_progress_note(
        self,
        project_path: str,
        date: Optional[str] = None
    ) -> str:
        """Create a daily progress note in a project's Daily Progress folder.
        
        Args:
            project_path: Path to the project (e.g., "Projects/My Research")
            date: Optional date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            Path to the created daily progress note
        """
        from datetime import datetime
        
        # Use today's date if not provided
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Convert date format from YYYY-MM-DD to YYYY_MM_DD
        date_formatted = date.replace('-', '_')
        
        # Create the file path
        filename = f"daily_progress_{date_formatted}.md"
        file_path = f"{project_path}/Daily Progress/{filename}"
        
        # Create the content with frontmatter
        content = f"""---
date: [[{date}]]
type: daily_progress
project: "[[{project_path.split('/')[-1]}]]"
tags: [daily-progress, research-planning]
---

# Daily Progress - [[{date}]]

## What I Learned Today

## Key Insights

## Questions & Challenges

## Next Steps

## Resources Referenced
"""
        
        # Write the file
        self.put_content(file_path, content)
        
        return file_path
    
    # ========================================
    # Automatic Internal Linking Methods
    # ========================================
    
    def _format_as_wiki_link(self, filepath: str) -> str:
        """Convert filepath to Obsidian wiki-link format.
        
        Obsidian can resolve links by just the filename, so we extract
        just the filename without the path for cleaner links.
        
        Args:
            filepath: Path like "Research/file.md" or "folder/subfolder/note.md"
            
        Returns:
            Wiki-link like "[[file]]" (just filename, without path or .md extension)
        """
        # Extract just the filename from the path
        filename = filepath.split('/')[-1]
        
        # Remove .md extension (Obsidian convention)
        if filename.endswith('.md'):
            filename = filename[:-3]
        
        return f"[[{filename}]]"
    
    def _file_exists_in_vault(self, filepath: str) -> bool:
        """Check if a file exists in the vault.
        
        Uses caching to avoid repeated API calls.
        
        Args:
            filepath: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        # Check cache first
        if filepath in self._file_existence_cache:
            return self._file_existence_cache[filepath]
        
        # Try to get file contents
        try:
            self.get_file_contents(filepath)
            self._file_existence_cache[filepath] = True
            return True
        except:
            self._file_existence_cache[filepath] = False
            return False
    
    def _is_in_code_block(self, content: str, position: int) -> bool:
        """Check if a position in content is inside a code block.
        
        Args:
            content: The full content string
            position: Position to check
            
        Returns:
            True if position is inside a code block, False otherwise
        """
        # Count code block markers before this position
        before = content[:position]
        triple_backticks = before.count('```')
        
        # Count single backticks (excluding those in triple backticks)
        single_backticks = before.count('`') - (triple_backticks * 3)
        
        # If odd number of markers, we're inside a code block
        return (triple_backticks % 2 == 1) or (single_backticks % 2 == 1)
    
    def _normalize_frontmatter_links(self, frontmatter_text: str) -> str:
        """Normalize wiki-links in frontmatter YAML.
        
        Removes relative paths (../, ./) and full paths from wiki-links in frontmatter,
        leaving only the filename. Only normalizes links to files that actually exist.
        
        Args:
            frontmatter_text: The YAML frontmatter text (without --- delimiters)
            
        Returns:
            Normalized frontmatter text
        """
        def normalize_yaml_link(match):
            original_link = match.group(0)
            link_content = match.group(1)
            
            # Skip if it's a display text link like [[file|Display Text]]
            if '|' in link_content:
                parts = link_content.split('|', 1)
                link_path = parts[0].strip()
                display_text = parts[1].strip()
                
                # Normalize the link path part
                # Remove ../ and ./ prefixes
                normalized_path = re.sub(r'(?:\.\.\/|\.\/)+', '', link_path)
                # Extract just filename
                if '/' in normalized_path:
                    normalized_path = normalized_path.split('/')[-1]
                # Remove .md extension
                if normalized_path.endswith('.md'):
                    normalized_path = normalized_path[:-3]
                
                # Check if file exists (try both original path and normalized filename)
                # First try the original path (in case it's a valid path)
                original_path_clean = re.sub(r'(?:\.\.\/|\.\/)+', '', link_path)
                if original_path_clean.endswith('.md'):
                    original_path_clean = original_path_clean[:-3]
                    
                if (self._file_exists_in_vault(original_path_clean) or 
                    self._file_exists_in_vault(original_path_clean + '.md') or
                    self._file_exists_in_vault(normalized_path) or 
                    self._file_exists_in_vault(normalized_path + '.md')):
                    return f"[[{normalized_path}|{display_text}]]"
                else:
                    # File doesn't exist, return original link unchanged
                    return original_link
            else:
                # Remove ../ and ./ prefixes
                normalized_content = re.sub(r'(?:\.\.\/|\.\/)+', '', link_content)
                # Extract just filename from path
                if '/' in normalized_content:
                    normalized_content = normalized_content.split('/')[-1]
                # Remove .md extension if present
                if normalized_content.endswith('.md'):
                    normalized_content = normalized_content[:-3]
                
                # Check if file exists (try both original path and normalized filename)
                # First try the original path (in case it's a valid path)
                original_path_clean = re.sub(r'(?:\.\.\/|\.\/)+', '', link_content)
                if original_path_clean.endswith('.md'):
                    original_path_clean = original_path_clean[:-3]
                    
                if (self._file_exists_in_vault(original_path_clean) or 
                    self._file_exists_in_vault(original_path_clean + '.md') or
                    self._file_exists_in_vault(normalized_content) or 
                    self._file_exists_in_vault(normalized_content + '.md')):
                    return f"[[{normalized_content}]]"
                else:
                    # File doesn't exist, return original link unchanged
                    return original_link
        
        # Normalize all wiki-links in frontmatter
        return re.sub(r'\[\[([^\]]+)\]\]', normalize_yaml_link, frontmatter_text)
    
    def _auto_link_content(self, content: str) -> str:
        """Automatically convert file path mentions to wiki-links.
        
        Detects patterns like:
        - "path/to/file.md"
        - "Research/mental_models.md"
        - "Daily Notes/2024-01-15.md"
        
        And converts to: [[filename]]
        
        Also normalizes existing wiki-links to use clean filename format.
        Processes both frontmatter and content body.
        
        Args:
            content: Content to process (including frontmatter if present)
            
        Returns:
            Content with file paths converted to wiki-links and frontmatter normalized
        """
        # Check if content has frontmatter
        if content.startswith('---\n'):
            # Split frontmatter from content
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                # parts[0] is empty, parts[1] is frontmatter, parts[2] is content
                frontmatter = parts[1]
                body = parts[2]
                
                # Normalize frontmatter links
                normalized_frontmatter = self._normalize_frontmatter_links(frontmatter)
                
                # Process body content (existing logic below)
                processed_body = self._process_body_content(body)
                
                # Reassemble
                return f"---\n{normalized_frontmatter}---\n{processed_body}"
            
        # No frontmatter, process as body content
        return self._process_body_content(content)
    
    def _process_body_content(self, content: str) -> str:
        """Process the body content (non-frontmatter) for auto-linking.
        
        Args:
            content: Body content to process
            
        Returns:
            Processed content with normalized links
        """
        # First, normalize any existing wiki-links that have paths
        # This handles cases where Claude or users write [[../../path/file]] or [[path/to/file]]
        def normalize_wiki_link(match):
            original_link = match.group(0)
            link_content = match.group(1)
            
            # Skip if it's a display text link like [[file|Display Text]]
            if '|' in link_content:
                parts = link_content.split('|', 1)
                link_path = parts[0].strip()
                display_text = parts[1].strip()
                
                # Normalize the link path part
                # Remove ../ and ./ prefixes
                normalized_path = re.sub(r'(?:\.\.\/|\.\/)+', '', link_path)
                # Extract just filename
                if '/' in normalized_path:
                    normalized_path = normalized_path.split('/')[-1]
                # Remove .md extension
                if normalized_path.endswith('.md'):
                    normalized_path = normalized_path[:-3]
                
                # Check if file exists (try both original path and normalized filename)
                original_path_clean = re.sub(r'(?:\.\.\/|\.\/)+', '', link_path)
                if original_path_clean.endswith('.md'):
                    original_path_clean = original_path_clean[:-3]
                    
                if (self._file_exists_in_vault(original_path_clean) or 
                    self._file_exists_in_vault(original_path_clean + '.md') or
                    self._file_exists_in_vault(normalized_path) or 
                    self._file_exists_in_vault(normalized_path + '.md')):
                    return f"[[{normalized_path}|{display_text}]]"
                else:
                    # File doesn't exist, return original link unchanged
                    return original_link
            else:
                # Remove ../ and ./ prefixes
                normalized_content = re.sub(r'(?:\.\.\/|\.\/)+', '', link_content)
                # Extract just filename from path
                if '/' in normalized_content:
                    normalized_content = normalized_content.split('/')[-1]
                # Remove .md extension if present
                if normalized_content.endswith('.md'):
                    normalized_content = normalized_content[:-3]
                
                # Check if file exists (try both original path and normalized filename)
                original_path_clean = re.sub(r'(?:\.\.\/|\.\/)+', '', link_content)
                if original_path_clean.endswith('.md'):
                    original_path_clean = original_path_clean[:-3]
                    
                if (self._file_exists_in_vault(original_path_clean) or 
                    self._file_exists_in_vault(original_path_clean + '.md') or
                    self._file_exists_in_vault(normalized_content) or 
                    self._file_exists_in_vault(normalized_content + '.md')):
                    return f"[[{normalized_content}]]"
                else:
                    # File doesn't exist, return original link unchanged
                    return original_link
        
        # Normalize all existing wiki-links
        content = re.sub(r'\[\[([^\]]+)\]\]', normalize_wiki_link, content)
        
        # Skip further processing if content already has many wiki-links (likely already processed)
        existing_links = re.findall(r'\[\[[^\]]+\]\]', content)
        if len(existing_links) > 10:
            return content
        
        # Find all potential file path mentions
        potential_paths = []
        
        # Pattern 1: Quoted paths with .md extension
        potential_paths.extend(re.findall(r'"([^"]+\.md)"', content))
        potential_paths.extend(re.findall(r"'([^']+\.md)'", content))
        
        # Pattern 2: Contextual mentions (after keywords)
        contextual = re.findall(
            r'(?:from|in|see|based on|according to|source:|reference:)\s+([A-Za-z0-9_\-\s/]+\.md)',
            content,
            re.IGNORECASE
        )
        potential_paths.extend(contextual)
        
        # Pattern 3: Standalone file paths with folder structure
        standalone = re.findall(r'\b([A-Za-z0-9_\-\s/]+/[A-Za-z0-9_\-\s/]+\.md)\b', content)
        potential_paths.extend(standalone)
        
        # Process each unique path
        for path in set(potential_paths):
            path = path.strip()
            
            # Skip if empty
            if not path:
                continue
            
            # Skip URLs
            if path.startswith('http://') or path.startswith('https://'):
                continue
            
            # Skip if already a wiki-link
            path_without_ext = path[:-3] if path.endswith('.md') else path
            if f'[[{path}]]' in content or f'[[{path_without_ext}]]' in content:
                continue
            
            # Check if file exists in vault
            if self._file_exists_in_vault(path):
                wiki_link = self._format_as_wiki_link(path)
                
                # Replace the path with wiki-link
                # Use word boundaries and negative lookbehind/lookahead to avoid replacing inside quotes initially
                # But do replace quoted paths
                escaped_path = re.escape(path)
                
                # Replace quoted versions first
                content = re.sub(rf'"{escaped_path}"', wiki_link, content)
                content = re.sub(rf"'{escaped_path}'", wiki_link, content)
                
                # Then replace unquoted standalone mentions
                # Avoid replacing if it's already part of a wiki-link
                content = re.sub(
                    rf'(?<!\[\[)(?<!")(?<!\')(?<!\w){escaped_path}(?!\]\])(?!")(?!\')(?!\w)',
                    wiki_link,
                    content
                )
        
        return content
