"""
🚀 Migration System - نظام ترحيل قاعدة البيانات
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

class MigrationManager:
    """مدير ترحيل قاعدة البيانات"""
    
    def __init__(self, database_url: str, migrations_dir: str = "migrations"):
        """تهيئة مدير الترحيل"""
        self.database_url = database_url
        self.migrations_dir = migrations_dir
        
        # إنشاء مجلد الترحيلات إذا لم يكن موجودًا
        os.makedirs(migrations_dir, exist_ok=True)
        
        # تهيئة إعدادات Alembic
        self.alembic_cfg = Config()
        self.alembic_cfg.set_main_option("script_location", migrations_dir)
        self.alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    def init_migrations(self):
        """تهيئة نظام الترحيل"""
        try:
            # إنشاء هيكل الترحيلات
            command.init(self.alembic_cfg, self.migrations_dir)
            
            # تعديل ملف env.py لإضافة النماذج
            env_file = Path(self.migrations_dir) / "env.py"
            
            if env_file.exists():
                with open(env_file, 'r') as f:
                    content = f.read()
                
                # إضافة استيراد النماذج
                new_content = content.replace(
                    "from myapp import mymodel",
                    """from src.database.models import Base
target_metadata = Base.metadata"""
                )
                
                with open(env_file, 'w') as f:
                    f.write(new_content)
            
            print("✅ تم تهيئة نظام الترحيلات")
            return True
            
        except Exception as e:
            print(f"❌ فشل في تهيئة الترحيلات: {e}")
            return False
    
    def create_migration(self, message: str = "auto migration"):
        """إنشاء ترحيل جديد"""
        try:
            # إنشاء نسخة من الترحيل
            command.revision(
                self.alembic_cfg,
                message=message,
                autogenerate=True
            )
            
            print(f"✅ تم إنشاء ترحيل جديد: {message}")
            return True
            
        except Exception as e:
            print(f"❌ فشل في إنشاء الترحيل: {e}")
            return False
    
    def apply_migrations(self):
        """تطبيق جميع الترحيلات المعلقة"""
        try:
            command.upgrade(self.alembic_cfg, "head")
            print("✅ تم تطبيق جميع الترحيلات")
            return True
        except Exception as e:
            print(f"❌ فشل في تطبيق الترحيلات: {e}")
            return False
    
    def rollback_migration(self, revision: str = "-1"):
        """التراجع عن ترحيل"""
        try:
            command.downgrade(self.alembic_cfg, revision)
            print(f"✅ تم التراجع إلى الإصدار: {revision}")
            return True
        except Exception as e:
            print(f"❌ فشل في التراجع: {e}")
            return False
    
    def show_migrations(self):
        """عرض حالة الترحيلات"""
        try:
            command.history(self.alembic_cfg)
            return True
        except Exception as e:
            print(f"❌ فشل في عرض الترحيلات: {e}")
            return False
    
    def check_pending(self) -> List[str]:
        """التحقق من الترحيلات المعلقة"""
        try:
            engine = create_engine(self.database_url)
            
            # التحقق مما إذا كان جدول الترحيلات موجودًا
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
                ))
                
                if result.fetchone():
                    # الجدول موجود، التحقق من الترحيلات المعلقة
                    command.current(self.alembic_cfg)
                    # سيتم عرض الترحيلات المعلقة إذا وجدت
                    return []
                else:
                    return ["no_migrations_table"]
                    
        except Exception as e:
            print(f"❌ فشل في التحقق من الترحيلات المعلقة: {e}")
            return ["error"]
    
    def create_manual_migration(self, sql_up: str, sql_down: str, description: str):
        """إنشاء ترحيل يدوي"""
        try:
            # إنشاء اسم الملف
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{description.replace(' ', '_').lower()}.py"
            filepath = Path(self.migrations_dir) / "versions" / filename
            
            # إنشاء محتوى الملف
            content = f'''"""{{description}}

Revision ID: {timestamp}
Revises: 
Create Date: {datetime.now().isoformat()}

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '{timestamp}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """upgrade migration"""
    # ### commands auto generated by Alembic - please adjust! ###
    {sql_up}
    # ### end Alembic commands ###


def downgrade():
    """downgrade migration"""
    # ### commands auto generated by Alembic - please adjust! ###
    {sql_down}
    # ### end Alembic commands ###
'''
            
            with open(filepath, 'w') as f:
                f.write(content)
            
            print(f"✅ تم إنشاء ترحيل يدوي: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ فشل في إنشاء ترحيل يدوي: {e}")
            return False

# دالة مساعدة لترحيل قاعدة البيانات
def migrate_database(database_url: str = None):
    """ترحيل قاعدة البيانات"""
    if database_url is None:
        db_path = os.path.join('data', 'whatsapp_bot.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        database_url = f"sqlite:///{db_path}"
    
    migration_manager = MigrationManager(database_url)
    
    # التحقق مما إذا كان نظام الترحيلات مهيئًا
    pending = migration_manager.check_pending()
    
    if "no_migrations_table" in pending:
        print("🔧 تهيئة نظام الترحيلات لأول مرة...")
        migration_manager.init_migrations()
        migration_manager.create_migration("Initial migration")
    
    # تطبيق الترحيلات المعلقة
    print("🚀 تطبيق الترحيلات المعلقة...")
    migration_manager.apply_migrations()
    
    print("✅ تم ترحيل قاعدة البيانات بنجاح!")

if __name__ == "__main__":
    migrate_database()
