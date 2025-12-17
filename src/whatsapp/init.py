"""
ماين WhatsApp البوت - نظام إدارة الحسابات المصاحبة
"""

__version__ = "1.0.0"
__author__ = "WhatsApp Bot Team"

from .client import WhatsAppClient
from .qr_handler import QRHandler
from .message_handler import MessageHandler
from .group_manager import GroupManager

__all__ = [
    "WhatsAppClient",
    "QRHandler",
    "MessageHandler",
    "GroupManager"
]
