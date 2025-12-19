/**
 * Handler: اختيار وتبديل الحساب النشط
 * - عرض الحسابات
 * - تعيين حساب نشط
 * - حفظ الحالة بشكل دائم
 */

const fs = require('fs');
const path = require('path');

const { listAccounts } = require('../../whatsapp/accounts');

const STATE_FILE = path.join(
  __dirname,
  '../../storage/state/active_account.json'
);

/**
 * التأكد من وجود ملف الحالة
 */
function ensureStateFile() {
  if (!fs.existsSync(STATE_FILE)) {
    fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
    fs.writeFileSync(
      STATE_FILE,
      JSON.stringify({ activeAccountId: null }, null, 2)
    );
  }
}

/**
 * تحميل الحالة
 */
function loadState() {
  ensureStateFile();
  return JSON.parse(fs.readFileSync(STATE_FILE));
}

/**
 * حفظ الحالة
 */
function saveState(state) {
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

/**
 * جلب الحساب النشط
 */
function getActiveAccountId() {
  const state = loadState();
  return state.activeAccountId;
}

/**
 * عرض قائمة اختيار الحساب النشط
 */
async function handleSelectAccount(bot, chatId) {
  const accounts = listAccounts();

  if (!accounts.length) {
    return bot.sendMessage(
      chatId,
      '❌ لا توجد حسابات واتساب مرتبطة\n\nيرجى ربط حساب أولاً'
    );
  }

  const keyboard = accounts.map(accId => [
    {
      text: `📱 ${accId}`,
      callback_data: `set_active_${accId}`
    }
  ]);

  await bot.sendMessage(
    chatId,
    '🔁 اختر الحساب الذي تريد تعيينه كحساب نشط:',
    {
      reply_markup: {
        inline_keyboard: keyboard
      }
    }
  );
}

/**
 * تعيين حساب نشط
 */
async function handleSetActive(bot, chatId, accountId) {
  const accounts = listAccounts();

  if (!accounts.includes(accountId)) {
    return bot.sendMessage(
      chatId,
      '❌ هذا الحساب غير موجود أو غير متصل'
    );
  }

  saveState({ activeAccountId: accountId });

  await bot.sendMessage(
    chatId,
    `✅ تم تعيين الحساب النشط بنجاح\n\n🆔 \`${accountId}\``,
    { parse_mode: 'Markdown' }
  );
}

module.exports = {
  handleSelectAccount,
  handleSetActive,
  getActiveAccountId
};
