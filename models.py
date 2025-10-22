"""
Brain Hair Database Models

Models for storing chat sessions, messages, and history.
"""

from datetime import datetime
from extensions import db


class ChatSession(db.Model):
    """
    Represents a chat session between a user and the AI.

    Each session has context (ticket, client) and contains multiple messages.
    """
    __tablename__ = 'chat_sessions'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    user_id = db.Column(db.String(150), nullable=False, index=True)
    user_name = db.Column(db.String(150))

    # Context
    ticket_number = db.Column(db.String(50), index=True)
    client_name = db.Column(db.String(150), index=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime)

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)

    # Summary (auto-generated from first few messages or manually set)
    title = db.Column(db.String(255))
    summary = db.Column(db.Text)

    # Relationships
    messages = db.relationship('ChatMessage', back_populates='session',
                             cascade='all, delete-orphan',
                             order_by='ChatMessage.created_at')

    def __repr__(self):
        return f'<ChatSession {self.id} user={self.user_id} ticket={self.ticket_number}>'

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'ticket_number': self.ticket_number,
            'client_name': self.client_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'is_active': self.is_active,
            'title': self.title,
            'summary': self.summary,
            'message_count': len(self.messages) if self.messages else 0
        }


class ChatMessage(db.Model):
    """
    Represents a single message in a chat session.

    Can be from user or assistant (AI).
    """
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(36), db.ForeignKey('chat_sessions.id'), nullable=False, index=True)

    # Message data
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)

    # Tool usage tracking
    tool_calls = db.Column(db.JSON)  # List of tools called in this message
    tool_results = db.Column(db.JSON)  # Results from tool calls

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Filtering info
    was_filtered = db.Column(db.Boolean, default=False)
    filter_type = db.Column(db.String(20))  # 'phi' or 'cjis'

    # Relationships
    session = db.relationship('ChatSession', back_populates='messages')

    def __repr__(self):
        return f'<ChatMessage {self.id} session={self.session_id} role={self.role}>'

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': self.role,
            'content': self.content,
            'tool_calls': self.tool_calls,
            'tool_results': self.tool_results,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'was_filtered': self.was_filtered,
            'filter_type': self.filter_type
        }
