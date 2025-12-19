/**
 * Telegram Bot Core
 */

const TelegramBot = require('node-telegram-bot-api');
const config = require('../config/telegram');
const menus = require('./menus');
const logger = require('../utils/logger');

// Handlers
const { handleLinkAccount } = require('./handlers/linkAccount');
const { handleListAccounts, handleLogout } = require('./handlers/accounts');
const { handleSelectAccount, handleSetActive } = require('./handlers/activeAccount');
const { handleStartScraping, handleStopScraping } = require('./handlers/scraper');
const { handleViewLinks, handleExportLinks } = require('./handlers/links');
const { handleAutoPublish, handleStopPublish } = require('./handlers/publisher');
const { handleRepliesMenu, handleRepliesOn, handleRepliesOff } = require('./handlers/replies');
const { handleJoinGroups } = require('./handlers/groups');
const { handleDashboard } = require('./handlers/dashboard');

let bot;

/**
 * تشغيل بوت تيليجرام
 */
async function startTelegramBot() {
  if (!config.token) {
    throw new Error('TELEGRAM_BOT_TOKEN غير موجود في env');
  }

  bot = new TelegramBot(config.token, config.options);

  /**
   * أمر /start
   */
  bot.onText(/\/start/, async (msg) => {
    await bot.sendMessage(
      msg.chat.id,
      config.messages.start,
      menus.mainMenu
    );
  });

  /**
   * أزرار Inline
   */
  bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const userId = query.from.id;
    const action = query.data;

    try {
      await bot.answerCallbackQuery(query.id);

      // لوحة التحكم
      if (action === 'dashboard') {
        return handleDashboard(bot, chatId);
      }

      // ربط حساب
      if (action === 'link_whatsapp') {
        return handleLinkAccount(bot, chatId);
      }

      // الحسابات
      if (action === 'list_accounts') {
        return handleListAccounts(bot, chatId);
      }

      if (action.startsWith('logout_')) {
        const accId = action.replace('logout_', '');
        return handleLogout(bot, chatId, accId);
      }

      // اختيار الحساب النشط
      if (action === 'select_active_account') {
        return handleSelectAccount(bot, chatId);
      }

      if (action.startsWith('set_active_')) {
        const accId = action.replace('set_active_', '');
        return handleSetActive(bot, chatId, accId);
      }

      // الروابط
      if (action === 'start_scraping') {
        return handleStartScraping(bot, chatId);
      }

      if (action === 'stop_scraping') {
        return handleStopScraping(bot, chatId);
      }

      if (action === 'view_links') {
        return handleViewLinks(bot, chatId);
      }

      if (action === 'export_links') {
        return handleExportLinks(bot, chatId);
      }

      // النشر
      if (action === 'auto_publish') {
        return handleAutoPublish(bot, chatId);
      }

      if (action === 'stop_publish') {
        return handleStopPublish(bot, chatId);
      }

      // الردود
      if (action === 'replies') {
        return handleRepliesMenu(bot, chatId);
      }

      if (action === 'replies_on') {
        return handleRepliesOn(bot, chatId);
      }

      if (action === 'replies_off') {
        return handleRepliesOff(bot, chatId);
      }

      // القروبات
      if (action === 'join_groups') {
        return handleJoinGroups(bot, chatId);
      }

      // افتراضي
      await bot.sendMessage(chatId, '⚙️ هذا الخيار غير معروف حالياً');

    } catch (err) {
      logger.error('❌ خطأ في Telegram callback', err);
      await bot.sendMessage(chatId, '❌ حدث خطأ غير متوقع');
    }
  });

  logger.info('🤖 Telegram Bot Started');
}

module.exports = {
  startTelegramBot,
  getBot: () => bot
};
