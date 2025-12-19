/**
 * Handler: التحكم في تجميع الروابط (تشغيل / إيقاف)
 * يعمل فقط على الحساب النشط
 */

const { getAccount } = require('../../whatsapp/accounts');
const { getActiveAccountId } = require('./activeAccount');

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
    bot.sendMessage(
      chatId,
      '❌ الحساب النشط غير متصل حالياً'
    );
    return null;
  }

  return account;
}

/**
 * تشغيل تجميع الروابط
 */
async function handleStartScraping(bot, chatId) {
  const account = getActiveAccountOrFail(bot, chatId);
  if (!account) return;

  // تفعيل التجميع على مستوى الحساب
  account.scrapingEnabled = true;

  await bot.sendMessage(
    chatId,
    `▶️ تم تشغيل تجميع الروابط\n\n🆔 الحساب: \`${account.id}\``,
    { parse_mode: 'Markdown' }
  );
}

/**
 * إيقاف تجميع الروابط
 */
async function handleStopScraping(bot, chatId) {
  const account = getActiveAccountOrFail(bot, chatId);
  if (!account) return;

  account.scrapingEnabled = false;

  await bot.sendMessage(
    chatId,
    `⏹️ تم إيقاف تجميع الروابط\n\n🆔 الحساب: \`${account.id}\``,
    { parse_mode: 'Markdown' }
  );
}

module.exports = {
  handleStartScraping,
  handleStopScraping
};
