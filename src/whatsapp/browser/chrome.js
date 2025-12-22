import puppeteer from 'puppeteer';
import { logger } from '../../logger/logger.js';

export async function launchChrome(userDataDir) {
  logger.info(`Launching Chrome with profile: ${userDataDir}`);

  const browser = await puppeteer.launch({
    headless: false, // مهم جدًا
    executablePath: '/usr/bin/google-chrome',
    userDataDir,
    defaultViewport: null,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-infobars',
      '--disable-blink-features=AutomationControlled',
      '--start-maximized',
    ],
  });

  return browser;
}
