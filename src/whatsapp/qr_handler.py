"""
📱 QR Code Handler - معالج الQR Code للربط
"""

import asyncio
import base64
import logging
import os
import qrcode
import time
from io import BytesIO
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class QRHandler:
    """فئة معالجة QR Code"""
    
    def __init__(self, whatsapp_client):
        """تهيئة المعالج"""
        self.client = whatsapp_client
        self.qr_data: Optional[str] = None
        self.qr_image_path: Optional[str] = None
        self.qr_generated_at: Optional[float] = None
        self.is_waiting = False
        
    async def generate_qr_code(self) -> Optional[Dict[str, Any]]:
        """توليد QR Code"""
        try:
            logger.info("🔄 توليد QR Code جديد...")
            
            # تهيئة العميل
            if not await self.client.initialize():
                logger.error("❌ فشل في تهيئة العميل")
                return None
            
            # انتظار ظهور QR Code
            qr_path = await self.client.wait_for_qr_code(timeout=30)
            
            if not qr_path:
                logger.error("❌ فشل في الحصول على QR Code")
                return None
            
            # قراءة صورة QR Code وتحويلها لـ base64
            with open(qr_path, 'rb') as f:
                qr_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            self.qr_data = qr_base64
            self.qr_image_path = qr_path
            self.qr_generated_at = time.time()
            
            # إنشاء QR Code بديل للعرض
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            # استخدام رابط افتراضي (في الواقع سيتم استخدام QR من واتساب)
            qr.add_data(f"whatsapp://session/{self.client.session_id}")
            qr.make(fit=True)
            
            # حفظ صورة QR Code بديلة
            img = qr.make_image(fill_color="black", back_color="white")
            alt_qr_path = os.path.join(self.client.session_dir, "qr_alt.png")
            img.save(alt_qr_path)
            
            logger.info(f"✅ تم توليد QR Code للجلسة: {self.client.session_id}")
            
            return {
                'session_id': self.client.session_id,
                'qr_path': qr_path,
                'qr_alt_path': alt_qr_path,
                'qr_base64': qr_base64,
                'expires_in': 300  # ثانية
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في توليد QR Code: {e}")
            return None
    
    async def wait_for_connection(self, timeout: int = 300) -> Dict[str, Any]:
        """انتظار الاتصال بعد مسح QR Code"""
        try:
            logger.info("⏳ في انتظار مسح QR Code...")
            
            self.is_waiting = True
            
            # انتظار المصادقة
            success = await self.client.wait_for_authentication(timeout)
            
            if success:
                # الحصول على بيانات الجلسة
                session_data = await self.client.get_session_data()
                
                return {
                    'success': True,
                    'session_id': self.client.session_id,
                    'phone_number': self.client.phone_number,
                    'session_data': session_data,
                    'message': 'تم الربط بنجاح'
                }
            else:
                return {
                    'success': False,
                    'error': 'انتهى الوقت المحدد دون مسح QR Code',
                    'session_id': self.client.session_id
                }
                
        except Exception as e:
            logger.error(f"❌ خطأ في انتظار الاتصال: {e}")
            return {
                'success': False,
                'error': str(e),
                'session_id': self.client.session_id
            }
        finally:
            self.is_waiting = False
    
    def get_qr_image(self) -> Optional[bytes]:
        """الحصول على صورة QR Code كبايت"""
        try:
            if not self.qr_image_path or not os.path.exists(self.qr_image_path):
                return None
            
            with open(self.qr_image_path, 'rb') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"❌ خطأ في قراءة صورة QR: {e}")
            return None
    
    def get_qr_base64(self) -> Optional[str]:
        """الحصول على QR Code كـ base64"""
        return self.qr_data
    
    def is_qr_expired(self) -> bool:
        """التحقق مما إذا انتهت صلاحية QR Code"""
        if not self.qr_generated_at:
            return True
        
        current_time = time.time()
        time_passed = current_time - self.qr_generated_at
        
        # QR Code ينتهي بعد 5 دقائق
        return time_passed > 300
    
    async def refresh_qr_code(self) -> Optional[Dict[str, Any]]:
        """تحديث QR Code"""
        try:
            logger.info("🔄 تحديث QR Code...")
            
            # إغلاق المتصفح الحالي
            if self.client.driver:
                try:
                    self.client.driver.quit()
                except:
                    pass
            
            # إنشاء عميل جديد
            self.client = type(self.client)(self.client.session_id)
            
            # توليد QR Code جديد
            return await self.generate_qr_code()
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث QR Code: {e}")
            return None
    
    def cleanup(self):
        """تنظيف الملفات المؤقتة"""
        try:
            # حذف صورة QR Code المؤقتة
            if self.qr_image_path and os.path.exists(self.qr_image_path):
                os.remove(self.qr_image_path)
                logger.info(f"🧹 تم حذف ملف QR: {self.qr_image_path}")
                
            # تنظيف المجلد إذا كان فارغًا
            if hasattr(self.client, 'session_dir'):
                try:
                    if os.path.exists(self.client.session_dir) and not os.listdir(self.client.session_dir):
                        os.rmdir(self.client.session_dir)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"❌ خطأ في التنظيف: {e}")
