/**
 * Advanced Dashboard Handler
 * يعرض لوحة تحكم متقدمة للحساب النشط
 */

const fs = require('fs');
const path = require('path');

const { listAccounts } = require('../../whatsapp/accounts');
const { getActiveAccountId } = require('./activeAccount');

/**
 * قراءة إعدادات الردود
 */
function loadRepliesConfig(accId) {
  const file = path.join(
    __dirname,
    `../../storage/accounts/data/${accId}/replies/config.json`
  );

  if (!fs.existsSync(file)) {
    return { enabled: false };
  }

  return JSON.parse(fs.readFileSync(file));
}

/**
 * عدّ الروابط لكل حساب
 */
function countLinks(accId) {
  const linksDir = path.join(
    __dirname,
    `../../storage/accounts/data/${accId}/links`
  );

  if (!fs.existsSync(linksDir)) return 0;

  let total = 0;

  for (const file of fs.readdirSync(linksDir)) {
    const data = JSON.parse(
      fs.readFileSync(path.join(linksDir, file))
    );
    total += (data.links || []).length;
  }

  return total;
}

/**
 * قراءة تقرير القروبات
 */
function loadGroupReport(accId) {
  const file = path.join(
    __dirname,
    `../../storage/accounts/data/${accId}/groups/report.json`
  );

  if (!fs.existsSync(file)) {
    return { joined: [], pending: [], failed: [] };
  }

  return JSON.parse(fs.readFileSync(file));
}

/**
 * لوحة التحكم
 */
async function handleDashboard(bot, chatId) {
  const activeAccountId = getActiveAccountId();
  const accountsCount = listAccounts().length;

  if (!activeAccountId) {
    return bot.sendMessage(
      chatId,
      '⚠️ لا يوجد حساب واتساب نشط\n\n' +
      'يرجى اختيار حساب من زر 🔁 اختيار الحساب النشط'
    );
  }

  const linksCount = countLinks(activeAccountId);
  const groupReport = loadGroupReport(activeAccountId);
  const repliesConfig = loadRepliesConfig(activeAccountId);

  const message =
`📊 *لوحة التحكم المتقدمة*
────────────────────
👤 الحساب النشط:
\`${activeAccountId}\`

📱 الحسابات المرتبطة:
*${accountsCount}*

────────────────────
▶️ تجميع الروابط:
*ON*

📥 إجمالي الروابط:
*${linksCount}*

────────────────────
📢 النشر التلقائي:
*OFF*

💬 الردود التلقائية:
*${repliesConfig.enabled ? 'ON' : 'OFF'}*

────────────────────
👥 القروبات:
• تم الانضمام: *${groupReport.joined.length}*
• بانتظار الموافقة: *${groupReport.pending.length}*
• فشل: *${groupReport.failed.length}*

────────────────────
⏱️ الحالة:
*النظام يعمل بشكل طبيعي ✅*`;

  await bot.sendMessage(chatId, message, {
    parse_mode: 'Markdown',
    reply_markup: {
      inline_keyboard: [
        [{ text: '🔁 تبديل الحساب', callback_data: 'select_active_account' }],
        [
          { text: '▶️ تشغيل الجمع', callback_data: 'start_scraping' },
          { text: '⏹️ إيقاف الجمع', callback_data: 'stop_scraping' }
        ],
        [
          { text: '📢 نشر تلقائي', callback_data: 'auto_publish' },
          { text: '⛔ إيقاف النشر', callback_data: 'stop_publish' }
        ],
        [{ text: '💬 إعدادات الردود', callback_data: 'replies' }],
        [{ text: '👥 الانضمام إلى القروبات', callback_data: 'join_groups' }]
      ]
    }
  });
}

module.exports = {
  handleDashboard
};
