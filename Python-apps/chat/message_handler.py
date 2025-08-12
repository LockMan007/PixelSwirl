# message_handler.py

import datetime
from config import MESSAGE_TYPE_TEXT, MESSAGE_TYPE_IMAGE, MESSAGE_TYPE_DOCUMENT, MESSAGE_TYPE_VIDEO

class Message:
    """
    Represents a single chat message with its content and metadata.
    """
    def __init__(self, sender, content, message_type=MESSAGE_TYPE_TEXT):
        """
        Initializes a Message object.
        """
        self.sender = sender
        self.content = content
        self.message_type = message_type
        self.timestamp = datetime.datetime.now()

    def to_dict(self):
        """
        Serializes the message object into a dictionary for transmission.
        """
        return {
            'sender': self.sender,
            'content': self.content,
            'type': self.message_type,
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data):
        """
        Deserializes a dictionary into a Message object.
        """
        sender = data.get('sender')
        content = data.get('content')
        message_type = data.get('type', MESSAGE_TYPE_TEXT)
        message = cls(sender, content, message_type)
        message.timestamp = datetime.datetime.fromisoformat(data.get('timestamp'))
        return message

    def __repr__(self):
        """Returns a string representation of the message."""
        return f"Message(sender='{self.sender}', type={self.message_type}, content='{self.content}')"