"""
🔔 Notification Manager - مدير الإشعارات
"""

import asyncio
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class NotificationType:
    """أنواع الإشعارات"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Notification:
    """إشعار"""
    id: str
    title: str
    message: str
    type: str
    source: str
    timestamp: datetime
    read: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

class NotificationManager:
    """مدير الإشعارات"""
    
    def __init__(self, config=None):
        """تهيئة مدير الإشعارات"""
        self.config = config
        self.notifications: Dict[str, Notification] = {}
        self.handlers = {}
        self.max_notifications = 1000
        
        # تسجيل معالجات افتراضية
        self._register_default_handlers()
        
        logger.info("🔔 تم تهيئة مدير الإشعارات")
    
    def _register_default_handlers(self):
        """تسجيل معالجات افتراضية"""
        self.handlers = {
            'console': self._send_to_console,
            'database': self._save_to_database,
            'file': self._save_to_file,
            'email': self._send_email,
            'webhook': self._send_webhook
        }
    
    async def send(self, title: str, message: str, 
                   notification_type: str = NotificationType.INFO,
                   source: str = "system",
                   metadata: Dict[str, Any] = None,
                   channels: List[str] = None) -> str:
        """إرسال إشعار"""
        try:
            # إنشاء الإشعار
            notification_id = self._generate_id()
            notification = Notification(
                id=notification_id,
                title=title,
                message=message,
                type=notification_type,
                source=source,
                timestamp=datetime.now(),
                metadata=metadata or {}
            )
            
            # حفظ محليًا
            self._store_notification(notification)
            
            # إرسال عبر القنوات
            if channels is None:
                channels = ['console']  # افتراضيًا إلى الكونسول
            
            for channel in channels:
                if channel in self.handlers:
                    try:
                        await self.handlers[channel](notification)
                    except Exception as e:
                        logger.error(f"❌ خطأ في إرسال الإشعار عبر {channel}: {e}")
            
            logger.info(f"📨 تم إرسال إشعار: {title}")
            return notification_id
            
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال الإشعار: {e}")
            return ""
    
    def _generate_id(self) -> str:
        """إنشاء معرف فريد للإشعار"""
        import time
        import random
        timestamp = int(time.time() * 1000)
        random_str = ''.join(random.choices('abcdef0123456789', k=6))
        return f"notif_{timestamp}_{random_str}"
    
    def _store_notification(self, notification: Notification):
        """تخزين الإشعار محليًا"""
        # الحفاظ على الحد الأقصى
        if len(self.notifications) >= self.max_notifications:
            # حذف أقدم إشعار
            oldest_id = min(self.notifications.keys(), 
                          key=lambda k: self.notifications[k].timestamp)
            del self.notifications[oldest_id]
        
        self.notifications[notification.id] = notification
    
    async def _send_to_console(self, notification: Notification):
        """إرسال الإشعار إلى الكونسول"""
        colors = {
            NotificationType.INFO: '\033[94m',     # أزرق
            NotificationType.SUCCESS: '\033[92m',  # أخضر
            NotificationType.WARNING: '\033[93m',  # أصفر
            NotificationType.ERROR: '\033[91m',    # أحمر
            NotificationType.CRITICAL: '\033[41m'  # خلفية حمراء
        }
        
        reset = '\033[0m'
        color = colors.get(notification.type, '\033[94m')
        
        print(f"\n{color}╔══════════════════════════════════════════╗{reset}")
        print(f"{color}║ {notification.title:^38} ║{reset}")
        print(f"{color}╠══════════════════════════════════════════╣{reset}")
        print(f"{color}║ {notification.message:38} ║{reset}")
        print(f"{color}║ المصدر: {notification.source:30} ║{reset}")
        print(f"{color}║ الوقت: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S'):30} ║{reset}")
        print(f"{color}╚══════════════════════════════════════════╝{reset}\n")
    
    async def _save_to_database(self, notification: Notification):
        """حفظ الإشعار في قاعدة البيانات"""
        # هذه دالة افتراضية - تحتاج للتطبيق الفعلي
        # سيتم حفظ الإشعار في جدول الإشعارات في قاعدة البيانات
        pass
    
    async def _save_to_file(self, notification: Notification):
        """حفظ الإشعار في ملف"""
        try:
            from pathlib import Path
            import json
            
            logs_dir = Path("logs/notifications")
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            # ملف لكل يوم
            filename = logs_dir / f"notifications_{datetime.now().strftime('%Y-%m-%d')}.json"
            
            # تحميل الإشعارات الحالية
            notifications = []
            if filename.exists():
                with open(filename, 'r', encoding='utf-8') as f:
                    notifications = json.load(f)
            
            # إضافة الإشعار الجديد
            notification_dict = {
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.type,
                'source': notification.source,
                'timestamp': notification.timestamp.isoformat(),
                'metadata': notification.metadata
            }
            
            notifications.append(notification_dict)
            
            # حفظ الملف
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(notifications, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الإشعار في ملف: {e}")
    
    async def _send_email(self, notification: Notification):
        """إرسال الإشعار بالبريد الإلكتروني"""
        try:
            if not self.config or not hasattr(self.config, 'email'):
                logger.warning("⚠️ إعدادات البريد الإلكتروني غير متوفرة")
                return
            
            # إعدادات البريد
            email_config = self.config.email
            
            msg = MIMEMultipart()
            msg['From'] = email_config.sender
            msg['To'] = ', '.join(email_config.recipients)
            msg['Subject'] = f"{notification.title} - {self.config.app_name}"
            
            # بناء نص الرسالة
            body = f"""
            <html>
            <body>
                <h2>{notification.title}</h2>
                <p>{notification.message}</p>
                <hr>
                <p><strong>المصدر:</strong> {notification.source}</p>
                <p><strong>الوقت:</strong> {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>النوع:</strong> {notification.type}</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # إرسال البريد
            with smtplib.SMTP(email_config.smtp_server, email_config.smtp_port) as server:
                server.starttls()
                server.login(email_config.username, email_config.password)
                server.send_message(msg)
            
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال البريد الإلكتروني: {e}")
    
    async def _send_webhook(self, notification: Notification):
        """إرسال الإشعار عبر Webhook"""
        try:
            if not self.config or not hasattr(self.config, 'webhooks'):
                logger.warning("⚠️ إعدادات Webhook غير متوفرة")
                return
            
            import aiohttp
            
            webhook_url = self.config.webhooks.url
            
            payload = {
                'notification_id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.type,
                'source': notification.source,
                'timestamp': notification.timestamp.isoformat(),
                'metadata': notification.metadata
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"❌ فشل إرسال Webhook: {response.status}")
                    
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال Webhook: {e}")
    
    async def mark_as_read(self, notification_id: str) -> bool:
        """وضع علامة على الإشعار بأنه مقروء"""
        try:
            if notification_id in self.notifications:
                self.notifications[notification_id].read = True
                return True
            return False
        except Exception as e:
            logger.error(f"❌ خطأ في وضع علامة مقروء: {e}")
            return False
    
    async def get_notifications(self, unread_only: bool = False, 
                               limit: int = 50) -> List[Dict[str, Any]]:
        """الحصول على الإشعارات"""
        notifications_list = []
        
        for notification in self.notifications.values():
            if unread_only and notification.read:
                continue
            
            notifications_list.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.type,
                'source': notification.source,
                'timestamp': notification.timestamp.isoformat(),
                'read': notification.read,
                'metadata': notification.metadata
            })
        
        # ترتيب حسب الوقت (الأحدث أولاً)
        notifications_list.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return notifications_list[:limit]
    
    async def clear_notifications(self, older_than_days: int = None) -> int:
        """مسح الإشعارات"""
        try:
            count = 0
            
            if older_than_days:
                cutoff_date = datetime.now().timestamp() - (older_than_days * 86400)
                
                ids_to_remove = []
                for notification_id, notification in self.notifications.items():
                    if notification.timestamp.timestamp() < cutoff_date:
                        ids_to_remove.append(notification_id)
                        count += 1
                
                for notification_id in ids_to_remove:
                    del self.notifications[notification_id]
            else:
                count = len(self.notifications)
                self.notifications.clear()
            
            logger.info(f"🧹 تم مسح {count} إشعار")
            return count
            
        except Exception as e:
            logger.error(f"❌ خطأ في مسح الإشعارات: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الإشعارات"""
        total = len(self.notifications)
        unread = len([n for n in self.notifications.values() if not n.read])
        
        # حسب النوع
        by_type = {}
        for notification in self.notifications.values():
            n_type = notification.type
            if n_type not in by_type:
                by_type[n_type] = 0
            by_type[n_type] += 1
        
        # حسب المصدر
        by_source = {}
        for notification in self.notifications.values():
            source = notification.source
            if source not in by_source:
                by_source[source] = 0
            by_source[source] += 1
        
        return {
            'total': total,
            'unread': unread,
            'read': total - unread,
            'by_type': by_type,
            'by_source': by_source,
            'max_capacity': self.max_notifications
        }
    
    def register_handler(self, name: str, handler_func):
        """تسجيل معالج جديد"""
        self.handlers[name] = handler_func
        logger.info(f"✅ تم تسجيل معالج جديد: {name}")
    
    def unregister_handler(self, name: str) -> bool:
        """إلغاء تسجيل معالج"""
        if name in self.handlers:
            del self.handlers[name]
            logger.info(f"🗑️ تم إلغاء تسجيل المعالج: {name}")
            return True
        return False
    
    async def test_notification(self, channel: str = 'console') -> bool:
        """اختبار إرسال إشعار"""
        try:
            test_notification = Notification(
                id="test_123",
                title="إشعار اختبار",
                message="هذا إشعار اختبار لفحص النظام",
                type=NotificationType.INFO,
                source="notification_manager",
                timestamp=datetime.now()
            )
            
            if channel in self.handlers:
                await self.handlers[channel](test_notification)
                logger.info(f"✅ تم اختبار إرسال الإشعار عبر {channel}")
                return True
            else:
                logger.error(f"❌ القناة غير موجودة: {channel}")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في اختبار الإشعار: {e}")
            return False
