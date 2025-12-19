/**
 * Telegram Handler – Link WhatsApp Account (Pairing Code)
 * المسؤول عن:
 * - بدء عملية ربط الحساب
 * - طلب رقم الهاتف من المستخدم
 * - تشغيل connectWithPairing
 */

const WhatsAppAccount = require('../../whatsapp/accounts/account');
const {
  createAccount
} = require('../../whatsapp/accounts/index');
const logger = require('../../utils/logger');

// تخزين حالة انتظار رقم الهاتف لكل مستخدم تيليجرام
const waitingForPhone = new Map();

/**
 * بدء ربط حساب واتساب
 */
async function startLinkAccount(bot, chatId) {
  waitingForPhone.set(chatId, true);

  await bot.sendMessage(
    chatId,
    '📱 *ربط حساب واتساب*\n\n' +
      'أرسل رقم الهاتف الدولي بدون علامة +\n\n' +
      'مثال:\n' +
      '`9677XXXXXXXX`\n\n' +
      '⚠️ يجب أن يكون الرقم مفعل عليه واتساب',
    { parse_mode: 'Markdown' }
  );
}

/**
 * استقبال رقم الهاتف وبدء الربط
 */
async function handlePhoneNumber(bot, msg) {
  const chatId = msg.chat.id;
  const text = msg.text ? msg.text.trim() : '';

  // إذا لم يكن المستخدم في وضع ربط
  if (!waitingForPhone.has(chatId)) return;

  // تجاهل الأوامر
  if (text.startsWith('/')) return;

  // تنظيف الرقم
  const phone = text.replace(/\s+/g, '');

  // تحقق بسيط من صحة الرقم
  if (!/^\d{8,15}$/.test(phone)) {
    await bot.sendMessage(
      chatId,
      '❌ رقم غير صالح.\n\n' +
        'أرسل رقم الهاتف الدولي بدون +\n' +
        'مثال:\n' +
        '`9677XXXXXXXX`',
      { parse_mode: 'Markdown' }
    );
    return;
  }

  // إلغاء وضع الانتظار
  waitingForPhone.delete(chatId);

  // إنشاء حساب جديد
  const account = createAccount();

  await bot.sendMessage(
    chatId,
    '🔗 يتم الآن إنشاء جلسة ربط واتساب...\n\n' +
      '📲 سيتم توليد *رمز اقتران* خلال لحظات\n\n' +
      'اذهب إلى واتساب:\n' +
      'الأجهزة المرتبطة → ربط جهاز → الربط برقم الهاتف',
    { parse_mode: 'Markdown' }
  );

  try {
    // بدء الربط برقم الهاتف
    await account.connectWithPairing(phone);

    await bot.sendMessage(
      chatId,
      '🔐 *تم توليد رمز الاقتران*\n\n' +
        '📱 افتح واتساب وأدخل الرمز الذي ظهر في السيرفر\n\n' +
        `🆔 *معرّف الحساب:*\n\`${account.id}\``,
      { parse_mode: 'Markdown' }
    );

    logger.info(
      `📱 بدء Pairing Code للحساب ${account.id} (phone: ${phone})`
    );
  } catch (err) {
    logger.error('❌ فشل ربط حساب واتساب', err);

    await bot.sendMessage(
      chatId,
      '❌ حدث خطأ أثناء ربط الحساب.\n\n' +
        'يرجى المحاولة مرة أخرى من زر ربط حساب واتساب.'
    );
  }
}

module.exports = {
  startLinkAccount,
  handlePhoneNumber
};
