/**
 * Entry Point
 * WhatsApp – Telegram Control System
 * Author: Mohammed
 */

require('dotenv').config();

const fs = require('fs');
const path = require('path');

const logger = require('./utils/logger');
const { startTelegramBot } = require('./telegram/bot');
const { loadAccounts } = require('./whatsapp/accounts/registry');
const { createAccount } = require('./whatsapp/accounts');

/**
 * تأكد من وجود مجلدات التخزين الأساسية
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
    }
  }
}

/**
 * إعادة تشغيل الحسابات المرتبطة تلقائيًا عند بدء السيرفر
 */
async function restoreLinkedAccounts() {
  const data = loadAccounts();

  if (!data.accounts || !data.accounts.length) {
    logger.info('ℹ️ لا توجد حسابات واتساب محفوظة لإعادة تشغيلها');
    return;
  }

  logger.info(`🔄 إعادة تشغيل ${data.accounts.length} حساب واتساب`);

  for (const acc of data.accounts) {
    try {
      await createAccount(acc.id);
      logger.info(`✅ تم إعادة تشغيل الحساب: ${acc.id}`);
    } catch (err) {
      logger.error(`❌ فشل تشغيل الحساب: ${acc.id}`, err);
    }
  }
}

/**
 * تشغيل التطبيق
 */
async function startApp() {
  try {
    logger.info('🚀 بدء تشغيل النظام...');
    
    ensureBaseStorage();

    // تشغيل بوت تيليجرام
    await startTelegramBot();
    logger.info('🤖 بوت تيليجرام يعمل بنجاح');

    // إعادة تشغيل حسابات واتساب المرتبطة
    await restoreLinkedAccounts();

    logger.info('✅ النظام يعمل بكامل طاقته');
  } catch (err) {
    logger.error('🔥 خطأ قاتل أثناء التشغيل', err);
    process.exit(1);
  }
}

// بدء التشغيل
startApp();

// حماية من أخطاء غير متوقعة
process.on('unhandledRejection', (reason) => {
  logger.error('❌ Unhandled Promise Rejection', reason);
});

process.on('uncaughtException', (err) => {
  logger.error('❌ Uncaught Exception', err);
  process.exit(1);
});
