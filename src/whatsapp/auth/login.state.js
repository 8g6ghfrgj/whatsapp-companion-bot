import { logger } from '../../logger/logger.js';

export async function isLoggedIn(page) {
  try {
    // إذا ظهر QR → غير مسجّل
    const qr = await page.$('canvas[aria-label]');
    if (qr) {
      logger.info('WhatsApp not logged in (QR visible)');
      return false;
    }

    // انتظار واجهة التطبيق
    await page.waitForSelector('div[role="application"]', {
      timeout: 5000,
    });

    logger.info('WhatsApp session is active');
    return true;
  } catch {
    logger.warn('Unable to determine WhatsApp login state');
    return false;
  }
}
