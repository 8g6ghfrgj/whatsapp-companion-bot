"""
📥 AutoCollector - نظام التجميع التلقائي للروابط
"""

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urlparse

from ..scrapers.link_scraper import LinkScraper
from ..database.db_handler import Database

logger = logging.getLogger(__name__)

class AutoCollector:
    """نظام التجميع التلقائي للروابط"""
    
    def __init__(self, whatsapp_client, database_handler: Database = None):
        """تهيئة نظام التجميع التلقائي"""
        self.client = whatsapp_client
        self.db = database_handler
        self.is_collecting = False
        self.collection_tasks = []
        self.link_scraper = LinkScraper(self.db) if self.db else LinkScraper()
        self.collection_stats = {
            'total_links': 0,
            'last_collection': None,
            'collections_today': 0
        }
        self.collected_urls: Set[str] = set()
        self.collection_interval = 300  # 5 دقائق
        self.max_links_per_session = 10000
        self.last_group_check = {}
        
        logger.info("📥 تم تهيئة نظام التجميع التلقائي")
    
    async def start_auto_collection(self, interval: int = None) -> Dict[str, Any]:
        """بدء التجميع التلقائي"""
        try:
            if self.is_collecting:
                logger.warning("⚠️ التجميع التلقائي يعمل بالفعل")
                return {'success': False, 'error': 'التجميع يعمل بالفعل'}
            
            if not self.client.is_connected:
                logger.error("❌ العميل غير متصل")
                return {'success': False, 'error': 'العميل غير متصل'}
            
            self.is_collecting = True
            
            # تعيين الفترة الزمنية
            collection_interval = interval or self.collection_interval
            
            logger.info(f"🔍 بدء التجميع التلقائي (فترة: {collection_interval} ثانية)")
            
            # بدء التجميع في الخلفية
            collection_task = asyncio.create_task(
                self._collection_loop(collection_interval)
            )
            self.collection_tasks.append(collection_task)
            
            return {
                'success': True,
                'message': f'تم بدء التجميع التلقائي',
                'interval': collection_interval
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في بدء التجميع التلقائي: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _collection_loop(self, interval: int):
        """حلقة التجميع التلقائي"""
        try:
            while self.is_collecting:
                try:
                    # إعادة تعيين العداد اليومي إذا كان يوم جديد
                    await self._reset_daily_counter_if_needed()
                    
                    # التحقق من الحد اليومي
                    if self.collection_stats['collections_today'] >= 50:  # حد أقصى 50 عملية جمع يوميًا
                        logger.warning("⚠️ تم الوصول إلى الحد الأقصى اليومي للتجميع")
                        await asyncio.sleep(3600)  # انتظار ساعة
                        continue
                    
                    # بدء عملية التجميع
                    await self._collect_from_all_groups()
                    
                    # زيادة عداد اليوم
                    self.collection_stats['collections_today'] += 1
                    
                    # انتظار الفترة المحددة
                    logger.debug(f"⏳ انتظار {interval} ثانية للتجميع التالي")
                    await asyncio.sleep(interval)
                    
                except Exception as e:
                    logger.error(f"❌ خطأ في حلقة التجميع: {e}")
                    await asyncio.sleep(60)  # انتظار دقيقة ثم إعادة المحاولة
            
        except Exception as e:
            logger.error(f"❌ خطأ في حلقة التجميع الرئيسية: {e}")
            self.is_collecting = False
    
    async def _reset_daily_counter_if_needed(self):
        """إعادة تعيين العداد اليومي إذا كان يوم جديد"""
        try:
            today = datetime.now().date()
            last_collection_date = self.collection_stats.get('last_collection_date')
            
            if last_collection_date != today:
                self.collection_stats['collections_today'] = 0
                self.collection_stats['last_collection_date'] = today
                logger.debug("🔄 تم إعادة تعيين عداد التجميع اليومي")
                
        except Exception as e:
            logger.error(f"❌ خطأ في إعادة تعيين العداد اليومي: {e}")
    
    async def _collect_from_all_groups(self):
        """التجميع من جميع المجموعات"""
        try:
            logger.info("🔍 بدء التجميع من المجموعات...")
            
            # الحصول على جميع المجموعات
            from ..whatsapp.group_manager import GroupManager
            group_manager = GroupManager(self.client, self.db)
            groups = await group_manager.get_all_groups()
            
            if not groups:
                logger.warning("⚠️ لا توجد مجموعات متاحة للتجميع")
                return
            
            total_links_collected = 0
            
            for group in groups:
                if not self.is_collecting:
                    break
                
                try:
                    group_id = group['id']
                    group_name = group['name']
                    
                    # التحقق من وقت آخر فحص لهذه المجموعة
                    last_check = self.last_group_check.get(group_id)
                    if last_check:
                        time_since_last = datetime.now() - last_check
                        if time_since_last.total_seconds() < 3600:  # ساعة واحدة
                            logger.debug(f"⏭️ تخطي المجموعة {group_name} (تم فحصها مؤخرًا)")
                            continue
                    
                    logger.info(f"📋 التجميع من المجموعة: {group_name}")
                    
                    # الحصول على رسائل المجموعة
                    from ..whatsapp.message_handler import MessageHandler
                    message_handler = MessageHandler(self.client, self.db)
                    
                    messages = await message_handler.get_group_messages(
                        group_id,
                        include_old=False,  # فقط الرسائل الجديدة منذ آخر فحص
                        limit=100  # آخر 100 رسالة فقط
                    )
                    
                    # استخراج الروابط من الرسائل
                    links_collected = await self._process_group_messages(
                        messages, 
                        group_id, 
                        group_name
                    )
                    
                    total_links_collected += links_collected
                    
                    # تحديث وقت آخر فحص
                    self.last_group_check[group_id] = datetime.now()
                    
                    # انتظار قصير بين المجموعات
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ خطأ في معالجة المجموعة {group.get('name')}: {e}")
                    continue
            
            # تحديث الإحصائيات
            self.collection_stats['total_links'] += total_links_collected
            self.collection_stats['last_collection'] = datetime.now().isoformat()
            
            logger.info(f"✅ تم الانتهاء من التجميع: {total_links_collected} رابط جديد")
            
        except Exception as e:
            logger.error(f"❌ خطأ في التجميع من المجموعات: {e}")
    
    async def _process_group_messages(self, messages: List[Dict[str, Any]], 
                                     group_id: str, group_name: str) -> int:
        """معالجة رسائل المجموعة واستخراج الروابط"""
        try:
            links_collected = 0
            
            for message in messages:
                try:
                    message_text = message.get('body', '')
                    message_id = message.get('id', '')
                    sender = message.get('sender', '')
                    
                    if not message_text:
                        continue
                    
                    # استخراج جميع الروابط من النص
                    all_links = self.link_scraper.extract_links(message_text)
                    
                    for link in all_links:
                        # التحقق من عدم تكرار الرابط
                        if link in self.collected_urls:
                            continue
                        
                        # تصنيف الرابط
                        category = self.link_scraper.categorize_link(link)
                        
                        # حفظ الرابط
                        if self.db:
                            success = await self.db.save_link({
                                'session_id': self.client.session_id if hasattr(self.client, 'session_id') else 'unknown',
                                'url': link,
                                'found_in': f"{group_name} - {sender}",
                                'group_id': group_id,
                                'message_id': message_id,
                                'category': category,
                                'metadata': {
                                    'group_name': group_name,
                                    'sender': sender,
                                    'message_preview': message_text[:100]
                                }
                            })
                            
                            if success:
                                links_collected += 1
                                self.collected_urls.add(link)
                                logger.debug(f"🔗 تم حفظ رابط: {link[:50]}...")
                        
                except Exception as e:
                    logger.error(f"❌ خطأ في معالجة رسالة: {e}")
                    continue
            
            return links_collected
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة رسائل المجموعة: {e}")
            return 0
    
    async def stop_auto_collection(self) -> bool:
        """إيقاف التجميع التلقائي"""
        try:
            if not self.is_collecting:
                return True
            
            self.is_collecting = False
            
            # إلغاء جميع مهام التجميع
            for task in self.collection_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self.collection_tasks.clear()
            
            logger.info("⏹️ تم إيقاف التجميع التلقائي")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في إيقاف التجميع: {e}")
            return False
    
    async def get_collection_status(self) -> Dict[str, Any]:
        """الحصول على حالة التجميع"""
        status = {
            'is_collecting': self.is_collecting,
            'total_links_collected': self.collection_stats['total_links'],
            'last_collection': self.collection_stats['last_collection'],
            'collections_today': self.collection_stats['collections_today'],
            'unique_urls': len(self.collected_urls),
            'groups_monitored': len(self.last_group_check),
            'collection_interval': self.collection_interval,
            'max_links_per_session': self.max_links_per_session
        }
        
        if self.is_collecting and self.collection_tasks:
            status['active_tasks'] = len([t for t in self.collection_tasks if not t.done()])
        
        return status
    
    async def collect_from_specific_group(self, group_id: str, limit: int = 200) -> Dict[str, Any]:
        """التجميع من مجموعة محددة"""
        try:
            logger.info(f"🔍 التجميع من مجموعة محددة: {group_id}")
            
            from ..whatsapp.message_handler import MessageHandler
            from ..whatsapp.group_manager import GroupManager
            
            message_handler = MessageHandler(self.client, self.db)
            group_manager = GroupManager(self.client, self.db)
            
            # الحصول على معلومات المجموعة
            group_info = await group_manager.get_group_info(group_id)
            if not group_info:
                return {'success': False, 'error': 'المجموعة غير موجودة'}
            
            # الحصول على رسائل المجموعة
            messages = await message_handler.get_group_messages(
                group_id,
                include_old=True,
                limit=limit
            )
            
            # معالجة الرسائل
            links_collected = await self._process_group_messages(
                messages, 
                group_id, 
                group_info.get('name', 'غير معروف')
            )
            
            # تحديث الإحصائيات
            self.collection_stats['total_links'] += links_collected
            
            return {
                'success': True,
                'group_name': group_info.get('name'),
                'messages_processed': len(messages),
                'links_collected': links_collected,
                'total_links_now': self.collection_stats['total_links']
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في التجميع من مجموعة محددة: {e}")
            return {'success': False, 'error': str(e)}
    
    async def clear_collected_urls(self) -> int:
        """مسح الروابط المجمعة مؤقتًا"""
        try:
            count = len(self.collected_urls)
            self.collected_urls.clear()
            
            logger.info(f"🧹 تم مسح {count} رابط من الذاكرة المؤقتة")
            return count
            
        except Exception as e:
            logger.error(f"❌ خطأ في مسح الروابط: {e}")
            return 0
    
    async def export_collected_links(self, format: str = 'txt') -> Optional[str]:
        """تصدير الروابط المجمعة"""
        try:
            if not self.db:
                logger.error("❌ قاعدة البيانات غير متوفرة")
                return None
            
            # الحصول على الروابط من قاعدة البيانات
            links = await self.db.get_links(
                session_id=self.client.session_id if hasattr(self.client, 'session_id') else 'unknown',
                limit=10000
            )
            
            if not links:
                logger.warning("⚠️ لا توجد روابط للتصدير")
                return None
            
            # تجميع الروابط حسب الفئة
            categorized_links = {}
            for link in links:
                category = link['category']
                if category not in categorized_links:
                    categorized_links[category] = []
                categorized_links[category].append(link['url'])
            
            # إنشاء المحتوى
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format == 'txt':
                filename = f"collected_links_{timestamp}.txt"
                filepath = f"data/exports/{filename}"
                
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"📋 روابط مجمعة - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for category, urls in categorized_links.items():
                        f.write(f"📁 {category.upper()} ({len(urls)} رابط):\n")
                        f.write("-" * 30 + "\n")
                        for url in urls:
                            f.write(f"{url}\n")
                        f.write("\n")
                
                logger.info(f"📤 تم تصدير {len(links)} رابط إلى: {filepath}")
                return filepath
            
            elif format == 'json':
                filename = f"collected_links_{timestamp}.json"
                filepath = f"data/exports/{filename}"
                
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                export_data = {
                    'exported_at': datetime.now().isoformat(),
                    'total_links': len(links),
                    'categories': categorized_links
                }
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"📤 تم تصدير {len(links)} رابط إلى: {filepath}")
                return filepath
            
            else:
                logger.error(f"❌ تنسيق غير مدعوم: {format}")
                return None
            
        except Exception as e:
            logger.error(f"❌ خطأ في تصدير الروابط: {e}")
            return None
    
    async def get_link_statistics(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الروابط"""
        try:
            if not self.db:
                return {
                    'memory_only': True,
                    'unique_urls': len(self.collected_urls),
                    'categories': {}
                }
            
            # الحصول على الروابط من قاعدة البيانات
            links = await self.db.get_links(
                session_id=self.client.session_id if hasattr(self.client, 'session_id') else 'unknown',
                limit=10000
            )
            
            # حساب الإحصائيات
            total_links = len(links)
            
            # التصنيف حسب النوع
            category_stats = {}
            for link in links:
                category = link['category']
                if category not in category_stats:
                    category_stats[category] = 0
                category_stats[category] += 1
            
            # الروابط اليومية
            today = datetime.now().date()
            today_links = 0
            for link in links:
                try:
                    found_at = datetime.fromisoformat(link['found_at'].replace('Z', '+00:00'))
                    if found_at.date() == today:
                        today_links += 1
                except:
                    continue
            
            return {
                'total_links': total_links,
                'today_links': today_links,
                'categories': category_stats,
                'unique_in_memory': len(self.collected_urls)
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحصائيات الروابط: {e}")
            return {'total_links': 0, 'today_links': 0, 'categories': {}}
    
    async def search_links(self, keyword: str, category: str = None) -> List[Dict[str, Any]]:
        """بحث في الروابط المجمعة"""
        try:
            if not self.db:
                return []
            
            # الحصول على جميع الروابط
            links = await self.db.get_links(
                session_id=self.client.session_id if hasattr(self.client, 'session_id') else 'unknown',
                category=category,
                limit=1000
            )
            
            # البحث عن الكلمة المفتاحية
            results = []
            keyword_lower = keyword.lower()
            
            for link in links:
                try:
                    url = link.get('url', '').lower()
                    title = link.get('title', '').lower()
                    description = link.get('description', '').lower()
                    found_in = link.get('found_in', '').lower()
                    
                    if (keyword_lower in url or 
                        keyword_lower in title or 
                        keyword_lower in description or
                        keyword_lower in found_in):
                        results.append(link)
                        
                except:
                    continue
            
            logger.info(f"🔍 تم العثور على {len(results)} رابط مطابق لـ '{keyword}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ خطأ في البحث عن الروابط: {e}")
            return []
