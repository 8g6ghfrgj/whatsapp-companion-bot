/**
 * تأخير التنفيذ لمدة معينة (ms)
 * @param {number} ms - الوقت بالمللي ثانية
 */
export function delay(ms) {
  if (!ms || typeof ms !== 'number') {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
