import config from './config.js';
import { connectWhatsApp } from './core/connect.js';
import { startMessageListener } from './core/listener.js';

// Handlers
import {
  showMainMenu,
  handleButtonAction
} from './handlers/buttons.js';

import {
  initLinkCollector,
  handleLinkCollection
} from './handlers/linkCollector.js';

import { handleAutoReply } from './handlers/autoReply.js';

import {
  handleJoinGroups,
  processGroupJoins,
  sendJoinReport,
  monitorExpiredGroups
} from './handlers/joinGroups.js';

import {
  startAutoPost
} from './handlers/autoPost.js';

// Database init
import { initLinksTable } from './database/models/links.model.js';
import { initGroupsTable } from './database/models/groups.model.js';

// منع سقوط التطبيق
process.on('unhandledRejection', (reason) => {
  console.error('❌ Unhandled Rejection:', reason);
});

process.on('uncaughtException', (error) => {
  console.error('❌ Uncaught Exception:', error);
});

async function startBot() {
  console.log('🚀 تشغيل WhatsApp Companion Bot');

  // 1️⃣ الاتصال بواتساب
  await connectWhatsApp();

  // 2️⃣ تهيئة قواعد البيانات
  await initLinksTable();
  await initGroupsTable();
  await initLinkCollector();

  console.log('🧠 النظام جاهز – بدء الاستماع للرسائل');

  // 3️⃣ بدء الاستماع للرسائل
  startMessageListener(async (message) => {
    try {
      const { chatId, text } = message;

      // عرض القائمة عند كتابة "menu"
      if (text && text.toLowerCase() === 'menu') {
        await showMainMenu(chatId);
        return;
      }

      // معالجة ضغط الأزرار
      await handleButtonAction(message);

      // تجميع الروابط
      await handleLinkCollection(message);

      // الردود التلقائية
      await handleAutoReply(message);

      // استقبال روابط المجموعات
      await handleJoinGroups(message);

      // بدء النشر التلقائي (يعمل فقط إذا مفعّل)
      await startAutoPost();

    } catch (err) {
      console.error('❌ Message processing error:', err);
    }
  });

  // 4️⃣ فحص الطلبات المنتهية كل ساعة
  setInterval(async () => {
    await monitorExpiredGroups();
  }, 60 * 60 * 1000);
}

startBot();
