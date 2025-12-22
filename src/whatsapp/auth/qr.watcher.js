import fs from 'fs';
import path from 'path';
import { logger } from '../../logger/logger.js';

export async function waitForQR(page, onQR) {
  logger.info('Waiting for WhatsApp QR code');

  const qrSelector = 'canvas[aria-label]';

  // انتظار ظهور QR
  await page.waitForSelector(qrSelector, { timeout: 0 });

  const qrElement = await page.$(qrSelector);
  if (!qrElement) {
    throw new Error('QR element not found');
  }

  const qrPath = path.join(process.cwd(), 'whatsapp_qr.png');

  await qrElement.screenshot({ path: qrPath });

  logger.info('QR code captured');

  if (typeof onQR === 'function') {
    onQR(qrPath);
  }

  return qrPath;
}
