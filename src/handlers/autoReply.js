import { sendTextMessage } from '../services/messageService.js';
import { getBotState } from './buttons.js';
import config from '../config.js';

/**
 * نصوص الردود الافتراضية
 */
const DEFAULT_REPLIES = {
  private:
    '👋 أهلاً بك، شكرًا لتواصلك.\nسيتم الرد عليك في أقرب وقت.',
  group:
    '📢 مرحبًا بالجميع، لأي استفسار تواصلوا معنا على الخاص.'
};

/**
 * معالجة الردود التلقائية
 */
export async function handleAutoReply(message) {
  const state = getBotState();
  if (!state.autoReply) return;
  if (!config.features.autoReply) return;

  const { chatId, isGroup, text } = message;

  // لا ترد إذا لا يوجد نص
  if (!text) return;

  // الرد في الخاص
  if (!isGroup) {
    await sendTextMessage(
      chatId,
      DEFAULT_REPLIES.private
    );
    return;
  }

  // الرد داخل القروبات
  if (isGroup) {
    await sendTextMessage(
      chatId,
      DEFAULT_REPLIES.group
    );
  }
}
