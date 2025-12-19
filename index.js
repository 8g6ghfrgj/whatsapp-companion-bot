/**
 * Entry Point
 * WhatsApp – Telegram Control System
 * Author: Mohammed
 * Mode: Pairing Code (Phone Number)
 */

require('dotenv').config();

const fs = require('fs');
const path = require('path');

const logger = require('./utils/logger');

// تشغيل بوت تيليجرام
require('./telegram/bot');

// إدارة حسابات واتساب
const {
  restoreLinkedAccounts
} = require('./whatsapp/accounts');

/**
 * التأكد من وجود مجلدات التخزين الأساسية
 */
function ensureBaseStorage() {
  const dirs = [
    'storage/accounts',
    'storage/accounts/sessions',
    'storage/accounts/data',
    'storage/state'
  ];

  for (const dir of dirs) {
    const fullPath = path.join(__dirname, dir);
    if (!fs.existsSync(fullPath)) {
      fs.mkdirSync(fullPath, { recursive: true });
      logger.info(`📁 تم إنشاء المجلد: ${dir}`);
    }
  }
}

/**
 * تشغيل التطبيق
 */
async function startApp() {
  try {
    logger.info('🚀 بدء تشغيل النظام...');

    // تأكد من بنية التخزين
    ensureBaseStorage();

    // تحميل الحسابات المحفوظة (بدون تشغيل اتصال)
    restoreLinkedAccounts();
    logger.info('📦 تم تحميل الحسابات المحفوظة (بدون اتصال)');

    logger.info('🤖 بوت تيليجرام يعمل وجاهز للأوامر');
    logger.info('✅ النظام يعمل بوضع Pairing Code');
  } catch (err) {
    logger.error('🔥 خطأ قاتل أثناء التشغيل', err);
    process.exit(1);
  }
}

// بدء التشغيل
startApp();

/**
 * حماية من الأخطاء غير المتوقعة
 */
process.on('unhandledRejection', (reason) => {
  logger.error('❌ Unhandled Promise Rejection', reason);
});

process.on('uncaughtException', (err) => {
  logger.error('❌ Uncaught Exception', err);
  process.exit(1);
});
