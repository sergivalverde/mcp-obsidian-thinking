"""GitHub-based backend for vault operations using local file system."""

import os
import subprocess
import glob
import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from .backend import VaultBackend


class GitHubBackend(VaultBackend):
    """Backend that operates on a local git clone of the vault.
    
    This backend reads/writes files directly from the file system and provides
    git sync capabilities for pushing/pulling changes to/from GitHub.
    """
    
    def __init__(self, vault_path: str, github_repo: str, github_token: Optional[str] = None):
        """Initialize GitHub backend.
        
        Args:
            vault_path: Local path to git clone (same as vault root)
            github_repo: GitHub repo URL (https or ssh format)
            github_token: Optional GitHub token for HTTPS auth
        """
        self.vault_path = Path(vault_path).resolve()
        self.github_repo = github_repo
        self.github_token = github_token
        self._file_existence_cache = {}
        
        # Validate that vault_path exists and is a git repo
        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {vault_path}")
        
        git_dir = self.vault_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"Not a git repository: {vault_path}")
        
        # Pull once at initialization
        self._git_pull()
    
    # ========================================
    # Git Operations
    # ========================================
    
    def _git_pull(self):
        """Pull latest changes from remote."""
        try:
            subprocess.run(
                ["git", "pull", "--rebase"],
                cwd=self.vault_path,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise Exception(f"Git pull failed: {e.stderr}")
    
    def git_sync(self, commit_message: str = "Update vault from MCP session"):
        """Commit and push changes to remote.
        
        Args:
            commit_message: Commit message for the changes
        """
        try:
            # Stage all changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.vault_path,
                check=True,
                capture_output=True
            )
            
            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.vault_path,
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                return {"success": True, "message": "No changes to commit"}
            
            # Commit
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.vault_path,
                check=True,
                capture_output=True
            )
            
            # Pull with auto-merge before push
            subprocess.run(
                ["git", "pull", "--rebase"],
                cwd=self.vault_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Push
            subprocess.run(
                ["git", "push"],
                cwd=self.vault_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            return {"success": True, "message": "Changes synced to GitHub"}
        except subprocess.CalledProcessError as e:
            raise Exception(f"Git sync failed: {e.stderr}")
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def _get_file_path(self, filepath: str) -> Path:
        """Convert relative filepath to absolute Path object."""
        return self.vault_path / filepath
    
    def _get_relative_path(self, absolute_path: Path) -> str:
        """Convert absolute path to relative path from vault root."""
        return str(absolute_path.relative_to(self.vault_path))
    
    def _read_file(self, filepath: str) -> str:
        """Read file contents."""
        file_path = self._get_file_path(filepath)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        return file_path.read_text(encoding='utf-8')
    
    def _write_file(self, filepath: str, content: str):
        """Write file contents."""
        file_path = self._get_file_path(filepath)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
    
    def _list_markdown_files(self, directory: Optional[Path] = None) -> List[Path]:
        """List all markdown files in directory (recursive)."""
        if directory is None:
            directory = self.vault_path
        
        md_files = []
        for path in directory.rglob("*.md"):
            if not any(part.startswith('.') for part in path.parts):
                md_files.append(path)
        return md_files
    
    # ========================================
    # Auto-linking Methods (copied from ObsidianAPIBackend)
    # ========================================
    
    def _format_as_wiki_link(self, filepath: str) -> str:
        """Convert filepath to Obsidian wiki-link format."""
        filename = filepath.split('/')[-1]
        if filename.endswith('.md'):
            filename = filename[:-3]
        return f"[[{filename}]]"
    
    def _file_exists_in_vault(self, filepath: str) -> bool:
        """Check if a file exists in the vault."""
        if filepath in self._file_existence_cache:
            return self._file_existence_cache[filepath]
        
        # Try exact path
        file_path = self._get_file_path(filepath)
        if file_path.exists():
            self._file_existence_cache[filepath] = True
            return True
        
        # If no path separators, search for filename
        if '/' not in filepath:
            search_name = filepath if not filepath.endswith('.md') else filepath[:-3]
            for md_file in self._list_markdown_files():
                if md_file.stem == search_name or md_file.name == filepath:
                    self._file_existence_cache[filepath] = True
                    return True
        
        self._file_existence_cache[filepath] = False
        return False
    
    def _is_in_code_block(self, content: str, position: int) -> bool:
        """Check if a position in content is inside a code block."""
        before_position = content[:position]
        code_blocks = re.findall(r'```', before_position)
        return len(code_blocks) % 2 == 1
    
    def _normalize_frontmatter_links(self, frontmatter_text: str) -> str:
        """Normalize wiki-links in frontmatter YAML."""
        def normalize_yaml_link(match):
            original_link = match.group(0)
            link_content = match.group(1)
            
            if '|' in link_content:
                link_path, display_text = link_content.split('|', 1)
                normalized_path = re.sub(r'(?:\.\.\/|\.\/)+', '', link_path)
                if '/' in normalized_path:
                    normalized_path = normalized_path.split('/')[-1]
                if normalized_path.endswith('.md'):
                    normalized_path = normalized_path[:-3]
                
                original_path_clean = re.sub(r'(?:\.\.\/|\.\/)+', '', link_path)
                if original_path_clean.endswith('.md'):
                    original_path_clean = original_path_clean[:-3]
                
                if (self._file_exists_in_vault(original_path_clean) or 
                    self._file_exists_in_vault(original_path_clean + '.md') or
                    self._file_exists_in_vault(normalized_path) or 
                    self._file_exists_in_vault(normalized_path + '.md')):
                    return f"[[{normalized_path}|{display_text}]]"
                else:
                    return original_link
            else:
                normalized_content = re.sub(r'(?:\.\.\/|\.\/)+', '', link_content)
                if '/' in normalized_content:
                    normalized_content = normalized_content.split('/')[-1]
                if normalized_content.endswith('.md'):
                    normalized_content = normalized_content[:-3]
                
                original_path_clean = re.sub(r'(?:\.\.\/|\.\/)+', '', link_content)
                if original_path_clean.endswith('.md'):
                    original_path_clean = original_path_clean[:-3]
                    
                if (self._file_exists_in_vault(original_path_clean) or 
                    self._file_exists_in_vault(original_path_clean + '.md') or
                    self._file_exists_in_vault(normalized_content) or 
                    self._file_exists_in_vault(normalized_content + '.md')):
                    return f"[[{normalized_content}]]"
                else:
                    return original_link
        
        return re.sub(r'\[\[([^\]]+)\]\]', normalize_yaml_link, frontmatter_text)
    
    def _process_body_content(self, content: str) -> str:
        """Process body content for auto-linking."""
        def normalize_wiki_link(match):
            original_link = match.group(0)
            link_content = match.group(1)
            
            if '|' in link_content:
                link_path, display_text = link_content.split('|', 1)
                normalized_path = re.sub(r'(?:\.\.\/|\.\/)+', '', link_path)
                if '/' in normalized_path:
                    normalized_path = normalized_path.split('/')[-1]
                if normalized_path.endswith('.md'):
                    normalized_path = normalized_path[:-3]
                
                original_path_clean = re.sub(r'(?:\.\.\/|\.\/)+', '', link_path)
                if original_path_clean.endswith('.md'):
                    original_path_clean = original_path_clean[:-3]
                
                if (self._file_exists_in_vault(original_path_clean) or 
                    self._file_exists_in_vault(original_path_clean + '.md') or
                    self._file_exists_in_vault(normalized_path) or 
                    self._file_exists_in_vault(normalized_path + '.md')):
                    return f"[[{normalized_path}|{display_text}]]"
                else:
                    return original_link
            else:
                normalized_content = re.sub(r'(?:\.\.\/|\.\/)+', '', link_content)
                if '/' in normalized_content:
                    normalized_content = normalized_content.split('/')[-1]
                if normalized_content.endswith('.md'):
                    normalized_content = normalized_content[:-3]
                
                original_path_clean = re.sub(r'(?:\.\.\/|\.\/)+', '', link_content)
                if original_path_clean.endswith('.md'):
                    original_path_clean = original_path_clean[:-3]
                    
                if (self._file_exists_in_vault(original_path_clean) or 
                    self._file_exists_in_vault(original_path_clean + '.md') or
                    self._file_exists_in_vault(normalized_content) or 
                    self._file_exists_in_vault(normalized_content + '.md')):
                    return f"[[{normalized_content}]]"
                else:
                    return original_link
        
        content = re.sub(r'\[\[([^\]]+)\]\]', normalize_wiki_link, content)
        
        existing_links = re.findall(r'\[\[[^\]]+\]\]', content)
        if len(existing_links) > 10:
            return content
        
        potential_paths = []
        potential_paths.extend(re.findall(r'"([^"]+\.md)"', content))
        potential_paths.extend(re.findall(r"'([^']+\.md)'", content))
        backtick_paths = re.findall(r'`([^`]+\.md)`', content)
        potential_paths.extend(backtick_paths)
        contextual = re.findall(
            r'(?:from|in|see|based on|according to|source:|reference:|location:)\s+[`"]?([A-Za-z0-9_\-\s/,\(\)]+\.md)[`"]?',
            content,
            re.IGNORECASE
        )
        potential_paths.extend(contextual)
        standalone = re.findall(r'\b([A-Za-z0-9_\-\s/]+/[A-Za-z0-9_\-\s/]+\.md)\b', content)
        potential_paths.extend(standalone)
        
        for path in set(potential_paths):
            path = path.strip()
            if not path:
                continue
            if path.startswith('http://') or path.startswith('https://'):
                continue
            path_without_ext = path[:-3] if path.endswith('.md') else path
            if f'[[{path}]]' in content or f'[[{path_without_ext}]]' in content:
                continue
            
            if self._file_exists_in_vault(path):
                wiki_link = self._format_as_wiki_link(path)
                escaped_path = re.escape(path)
                content = re.sub(rf'`{escaped_path}`', wiki_link, content)
                content = re.sub(rf'"{escaped_path}"', wiki_link, content)
                content = re.sub(rf"'{escaped_path}'", wiki_link, content)
                content = re.sub(
                    rf'(?<!\[\[)(?<!")(?<!\')(?<!`)(?<!\w){escaped_path}(?!\]\])(?!")(?!\')(?!`)(?!\w)',
                    wiki_link,
                    content
                )
        
        return content
    
    def _auto_link_content(self, content: str) -> str:
        """Automatically convert file path mentions to wiki-links."""
        if content.startswith('---\n'):
            parts = content.split('---\n', 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2]
                normalized_frontmatter = self._normalize_frontmatter_links(frontmatter)
                processed_body = self._process_body_content(body)
                return f"---\n{normalized_frontmatter}---\n{processed_body}"
        
        return self._process_body_content(content)
    
    # ========================================
    # File Operations
    # ========================================
    
    def list_files_in_vault(self) -> List[str]:
        """List all files in the vault."""
        files = []
        for md_file in self._list_markdown_files():
            files.append(self._get_relative_path(md_file))
        return sorted(files)
    
    def list_files_in_dir(self, dirpath: str) -> List[str]:
        """List files in a specific directory."""
        dir_path = self._get_file_path(dirpath)
        if not dir_path.exists() or not dir_path.is_dir():
            return []
        
        files = []
        for item in dir_path.iterdir():
            if item.is_file() and not item.name.startswith('.'):
                files.append(item.name)
            elif item.is_dir() and not item.name.startswith('.'):
                files.append(item.name + '/')
        return sorted(files)
    
    def get_file_contents(self, filepath: str) -> str:
        """Get contents of a file."""
        return self._read_file(filepath)
    
    def get_batch_file_contents(self, filepaths: List[str]) -> str:
        """Get contents of multiple files concatenated."""
        result = []
        for filepath in filepaths:
            try:
                content = self.get_file_contents(filepath)
                result.append(f"# {filepath}\n\n{content}\n\n---\n\n")
            except Exception as e:
                result.append(f"# {filepath}\n\nError: {str(e)}\n\n---\n\n")
        return "".join(result)
    
    def put_content(self, filepath: str, content: str) -> Dict[str, Any]:
        """Create or overwrite a file with content."""
        content = self._auto_link_content(content)
        self._write_file(filepath, content)
        return {"success": True, "filepath": filepath}
    
    def append_content(self, filepath: str, content: str) -> Dict[str, Any]:
        """Append content to a file."""
        content = self._auto_link_content(content)
        try:
            existing = self._read_file(filepath)
            new_content = existing + "\n" + content
        except FileNotFoundError:
            new_content = content
        
        self._write_file(filepath, new_content)
        return {"success": True, "filepath": filepath}
    
    def patch_content(self, filepath: str, operation: str, target_type: str, 
                     target: str, content: str) -> Dict[str, Any]:
        """Patch content in a file at a specific location."""
        content = self._auto_link_content(content)
        existing = self._read_file(filepath)
        
        # Simple implementation - for full implementation, would need to parse markdown structure
        # For now, just append
        if operation == "append":
            new_content = existing + "\n" + content
        elif operation == "prepend":
            new_content = content + "\n" + existing
        else:
            new_content = existing + "\n" + content
        
        self._write_file(filepath, new_content)
        return {"success": True, "filepath": filepath}
    
    def delete_file(self, filepath: str) -> Dict[str, Any]:
        """Delete a file."""
        file_path = self._get_file_path(filepath)
        if file_path.exists():
            file_path.unlink()
        return {"success": True, "filepath": filepath}
    
    # ========================================
    # Search Operations
    # ========================================
    
    def search(self, query: str, context_length: int = 100) -> List[Dict[str, Any]]:
        """Search for text in vault."""
        results = []
        for md_file in self._list_markdown_files():
            try:
                content = md_file.read_text(encoding='utf-8')
                if query.lower() in content.lower():
                    # Find all occurrences
                    for match in re.finditer(re.escape(query), content, re.IGNORECASE):
                        start = max(0, match.start() - context_length)
                        end = min(len(content), match.end() + context_length)
                        context = content[start:end]
                        results.append({
                            "filename": self._get_relative_path(md_file),
                            "match": context
                        })
            except:
                pass
        return results
    
    def search_json(self, query: dict) -> List[str]:
        """Search using JsonLogic query."""
        # Simplified implementation - would need jsonlogic library for full support
        # For now, return empty list
        return []
    
    # ========================================
    # Periodic Notes
    # ========================================
    
    def get_periodic_note(self, period: str, type: str = "content") -> Any:
        """Get current periodic note."""
        # This would require integration with periodic notes plugin structure
        # For now, return None
        return None
    
    def get_recent_periodic_notes(self, period: str, limit: int = 5, 
                                  include_content: bool = False) -> List[Dict[str, Any]]:
        """Get recent periodic notes."""
        # This would require integration with periodic notes plugin structure
        return []
    
    def get_recent_changes(self, limit: int = 10, days: int = 90) -> List[Dict[str, Any]]:
        """Get recently modified files."""
        cutoff_time = datetime.now() - timedelta(days=days)
        files_with_mtime = []
        
        for md_file in self._list_markdown_files():
            mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
            if mtime >= cutoff_time:
                files_with_mtime.append({
                    "path": self._get_relative_path(md_file),
                    "mtime": mtime.isoformat()
                })
        
        # Sort by mtime descending
        files_with_mtime.sort(key=lambda x: x["mtime"], reverse=True)
        return files_with_mtime[:limit]
    
    # ========================================
    # Frontmatter Operations
    # ========================================
    
    def get_frontmatter(self, filepath: str) -> Dict[str, Any]:
        """Get frontmatter from a file."""
        content = self._read_file(filepath)
        if not content.startswith('---\n'):
            return {}
        
        parts = content.split('---\n', 2)
        if len(parts) < 3:
            return {}
        
        try:
            return yaml.safe_load(parts[1]) or {}
        except:
            return {}
    
    def update_frontmatter(self, filepath: str, updates: Dict[str, Any]) -> None:
        """Update frontmatter fields in a file."""
        content = self._read_file(filepath)
        frontmatter = self.get_frontmatter(filepath)
        frontmatter.update(updates)
        
        # Remove old frontmatter
        if content.startswith('---\n'):
            parts = content.split('---\n', 2)
            body = parts[2] if len(parts) >= 3 else content
        else:
            body = content
        
        # Write new frontmatter
        new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
        new_content = f"---\n{new_frontmatter}---\n{body}"
        self._write_file(filepath, new_content)
    
    def delete_frontmatter_field(self, filepath: str, field: str) -> None:
        """Delete a frontmatter field."""
        frontmatter = self.get_frontmatter(filepath)
        if field in frontmatter:
            del frontmatter[field]
            
            content = self._read_file(filepath)
            if content.startswith('---\n'):
                parts = content.split('---\n', 2)
                body = parts[2] if len(parts) >= 3 else content
            else:
                body = content
            
            new_frontmatter = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
            new_content = f"---\n{new_frontmatter}---\n{body}"
            self._write_file(filepath, new_content)
    
    # ========================================
    # Tag Operations
    # ========================================
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags in the vault."""
        tags = set()
        for md_file in self._list_markdown_files():
            try:
                file_tags = self.get_tags_from_file(self._get_relative_path(md_file))
                tags.update(file_tags)
            except:
                pass
        return sorted(list(tags))
    
    def get_tags_from_file(self, filepath: str) -> List[str]:
        """Get tags from a specific file."""
        tags = set()
        
        # Get tags from frontmatter
        frontmatter = self.get_frontmatter(filepath)
        if 'tags' in frontmatter:
            fm_tags = frontmatter['tags']
            if isinstance(fm_tags, list):
                tags.update(fm_tags)
            elif isinstance(fm_tags, str):
                tags.add(fm_tags)
        
        # Get inline tags from content
        content = self._read_file(filepath)
        inline_tags = re.findall(r'#([a-zA-Z0-9_\-/]+)', content)
        tags.update(inline_tags)
        
        return sorted(list(tags))
    
    def find_files_by_tags(self, tags: List[str], match_all: bool = False) -> List[str]:
        """Find files by tags."""
        matching_files = []
        
        for md_file in self._list_markdown_files():
            try:
                filepath = self._get_relative_path(md_file)
                file_tags = set(self.get_tags_from_file(filepath))
                search_tags = set(tags)
                
                if match_all:
                    if search_tags.issubset(file_tags):
                        matching_files.append(filepath)
                else:
                    if search_tags.intersection(file_tags):
                        matching_files.append(filepath)
            except:
                pass
        
        return sorted(matching_files)
    
    # ========================================
    # Attachment Operations
    # ========================================
    
    def list_attachments(self, folder_path: str = "attachments") -> List[Dict[str, Any]]:
        """List files in attachments folder."""
        dir_path = self._get_file_path(folder_path)
        if not dir_path.exists():
            return []
        
        attachments = []
        for item in dir_path.iterdir():
            if item.is_file() and not item.name.startswith('.'):
                attachments.append({
                    "name": item.name,
                    "path": self._get_relative_path(item),
                    "size": item.stat().st_size
                })
        return attachments
    
    def find_attachment_references(self, filepath: str) -> List[str]:
        """Find files that reference an attachment."""
        filename = Path(filepath).name
        references = []
        
        for md_file in self._list_markdown_files():
            try:
                content = md_file.read_text(encoding='utf-8')
                if filename in content:
                    references.append(self._get_relative_path(md_file))
            except:
                pass
        
        return references
    
    def rename_attachment(self, old_path: str, new_name: str) -> None:
        """Rename an attachment and update references."""
        old_file_path = self._get_file_path(old_path)
        new_file_path = old_file_path.parent / new_name
        
        # Rename file
        old_file_path.rename(new_file_path)
        
        # Update references
        old_name = old_file_path.name
        for md_file in self._list_markdown_files():
            try:
                content = md_file.read_text(encoding='utf-8')
                if old_name in content:
                    new_content = content.replace(old_name, new_name)
                    md_file.write_text(new_content, encoding='utf-8')
            except:
                pass
    
    # ========================================
    # Link Operations
    # ========================================
    
    def get_links_in_file(self, filepath: str) -> Dict[str, List[str]]:
        """Get all links in a file."""
        content = self._read_file(filepath)
        
        # Internal links
        internal = re.findall(r'\[\[([^\]]+)\]\]', content)
        
        # External links
        external = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        external_urls = [url for _, url in external if url.startswith('http')]
        
        return {
            "internal": internal,
            "external": external_urls
        }
    
    def get_backlinks(self, filepath: str) -> List[str]:
        """Get files that link to this file."""
        filename = Path(filepath).stem
        backlinks = []
        
        for md_file in self._list_markdown_files():
            try:
                content = md_file.read_text(encoding='utf-8')
                if f'[[{filename}]]' in content or f'[[{filepath}]]' in content:
                    backlinks.append(self._get_relative_path(md_file))
            except:
                pass
        
        return backlinks
    
    def update_links(self, old_path: str, new_path: str) -> int:
        """Update links when a file is renamed."""
        old_name = Path(old_path).stem
        new_name = Path(new_path).stem
        count = 0
        
        for md_file in self._list_markdown_files():
            try:
                content = md_file.read_text(encoding='utf-8')
                if f'[[{old_name}]]' in content or f'[[{old_path}]]' in content:
                    new_content = content.replace(f'[[{old_name}]]', f'[[{new_name}]]')
                    new_content = new_content.replace(f'[[{old_path}]]', f'[[{new_path}]]')
                    md_file.write_text(new_content, encoding='utf-8')
                    count += 1
            except:
                pass
        
        return count
    
    # ========================================
    # Date Range Operations
    # ========================================
    
    def get_files_by_date_range(self, start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               days_back: Optional[int] = None,
                               folder_path: str = "",
                               include_content: bool = False) -> List[Dict[str, Any]]:
        """Get files by date range."""
        if days_back:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=days_back)
        else:
            start_dt = datetime.fromisoformat(start_date) if start_date else datetime.min
            end_dt = datetime.fromisoformat(end_date) if end_date else datetime.max
        
        search_dir = self._get_file_path(folder_path) if folder_path else self.vault_path
        results = []
        
        for md_file in self._list_markdown_files(search_dir):
            mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
            if start_dt <= mtime <= end_dt:
                result = {
                    "path": self._get_relative_path(md_file),
                    "mtime": mtime.isoformat()
                }
                if include_content:
                    result["content"] = md_file.read_text(encoding='utf-8')
                results.append(result)
        
        return sorted(results, key=lambda x: x["mtime"], reverse=True)
    
    def get_folder_progress(self, folder_path: str, days_back: int = 3,
                           include_content: bool = False) -> Dict[str, Any]:
        """Get progress summary for a folder."""
        files = self.get_files_by_date_range(
            days_back=days_back,
            folder_path=folder_path,
            include_content=include_content
        )
        
        return {
            "folder": folder_path,
            "days_back": days_back,
            "file_count": len(files),
            "files": files
        }
    
    # ========================================
    # Project/Folder Structure Operations
    # ========================================
    
    def create_folder_structure(self, base_path: str, template: str = "research_project") -> Dict[str, Any]:
        """Create a project folder with standardized structure."""
        # Ensure base_path starts with Projects/
        if not base_path.startswith("Projects/"):
            base_path = f"Projects/{base_path}"
        
        base_dir = self._get_file_path(base_path)
        base_dir.mkdir(parents=True, exist_ok=True)
        
        if template == "research_project":
            # Create subfolders
            (base_dir / "Chats").mkdir(exist_ok=True)
            (base_dir / "Research").mkdir(exist_ok=True)
            (base_dir / "Daily Progress").mkdir(exist_ok=True)
            
            # Create index.md with thinking mode frontmatter
            project_name = base_path.split('/')[-1]
            index_content = f"""---
project: {project_name}
status: active
mode: thinking
instructions: |
  You are in THINKING mode. Your role is to help me think, not to think for me.
  - Ask clarifying questions
  - Point out assumptions
  - Suggest frameworks or mental models
  - Challenge my reasoning
  - DO NOT create content, research summaries, or solutions unless explicitly asked
  - DO NOT make decisions for me
  - Help me explore ideas through dialogue
stage: exploration
---

# {project_name}

## Overview

## Key Questions

## Resources

## Notes
"""
            self._write_file(f"{base_path}/index.md", index_content)
            
            # Create empty README.md
            self._write_file(f"{base_path}/README.md", "")
            
            return {
                "success": True,
                "path": base_path,
                "folders": ["Chats", "Research", "Daily Progress"],
                "files": ["index.md", "README.md"]
            }
        else:
            # Simple template
            self._write_file(f"{base_path}/index.md", "")
            return {
                "success": True,
                "path": base_path,
                "folders": [],
                "files": ["index.md"]
            }
    
    def create_daily_progress_note(self, project_path: str, date: Optional[str] = None) -> str:
        """Create a daily progress note in a project."""
        # Ensure project_path starts with Projects/
        if not project_path.startswith("Projects/"):
            project_path = f"Projects/{project_path}"
        
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Format: daily_progress_YYYY_MM_DD.md
        date_formatted = date.replace("-", "_")
        filename = f"daily_progress_{date_formatted}.md"
        file_path = f"{project_path}/Daily Progress/{filename}"
        
        project_name = project_path.split('/')[-1]
        content = f"""---
date: [[{date}]]
type: daily_progress
project: "[[{project_name}]]"
tags: [daily-progress, research-planning]
---

# Daily Progress - [[{date}]]

## What I Learned Today

## Key Insights

## Questions That Emerged

## Next Steps

## Resources Encountered
"""
        
        self._write_file(file_path, content)
        return file_path

