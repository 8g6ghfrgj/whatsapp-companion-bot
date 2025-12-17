#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 WhatsApp Bot - الملف الرئيسي
نظام متكامل لإدارة حساب واتساب كجهاز مصاحب
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional

# إضافة المسار للمكتبات الداخلية
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.whatsapp.client import WhatsAppClient
from src.whatsapp.qr_handler import QRHandler
from src.whatsapp.message_handler import MessageHandler
from src.whatsapp.group_manager import GroupManager
from src.database.db_handler import Database
from src.scrapers.link_scraper import LinkScraper
from src.scrapers.link_classifier import LinkClassifier
from src.automations.auto_poster import AutoPoster
from src.automations.auto_joiner import AutoJoiner
from src.automations.auto_replier import AutoReplier
from src.utils.config import Config
from src.utils.helpers import setup_logging, save_backup, load_backup
from src.utils.notifications import NotificationManager

# إعداد نظام التسجيل
setup_logging()
logger = logging.getLogger(__name__)

class WhatsAppBot:
    """الفئة الرئيسية للبوت"""
    
    def __init__(self):
        """تهيئة البوت"""
        logger.info("🚀 تهيئة بوت واتساب...")
        
        # تحميل الإعدادات
        self.config = Config()
        
        # إعداد قاعدة البيانات
        self.db = Database(self.config.DATABASE_URL)
        
        # إدارة العملاء (يمكن ربط حسابات متعددة)
        self.clients: Dict[str, WhatsAppClient] = {}
        self.active_client: Optional[WhatsAppClient] = None
        
        # المكونات الرئيسية
        self.qr_handler: Optional[QRHandler] = None
        self.message_handler: Optional[MessageHandler] = None
        self.group_manager: Optional[GroupManager] = None
        self.link_scraper: Optional[LinkScraper] = None
        self.link_classifier: Optional[LinkClassifier] = None
        self.auto_poster: Optional[AutoPoster] = None
        self.auto_joiner: Optional[AutoJoiner] = None
        self.auto_replier: Optional[AutoReplier] = None
        self.notifier: Optional[NotificationManager] = None
        
        # حالة النظام
        self.is_running = False
        self.is_collecting_links = False
        self.is_auto_posting = False
        self.is_auto_joining = False
        self.is_auto_replying = False
        
        # بيانات النظام
        self.collected_links = {
            'whatsapp': [],
            'telegram': [],
            'instagram': [],
            'facebook': [],
            'youtube': [],
            'tiktok': [],
            'other': []
        }
        
        # إعداد معالجة الإشارات
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
        logger.info("✅ تم تهيئة البوت بنجاح")
    
    async def initialize(self):
        """تهيئة جميع المكونات"""
        try:
            logger.info("🔧 تهيئة مكونات البوت...")
            
            # تهيئة قاعدة البيانات
            await self.db.initialize()
            
            # تحميل الجلسات المحفوظة
            await self.load_saved_sessions()
            
            # تهيئة المكونات
            self.notifier = NotificationManager()
            self.link_scraper = LinkScraper(self.db)
            self.link_classifier = LinkClassifier(self.config.LINK_CATEGORIES)
            self.auto_replier = AutoReplier(self.db)
            
            logger.info("✅ تم تهيئة جميع المكونات")
            
            # إرسال إشعار
            await self.notifier.send(
                title="🤖 البوت جاهز للعمل",
                message=f"تم تشغيل البوت بنجاح في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                level="info"
            )
            
        except Exception as e:
            logger.error(f"❌ فشل في تهيئة البوت: {e}")
            raise
    
    async def load_saved_sessions(self):
        """تحميل الجلسات المحفوظة"""
        try:
            sessions = await self.db.get_sessions()
            
            for session in sessions:
                if session['status'] == 'active':
                    client = WhatsAppClient(session['session_id'])
                    
                    # محاولة استعادة الجلسة
                    success = await client.restore_session(session['session_data'])
                    
                    if success:
                        self.clients[session['session_id']] = client
                        logger.info(f"✅ تم تحميل الجلسة: {session['name']}")
                        
                        # تعيين العميل النشط إذا لم يكن هناك عميل نشط
                        if not self.active_client:
                            self.active_client = client
                    else:
                        logger.warning(f"⚠️ فشل في تحميل الجلسة: {session['name']}")
                        # تحديث حالة الجلسة في قاعدة البيانات
                        await self.db.update_session_status(session['session_id'], 'expired')
            
            logger.info(f"📊 تم تحميل {len(self.clients)} جلسة نشطة")
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحميل الجلسات: {e}")
    
    async def connect_whatsapp_account(self, account_name: str = "الحساب الرئيسي"):
        """ربط حساب واتساب جديد"""
        try:
            logger.info(f"🔗 محاولة ربط حساب واتساب: {account_name}")
            
            # إنشاء عميل جديد
            client = WhatsAppClient()
            
            # إنشاء معالج QR
            self.qr_handler = QRHandler(client)
            
            # توليد QR Code
            qr_data = await self.qr_handler.generate_qr_code()
            
            if not qr_data:
                logger.error("❌ فشل في توليد QR Code")
                return None
            
            # حفظ بيانات QR مؤقتًا
            qr_session_id = qr_data['session_id']
            qr_image_path = qr_data['qr_path']
            
            logger.info(f"📱 تم توليد QR Code للجلسة: {qr_session_id}")
            
            # انتظار مسح QR Code
            logger.info("⏳ في انتظار مسح QR Code...")
            
            connection_result = await self.qr_handler.wait_for_connection(
                timeout=self.config.WHATSAPP_QR_TIMEOUT
            )
            
            if connection_result['success']:
                # حفظ الجلسة
                session_data = connection_result['session_data']
                
                # حفظ في قاعدة البيانات
                session_info = {
                    'session_id': qr_session_id,
                    'name': account_name,
                    'phone_number': connection_result.get('phone_number', ''),
                    'session_data': session_data,
                    'status': 'active',
                    'connected_at': datetime.now().isoformat()
                }
                
                await self.db.save_session(session_info)
                
                # إضافة العميل إلى القائمة
                self.clients[qr_session_id] = client
                
                # تعيين كعميل نشط
                self.active_client = client
                
                # تهيئة معالج الرسائل لهذا العميل
                self.message_handler = MessageHandler(client, self.db)
                self.group_manager = GroupManager(client, self.db)
                self.auto_poster = AutoPoster(client, self.db)
                self.auto_joiner = AutoJoiner(client, self.db)
                
                logger.info(f"✅ تم ربط حساب واتساب بنجاح: {account_name}")
                
                # إرسال إشعار
                await self.notifier.send(
                    title="✅ حساب جديد متصل",
                    message=f"تم ربط حساب واتساب: {account_name}",
                    level="success"
                )
                
                return {
                    'success': True,
                    'session_id': qr_session_id,
                    'account_name': account_name,
                    'client': client
                }
            else:
                logger.error(f"❌ فشل في ربط الحساب: {connection_result.get('error', 'Unknown error')}")
                return {
                    'success': False,
                    'error': connection_result.get('error', 'فشل الاتصال')
                }
                
        except Exception as e:
            logger.error(f"❌ خطأ في ربط الحساب: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def disconnect_account(self, session_id: str):
        """فصل حساب واتساب"""
        try:
            if session_id in self.clients:
                client = self.clients[session_id]
                
                # تسجيل الخروج
                await client.logout()
                
                # تحديث حالة الجلسة في قاعدة البيانات
                await self.db.update_session_status(session_id, 'disconnected')
                
                # إزالة من الذاكرة
                del self.clients[session_id]
                
                # إذا كان هذا هو العميل النشط، اختيار عميل آخر
                if self.active_client == client:
                    self.active_client = next(iter(self.clients.values()), None)
                
                logger.info(f"✅ تم فصل الحساب: {session_id}")
                
                return True
            else:
                logger.warning(f"⚠️ لم يتم العثور على الجلسة: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في فصل الحساب: {e}")
            return False
    
    async def start_link_collection(self):
        """بدء تجميع الروابط"""
        try:
            if not self.active_client:
                logger.error("❌ لا يوجد عميل نشط")
                return False
            
            if self.is_collecting_links:
                logger.warning("⚠️ تجميع الروابط يعمل بالفعل")
                return True
            
            self.is_collecting_links = True
            logger.info("📥 بدء تجميع الروابط...")
            
            # الحصول على جميع المجموعات
            groups = await self.group_manager.get_all_groups()
            
            # تجميع الروابط من كل مجموعة
            total_links_collected = 0
            
            for group in groups:
                if not self.is_collecting_links:
                    break
                
                try:
                    # الحصول على رسائل المجموعة (القديمة والجديدة)
                    messages = await self.message_handler.get_group_messages(
                        group['id'],
                        include_old=True
                    )
                    
                    # استخراج الروابط من الرسائل
                    for message in messages:
                        if message.get('body'):
                            links = self.link_scraper.extract_links(message['body'])
                            
                            for link in links:
                                # تصنيف الرابط
                                category = self.link_classifier.classify(link)
                                
                                # إضافة الرابط مع منع التكرار
                                added = await self.link_scraper.add_link(
                                    link=link,
                                    category=category,
                                    source=group['name'],
                                    message_id=message.get('id')
                                )
                                
                                if added:
                                    total_links_collected += 1
                                    self.collected_links[category].append(link)
                    
                    logger.debug(f"✅ تم معالجة مجموعة: {group['name']}")
                    
                except Exception as e:
                    logger.error(f"❌ خطأ في معالجة المجموعة {group['name']}: {e}")
            
            logger.info(f"✅ تم تجميع {total_links_collected} رابط جديد")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في تجميع الروابط: {e}")
            self.is_collecting_links = False
            return False
    
    async def stop_link_collection(self):
        """إيقاف تجميع الروابط"""
        self.is_collecting_links = False
        logger.info("⏹️ تم إيقاف تجميع الروابط")
        return True
    
    async def get_collected_links(self):
        """الحصول على الروابط المجمعة"""
        try:
            links_by_category = {}
            total_count = 0
            
            for category in self.collected_links:
                links = self.collected_links[category]
                links_by_category[category] = {
                    'count': len(links),
                    'links': links
                }
                total_count += len(links)
            
            return {
                'total': total_count,
                'categories': links_by_category
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على الروابط: {e}")
            return {'total': 0, 'categories': {}}
    
    async def export_links(self, format: str = 'txt'):
        """تصدير الروابط المجمعة"""
        try:
            logger.info(f"📤 تصدير الروابط بصيغة {format}...")
            
            export_path = await self.link_scraper.export_links(
                self.collected_links,
                format=format
            )
            
            if export_path:
                logger.info(f"✅ تم تصدير الروابط إلى: {export_path}")
                return export_path
            else:
                logger.error("❌ فشل في تصدير الروابط")
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في تصدير الروابط: {e}")
            return None
    
    async def start_auto_posting(self, advertisement_data: dict):
        """بدء النشر التلقائي"""
        try:
            if not self.active_client:
                logger.error("❌ لا يوجد عميل نشط")
                return False
            
            if self.is_auto_posting:
                logger.warning("⚠️ النشر التلقائي يعمل بالفعل")
                return False
            
            self.is_auto_posting = True
            
            # تعيين الإعلان
            await self.auto_poster.set_advertisement(advertisement_data)
            
            # الحصول على المجموعات للنشر
            groups = await self.group_manager.get_all_groups()
            group_ids = [group['id'] for group in groups]
            
            logger.info(f"📢 بدء النشر التلقائي في {len(group_ids)} مجموعة...")
            
            # بدء النشر في الخلفية
            asyncio.create_task(
                self._auto_posting_task(group_ids)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في بدء النشر التلقائي: {e}")
            self.is_auto_posting = False
            return False
    
    async def _auto_posting_task(self, group_ids: List[str]):
        """مهمة النشر التلقائي"""
        try:
            while self.is_auto_posting and group_ids:
                for group_id in group_ids[:]:  # نسخة من القائمة للتعديل
                    if not self.is_auto_posting:
                        break
                    
                    try:
                        # النشر في المجموعة
                        success = await self.auto_poster.post_to_group(group_id)
                        
                        if success:
                            logger.debug(f"✅ تم النشر في المجموعة: {group_id}")
                        else:
                            logger.warning(f"⚠️ فشل النشر في المجموعة: {group_id}")
                        
                        # انتظار الفترة المحددة
                        await asyncio.sleep(self.config.AUTO_POST_INTERVAL)
                        
                    except Exception as e:
                        logger.error(f"❌ خطأ في النشر للمجموعة {group_id}: {e}")
                        continue
                
                # إذا أكملنا جميع المجموعات، نعيد الدورة
                if self.is_auto_posting:
                    logger.info("🔄 إعادة دورة النشر للمجموعات...")
                    await asyncio.sleep(60)  # انتظار دقيقة قبل إعادة الدورة
                    
        except Exception as e:
            logger.error(f"❌ خطأ في مهمة النشر التلقائي: {e}")
        finally:
            self.is_auto_posting = False
    
    async def stop_auto_posting(self):
        """إيقاف النشر التلقائي"""
        self.is_auto_posting = False
        logger.info("⏹️ تم إيقاف النشر التلقائي")
        return True
    
    async def start_auto_joining(self, group_links: List[str]):
        """بدء الانظمام التلقائي"""
        try:
            if not self.active_client:
                logger.error("❌ لا يوجد عميل نشط")
                return False
            
            if self.is_auto_joining:
                logger.warning("⚠️ الانظمام التلقائي يعمل بالفعل")
                return False
            
            self.is_auto_joining = True
            
            # تصفية روابط واتساب فقط
            whatsapp_links = []
            for link in group_links:
                if 'chat.whatsapp.com' in link:
                    whatsapp_links.append(link)
            
            logger.info(f"👥 بدء الانظمام التلقائي إلى {len(whatsapp_links)} مجموعة...")
            
            # بدء الانظمام في الخلفية
            asyncio.create_task(
                self._auto_joining_task(whatsapp_links)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في بدء الانظمام التلقائي: {e}")
            self.is_auto_joining = False
            return False
    
    async def _auto_joining_task(self, group_links: List[str]):
        """مهمة الانظمام التلقائي"""
        try:
            for link in group_links:
                if not self.is_auto_joining:
                    break
                
                try:
                    logger.info(f"🔗 محاولة الانظمام إلى: {link}")
                    
                    # الانظمام إلى المجموعة
                    result = await self.auto_joiner.join_group(link)
                    
                    if result['success']:
                        logger.info(f"✅ تم الانظمام بنجاح إلى: {link}")
                        
                        # حفظ في قاعدة البيانات
                        await self.db.save_group_join({
                            'link': link,
                            'status': 'joined',
                            'joined_at': datetime.now().isoformat()
                        })
                    else:
                        logger.warning(f"⚠️ فشل الانظمام إلى {link}: {result.get('error')}")
                        
                        # حفظ المحاولة الفاشلة
                        await self.db.save_group_join({
                            'link': link,
                            'status': 'failed',
                            'error': result.get('error'),
                            'attempted_at': datetime.now().isoformat()
                        })
                    
                    # انتظار الفترة المحددة (2 دقيقة)
                    await asyncio.sleep(self.config.JOIN_INTERVAL)
                    
                except Exception as e:
                    logger.error(f"❌ خطأ في الانظمام إلى {link}: {e}")
                    continue
            
            # بعد الانتهاء من جميع الروابط
            self.is_auto_joining = False
            
            # إرسال تقرير
            await self._send_join_report()
            
        except Exception as e:
            logger.error(f"❌ خطأ في مهمة الانظمام التلقائي: {e}")
            self.is_auto_joining = False
    
    async def _send_join_report(self):
        """إرسال تقرير الانظمام"""
        try:
            # الحصول على تقرير من قاعدة البيانات
            report = await self.db.get_join_report()
            
            # إرسال الإشعار
            await self.notifier.send(
                title="📊 تقرير الانظمام التلقائي",
                message=f"""
                تم الانتهاء من عملية الانظمام التلقائي:
                
                ✅ الناجحة: {report['successful']}
                ❌ الفاشلة: {report['failed']}
                ⏳ المعلقة: {report['pending']}
                
                المجموع: {report['total']}
                """,
                level="info"
            )
            
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال تقرير الانظمام: {e}")
    
    async def start_auto_replying(self, reply_rules: dict):
        """بدء الرد التلقائي"""
        try:
            if not self.active_client:
                logger.error("❌ لا يوجد عميل نشط")
                return False
            
            if self.is_auto_replying:
                logger.warning("⚠️ الرد التلقائي يعمل بالفعل")
                return False
            
            self.is_auto_replying = True
            
            # تعيين قواعد الرد
            await self.auto_replier.set_reply_rules(reply_rules)
            
            logger.info("💬 بدء الرد التلقائي...")
            
            # بدء الاستماع للرسائل
            await self.message_handler.start_listening(
                callback=self._handle_incoming_message
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في بدء الرد التلقائي: {e}")
            self.is_auto_replying = False
            return False
    
    async def _handle_incoming_message(self, message: dict):
        """معالجة الرسائل الواردة للرد التلقائي"""
        try:
            if not self.is_auto_replying:
                return
            
            # التحقق مما إذا كانت الرسالة تحتاج إلى رد
            should_reply = await self.auto_replier.should_reply(message)
            
            if should_reply:
                # توليد الرد
                reply = await self.auto_replier.generate_reply(message)
                
                if reply:
                    # إرسال الرد
                    await self.message_handler.send_reply(
                        to=message['from'],
                        message=reply,
                        quoted_msg_id=message.get('id')
                    )
                    
                    logger.debug(f"✅ تم الرد على رسالة من: {message['from']}")
                    
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الرسالة: {e}")
    
    async def stop_auto_replying(self):
        """إيقاف الرد التلقائي"""
        self.is_auto_replying = False
        
        if self.message_handler:
            await self.message_handler.stop_listening()
        
        logger.info("⏹️ تم إيقاف الرد التلقائي")
        return True
    
    async def get_connected_accounts(self):
        """الحصول على الحسابات المتصلة"""
        accounts = []
        
        for session_id, client in self.clients.items():
            account_info = await client.get_account_info()
            account_info['session_id'] = session_id
            account_info['is_active'] = (client == self.active_client)
            accounts.append(account_info)
        
        return accounts
    
    async def backup_data(self):
        """نسخ احتياطي للبيانات"""
        try:
            logger.info("💾 إنشاء نسخة احتياطية...")
            
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'clients_count': len(self.clients),
                'collected_links': self.collected_links,
                'sessions': []
            }
            
            # نسخ بيانات الجلسات
            for session_id, client in self.clients.items():
                session_data = await client.get_session_data()
                backup_data['sessions'].append({
                    'session_id': session_id,
                    'data': session_data
                })
            
            # حفظ النسخة الاحتياطية
            backup_path = save_backup(backup_data)
            
            logger.info(f"✅ تم إنشاء نسخة احتياطية في: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"❌ خطأ في النسخ الاحتياطي: {e}")
            return None
    
    async def restore_from_backup(self, backup_path: str):
        """استعادة البيانات من نسخة احتياطية"""
        try:
            logger.info(f"🔄 استعادة البيانات من: {backup_path}")
            
            backup_data = load_backup(backup_path)
            
            if not backup_data:
                logger.error("❌ فشل في تحميل النسخة الاحتياطية")
                return False
            
            # استعادة الروابط المجمعة
            if 'collected_links' in backup_data:
                self.collected_links = backup_data['collected_links']
            
            # استعادة الجلسات
            for session_info in backup_data.get('sessions', []):
                client = WhatsAppClient()
                success = await client.restore_session(session_info['data'])
                
                if success:
                    self.clients[session_info['session_id']] = client
                    logger.info(f"✅ تم استعادة جلسة: {session_info['session_id']}")
            
            logger.info("✅ تم استعادة البيانات بنجاح")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في استعادة البيانات: {e}")
            return False
    
    async def run(self):
        """تشغيل البوت"""
        try:
            self.is_running = True
            
            # تهيئة البوت
            await self.initialize()
            
            logger.info("🎉 بوت واتساب يعمل الآن!")
            
            # الحلقة الرئيسية
            while self.is_running:
                try:
                    # فحص الجلسات النشطة
                    await self._check_sessions_health()
                    
                    # فحص طلبات الانظمام المعلقة
                    if self.auto_joiner:
                        expired_requests = await self.auto_joiner.check_pending_requests()
                        
                        if expired_requests:
                            logger.warning(f"⚠️ هناك {len(expired_requests)} طلب انظمام منتهي الصلاحية")
                            # يمكن إضافة منطق لإرسال إشعار هنا
                    
                    # انتظار قبل التكرار التالي
                    await asyncio.sleep(60)  # فحص كل دقيقة
                    
                except Exception as e:
                    logger.error(f"❌ خطأ في الحلقة الرئيسية: {e}")
                    await asyncio.sleep(10)  # انتظار قصير قبل إعادة المحاولة
            
        except KeyboardInterrupt:
            logger.info("👋 إيقاف البوت بواسطة المستخدم")
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع: {e}")
        finally:
            await self.shutdown()
    
    async def _check_sessions_health(self):
        """فحص صحة الجلسات"""
        try:
            for session_id, client in list(self.clients.items()):
                is_healthy = await client.check_health()
                
                if not is_healthy:
                    logger.warning(f"⚠️ جلسة غير صحية: {session_id}")
                    
                    # محاولة إعادة الاتصال
                    success = await client.reconnect()
                    
                    if not success:
                        logger.error(f"❌ فشل إعادة الاتصال للجلسة: {session_id}")
                        
                        # تحديث الحالة في قاعدة البيانات
                        await self.db.update_session_status(session_id, 'dead')
                        
                        # إزالة من الذاكرة
                        del self.clients[session_id]
                        
                        if self.active_client == client:
                            self.active_client = next(iter(self.clients.values()), None)
        
        except Exception as e:
            logger.error(f"❌ خطأ في فحص صحة الجلسات: {e}")
    
    def shutdown(self, signum=None, frame=None):
        """إيقاف البوت"""
        async def _async_shutdown():
            logger.info("🛑 إيقاف البوت...")
            
            self.is_running = False
            self.is_collecting_links = False
            self.is_auto_posting = False
            self.is_auto_joining = False
            self.is_auto_replying = False
            
            # إيقاف جميع العملاء
            for session_id, client in self.clients.items():
                try:
                    await client.logout()
                    logger.info(f"✅ تم تسجيل خروج الجلسة: {session_id}")
                except Exception as e:
                    logger.error(f"❌ خطأ في تسجيل خروج الجلسة {session_id}: {e}")
            
            # إغلاق قاعدة البيانات
            if self.db:
                await self.db.close()
            
            # إرسال إشعار الإيقاف
            if self.notifier:
                await self.notifier.send(
                    title="🛑 البوت متوقف",
                    message=f"تم إيقاف البوت في {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    level="warning"
                )
            
            logger.info("👋 البوت متوقف. إلى اللقاء!")
            
            # إنهاء البرنامج
            sys.exit(0)
        
        # تشغيل الإيقاف غير المتزامن
        asyncio.create_task(_async_shutdown())

async def main():
    """الدالة الرئيسية"""
    print("""
    ╔══════════════════════════════════════════╗
    ║        🤖 بوت واتساب المتقدم             ║
    ║        نظام إدارة الحسابات المصاحبة     ║
    ╚══════════════════════════════════════════╝
    """)
    
    # إنشاء البوت
    bot = WhatsAppBot()
    
    # تشغيل البوت
    try:
        await bot.run()
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # تشغيل الدالة الرئيسية
    asyncio.run(main())
