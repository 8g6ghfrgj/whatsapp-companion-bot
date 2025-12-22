import { delay } from './delay.js';

export async function retry(fn, options = {}) {
  const {
    retries = 3,
    delayMs = 2000,
    onRetry = null,
  } = options;

  let lastError;

  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;

      if (typeof onRetry === 'function') {
        onRetry(err, attempt);
      }

      if (attempt < retries) {
        await delay(delayMs);
      }
    }
  }

  throw lastError;
}
