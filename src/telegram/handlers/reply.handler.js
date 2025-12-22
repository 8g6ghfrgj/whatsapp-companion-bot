import { bot } from '../bot.js';
import { RuntimeState } from '../../state/runtime.state.js';

export async function toggle(chatId) {
  RuntimeState.autoReply = !RuntimeState.autoReply;

  bot.sendMessage(
    chatId,
    RuntimeState.autoReply
      ? '💬 الردود التلقائية مفعلة'
      : '💬 الردود التلقائية متوقفة'
  );
}
