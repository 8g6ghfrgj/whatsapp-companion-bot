import { bot } from '../bot.js';

/**
 * الانضمام إلى مجموعات واتساب
 * (معطّل مؤقتًا حتى اكتمال ربط منطق الجلسة النهائية)
 */
export async function join(chatId) {
  try {
    await bot.sendMessage(
      chatId,
      '⚠️ الانضمام إلى المجموعات غير مفعل حاليًا.\n' +
      'سيتم تفعيله بعد استقرار ربط الجلسة بشكل كامل.'
    );
  } catch (_) {}
}
