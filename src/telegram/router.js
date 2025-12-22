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
  const msg = query.message;
  if (!isAdmin(msg)) return;

  const chatId = msg.chat.id;
  const action = query.data;

  try {
    await bot.answerCallbackQuery(query.id);
  } catch (_) {}

  try {
    switch (action) {
      // Accounts
      case 'wa_link':
        return accountHandler.link(chatId);

      case 'wa_accounts':
        return accountHandler.list(chatId);

      // Links
      case 'links_start':
        return linkHandler.start(chatId);

      case 'links_stop':
        return linkHandler.stop(chatId);

      case 'links_show':
        return linkHandler.show(chatId);

      case 'links_export':
        return linkHandler.exportLinks(chatId);

      // Posting
      case 'post_start':
        return postHandler.start(chatId);

      case 'post_stop':
        return postHandler.stop(chatId);

      // Auto Reply
      case 'reply_toggle':
        return replyHandler.toggle(chatId);

      // Groups
      case 'group_join':
        return groupHandler.join(chatId);

      default:
        return bot.sendMessage(chatId, '❓ أمر غير معروف');
    }
  } catch (err) {
    bot.sendMessage(chatId, '❌ حدث خطأ أثناء تنفيذ الأمر');
  }
});
