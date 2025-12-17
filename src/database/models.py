"""
🗄️ نماذج قاعدة البيانات - تعريف الجداول والعلاقات
"""

import enum
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, 
    Boolean, DateTime, ForeignKey, JSON, Enum,
    BigInteger, Float, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session

Base = declarative_base()

class SessionStatus(enum.Enum):
    """حالات الجلسات"""
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"
    ERROR = "error"
    PENDING = "pending"

class MessageType(enum.Enum):
    """أنواع الرسائل"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    CONTACT = "contact"
    LOCATION = "location"

class LinkCategory(enum.Enum):
    """فئات الروابط"""
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    OTHER = "other"

class JoinStatus(enum.Enum):
    """حالات طلبات الانظمام"""
    PENDING = "pending"
    JOINED = "joined"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ERROR = "error"

class BroadcastStatus(enum.Enum):
    """حالات البث"""
    SCHEDULED = "scheduled"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class Session(Base):
    """جدول الجلسات"""
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=True)
    session_data = Column(Text, nullable=True)  # بيانات الجلسة المشفرة
    status = Column(Enum(SessionStatus), default=SessionStatus.PENDING)
    connected_at = Column(DateTime, default=datetime.utcnow)
    disconnected_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, nullable=True)  # بيانات إضافية
    
    # العلاقات
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_session_status', 'status'),
        Index('idx_session_phone', 'phone_number'),
    )
    
    def __repr__(self):
        return f"<Session(name='{self.name}', phone='{self.phone_number}', status='{self.status.value}')>"

class Group(Base):
    """جدول المجموعات"""
    __tablename__ = 'groups'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(100), nullable=False, index=True)  # ID من واتساب
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    participants_count = Column(Integer, default=0)
    is_admin = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, nullable=True)
    
    # المفاتيح الخارجية
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    
    # العلاقات
    session = relationship("Session", back_populates="groups")
    messages = relationship("Message", back_populates="group", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('session_id', 'group_id', name='uq_session_group'),
        Index('idx_group_name', 'name'),
        Index('idx_group_session', 'session_id'),
    )
    
    def __repr__(self):
        return f"<Group(name='{self.name}', participants={self.participants_count})>"

class Message(Base):
    """جدول الرسائل"""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(100), nullable=False, index=True)  # ID من واتساب
    sender = Column(String(100), nullable=False)
    receiver = Column(String(100), nullable=False)
    content = Column(Text, nullable=True)
    message_type = Column(Enum(MessageType), default=MessageType.TEXT)
    media_path = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_outgoing = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)
    metadata = Column(JSON, nullable=True)  # بيانات إضافية
    
    # المفاتيح الخارجية
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id', ondelete='SET NULL'), nullable=True)
    reply_to_id = Column(Integer, ForeignKey('messages.id', ondelete='SET NULL'), nullable=True)
    
    # العلاقات
    session = relationship("Session", back_populates="messages")
    group = relationship("Group", back_populates="messages")
    replies = relationship("Message", backref=relationship("parent_message", remote_side=[id]))
    
    __table_args__ = (
        Index('idx_message_timestamp', 'timestamp'),
        Index('idx_message_sender', 'sender'),
        Index('idx_message_session', 'session_id'),
        Index('idx_message_group', 'group_id'),
    )
    
    def __repr__(self):
        return f"<Message(sender='{self.sender}', type='{self.message_type.value}')>"

class Link(Base):
    """جدول الروابط المجمعة"""
    __tablename__ = 'links'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), nullable=False)
    category = Column(Enum(LinkCategory), default=LinkCategory.OTHER)
    domain = Column(String(100), nullable=False)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    found_in = Column(String(200), nullable=True)  # أين تم العثور عليه
    found_at = Column(DateTime, default=datetime.utcnow)
    is_processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # المفاتيح الخارجية
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    group_id = Column(Integer, ForeignKey('groups.id', ondelete='SET NULL'), nullable=True)
    message_id = Column(Integer, ForeignKey('messages.id', ondelete='SET NULL'), nullable=True)
    
    # العلاقات
    session = relationship("Session")
    group = relationship("Group")
    message = relationship("Message")
    
    __table_args__ = (
        UniqueConstraint('session_id', 'url', name='uq_session_link'),
        Index('idx_link_category', 'category'),
        Index('idx_link_domain', 'domain'),
        Index('idx_link_session', 'session_id'),
        Index('idx_link_processed', 'is_processed'),
    )
    
    def __repr__(self):
        return f"<Link(url='{self.url[:50]}...', category='{self.category.value}')>"

class Broadcast(Base):
    """جدول عمليات البث"""
    __tablename__ = 'broadcasts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    broadcast_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(20), default='text')  # text, image, video, etc.
    media_path = Column(String(500), nullable=True)
    target_type = Column(String(20), default='groups')  # groups, contacts, all
    target_ids = Column(JSON, nullable=True)  # قائمة IDs المستهدفين
    scheduled_for = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(Enum(BroadcastStatus), default=BroadcastStatus.SCHEDULED)
    total_targets = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    error_log = Column(Text, nullable=True)
    
    # المفاتيح الخارجية
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    
    # العلاقات
    session = relationship("Session")
    
    __table_args__ = (
        Index('idx_broadcast_status', 'status'),
        Index('idx_broadcast_session', 'session_id'),
        Index('idx_broadcast_schedule', 'scheduled_for'),
    )
    
    def __repr__(self):
        return f"<Broadcast(name='{self.name}', status='{self.status.value}')>"

class JoinRequest(Base):
    """جدول طلبات الانظمام"""
    __tablename__ = 'join_requests'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    invite_link = Column(String(500), nullable=False)
    group_name = Column(String(200), nullable=True)
    status = Column(Enum(JoinStatus), default=JoinStatus.PENDING)
    requested_at = Column(DateTime, default=datetime.utcnow)
    joined_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    attempts_count = Column(Integer, default=0)
    
    # المفاتيح الخارجية
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    
    # العلاقات
    session = relationship("Session")
    
    __table_args__ = (
        UniqueConstraint('session_id', 'invite_link', name='uq_session_invite'),
        Index('idx_join_status', 'status'),
        Index('idx_join_session', 'session_id'),
        Index('idx_join_requested', 'requested_at'),
    )
    
    def __repr__(self):
        return f"<JoinRequest(group='{self.group_name}', status='{self.status.value}')>"

class User(Base):
    """جدول المستخدمين (لإدارة البوت)"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # العلاقات
    settings = relationship("Setting", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_user_username', 'username'),
        Index('idx_user_email', 'email'),
    )
    
    def __repr__(self):
        return f"<User(username='{self.username}', is_admin={self.is_admin})>"

class Setting(Base):
    """جدول الإعدادات"""
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default='string')  # string, integer, boolean, json
    category = Column(String(50), default='general')
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # المفاتيح الخارجية
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    
    # العلاقات
    user = relationship("User", back_populates="settings")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'key', name='uq_user_setting'),
        Index('idx_setting_key', 'key'),
        Index('idx_setting_category', 'category'),
    )
    
    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{self.value[:50] if self.value else None}')>"

class Statistics(Base):
    """جدول الإحصائيات"""
    __tablename__ = 'statistics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    metric_name = Column(String(50), nullable=False)
    metric_value = Column(Float, default=0)
    metric_type = Column(String(20), default='count')  # count, sum, average
    
    # المفاتيح الخارجية
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'), nullable=True)
    
    # العلاقات
    session = relationship("Session")
    
    __table_args__ = (
        Index('idx_stats_date', 'date'),
        Index('idx_stats_metric', 'metric_name'),
        Index('idx_stats_session', 'session_id'),
    )
    
    def __repr__(self):
        return f"<Statistics(date='{self.date}', metric='{self.metric_name}', value={self.metric_value})>"

# إنشاء جميع الجداول
def create_all_tables(engine):
    """إنشاء جميع الجداول في قاعدة البيانات"""
    Base.metadata.create_all(engine)
    print("✅ تم إنشاء جميع جداول قاعدة البيانات")

# حذف جميع الجداول
def drop_all_tables(engine):
    """حذف جميع الجداول من قاعدة البيانات"""
    Base.metadata.drop_all(engine)
    print("🗑️ تم حذف جميع جداول قاعدة البيانات")
