"""Abstract backend interface for vault operations."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VaultBackend(ABC):
    """Abstract interface for vault operations.
    
    This interface defines all operations that can be performed on a vault,
    whether through the Obsidian API or direct file system access.
    """
    
    # ========================================
    # File Operations
    # ========================================
    
    @abstractmethod
    def list_files_in_vault(self) -> Any:
        """List all files in the vault."""
        pass
    
    @abstractmethod
    def list_files_in_dir(self, dirpath: str) -> Any:
        """List files in a specific directory.
        
        Args:
            dirpath: Path to directory relative to vault root
        """
        pass
    
    @abstractmethod
    def get_file_contents(self, filepath: str) -> str:
        """Get contents of a file.
        
        Args:
            filepath: Path to file relative to vault root
            
        Returns:
            File contents as string
        """
        pass
    
    @abstractmethod
    def get_batch_file_contents(self, filepaths: List[str]) -> str:
        """Get contents of multiple files concatenated.
        
        Args:
            filepaths: List of file paths
            
        Returns:
            Concatenated file contents with headers
        """
        pass
    
    @abstractmethod
    def put_content(self, filepath: str, content: str) -> Any:
        """Create or overwrite a file with content.
        
        Args:
            filepath: Path to file relative to vault root
            content: Content to write
        """
        pass
    
    @abstractmethod
    def append_content(self, filepath: str, content: str) -> Any:
        """Append content to a file.
        
        Args:
            filepath: Path to file relative to vault root
            content: Content to append
        """
        pass
    
    @abstractmethod
    def patch_content(self, filepath: str, operation: str, target_type: str, 
                     target: str, content: str) -> Any:
        """Patch content in a file at a specific location.
        
        Args:
            filepath: Path to file
            operation: Operation to perform (append, prepend, replace)
            target_type: Type of target (heading, block, frontmatter)
            target: Target identifier
            content: Content to insert
        """
        pass
    
    @abstractmethod
    def delete_file(self, filepath: str) -> Any:
        """Delete a file.
        
        Args:
            filepath: Path to file relative to vault root
        """
        pass
    
    # ========================================
    # Search Operations
    # ========================================
    
    @abstractmethod
    def search(self, query: str, context_length: int = 100) -> Any:
        """Search for text in vault.
        
        Args:
            query: Search query
            context_length: Amount of context to return
        """
        pass
    
    @abstractmethod
    def search_json(self, query: dict) -> Any:
        """Search using JsonLogic query.
        
        Args:
            query: JsonLogic query object
        """
        pass
    
    # ========================================
    # Periodic Notes
    # ========================================
    
    @abstractmethod
    def get_periodic_note(self, period: str, type: str = "content") -> Any:
        """Get current periodic note.
        
        Args:
            period: Period type (daily, weekly, monthly, etc.)
            type: Return type (content or metadata)
        """
        pass
    
    @abstractmethod
    def get_recent_periodic_notes(self, period: str, limit: int = 5, 
                                  include_content: bool = False) -> Any:
        """Get recent periodic notes.
        
        Args:
            period: Period type
            limit: Maximum number of notes
            include_content: Whether to include content
        """
        pass
    
    @abstractmethod
    def get_recent_changes(self, limit: int = 10, days: int = 90) -> Any:
        """Get recently modified files.
        
        Args:
            limit: Maximum number of files
            days: Only include files modified within this many days
        """
        pass
    
    # ========================================
    # Frontmatter Operations
    # ========================================
    
    @abstractmethod
    def get_frontmatter(self, filepath: str) -> Dict[str, Any]:
        """Get frontmatter from a file.
        
        Args:
            filepath: Path to file
            
        Returns:
            Dictionary of frontmatter fields
        """
        pass
    
    @abstractmethod
    def update_frontmatter(self, filepath: str, updates: Dict[str, Any]) -> None:
        """Update frontmatter fields in a file.
        
        Args:
            filepath: Path to file
            updates: Dictionary of fields to update
        """
        pass
    
    @abstractmethod
    def delete_frontmatter_field(self, filepath: str, field: str) -> None:
        """Delete a frontmatter field.
        
        Args:
            filepath: Path to file
            field: Field name to delete
        """
        pass
    
    # ========================================
    # Tag Operations
    # ========================================
    
    @abstractmethod
    def get_all_tags(self) -> List[str]:
        """Get all unique tags in the vault."""
        pass
    
    @abstractmethod
    def get_tags_from_file(self, filepath: str) -> List[str]:
        """Get tags from a specific file.
        
        Args:
            filepath: Path to file
        """
        pass
    
    @abstractmethod
    def find_files_by_tags(self, tags: List[str], match_all: bool = False) -> List[str]:
        """Find files by tags.
        
        Args:
            tags: List of tags to search for
            match_all: If True, file must have all tags (AND), else any tag (OR)
        """
        pass
    
    # ========================================
    # Attachment Operations
    # ========================================
    
    @abstractmethod
    def list_attachments(self, folder_path: str = "attachments") -> List[Dict[str, Any]]:
        """List files in attachments folder.
        
        Args:
            folder_path: Path to attachments folder
        """
        pass
    
    @abstractmethod
    def find_attachment_references(self, filepath: str) -> List[str]:
        """Find files that reference an attachment.
        
        Args:
            filepath: Path to attachment
        """
        pass
    
    @abstractmethod
    def rename_attachment(self, old_path: str, new_name: str) -> None:
        """Rename an attachment and update references.
        
        Args:
            old_path: Current path to attachment
            new_name: New filename
        """
        pass
    
    # ========================================
    # Link Operations
    # ========================================
    
    @abstractmethod
    def get_links_in_file(self, filepath: str) -> Dict[str, List[str]]:
        """Get all links in a file.
        
        Args:
            filepath: Path to file
            
        Returns:
            Dictionary with 'internal' and 'external' link lists
        """
        pass
    
    @abstractmethod
    def get_backlinks(self, filepath: str) -> List[str]:
        """Get files that link to this file.
        
        Args:
            filepath: Path to file
        """
        pass
    
    @abstractmethod
    def update_links(self, old_path: str, new_path: str) -> int:
        """Update links when a file is renamed.
        
        Args:
            old_path: Old file path
            new_path: New file path
            
        Returns:
            Number of files updated
        """
        pass
    
    # ========================================
    # Date Range Operations
    # ========================================
    
    @abstractmethod
    def get_files_by_date_range(self, start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               days_back: Optional[int] = None,
                               folder_path: str = "",
                               include_content: bool = False) -> List[Dict[str, Any]]:
        """Get files by date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            days_back: Alternative to start_date/end_date
            folder_path: Filter by folder
            include_content: Whether to include file content
        """
        pass
    
    @abstractmethod
    def get_folder_progress(self, folder_path: str, days_back: int = 3,
                           include_content: bool = False) -> Dict[str, Any]:
        """Get progress summary for a folder.
        
        Args:
            folder_path: Path to folder
            days_back: Number of days to look back
            include_content: Whether to include file content
        """
        pass
    
    # ========================================
    # Project/Folder Structure Operations
    # ========================================
    
    @abstractmethod
    def create_folder_structure(self, base_path: str, template: str = "research_project") -> Dict[str, Any]:
        """Create a project folder with standardized structure.
        
        Args:
            base_path: Base path for project
            template: Template name (research_project or simple)
        """
        pass
    
    @abstractmethod
    def create_daily_progress_note(self, project_path: str, date: Optional[str] = None) -> str:
        """Create a daily progress note in a project.
        
        Args:
            project_path: Path to project
            date: Date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            Path to created note
        """
        pass

