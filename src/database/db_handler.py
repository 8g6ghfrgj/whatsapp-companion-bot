"""
🗃️ Database Handler - معالج قاعدة البيانات
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from contextlib import asynccontextmanager

import aiosqlite
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    Base, Session, Group, Message, Link, 
    Broadcast, JoinRequest, User, Setting,
    Statistics, SessionStatus, MessageType,
    LinkCategory, JoinStatus, BroadcastStatus
)

logger = logging.getLogger(__name__)

class Database:
    """فئة معالجة قاعدة البيانات"""
    
    def __init__(self, database_url: str = None):
        """تهيئة قاعدة البيانات"""
        if database_url is None:
            # استخدام SQLite افتراضيًا
            db_path = os.path.join('data', 'whatsapp_bot.db')
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            database_url = f"sqlite:///{db_path}"
        
        self.database_url = database_url
        self.is_sqlite = 'sqlite' in database_url
        
        # تهيئة محرك SQLAlchemy
        self.engine = create_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            connect_args={'check_same_thread': False} if self.is_sqlite else {}
        )
        
        # إنشاء جلسة
        self.SessionFactory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.Session = scoped_session(self.SessionFactory)
        
        # اتصال aiosqlite للنصوص غير المتزامنة (لـ SQLite فقط)
        self.async_conn = None
        if self.is_sqlite:
            self.async_db_path = database_url.replace('sqlite:///', '')
        
        logger.info(f"📊 تم تهيئة قاعدة البيانات: {database_url}")
    
    async def initialize(self):
        """تهيئة قاعدة البيانات وإنشاء الجداول"""
        try:
            # إنشاء الجداول
            Base.metadata.create_all(self.engine)
            
            # إنشاء اتصال async لـ SQLite
            if self.is_sqlite and not os.path.exists(self.async_db_path):
                async with aiosqlite.connect(self.async_db_path) as conn:
                    await conn.execute("PRAGMA journal_mode=WAL")
                    await conn.commit()
            
            # إنشاء المستخدم الافتراضي إذا لم يكن موجودًا
            await self.create_default_user()
            
            # إنشاء الإعدادات الافتراضية
            await self.create_default_settings()
            
            logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")
            return True
            
        except Exception as e:
            logger.error(f"❌ فشل في تهيئة قاعدة البيانات: {e}")
            return False
    
    @asynccontextmanager
    async def get_session(self):
        """الحصول على جلسة قاعدة بيانات"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    async def close(self):
        """إغلاق اتصالات قاعدة البيانات"""
        try:
            self.Session.remove()
            self.engine.dispose()
            
            if self.async_conn:
                await self.async_conn.close()
            
            logger.info("🔒 تم إغلاق اتصالات قاعدة البيانات")
            
        except Exception as e:
            logger.error(f"❌ خطأ في إغلاق قاعدة البيانات: {e}")
    
    # ===== عمليات الجلسات =====
    
    async def save_session(self, session_data: Dict[str, Any]) -> bool:
        """حفظ جلسة جديدة"""
        try:
            async with self.get_session() as session:
                db_session = Session(
                    session_id=session_data['session_id'],
                    name=session_data.get('name', 'غير معروف'),
                    phone_number=session_data.get('phone_number'),
                    session_data=session_data.get('session_data'),
                    status=SessionStatus.ACTIVE,
                    connected_at=datetime.fromisoformat(session_data.get('connected_at', datetime.now().isoformat())),
                    metadata=session_data.get('metadata', {})
                )
                session.add(db_session)
                
                # تحديث الإحصائيات
                await self.update_statistics('sessions_created', 1)
                
                logger.debug(f"💾 تم حفظ الجلسة: {session_data['session_id']}")
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الجلسة: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """الحصول على جلسة بواسطة ID"""
        try:
            async with self.get_session() as session:
                db_session = session.query(Session).filter(
                    Session.session_id == session_id
                ).first()
                
                if db_session:
                    return {
                        'id': db_session.id,
                        'session_id': db_session.session_id,
                        'name': db_session.name,
                        'phone_number': db_session.phone_number,
                        'status': db_session.status.value,
                        'connected_at': db_session.connected_at.isoformat() if db_session.connected_at else None,
                        'disconnected_at': db_session.disconnected_at.isoformat() if db_session.disconnected_at else None,
                        'last_activity': db_session.last_activity.isoformat() if db_session.last_activity else None,
                        'metadata': db_session.metadata or {}
                    }
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الجلسة: {e}")
            return None
    
    async def get_sessions(self, status: str = None) -> List[Dict[str, Any]]:
        """الحصول على جميع الجلسات"""
        try:
            async with self.get_session() as session:
                query = session.query(Session)
                
                if status:
                    query = query.filter(Session.status == SessionStatus(status))
                
                db_sessions = query.order_by(Session.connected_at.desc()).all()
                
                sessions = []
                for db_session in db_sessions:
                    sessions.append({
                        'id': db_session.id,
                        'session_id': db_session.session_id,
                        'name': db_session.name,
                        'phone_number': db_session.phone_number,
                        'status': db_session.status.value,
                        'connected_at': db_session.connected_at.isoformat() if db_session.connected_at else None,
                        'last_activity': db_session.last_activity.isoformat() if db_session.last_activity else None,
                        'groups_count': len(db_session.groups)
                    })
                
                return sessions
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الجلسات: {e}")
            return []
    
    async def update_session_status(self, session_id: str, status: str, metadata: Dict = None) -> bool:
        """تحديث حالة الجلسة"""
        try:
            async with self.get_session() as session:
                db_session = session.query(Session).filter(
                    Session.session_id == session_id
                ).first()
                
                if db_session:
                    db_session.status = SessionStatus(status)
                    db_session.last_activity = datetime.utcnow()
                    
                    if status == 'disconnected' or status == 'expired':
                        db_session.disconnected_at = datetime.utcnow()
                    
                    if metadata:
                        if db_session.metadata:
                            db_session.metadata.update(metadata)
                        else:
                            db_session.metadata = metadata
                    
                    logger.debug(f"🔄 تم تحديث حالة الجلسة {session_id} إلى {status}")
                    return True
                
                logger.warning(f"⚠️ لم يتم العثور على الجلسة: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث حالة الجلسة: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """حذف جلسة"""
        try:
            async with self.get_session() as session:
                db_session = session.query(Session).filter(
                    Session.session_id == session_id
                ).first()
                
                if db_session:
                    session.delete(db_session)
                    logger.info(f"🗑️ تم حذف الجلسة: {session_id}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في حذف الجلسة: {e}")
            return False
    
    # ===== عمليات المجموعات =====
    
    async def save_group(self, group_data: Dict[str, Any]) -> bool:
        """حفظ مجموعة جديدة"""
        try:
            async with self.get_session() as session:
                # البحث عن الجلسة
                db_session = session.query(Session).filter(
                    Session.session_id == group_data['session_id']
                ).first()
                
                if not db_session:
                    logger.error(f"❌ لم يتم العثور على الجلسة: {group_data['session_id']}")
                    return False
                
                # التحقق مما إذا كانت المجموعة موجودة مسبقًا
                existing_group = session.query(Group).filter(
                    Group.session_id == db_session.id,
                    Group.group_id == group_data['group_id']
                ).first()
                
                if existing_group:
                    # تحديث المجموعة الموجودة
                    existing_group.name = group_data.get('name', existing_group.name)
                    existing_group.description = group_data.get('description', existing_group.description)
                    existing_group.participants_count = group_data.get('participants_count', existing_group.participants_count)
                    existing_group.is_admin = group_data.get('is_admin', existing_group.is_admin)
                    existing_group.last_message_at = group_data.get('last_message_at')
                    logger.debug(f"🔄 تم تحديث المجموعة: {group_data['group_id']}")
                else:
                    # إنشاء مجموعة جديدة
                    group = Group(
                        group_id=group_data['group_id'],
                        name=group_data.get('name', 'غير معروف'),
                        description=group_data.get('description'),
                        participants_count=group_data.get('participants_count', 0),
                        is_admin=group_data.get('is_admin', False),
                        joined_at=datetime.fromisoformat(group_data.get('joined_at', datetime.now().isoformat())),
                        last_message_at=group_data.get('last_message_at'),
                        session=db_session
                    )
                    session.add(group)
                    logger.debug(f"✅ تم حفظ مجموعة جديدة: {group_data['group_id']}")
                
                # تحديث الإحصائيات
                await self.update_statistics('groups_saved', 1, session_id=db_session.id)
                
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ المجموعة: {e}")
            return False
    
    async def get_groups(self, session_id: str = None) -> List[Dict[str, Any]]:
        """الحصول على المجموعات"""
        try:
            async with self.get_session() as session:
                query = session.query(Group)
                
                if session_id:
                    # البحث عن الجلسة أولاً
                    db_session = session.query(Session).filter(
                        Session.session_id == session_id
                    ).first()
                    
                    if db_session:
                        query = query.filter(Group.session_id == db_session.id)
                    else:
                        return []
                
                groups = query.order_by(Group.name).all()
                
                result = []
                for group in groups:
                    result.append({
                        'id': group.id,
                        'group_id': group.group_id,
                        'name': group.name,
                        'description': group.description,
                        'participants_count': group.participants_count,
                        'is_admin': group.is_admin,
                        'joined_at': group.joined_at.isoformat() if group.joined_at else None,
                        'last_message_at': group.last_message_at.isoformat() if group.last_message_at else None,
                        'messages_count': len(group.messages)
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب المجموعات: {e}")
            return []
    
    async def update_group_last_message(self, group_id: str, session_id: str) -> bool:
        """تحديث وقت آخر رسالة في المجموعة"""
        try:
            async with self.get_session() as session:
                db_session = session.query(Session).filter(
                    Session.session_id == session_id
                ).first()
                
                if not db_session:
                    return False
                
                group = session.query(Group).filter(
                    Group.session_id == db_session.id,
                    Group.group_id == group_id
                ).first()
                
                if group:
                    group.last_message_at = datetime.utcnow()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث آخر رسالة للمجموعة: {e}")
            return False
    
    # ===== عمليات الرسائل =====
    
    async def save_message(self, message_data: Dict[str, Any]) -> bool:
        """حفظ رسالة"""
        try:
            async with self.get_session() as session:
                # البحث عن الجلسة
                db_session = session.query(Session).filter(
                    Session.session_id == message_data['session_id']
                ).first()
                
                if not db_session:
                    logger.error(f"❌ لم يتم العثور على الجلسة: {message_data['session_id']}")
                    return False
                
                # البحث عن المجموعة إذا كان هناك group_id
                db_group = None
                if message_data.get('group_id'):
                    db_group = session.query(Group).filter(
                        Group.session_id == db_session.id,
                        Group.group_id == message_data['group_id']
                    ).first()
                
                # البحث عن الرسالة الأصل إذا كان هناك reply_to_id
                parent_message = None
                if message_data.get('reply_to_id'):
                    parent_message = session.query(Message).filter(
                        Message.message_id == message_data['reply_to_id']
                    ).first()
                
                # إنشاء الرسالة
                message = Message(
                    message_id=message_data.get('message_id', f"msg_{int(datetime.now().timestamp())}"),
                    sender=message_data.get('sender', 'unknown'),
                    receiver=message_data.get('receiver', 'unknown'),
                    content=message_data.get('content'),
                    message_type=MessageType(message_data.get('type', 'text')),
                    media_path=message_data.get('media_path'),
                    timestamp=datetime.fromisoformat(message_data.get('timestamp', datetime.now().isoformat())),
                    is_outgoing=message_data.get('is_outgoing', False),
                    is_read=message_data.get('is_read', False),
                    metadata=message_data.get('metadata', {}),
                    session=db_session,
                    group=db_group,
                    parent_message=parent_message
                )
                session.add(message)
                
                # تحديث وقت آخر رسالة في المجموعة
                if db_group:
                    db_group.last_message_at = message.timestamp
                
                # تحديث الإحصائيات
                await self.update_statistics('messages_saved', 1, session_id=db_session.id)
                
                logger.debug(f"💾 تم حفظ رسالة من {message.sender}")
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الرسالة: {e}")
            return False
    
    async def get_messages(self, session_id: str, limit: int = 100, 
                          group_id: str = None, start_date: str = None) -> List[Dict[str, Any]]:
        """الحصول على الرسائل"""
        try:
            async with self.get_session() as session:
                # البحث عن الجلسة
                db_session = session.query(Session).filter(
                    Session.session_id == session_id
                ).first()
                
                if not db_session:
                    return []
                
                query = session.query(Message).filter(
                    Message.session_id == db_session.id
                )
                
                if group_id:
                    db_group = session.query(Group).filter(
                        Group.session_id == db_session.id,
                        Group.group_id == group_id
                    ).first()
                    
                    if db_group:
                        query = query.filter(Message.group_id == db_group.id)
                
                if start_date:
                    start_datetime = datetime.fromisoformat(start_date)
                    query = query.filter(Message.timestamp >= start_datetime)
                
                messages = query.order_by(Message.timestamp.desc()).limit(limit).all()
                
                result = []
                for msg in messages:
                    result.append({
                        'id': msg.id,
                        'message_id': msg.message_id,
                        'sender': msg.sender,
                        'receiver': msg.receiver,
                        'content': msg.content,
                        'type': msg.message_type.value,
                        'timestamp': msg.timestamp.isoformat(),
                        'is_outgoing': msg.is_outgoing,
                        'is_read': msg.is_read,
                        'group_id': msg.group.group_id if msg.group else None,
                        'group_name': msg.group.name if msg.group else None
                    })
                
                return result[::-1]  # عكس الترتيب لأقدم إلى أحدث
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الرسائل: {e}")
            return []
    
    async def save_incoming_message(self, message_data: Dict[str, Any]) -> bool:
        """حفظ رسالة واردة مع معالجة خاصة"""
        try:
            # حفظ الرسالة
            success = await self.save_message(message_data)
            
            if success:
                # التحقق مما إذا كانت الرسالة تحتوي على روابط
                if message_data.get('content'):
                    # استخراج الروابط من المحتوى
                    import re
                    urls = re.findall(r'https?://[^\s]+', message_data['content'])
                    
                    if urls:
                        # حفظ كل رابط
                        for url in urls:
                            await self.save_link({
                                'session_id': message_data['session_id'],
                                'url': url,
                                'found_in': message_data.get('sender', 'unknown'),
                                'group_id': message_data.get('group_id'),
                                'message_id': message_data.get('message_id')
                            })
                
                logger.debug(f"📥 تم حفظ رسالة واردة من {message_data.get('sender')}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الرسالة الواردة: {e}")
            return False
    
    # ===== عمليات الروابط =====
    
    async def save_link(self, link_data: Dict[str, Any]) -> bool:
        """حفظ رابط"""
        try:
            async with self.get_session() as session:
                # البحث عن الجلسة
                db_session = session.query(Session).filter(
                    Session.session_id == link_data['session_id']
                ).first()
                
                if not db_session:
                    logger.error(f"❌ لم يتم العثور على الجلسة: {link_data['session_id']}")
                    return False
                
                # استخراج النطاق من الرابط
                from urllib.parse import urlparse
                parsed_url = urlparse(link_data['url'])
                domain = parsed_url.netloc
                
                # تصنيف الرابط
                category = LinkCategory.OTHER
                if 'whatsapp' in domain.lower():
                    category = LinkCategory.WHATSAPP
                elif 'telegram' in domain.lower() or 't.me' in domain:
                    category = LinkCategory.TELEGRAM
                elif 'instagram' in domain.lower():
                    category = LinkCategory.INSTAGRAM
                elif 'facebook' in domain.lower():
                    category = LinkCategory.FACEBOOK
                elif 'youtube' in domain.lower() or 'youtu.be' in domain:
                    category = LinkCategory.YOUTUBE
                elif 'tiktok' in domain.lower():
                    category = LinkCategory.TIKTOK
                elif 'twitter.com' in domain.lower() or 'x.com' in domain:
                    category = LinkCategory.TWITTER
                
                # البحث عن المجموعة إذا كان هناك group_id
                db_group = None
                if link_data.get('group_id'):
                    db_group = session.query(Group).filter(
                        Group.session_id == db_session.id,
                        Group.group_id == link_data['group_id']
                    ).first()
                
                # البحث عن الرسالة إذا كان هناك message_id
                db_message = None
                if link_data.get('message_id'):
                    db_message = session.query(Message).filter(
                        Message.message_id == link_data['message_id']
                    ).first()
                
                # التحقق من عدم تكرار الرابط لنفس الجلسة
                existing_link = session.query(Link).filter(
                    Link.session_id == db_session.id,
                    Link.url == link_data['url']
                ).first()
                
                if existing_link:
                    # تحديث الرابط الموجود
                    existing_link.found_at = datetime.utcnow()
                    existing_link.found_in = link_data.get('found_in', existing_link.found_in)
                    logger.debug(f"🔄 تم تحديث الرابط الموجود: {link_data['url'][:50]}...")
                else:
                    # إنشاء رابط جديد
                    link = Link(
                        url=link_data['url'],
                        category=category,
                        domain=domain,
                        title=link_data.get('title'),
                        description=link_data.get('description'),
                        found_in=link_data.get('found_in', 'unknown'),
                        found_at=datetime.utcnow(),
                        is_processed=False,
                        session=db_session,
                        group=db_group,
                        message=db_message,
                        metadata=link_data.get('metadata', {})
                    )
                    session.add(link)
                    logger.debug(f"✅ تم حفظ رابط جديد: {category.value} - {link_data['url'][:50]}...")
                
                # تحديث الإحصائيات
                await self.update_statistics('links_saved', 1, session_id=db_session.id)
                
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الرابط: {e}")
            return False
    
    async def get_links(self, session_id: str = None, category: str = None, 
                       processed: bool = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """الحصول على الروابط"""
        try:
            async with self.get_session() as session:
                query = session.query(Link)
                
                if session_id:
                    db_session = session.query(Session).filter(
                        Session.session_id == session_id
                    ).first()
                    
                    if db_session:
                        query = query.filter(Link.session_id == db_session.id)
                    else:
                        return []
                
                if category:
                    query = query.filter(Link.category == LinkCategory(category))
                
                if processed is not None:
                    query = query.filter(Link.is_processed == processed)
                
                links = query.order_by(Link.found_at.desc()).limit(limit).all()
                
                result = []
                for link in links:
                    result.append({
                        'id': link.id,
                        'url': link.url,
                        'category': link.category.value,
                        'domain': link.domain,
                        'title': link.title,
                        'description': link.description,
                        'found_in': link.found_in,
                        'found_at': link.found_at.isoformat() if link.found_at else None,
                        'is_processed': link.is_processed,
                        'processed_at': link.processed_at.isoformat() if link.processed_at else None,
                        'session_id': link.session.session_id if link.session else None
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الروابط: {e}")
            return []
    
    async def mark_link_processed(self, link_id: int) -> bool:
        """وضع علامة على الرابط بأنه تمت معالجته"""
        try:
            async with self.get_session() as session:
                link = session.query(Link).filter(Link.id == link_id).first()
                
                if link:
                    link.is_processed = True
                    link.processed_at = datetime.utcnow()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في وضع علامة على الرابط: {e}")
            return False
    
    async def get_links_by_category(self, session_id: str = None) -> Dict[str, List[str]]:
        """الحصول على الروابط مصنفة حسب النوع"""
        try:
            links = await self.get_links(session_id=session_id, limit=5000)
            
            categorized = {
                'whatsapp': [],
                'telegram': [],
                'instagram': [],
                'facebook': [],
                'youtube': [],
                'tiktok': [],
                'twitter': [],
                'other': []
            }
            
            for link in links:
                category = link['category']
                if category in categorized:
                    categorized[category].append(link['url'])
            
            return categorized
            
        except Exception as e:
            logger.error(f"❌ خطأ في تصنيف الروابط: {e}")
            return {}
    
    # ===== عمليات البث =====
    
    async def save_broadcast(self, broadcast_data: Dict[str, Any]) -> str:
        """حفظ عملية بث جديدة"""
        try:
            async with self.get_session() as session:
                # البحث عن الجلسة
                db_session = session.query(Session).filter(
                    Session.session_id == broadcast_data['session_id']
                ).first()
                
                if not db_session:
                    raise ValueError(f"الجلسة غير موجودة: {broadcast_data['session_id']}")
                
                # إنشاء معرف فريد للبث
                import uuid
                broadcast_id = f"bcast_{uuid.uuid4().hex[:8]}"
                
                broadcast = Broadcast(
                    broadcast_id=broadcast_id,
                    name=broadcast_data['name'],
                    content=broadcast_data['content'],
                    content_type=broadcast_data.get('content_type', 'text'),
                    media_path=broadcast_data.get('media_path'),
                    target_type=broadcast_data.get('target_type', 'groups'),
                    target_ids=broadcast_data.get('target_ids'),
                    scheduled_for=datetime.fromisoformat(broadcast_data['scheduled_for']) if broadcast_data.get('scheduled_for') else None,
                    status=BroadcastStatus.SCHEDULED,
                    total_targets=broadcast_data.get('total_targets', 0),
                    session=db_session
                )
                session.add(broadcast)
                
                logger.info(f"📢 تم إنشاء بث جديد: {broadcast_data['name']} (ID: {broadcast_id})")
                
                return broadcast_id
                
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ البث: {e}")
            raise
    
    async def update_broadcast_status(self, broadcast_id: str, status: str, 
                                     sent_count: int = 0, failed_count: int = 0, 
                                     error_log: str = None) -> bool:
        """تحديث حالة البث"""
        try:
            async with self.get_session() as session:
                broadcast = session.query(Broadcast).filter(
                    Broadcast.broadcast_id == broadcast_id
                ).first()
                
                if broadcast:
                    broadcast.status = BroadcastStatus(status)
                    
                    if status == 'sending' and not broadcast.started_at:
                        broadcast.started_at = datetime.utcnow()
                    elif status == 'completed' or status == 'failed':
                        broadcast.completed_at = datetime.utcnow()
                    
                    broadcast.sent_count = sent_count
                    broadcast.failed_count = failed_count
                    
                    if error_log:
                        broadcast.error_log = error_log
                    
                    logger.debug(f"🔄 تم تحديث حالة البث {broadcast_id} إلى {status}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث حالة البث: {e}")
            return False
    
    async def get_broadcasts(self, session_id: str = None, status: str = None) -> List[Dict[str, Any]]:
        """الحصول على عمليات البث"""
        try:
            async with self.get_session() as session:
                query = session.query(Broadcast)
                
                if session_id:
                    db_session = session.query(Session).filter(
                        Session.session_id == session_id
                    ).first()
                    
                    if db_session:
                        query = query.filter(Broadcast.session_id == db_session.id)
                    else:
                        return []
                
                if status:
                    query = query.filter(Broadcast.status == BroadcastStatus(status))
                
                broadcasts = query.order_by(Broadcast.created_at.desc()).all()
                
                result = []
                for bcast in broadcasts:
                    result.append({
                        'id': bcast.id,
                        'broadcast_id': bcast.broadcast_id,
                        'name': bcast.name,
                        'content': bcast.content[:100] + '...' if len(bcast.content) > 100 else bcast.content,
                        'content_type': bcast.content_type,
                        'target_type': bcast.target_type,
                        'status': bcast.status.value,
                        'total_targets': bcast.total_targets,
                        'sent_count': bcast.sent_count,
                        'failed_count': bcast.failed_count,
                        'scheduled_for': bcast.scheduled_for.isoformat() if bcast.scheduled_for else None,
                        'started_at': bcast.started_at.isoformat() if bcast.started_at else None,
                        'completed_at': bcast.completed_at.isoformat() if bcast.completed_at else None,
                        'session_id': bcast.session.session_id if bcast.session else None
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب عمليات البث: {e}")
            return []
    
    async def save_broadcast_results(self, results_data: Dict[str, Any]) -> bool:
        """حفظ نتائج عملية بث"""
        try:
            # هذه دالة مبسطة - في الواقع تحتاج لربط النتائج ببث معين
            logger.info(f"📊 حفظ نتائج البث: {results_data.get('total', 0)} رسائل")
            
            # تحديث الإحصائيات
            await self.update_statistics('broadcasts_sent', results_data.get('sent_count', 0))
            await self.update_statistics('broadcasts_failed', results_data.get('failed_count', 0))
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ نتائج البث: {e}")
            return False
    
    # ===== عمليات طلبات الانظمام =====
    
    async def save_group_join(self, join_data: Dict[str, Any]) -> bool:
        """حفظ طلب انظمام"""
        try:
            async with self.get_session() as session:
                # البحث عن الجلسة
                db_session = session.query(Session).filter(
                    Session.session_id == join_data['session_id']
                ).first()
                
                if not db_session:
                    logger.error(f"❌ لم يتم العثور على الجلسة: {join_data['session_id']}")
                    return False
                
                # التحقق من عدم تكرار طلب الانظمام لنفس الرابط
                existing_request = session.query(JoinRequest).filter(
                    JoinRequest.session_id == db_session.id,
                    JoinRequest.invite_link == join_data['invite_link']
                ).first()
                
                if existing_request:
                    # تحديث الطلب الموجود
                    existing_request.status = JoinStatus(join_data.get('status', 'pending'))
                    existing_request.attempts_count += 1
                    
                    if join_data.get('status') == 'joined':
                        existing_request.joined_at = datetime.fromisoformat(join_data.get('joined_at', datetime.now().isoformat()))
                    elif join_data.get('status') == 'rejected':
                        existing_request.rejected_at = datetime.fromisoformat(join_data.get('rejected_at', datetime.now().isoformat()))
                    
                    existing_request.error_message = join_data.get('error')
                    logger.debug(f"🔄 تم تحديث طلب الانظمام الموجود: {join_data['invite_link'][:50]}...")
                else:
                    # إنشاء طلب جديد
                    join_request = JoinRequest(
                        invite_link=join_data['invite_link'],
                        group_name=join_data.get('group_name'),
                        status=JoinStatus(join_data.get('status', 'pending')),
                        requested_at=datetime.fromisoformat(join_data.get('requested_at', datetime.now().isoformat())),
                        joined_at=datetime.fromisoformat(join_data.get('joined_at')) if join_data.get('joined_at') else None,
                        rejected_at=datetime.fromisoformat(join_data.get('rejected_at')) if join_data.get('rejected_at') else None,
                        error_message=join_data.get('error'),
                        attempts_count=1,
                        session=db_session
                    )
                    session.add(join_request)
                    logger.debug(f"✅ تم حفظ طلب انظمام جديد: {join_data['invite_link'][:50]}...")
                
                # تحديث الإحصائيات
                status = join_data.get('status', 'pending')
                await self.update_statistics(f'join_{status}', 1, session_id=db_session.id)
                
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ طلب الانظمام: {e}")
            return False
    
    async def get_join_requests(self, session_id: str = None, status: str = None) -> List[Dict[str, Any]]:
        """الحصول على طلبات الانظمام"""
        try:
            async with self.get_session() as session:
                query = session.query(JoinRequest)
                
                if session_id:
                    db_session = session.query(Session).filter(
                        Session.session_id == session_id
                    ).first()
                    
                    if db_session:
                        query = query.filter(JoinRequest.session_id == db_session.id)
                    else:
                        return []
                
                if status:
                    query = query.filter(JoinRequest.status == JoinStatus(status))
                
                requests = query.order_by(JoinRequest.requested_at.desc()).all()
                
                result = []
                for req in requests:
                    result.append({
                        'id': req.id,
                        'invite_link': req.invite_link,
                        'group_name': req.group_name,
                        'status': req.status.value,
                        'requested_at': req.requested_at.isoformat() if req.requested_at else None,
                        'joined_at': req.joined_at.isoformat() if req.joined_at else None,
                        'rejected_at': req.rejected_at.isoformat() if req.rejected_at else None,
                        'error_message': req.error_message,
                        'attempts_count': req.attempts_count,
                        'session_id': req.session.session_id if req.session else None
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب طلبات الانظمام: {e}")
            return []
    
    async def get_join_report(self) -> Dict[str, Any]:
        """الحصول على تقرير الانظمام"""
        try:
            async with self.get_session() as session:
                # الحصول على إحصائيات الانظمام
                total = session.query(JoinRequest).count()
                successful = session.query(JoinRequest).filter(
                    JoinRequest.status == JoinStatus.JOINED
                ).count()
                failed = session.query(JoinRequest).filter(
                    JoinRequest.status == JoinStatus.REJECTED
                ).count()
                pending = session.query(JoinRequest).filter(
                    JoinRequest.status == JoinStatus.PENDING
                ).count()
                
                # الحصول على أحدث طلبات الانظمام
                recent_requests = session.query(JoinRequest).order_by(
                    JoinRequest.requested_at.desc()
                ).limit(10).all()
                
                recent = []
                for req in recent_requests:
                    recent.append({
                        'group_name': req.group_name,
                        'status': req.status.value,
                        'requested_at': req.requested_at.isoformat() if req.requested_at else None
                    })
                
                return {
                    'total': total,
                    'successful': successful,
                    'failed': failed,
                    'pending': pending,
                    'success_rate': (successful / total * 100) if total > 0 else 0,
                    'recent_requests': recent
                }
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب تقرير الانظمام: {e}")
            return {'total': 0, 'successful': 0, 'failed': 0, 'pending': 0, 'success_rate': 0}
    
    # ===== عمليات المستخدمين والإعدادات =====
    
    async def create_default_user(self):
        """إنشاء مستخدم افتراضي"""
        try:
            async with self.get_session() as session:
                # التحقق مما إذا كان هناك مستخدمون بالفعل
                user_count = session.query(User).count()
                
                if user_count == 0:
                    import hashlib
                    
                    default_password = "admin123"  # يجب تغيير هذا في الإنتاج
                    password_hash = hashlib.sha256(default_password.encode()).hexdigest()
                    
                    default_user = User(
                        username="admin",
                        password_hash=password_hash,
                        email="admin@whatsappbot.com",
                        full_name="مدير النظام",
                        is_active=True,
                        is_admin=True
                    )
                    session.add(default_user)
                    
                    logger.info("👤 تم إنشاء المستخدم الافتراضي (admin/admin123)")
                    
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء المستخدم الافتراضي: {e}")
    
    async def create_default_settings(self):
        """إنشاء الإعدادات الافتراضية"""
        try:
            async with self.get_session() as session:
                default_settings = [
                    {'key': 'auto_collect_interval', 'value': '30', 'value_type': 'integer', 'category': 'collection', 'description': 'الفترة بين عمليات التجميع (ثانية)'},
                    {'key': 'auto_post_interval', 'value': '60', 'value_type': 'integer', 'category': 'broadcast', 'description': 'الفترة بين عمليات النشر (ثانية)'},
                    {'key': 'max_links_per_session', 'value': '10000', 'value_type': 'integer', 'category': 'collection', 'description': 'الحد الأقصى للروابط لكل جلسة'},
                    {'key': 'backup_enabled', 'value': 'true', 'value_type': 'boolean', 'category': 'system', 'description': 'تفعيل النسخ الاحتياطي التلقائي'},
                    {'key': 'backup_interval', 'value': '24', 'value_type': 'integer', 'category': 'system', 'description': 'فترة النسخ الاحتياطي (ساعة)'},
                    {'key': 'language', 'value': 'ar', 'value_type': 'string', 'category': 'ui', 'description': 'لغة الواجهة'},
                    {'key': 'timezone', 'value': 'Asia/Riyadh', 'value_type': 'string', 'category': 'system', 'description': 'المنطقة الزمنية'},
                ]
                
                for setting in default_settings:
                    existing = session.query(Setting).filter(
                        Setting.key == setting['key']
                    ).first()
                    
                    if not existing:
                        new_setting = Setting(
                            key=setting['key'],
                            value=setting['value'],
                            value_type=setting['value_type'],
                            category=setting['category'],
                            description=setting['description']
                        )
                        session.add(new_setting)
                
                logger.info("⚙️ تم إنشاء الإعدادات الافتراضية")
                
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء الإعدادات الافتراضية: {e}")
    
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """الحصول على إعداد"""
        try:
            async with self.get_session() as session:
                setting = session.query(Setting).filter(Setting.key == key).first()
                
                if setting:
                    # تحويل القيمة حسب النوع
                    if setting.value_type == 'integer':
                        return int(setting.value) if setting.value else default
                    elif setting.value_type == 'boolean':
                        return setting.value.lower() == 'true'
                    elif setting.value_type == 'json':
                        try:
                            return json.loads(setting.value) if setting.value else default
                        except:
                            return default
                    else:
                        return setting.value or default
                
                return default
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الإعداد {key}: {e}")
            return default
    
    async def update_setting(self, key: str, value: Any, value_type: str = None) -> bool:
        """تحديث إعداد"""
        try:
            async with self.get_session() as session:
                setting = session.query(Setting).filter(Setting.key == key).first()
                
                if setting:
                    setting.value = str(value)
                    if value_type:
                        setting.value_type = value_type
                    setting.updated_at = datetime.utcnow()
                else:
                    new_setting = Setting(
                        key=key,
                        value=str(value),
                        value_type=value_type or 'string',
                        updated_at=datetime.utcnow()
                    )
                    session.add(new_setting)
                
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث الإعداد {key}: {e}")
            return False
    
    # ===== عمليات الإحصائيات =====
    
    async def update_statistics(self, metric_name: str, value: float = 1, 
                               metric_type: str = 'count', session_id: int = None) -> bool:
        """تحديث الإحصائيات"""
        try:
            async with self.get_session() as session:
                # البحث عن إحصائية اليوم لنفس المقياس والجلسة
                today = datetime.utcnow().date()
                start_of_day = datetime(today.year, today.month, today.day)
                
                stat = session.query(Statistics).filter(
                    Statistics.metric_name == metric_name,
                    Statistics.date >= start_of_day
                )
                
                if session_id:
                    stat = stat.filter(Statistics.session_id == session_id)
                else:
                    stat = stat.filter(Statistics.session_id.is_(None))
                
                stat = stat.first()
                
                if stat:
                    # تحديث الإحصائية الموجودة
                    if metric_type == 'count':
                        stat.metric_value += value
                    elif metric_type == 'sum':
                        stat.metric_value = value
                    elif metric_type == 'average':
                        # هذا يحتاج منطق أكثر تعقيدًا في الواقع
                        stat.metric_value = value
                else:
                    # إنشاء إحصائية جديدة
                    stat = Statistics(
                        date=datetime.utcnow(),
                        metric_name=metric_name,
                        metric_value=value,
                        metric_type=metric_type,
                        session_id=session_id
                    )
                    session.add(stat)
                
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث الإحصائيات: {e}")
            return False
    
    async def get_statistics(self, days: int = 7, session_id: str = None) -> Dict[str, Any]:
        """الحصول على الإحصائيات"""
        try:
            async with self.get_session() as session:
                # حساب تاريخ البدء
                start_date = datetime.utcnow() - timedelta(days=days)
                
                # الحصول على إحصائيات الجلسة المحددة
                db_session = None
                if session_id:
                    db_session = session.query(Session).filter(
                        Session.session_id == session_id
                    ).first()
                
                query = session.query(Statistics).filter(
                    Statistics.date >= start_date
                )
                
                if db_session:
                    query = query.filter(Statistics.session_id == db_session.id)
                else:
                    query = query.filter(Statistics.session_id.is_(None))
                
                stats = query.order_by(Statistics.date).all()
                
                # تنظيم الإحصائيات حسب التاريخ والمقياس
                organized_stats = {}
                
                for stat in stats:
                    date_str = stat.date.strftime('%Y-%m-%d')
                    
                    if date_str not in organized_stats:
                        organized_stats[date_str] = {}
                    
                    organized_stats[date_str][stat.metric_name] = stat.metric_value
                
                # حساب الإجماليات
                totals = {}
                for date_stats in organized_stats.values():
                    for metric, value in date_stats.items():
                        if metric not in totals:
                            totals[metric] = 0
                        totals[metric] += value
                
                return {
                    'daily': organized_stats,
                    'totals': totals,
                    'period_days': days
                }
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الإحصائيات: {e}")
            return {'daily': {}, 'totals': {}, 'period_days': days}
    
    # ===== عمليات النسخ الاحتياطي =====
    
    async def backup_database(self, backup_path: str = None) -> str:
        """إنشاء نسخة احتياطية من قاعدة البيانات"""
        try:
            if not self.is_sqlite:
                logger.warning("⚠️ النسخ الاحتياطي متاح فقط لقواعد SQLite")
                return None
            
            if backup_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = os.path.join('backups', f'whatsapp_bot_backup_{timestamp}.db')
            
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # نسخ ملف قاعدة البيانات
            import shutil
            shutil.copy2(self.async_db_path, backup_path)
            
            logger.info(f"💾 تم إنشاء نسخة احتياطية في: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"❌ خطأ في النسخ الاحتياطي: {e}")
            return None
    
    async def restore_database(self, backup_path: str) -> bool:
        """استعادة قاعدة البيانات من نسخة احتياطية"""
        try:
            if not self.is_sqlite:
                logger.warning("⚠️ الاستعادة متاحة فقط لقواعد SQLite")
                return False
            
            if not os.path.exists(backup_path):
                logger.error(f"❌ ملف النسخة الاحتياطية غير موجود: {backup_path}")
                return False
            
            # إغلاق جميع الاتصالات أولاً
            await self.close()
            
            # نسخ ملف النسخة الاحتياطية
            import shutil
            shutil.copy2(backup_path, self.async_db_path)
            
            # إعادة التهيئة
            await self.initialize()
            
            logger.info(f"🔄 تم استعادة قاعدة البيانات من: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في استعادة قاعدة البيانات: {e}")
            return False
    
    # ===== وظائف مساعدة =====
    
    async def execute_raw_sql(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """تنفيذ استعلام SQL مباشر"""
        try:
            if self.is_sqlite and self.async_db_path:
                async with aiosqlite.connect(self.async_db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    
                    if params:
                        cursor = await conn.execute(sql, params)
                    else:
                        cursor = await conn.execute(sql)
                    
                    rows = await cursor.fetchall()
                    await conn.commit()
                    
                    return [dict(row) for row in rows]
            else:
                # استخدام SQLAlchemy للقواعد الأخرى
                with self.engine.connect() as conn:
                    if params:
                        result = conn.execute(text(sql), params)
                    else:
                        result = conn.execute(text(sql))
                    
                    return [dict(row._mapping) for row in result]
                    
        except Exception as e:
            logger.error(f"❌ خطأ في تنفيذ SQL: {e}")
            return []
    
    async def get_database_info(self) -> Dict[str, Any]:
        """الحصول على معلومات قاعدة البيانات"""
        try:
            async with self.get_session() as session:
                info = {
                    'database_url': self.database_url,
                    'is_sqlite': self.is_sqlite,
                    'tables': {},
                    'total_records': 0
                }
                
                # حساب عدد السجلات في كل جدول
                tables = [Session, Group, Message, Link, Broadcast, JoinRequest, User, Setting, Statistics]
                
                for table in tables:
                    count = session.query(table).count()
                    info['tables'][table.__tablename__] = count
                    info['total_records'] += count
                
                # الحصول على حجم قاعدة البيانات (لـ SQLite فقط)
                if self.is_sqlite and os.path.exists(self.async_db_path):
                    size_bytes = os.path.getsize(self.async_db_path)
                    info['database_size'] = self._bytes_to_human(size_bytes)
                
                return info
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب معلومات قاعدة البيانات: {e}")
            return {}
    
    def _bytes_to_human(self, size_bytes: int) -> str:
        """تحويل البايتات إلى صيغة مقروءة"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """تنظيف البيانات القديمة"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted_counts = {
                'messages': 0,
                'links': 0,
                'statistics': 0
            }
            
            async with self.get_session() as session:
                # حذف الرسائل القديمة
                old_messages = session.query(Message).filter(
                    Message.timestamp < cutoff_date
                )
                deleted_counts['messages'] = old_messages.count()
                old_messages.delete(synchronize_session=False)
                
                # حذف الروابط القديمة
                old_links = session.query(Link).filter(
                    Link.found_at < cutoff_date
                )
                deleted_counts['links'] = old_links.count()
                old_links.delete(synchronize_session=False)
                
                # حذف الإحصائيات القديمة
                old_stats = session.query(Statistics).filter(
                    Statistics.date < cutoff_date
                )
                deleted_counts['statistics'] = old_stats.count()
                old_stats.delete(synchronize_session=False)
                
                logger.info(f"🧹 تم تنظيف البيانات الأقدم من {days} يوم: {deleted_counts}")
                
                return deleted_counts
                
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف البيانات القديمة: {e}")
            return {'messages': 0, 'links': 0, 'statistics': 0}
