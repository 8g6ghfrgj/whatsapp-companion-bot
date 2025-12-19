/**
 * Handler: إدارة الحسابات المرتبطة
 * - عرض الحسابات
 * - تسجيل خروج حساب (إلغاء ربط الجهاز المرافق)
 */

const fs = require('fs-extra');
const path = require('path');

const { listAccounts, getAccount } = require('../../whatsapp/accounts');
const { loadAccounts, saveAccounts } = require('../../whatsapp/accounts/registry');

/**
 * عرض جميع الحسابات المرتبطة
 */
async function handleListAccounts(bot, chatId) {
  const accounts = listAccounts();

  if (!accounts.length) {
    return bot.sendMessage(
      chatId,
      '❌ لا توجد حسابات واتساب مرتبطة حالياً'
    );
  }

  for (const accId of accounts) {
    await bot.sendMessage(
      chatId,
      `📱 حساب واتساب مرتبط:\n🆔 \`${accId}\``,
      {
        parse_mode: 'Markdown',
        reply_markup: {
          inline_keyboard: [
            [
              {
                text: '🚪 تسجيل خروج الحساب',
                callback_data: `logout_${accId}`
              }
            ]
          ]
        }
      }
    );
  }
}

/**
 * تسجيل خروج حساب (إلغاء الربط)
 */
async function handleLogout(bot, chatId, accountId) {
  try {
    const account = getAccount(accountId);

    if (!account || !account.sock) {
      return bot.sendMessage(
        chatId,
        '⚠️ هذا الحساب غير نشط حالياً'
      );
    }

    // تسجيل خروج واتساب (Linked Device logout)
    await account.sock.logout();

    // إزالة الجلسة من الذاكرة
    delete require('../../whatsapp/accounts').activeAccounts;

    // حذف بيانات الجلسة من التخزين
    const sessionPath = path.join(
      __dirname,
      `../../storage/accounts/sessions/${accountId}`
    );

    if (fs.existsSync(sessionPath)) {
      fs.removeSync(sessionPath);
    }

    // حذف بيانات الحساب من السجل
    const data = loadAccounts();
    data.accounts = data.accounts.filter(acc => acc.id !== accountId);
    saveAccounts(data);

    await bot.sendMessage(
      chatId,
      `🚪 تم تسجيل الخروج من الحساب بنجاح\n\n🆔 \`${accountId}\``,
      { parse_mode: 'Markdown' }
    );

  } catch (err) {
    console.error(err);
    await bot.sendMessage(
      chatId,
      '❌ حدث خطأ أثناء تسجيل خروج الحساب'
    );
  }
}

module.exports = {
  handleListAccounts,
  handleLogout
};
