import {
  isWhatsAppGroupLink,
  extractGroupLink,
  joinGroupsSequentially,
  checkExpiredGroupRequests
} from '../services/groupService.js';
import { sendTextMessage } from '../services/messageService.js';
import { getBotState } from './buttons.js';
import {
  getAllGroups,
  getGroupsByStatus
} from '../database/models/groups.model.js';

/**
 * قائمة روابط الانتظار
 */
let pendingInviteLinks = [];

/**
 * استقبال الرسائل لمعالجة روابط المجموعات
 */
export async function handleJoinGroups(message) {
  const { text, chatId } = message;
  if (!text) return;

  const state = getBotState();
  if (!state) return;

  // إذا لم يكن المستخدم في وضع الانضمام
  if (!state.autoReply && !state.autoPost && !state.linkCollector) {
    // نسمح دائمًا بالانضمام عند الضغط على الزر
  }

  // التحقق من وجود رابط مجموعة
  if (!isWhatsAppGroupLink(text)) return;

  const link = extractGroupLink(text);
  if (!link) return;

  pendingInviteLinks.push(link);

  await sendTextMessage(
    chatId,
    '⏳ تم استلام رابط المجموعة وسيتم طلب الانضمام إليه.'
  );
}

/**
 * بدء عملية الانضمام لكل الروابط المستلمة
 */
export async function processGroupJoins(chatId) {
  if (!pendingInviteLinks.length) {
    await sendTextMessage(
      chatId,
      'ℹ️ لا توجد روابط مجموعات للانضمام.'
    );
    return;
  }

  const linksToJoin = [...pendingInviteLinks];
  pendingInviteLinks = [];

  await sendTextMessage(
    chatId,
    `👥 بدء الانضمام إلى ${linksToJoin.length} مجموعة.\n⏱️ سيتم الانضمام كل دقيقتين.`
  );

  try {
    await joinGroupsSequentially(linksToJoin);
  } catch (error) {
    console.error('❌ Error during group joining:', error);
  }
}

/**
 * إرسال تقرير الانضمام
 */
export async function sendJoinReport(chatId) {
  const joined = await getGroupsByStatus('joined');
  const pending = await getGroupsByStatus('pending');
  const expired = await getGroupsByStatus('expired');
  const rejected = await getGroupsByStatus('rejected');

  let report = '📊 تقرير الانضمام للمجموعات:\n\n';

  report += `✅ تم الانضمام: ${joined.length}\n`;
  report += `⏳ قيد الانتظار: ${pending.length}\n`;
  report += `❌ مرفوضة: ${rejected.length}\n`;
  report += `⌛ منتهية (24 ساعة): ${expired.length}\n`;

  await sendTextMessage(chatId, report);
}

/**
 * فحص الطلبات المنتهية (يُستدعى دوريًا)
 */
export async function monitorExpiredGroups() {
  try {
    await checkExpiredGroupRequests();
  } catch (error) {
    console.error('❌ Expired groups check failed:', error);
  }
}
