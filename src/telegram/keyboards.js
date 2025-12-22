// =====================================
// Main Control Panel Keyboard
// =====================================
export const mainKeyboard = {
  reply_markup: {
    inline_keyboard: [
      [
        { text: '🔗 ربط حساب واتساب', callback_data: 'wa_link' },
        { text: '📱 عرض الحسابات المرتبطة', callback_data: 'wa_accounts' },
      ],
      [
        { text: '🔍 بدء تجميع الروابط', callback_data: 'links_start' },
        { text: '⏹️ إيقاف التجميع', callback_data: 'links_stop' },
      ],
      [
        { text: '📂 عرض الروابط المجمعة', callback_data: 'links_show' },
        { text: '📤 تصدير الروابط', callback_data: 'links_export' },
      ],
      [
        { text: '📢 بدء النشر التلقائي', callback_data: 'post_start' },
        { text: '🛑 إيقاف النشر', callback_data: 'post_stop' },
      ],
      [
        { text: '💬 تفعيل / إيقاف الردود', callback_data: 'reply_toggle' },
      ],
      [
        { text: '👥 الانضمام إلى مجموعات', callback_data: 'group_join' },
      ],
    ],
  },
};

// =====================================
// Accounts List Keyboard
// (Logout / Delete per account)
// =====================================
export function accountListKeyboard(accounts = []) {
  const keyboard = [];

  for (const acc of accounts) {
    keyboard.push([
      {
        text: `🔓 تسجيل خروج (${acc.name})`,
        callback_data: `account_logout:${acc.id}`,
      },
      {
        text: `🗑️ حذف الجلسة (${acc.name})`,
        callback_data: `account_delete:${acc.id}`,
      },
    ]);
  }

  keyboard.push([
    { text: '⬅️ رجوع', callback_data: 'back_main' },
  ]);

  return {
    inline_keyboard: keyboard,
  };
}
