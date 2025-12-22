import TelegramBot from 'node-telegram-bot-api';

import { ENV } from '../config/env.js';
import { logger } from '../logger/logger.js';

// =====================================
// Create Telegram Bot Instance
// =====================================
export const bot = new TelegramBot(ENV.TELEGRAM.TOKEN, {
  polling: true,
});

// =====================================
// Admin Guard
// =====================================
export function isAdmin(msg) {
  if (!msg || !msg.from) return false;
  return msg.from.id === ENV.TELEGRAM.ADMIN_ID;
}

// =====================================
// Global Error Handling
// =====================================
bot.on('polling_error', (err) => {
  logger.error(`Telegram polling error: ${err.message}`);
});

bot.on('webhook_error', (err) => {
  logger.error(`Telegram webhook error: ${err.message}`);
});

// =====================================
// Security (IMPORTANT FIX)
// =====================================
// نمنع فقط الأوامر النصية من غير الأدمن
// ولا نلمس callback_query نهائيًا
bot.on('message', (msg) => {
  if (!isAdmin(msg)) {
    // نرد فقط لو رسالة نصية (أوامر)
    if (msg.text && msg.text.startsWith('/')) {
      try {
        bot.sendMessage(
          msg.chat.id,
          '❌ غير مصرح لك باستخدام هذا البوت'
        );
      } catch (_) {}
      logger.warn(`Unauthorized command from ${msg.from.id}`);
    }
  }
});

// =====================================
// Startup Log
// =====================================
logger.info('Telegram bot started and polling');
