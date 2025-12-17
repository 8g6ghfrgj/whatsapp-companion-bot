"""
📅 Scheduler - نظام الجدولة الذكي
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """أنواع المهام"""
    COLLECT_LINKS = "collect_links"
    AUTO_POST = "auto_post"
    AUTO_JOIN = "auto_join"
    BACKUP = "backup"
    CLEANUP = "cleanup"
    CUSTOM = "custom"

class ScheduleFrequency(Enum):
    """تردد الجدولة"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

@dataclass
class ScheduledTask:
    """مهمة مجدولة"""
    id: str
    name: str
    task_type: TaskType
    frequency: ScheduleFrequency
    schedule_time: str  # وقت التشغيل (HH:MM أو cron expression)
    is_active: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    total_runs: int = 0
    success_count: int = 0
    fail_count: int = 0
    config: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable] = None

class Scheduler:
    """نظام الجدولة الذكي"""
    
    def __init__(self, database_handler=None):
        """تهيئة نظام الجدولة"""
        self.db = database_handler
        self.scheduler = AsyncIOScheduler()
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.task_handlers = {}
        
        # تسجيل معالجات المهام الافتراضية
        self._register_default_handlers()
        
        logger.info("📅 تم تهيئة نظام الجدولة")
    
    def _register_default_handlers(self):
        """تسجيل معالجات المهام الافتراضية"""
        self.task_handlers = {
            TaskType.COLLECT_LINKS: self._handle_collect_links,
            TaskType.AUTO_POST: self._handle_auto_post,
            TaskType.AUTO_JOIN: self._handle_auto_join,
            TaskType.BACKUP: self._handle_backup,
            TaskType.CLEANUP: self._handle_cleanup
        }
    
    async def start(self):
        """بدء نظام الجدولة"""
        try:
            self.scheduler.start()
            
            # تحميل المهام المحفوظة
            await self._load_saved_tasks()
            
            logger.info("🚀 تم بدء نظام الجدولة")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في بدء نظام الجدولة: {e}")
            return False
    
    async def _load_saved_tasks(self):
        """تحميل المهام المحفوظة"""
        try:
            if self.db:
                # تحميل المهام من قاعدة البيانات
                # هذه دالة افتراضية - تحتاج للتطبيق الفعلي
                pass
            
            # إضافة المهام الافتراضية
            await self._add_default_tasks()
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحميل المهام المحفوظة: {e}")
    
    async def _add_default_tasks(self):
        """إضافة المهام الافتراضية"""
        default_tasks = [
            ScheduledTask(
                id="daily_backup",
                name="نسخة احتياطية يومية",
                task_type=TaskType.BACKUP,
                frequency=ScheduleFrequency.DAILY,
                schedule_time="02:00",
                config={'backup_type': 'full'}
            ),
            ScheduledTask(
                id="hourly_collection",
                name="تجميع ساعي",
                task_type=TaskType.COLLECT_LINKS,
                frequency=ScheduleFrequency.HOURLY,
                schedule_time="*/60",
                config={'interval': 3600}
            ),
            ScheduledTask(
                id="weekly_cleanup",
                name="تنظيف أسبوعي",
                task_type=TaskType.CLEANUP,
                frequency=ScheduleFrequency.WEEKLY,
                schedule_time="04:00",
                config={'days_to_keep': 30}
            )
        ]
        
        for task in default_tasks:
            await self.schedule_task(task)
    
    async def schedule_task(self, task: ScheduledTask) -> bool:
        """جدولة مهمة جديدة"""
        try:
            # التحقق من صحة وقت الجدولة
            if not self._validate_schedule_time(task.schedule_time, task.frequency):
                logger.error(f"❌ وقت جدولة غير صالح: {task.schedule_time}")
                return False
            
            # حساب وقت التشغيل التالي
            task.next_run = self._calculate_next_run(task)
            
            # إضافة المهمة إلى الجدولة
            self._add_to_scheduler(task)
            
            # حفظ في القاموس
            self.scheduled_tasks[task.id] = task
            
            # حفظ في قاعدة البيانات
            if self.db:
                await self._save_task_to_db(task)
            
            logger.info(f"📅 تم جدولة مهمة: {task.name} ({task.id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في جدولة المهمة: {e}")
            return False
    
    def _validate_schedule_time(self, schedule_time: str, frequency: ScheduleFrequency) -> bool:
        """التحقق من صحة وقت الجدولة"""
        try:
            if frequency == ScheduleFrequency.CUSTOM:
                # cron expression
                return True
            
            # تنسيق HH:MM
            if ':' in schedule_time:
                hours, minutes = map(int, schedule_time.split(':'))
                return 0 <= hours < 24 and 0 <= minutes < 60
            
            return False
            
        except:
            return False
    
    def _calculate_next_run(self, task: ScheduledTask) -> datetime:
        """حساب وقت التشغيل التالي"""
        try:
            now = datetime.now()
            
            if task.frequency == ScheduleFrequency.HOURLY:
                return now + timedelta(hours=1)
            
            elif task.frequency == ScheduleFrequency.DAILY:
                # حساب وقت اليوم القادم
                schedule_time = datetime.strptime(task.schedule_time, "%H:%M").time()
                next_run = datetime.combine(now.date(), schedule_time)
                
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                return next_run
            
            elif task.frequency == ScheduleFrequency.WEEKLY:
                # كل أسبوع في نفس اليوم والوقت
                schedule_time = datetime.strptime(task.schedule_time, "%H:%M").time()
                next_run = datetime.combine(now.date(), schedule_time)
                next_run += timedelta(days=(7 - now.weekday()))
                return next_run
            
            elif task.frequency == ScheduleFrequency.MONTHLY:
                # أول يوم من الشهر القادم
                schedule_time = datetime.strptime(task.schedule_time, "%H:%M").time()
                next_month = now.month + 1 if now.month < 12 else 1
                next_year = now.year if now.month < 12 else now.year + 1
                next_run = datetime(next_year, next_month, 1, schedule_time.hour, schedule_time.minute)
                return next_run
            
            else:
                return now + timedelta(minutes=5)
                
        except Exception as e:
            logger.error(f"❌ خطأ في حساب وقت التشغيل التالي: {e}")
            return datetime.now() + timedelta(minutes=5)
    
    def _add_to_scheduler(self, task: ScheduledTask):
        """إضافة المهمة إلى الجدولة"""
        try:
            if task.frequency == ScheduleFrequency.CUSTOM:
                # استخدام cron expression
                trigger = CronTrigger.from_crontab(task.schedule_time)
            else:
                # استخدام الفترة الزمنية
                if task.frequency == ScheduleFrequency.HOURLY:
                    trigger = IntervalTrigger(hours=1)
                elif task.frequency == ScheduleFrequency.DAILY:
                    trigger = IntervalTrigger(days=1)
                elif task.frequency == ScheduleFrequency.WEEKLY:
                    trigger = IntervalTrigger(weeks=1)
                elif task.frequency == ScheduleFrequency.MONTHLY:
                    trigger = IntervalTrigger(days=30)  # تقريبي
                else:
                    trigger = IntervalTrigger(minutes=5)
            
            # إضافة المهمة إلى الجدولة
            self.scheduler.add_job(
                self._execute_task,
                trigger,
                args=[task.id],
                id=task.id,
                name=task.name,
                replace_existing=True
            )
            
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة المهمة إلى الجدولة: {e}")
    
    async def _execute_task(self, task_id: str):
        """تنفيذ المهمة"""
        try:
            if task_id not in self.scheduled_tasks:
                logger.error(f"❌ المهمة غير موجودة: {task_id}")
                return
            
            task = self.scheduled_tasks[task_id]
            
            if not task.is_active:
                logger.debug(f"⏭️ تخطي المهمة غير النشطة: {task.name}")
                return
            
            logger.info(f"🚀 بدء تنفيذ المهمة: {task.name}")
            
            # تحديث وقت التشغيل الأخير
            task.last_run = datetime.now()
            task.total_runs += 1
            
            try:
                # تنفيذ المهمة
                success = await self._run_task_handler(task)
                
                if success:
                    task.success_count += 1
                    logger.info(f"✅ تم تنفيذ المهمة بنجاح: {task.name}")
                else:
                    task.fail_count += 1
                    logger.error(f"❌ فشل تنفيذ المهمة: {task.name}")
                
                # تحديث وقت التشغيل التالي
                task.next_run = self._calculate_next_run(task)
                
                # حفظ في قاعدة البيانات
                if self.db:
                    await self._save_task_to_db(task)
                
            except Exception as e:
                task.fail_count += 1
                logger.error(f"❌ خطأ في تنفيذ المهمة {task.name}: {e}")
            
        except Exception as e:
            logger.error(f"❌ خطأ في تنفيذ المهمة: {e}")
    
    async def _run_task_handler(self, task: ScheduledTask) -> bool:
        """تشغيل معالج المهمة"""
        try:
            handler = self.task_handlers.get(task.task_type)
            
            if handler:
                return await handler(task.config)
            
            elif task.callback:
                return await task.callback(task.config)
            
            else:
                logger.error(f"❌ لا يوجد معالج للمهمة: {task.task_type}")
                return False
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالج المهمة: {e}")
            return False
    
    async def _handle_collect_links(self, config: Dict[str, Any]) -> bool:
        """معالج تجميع الروابط"""
        try:
            logger.info("🔍 بدء تجميع الروابط المجدول")
            # تنفيذ تجميع الروابط
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في تجميع الروابط: {e}")
            return False
    
    async def _handle_auto_post(self, config: Dict[str, Any]) -> bool:
        """معالج النشر التلقائي"""
        try:
            logger.info("📢 بدء النشر التلقائي المجدول")
            # تنفيذ النشر التلقائي
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في النشر التلقائي: {e}")
            return False
    
    async def _handle_auto_join(self, config: Dict[str, Any]) -> bool:
        """معالج الانظمام التلقائي"""
        try:
            logger.info("👥 بدء الانظمام التلقائي المجدول")
            # تنفيذ الانظمام التلقائي
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في الانظمام التلقائي: {e}")
            return False
    
    async def _handle_backup(self, config: Dict[str, Any]) -> bool:
        """معالج النسخ الاحتياطي"""
        try:
            logger.info("💾 بدء النسخ الاحتياطي المجدول")
            # تنفيذ النسخ الاحتياطي
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في النسخ الاحتياطي: {e}")
            return False
    
    async def _handle_cleanup(self, config: Dict[str, Any]) -> bool:
        """معالج التنظيف"""
        try:
            logger.info("🧹 بدء التنظيف المجدول")
            # تنفيذ التنظيف
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في التنظيف: {e}")
            return False
    
    async def _save_task_to_db(self, task: ScheduledTask):
        """حفظ المهمة في قاعدة البيانات"""
        try:
            # هذه دالة افتراضية - تحتاج للتطبيق الفعلي
            pass
            
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ المهمة: {e}")
    
    async def create_task(self, task_data: Dict[str, Any]) -> str:
        """إنشاء مهمة جديدة"""
        try:
            task_id = task_data.get('id', f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            task = ScheduledTask(
                id=task_id,
                name=task_data['name'],
                task_type=TaskType(task_data['task_type']),
                frequency=ScheduleFrequency(task_data['frequency']),
                schedule_time=task_data['schedule_time'],
                is_active=task_data.get('is_active', True),
                config=task_data.get('config', {})
            )
            
            # إذا كان هناك callback مخصص
            if 'callback' in task_data:
                task.callback = task_data['callback']
            
            # جدولة المهمة
            success = await self.schedule_task(task)
            
            if success:
                return task_id
            else:
                return ""
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء المهمة: {e}")
            return ""
    
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """تحديث مهمة"""
        try:
            if task_id not in self.scheduled_tasks:
                logger.error(f"❌ المهمة غير موجودة: {task_id}")
                return False
            
            task = self.scheduled_tasks[task_id]
            
            # تحديث الحقول
            if 'name' in updates:
                task.name = updates['name']
            
            if 'task_type' in updates:
                task.task_type = TaskType(updates['task_type'])
            
            if 'frequency' in updates:
                task.frequency = ScheduleFrequency(updates['frequency'])
            
            if 'schedule_time' in updates:
                task.schedule_time = updates['schedule_time']
            
            if 'is_active' in updates:
                task.is_active = updates['is_active']
            
            if 'config' in updates:
                task.config.update(updates['config'])
            
            # إعادة الجدولة
            await self.schedule_task(task)
            
            logger.info(f"🔄 تم تحديث المهمة: {task.name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث المهمة: {e}")
            return False
    
    async def delete_task(self, task_id: str) -> bool:
        """حذف مهمة"""
        try:
            if task_id in self.scheduled_tasks:
                task_name = self.scheduled_tasks[task_id].name
                
                # إزالة من الجدولة
                self.scheduler.remove_job(task_id)
                
                # إزالة من القاموس
                del self.scheduled_tasks[task_id]
                
                logger.info(f"🗑️ تم حذف المهمة: {task_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ خطأ في حذف المهمة: {e}")
            return False
    
    async def run_task_now(self, task_id: str) -> bool:
        """تشغيل مهمة فورًا"""
        try:
            if task_id in self.scheduled_tasks:
                task = self.scheduled_tasks[task_id]
                
                logger.info(f"⚡ تشغيل المهمة فورًا: {task.name}")
                
                # تشغيل المهمة
                success = await self._run_task_handler(task)
                
                # تحديث الإحصائيات
                if success:
                    task.success_count += 1
                else:
                    task.fail_count += 1
                
                return success
            
            logger.error(f"❌ المهمة غير موجودة: {task_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ خطأ في تشغيل المهمة فورًا: {e}")
            return False
    
    async def get_tasks(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """الحصول على قائمة المهام"""
        tasks_list = []
        
        for task in self.scheduled_tasks.values():
            if active_only and not task.is_active:
                continue
            
            tasks_list.append({
                'id': task.id,
                'name': task.name,
                'task_type': task.task_type.value,
                'frequency': task.frequency.value,
                'schedule_time': task.schedule_time,
                'is_active': task.is_active,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'total_runs': task.total_runs,
                'success_count': task.success_count,
                'fail_count': task.fail_count,
                'success_rate': (task.success_count / task.total_runs * 100) if task.total_runs > 0 else 0
            })
        
        # ترتيب حسب وقت التشغيل التالي
        tasks_list.sort(key=lambda x: x['next_run'] or '9999-12-31')
        
        return tasks_list
    
    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الجدولة"""
        total_tasks = len(self.scheduled_tasks)
        active_tasks = len([t for t in self.scheduled_tasks.values() if t.is_active])
        
        total_runs = sum(t.total_runs for t in self.scheduled_tasks.values())
        total_success = sum(t.success_count for t in self.scheduled_tasks.values())
        total_fail = sum(t.fail_count for t in self.scheduled_tasks.values())
        
        # المهام القادمة (في الساعة القادمة)
        upcoming_tasks = []
        now = datetime.now()
        one_hour_later = now + timedelta(hours=1)
        
        for task in self.scheduled_tasks.values():
            if task.is_active and task.next_run and task.next_run <= one_hour_later:
                upcoming_tasks.append({
                    'name': task.name,
                    'next_run': task.next_run.isoformat(),
                    'type': task.task_type.value
                })
        
        return {
            'total_tasks': total_tasks,
            'active_tasks': active_tasks,
            'total_runs': total_runs,
            'total_success': total_success,
            'total_fail': total_fail,
            'success_rate': (total_success / total_runs * 100) if total_runs > 0 else 0,
            'upcoming_tasks': upcoming_tasks,
            'scheduler_running': self.scheduler.running
        }
    
    async def stop(self):
        """إيقاف نظام الجدولة"""
        try:
            self.scheduler.shutdown()
            logger.info("⏹️ تم إيقاف نظام الجدولة")
            
        except Exception as e:
            logger.error(f"❌ خطأ في إيقاف نظام الجدولة: {e}")
