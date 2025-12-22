import { bot, isAdmin } from './bot.js';
import { mainKeyboard } from './keyboards.js';

// Handlers
import * as accountHandler from './handlers/account.handler.js';
import * as linkHandler from './handlers/link.handler.js';
import * as postHandler from './handlers/post.handler.js';
import * as replyHandler from './handlers/reply.handler.js';
import * as groupHandler from './handlers/group.handler.js';

// =====================================
// Start Command
// =====================================
bot.onText(/\/start/, (msg) => {
  if (!isAdmin(msg)) return;

  bot.sendMessage(
    msg.chat.id,
    '🛠️ لوحة التحكم الرئيسية',
    mainKeyboard
  );
});

// =====================================
// Inline Button Router
// =====================================
bot.on('callback_query', async (query) => {
  if (!query.from || !isAdmin({ from: query.from })) return;

  const chatId = query.message.chat.id;
  const action = query.data;

  try {
    await bot.answerCallbackQuery(query.id);
  } catch (_) {}

  try {
    // ===============================
    // Accounts
    // ===============================
    if (action === 'wa_link') {
      return accountHandler.link(chatId);
    }

    if (action === 'wa_accounts') {
      return accountHandler.list(chatId);
    }

    if (action.startsWith('account_logout:')) {
      const accountId = Number(action.split(':')[1]);
      return accountHandler.logout(chatId, accountId);
    }

    if (action.startsWith('account_delete:')) {
      const accountId = Number(action.split(':')[1]);
      return accountHandler.remove(chatId, accountId);
    }

    // ===============================
    // Navigation
    // ===============================
    if (action === 'back_main') {
      return bot.sendMessage(
        chatId,
        '🛠️ لوحة التحكم الرئيسية',
        mainKeyboard
      );
    }

    // ===============================
    // Links
    // ===============================
    if (action === 'links_start') {
      return linkHandler.start(chatId);
    }

    if (action === 'links_stop') {
      return linkHandler.stop(chatId);
    }

    if (action === 'links_show') {
      return linkHandler.show(chatId);
    }

    if (action === 'links_export') {
      return linkHandler.exportLinks(chatId);
    }

    // ===============================
    // Posting
    // ===============================
    if (action === 'post_start') {
      return postHandler.start(chatId);
    }

    if (action === 'post_stop') {
      return postHandler.stop(chatId);
    }

    // ===============================
    // Auto Reply
    // ===============================
    if (action === 'reply_toggle') {
      return replyHandler.toggle(chatId);
    }

    // ===============================
    // Groups
    // ===============================
    if (action === 'group_join') {
      return groupHandler.join(chatId);
    }

    // ===============================
    // Unknown
    // ===============================
    return bot.sendMessage(chatId, '❓ أمر غير معروف');
  } catch (err) {
    return bot.sendMessage(chatId, '❌ حدث خطأ أثناء تنفيذ الأمر');
  }
});
