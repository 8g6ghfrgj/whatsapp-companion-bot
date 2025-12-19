/**
 * Link Classifier Utility
 * مسؤول عن تصنيف الروابط حسب المنصة
 */

/**
 * تصنيف رابط حسب نوعه
 * @param {string} link
 * @returns {string} type
 */
function classifyLink(link = '') {
  if (typeof link !== 'string') return 'others';

  const url = link.toLowerCase();

  // WhatsApp Groups
  if (url.includes('chat.whatsapp.com')) {
    return 'whatsapp';
  }

  // Telegram
  if (
    url.includes('t.me/') ||
    url.includes('telegram.me/')
  ) {
    return 'telegram';
  }

  // X (Twitter)
  if (
    url.includes('twitter.com') ||
    url.includes('x.com')
  ) {
    return 'twitter';
  }

  // Instagram
  if (url.includes('instagram.com')) {
    return 'instagram';
  }

  // TikTok
  if (url.includes('tiktok.com')) {
    return 'tiktok';
  }

  // Anything else
  return 'others';
}

module.exports = {
  classifyLink
};
