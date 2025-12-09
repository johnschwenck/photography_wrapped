"""
Category and Group Models

Represents organizational hierarchies for photography sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict


@dataclass
class Group:
    """
    Represents a group of related sessions within a category.
    
    A group is a collection of sessions that are related, typically
    representing a recurring event or series (e.g., weekly running club).
    
    Attributes:
        id: Unique identifier (database primary key)
        name: Group name (e.g., "running_sole")
        category_id: Foreign key to parent category
        description: Optional description
        sessions: List of session IDs in this group
        total_sessions: Count of sessions in group
        total_photos: Total photos across all sessions
        created_at: When this record was created
        updated_at: When this record was last updated
    
    Example:
        >>> group = Group(
        ...     name="running_sole",
        ...     category_id=1,
        ...     description="Weekly running club at The Sole"
        ... )
    """
    
    name: str
    category_id: Optional[int] = None
    
    id: Optional[int] = None
    description: Optional[str] = None
    sessions: List[int] = field(default_factory=list)
    total_sessions: int = 0
    total_photos: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def add_session(self, session_id: int, photo_count: int = 0):
        """
        Add a session to this group.
        
        Args:
            session_id: ID of the session to add
            photo_count: Number of photos in the session
        """
        if session_id not in self.sessions:
            self.sessions.append(session_id)
            self.total_sessions = len(self.sessions)
            self.total_photos += photo_count
    
    def to_dict(self) -> dict:
        """Convert group to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'category_id': self.category_id,
            'description': self.description,
            'total_sessions': self.total_sessions,
            'total_photos': self.total_photos,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        """String representation of Group."""
        return (
            f"Group(name='{self.name}', "
            f"sessions={self.total_sessions}, photos={self.total_photos})"
        )


@dataclass
class Category:
    """
    Represents a top-level category of photography sessions.
    
    A category is the highest level of organization, representing a type
    of photography (e.g., "concerts", "running", "weddings").
    
    Attributes:
        id: Unique identifier (database primary key)
        name: Category name (e.g., "concerts", "running_sole")
        description: Optional description
        groups: List of group IDs in this category
        total_groups: Count of groups in category
        total_sessions: Total sessions across all groups
        total_photos: Total photos across all sessions
        created_at: When this record was created
        updated_at: When this record was last updated
    
    Example:
        >>> category = Category(
        ...     name="running",
        ...     description="Running club event photography"
        ... )
    """
    
    name: str
    
    id: Optional[int] = None
    description: Optional[str] = None
    groups: List[int] = field(default_factory=list)
    total_groups: int = 0
    total_sessions: int = 0
    total_photos: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def add_group(self, group_id: int, session_count: int = 0, photo_count: int = 0):
        """
        Add a group to this category.
        
        Args:
            group_id: ID of the group to add
            session_count: Number of sessions in the group
            photo_count: Total photos in the group
        """
        if group_id not in self.groups:
            self.groups.append(group_id)
            self.total_groups = len(self.groups)
            self.total_sessions += session_count
            self.total_photos += photo_count
    
    def to_dict(self) -> dict:
        """Convert category to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'total_groups': self.total_groups,
            'total_sessions': self.total_sessions,
            'total_photos': self.total_photos,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        """String representation of Category."""
        return (
            f"Category(name='{self.name}', groups={self.total_groups}, "
            f"sessions={self.total_sessions}, photos={self.total_photos})"
        )
