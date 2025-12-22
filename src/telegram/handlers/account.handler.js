import { bot } from '../bot.js';
import * as AccountsRepo from '../../database/repositories/accounts.repo.js';
import {
  startWhatsAppSession,
  isWhatsAppLoggedIn,
  logoutWhatsApp,
  destroyWhatsAppSession,
} from '../../whatsapp/whatsapp.controller.js';

import { accountListKeyboard } from '../keyboards.js';

/**
 * ربط حساب واتساب
 *
 * السلوك:
 * - كل ضغط زر = محاولة ربط جديدة
 * - إذا لم يتم الربط سابقًا → QR جديد (Chrome جديد)
 * - إذا تم الربط → لا QR ويظهر نجاح
 */
export async function link(chatId) {
  try {
    // إذا الحساب مربوط فعليًا
    if (await isWhatsAppLoggedIn()) {
      const active = await AccountsRepo.getActive();
      if (!active) {
        await AccountsRepo.create({
          name: `Account-${Date.now()}`,
          is_active: 1,
        });
      }

      await bot.sendMessage(chatId, '✅ تم ربط حساب واتساب بنجاح');
      return;
    }

    // لم يتم الربط بعد → نبدأ جلسة جديدة مع QR جديد
    await bot.sendMessage(chatId, '⏳ جارٍ إنشاء جلسة واتساب، انتظر لحظة...');

    await startWhatsAppSession(
      async (qrBuffer) => {
        await bot.sendPhoto(chatId, qrBuffer, {
          caption: '📲 امسح رمز QR لربط حساب واتساب',
        });
      },
      true // forceRestart = true → Chrome جديد + QR جديد
    );
  } catch (err) {
    await bot.sendMessage(chatId, '❌ فشل بدء ربط واتساب');
  }
}

/**
 * عرض الحسابات المرتبطة
 */
export async function list(chatId) {
  const accounts = await AccountsRepo.getAll();

  if (!accounts.length) {
    await bot.sendMessage(chatId, '📱 لا يوجد حسابات مرتبطة حاليًا');
    return;
  }

  let text = '📱 الحسابات المرتبطة:\n\n';
  for (const acc of accounts) {
    text += `• ${acc.name} (${acc.is_active ? 'نشط' : 'غير نشط'})\n`;
  }

  await bot.sendMessage(chatId, text, {
    reply_markup: accountListKeyboard(accounts),
  });
}

/**
 * تسجيل خروج من واتساب
 */
export async function logout(chatId, accountId) {
  try {
    await logoutWhatsApp();
    await AccountsRepo.setInactive(accountId);

    await bot.sendMessage(chatId, '🔓 تم تسجيل الخروج من حساب واتساب');
  } catch (_) {
    await bot.sendMessage(chatId, '❌ فشل تسجيل الخروج');
  }
}

/**
 * حذف الجلسة نهائيًا
 */
export async function remove(chatId, accountId) {
  try {
    await destroyWhatsAppSession();
    await AccountsRepo.deleteById(accountId);

    await bot.sendMessage(chatId, '🗑️ تم حذف الجلسة نهائيًا');
  } catch (_) {
    await bot.sendMessage(chatId, '❌ فشل حذف الجلسة');
  }
}
