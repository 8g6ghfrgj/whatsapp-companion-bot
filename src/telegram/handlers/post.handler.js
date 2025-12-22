import { bot } from '../bot.js';

/**
 * بدء النشر التلقائي
 * (معطّل مؤقتًا إلى أن يكتمل ربط منطق النشر مع جلسة واتساب الجديدة)
 */
export async function start(chatId) {
  try {
    await bot.sendMessage(
      chatId,
      '⚠️ النشر التلقائي غير مفعل حاليًا.\n' +
      'سيتم تفعيله بعد الانتهاء من ربط الجلسة النهائية بشكل كامل.'
    );
  } catch (_) {}
}

/**
 * إيقاف النشر التلقائي
 */
export async function stop(chatId) {
  try {
    await bot.sendMessage(
      chatId,
      '⛔ لا يوجد نشر تلقائي نشط حاليًا.'
    );
  } catch (_) {}
}
