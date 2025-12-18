import { parseLinks } from '../services/linkParser.js';
import {
  addLink,
  initLinksTable
} from '../database/models/links.model.js';
import { getBotState } from './buttons.js';

/**
 * تهيئة جدول الروابط
 * يجب استدعاؤها مرة واحدة عند التشغيل
 */
export async function initLinkCollector() {
  try {
    await initLinksTable();
    console.log('🔗 Links table ready');
  } catch (error) {
    console.error('❌ Failed to init links table:', error);
  }
}

/**
 * معالجة الرسائل وتجميع الروابط
 */
export async function handleLinkCollection(message) {
  const { text, chatId } = message;

  if (!text) return;

  const state = getBotState();
  if (!state.linkCollector) return;

  const links = parseLinks(text);
  if (!links.length) return;

  for (const link of links) {
    await addLink(
      link.url,
      link.type,
      chatId
    );
  }
}
