/**
 * Handler: إدارة الردود التلقائية
 * - تشغيل / إيقاف الردود
 * - يعمل فقط على الحساب النشط
 */

const fs = require('fs');
const path = require('path');

const { getActiveAccountId } = require('./activeAccount');
const { getAccount } = require('../../whatsapp/accounts');

/**
 * جلب الحساب النشط أو إرسال تنبيه
 */
function getActiveAccountOrFail(bot, chatId) {
  const accId = getActiveAccountId();

  if (!accId) {
    bot.sendMessage(
      chatId,
      '⚠️ لا يوجد حساب واتساب نشط\n\nيرجى اختيار حساب من زر 🔁 اختيار الحساب النشط'
    );
    return null;
  }

  const account = getAccount(accId);
  if (!account || !account.sock) {
    bot.sendMessage(chatId, '❌ الحساب النشط غير متصل حالياً');
    return null;
  }

  return account;
}

/**
 * مسار ملف إعدادات الردود
 */
function getRepliesConfigPath(accountId) {
  return path.join(
    __dirname,
    `../../storage/accounts/data/${accountId}/replies/config.json`
  );
}

/**
 * تحميل إعدادات الردود
 */
function loadRepliesConfig(accountId) {
  const file = getRepliesConfigPath(accountId);

  if (!fs.existsSync(file)) {
    const defaultConfig = {
      enabled: false,
      private_reply: 'مرحباً 👋\nتم استلام رسالتك، سيتم الرد عليك قريباً.',
      group_reply: '📌 للاستفسار يرجى مراسلتنا على الخاص'
    };

    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(defaultConfig, null, 2));
    return defaultConfig;
  }

  return JSON.parse(fs.readFileSync(file));
}

/**
 * حفظ إعدادات الردود
 */
function saveRepliesConfig(accountId, config) {
  const file = getRepliesConfigPath(accountId);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(config, null, 2));
}

/**
 * قائمة الردود
 */
async function handleRepliesMenu(bot, chatId) {
  const account = getActiveAccountOrFail(bot, chatId);
  if (!account) return;

  const config = loadRepliesConfig(account.id);

  await bot.sendMessage(
    chatId,
    `💬 *إعدادات الردود التلقائية*\n\n` +
    `الحالة الحالية: *${config.enabled ? 'ON' : 'OFF'}*`,
    {
      parse_mode: 'Markdown',
      reply_markup: {
        inline_keyboard: [
          [{ text: '▶️ تشغيل الردود', callback_data: 'replies_on' }],
          [{ text: '⏹️ إيقاف الردود', callback_data: 'replies_off' }]
        ]
      }
    }
  );
}

/**
 * تشغيل الردود
 */
async function handleRepliesOn(bot, chatId) {
  const account = getActiveAccountOrFail(bot, chatId);
  if (!account) return;

  const config = loadRepliesConfig(account.id);
  config.enabled = true;

  saveRepliesConfig(account.id, config);

  await bot.sendMessage(
    chatId,
    `✅ تم تشغيل الردود التلقائية\n\n🆔 الحساب: \`${account.id}\``,
    { parse_mode: 'Markdown' }
  );
}

/**
 * إيقاف الردود
 */
async function handleRepliesOff(bot, chatId) {
  const account = getActiveAccountOrFail(bot, chatId);
  if (!account) return;

  const config = loadRepliesConfig(account.id);
  config.enabled = false;

  saveRepliesConfig(account.id, config);

  await bot.sendMessage(
    chatId,
    `⛔ تم إيقاف الردود التلقائية\n\n🆔 الحساب: \`${account.id}\``,
    { parse_mode: 'Markdown' }
  );
}

module.exports = {
  handleRepliesMenu,
  handleRepliesOn,
  handleRepliesOff
};
