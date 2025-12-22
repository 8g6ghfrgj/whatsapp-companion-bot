export const LINK_PATTERNS = {
  whatsapp: /chat\.whatsapp\.com/i,
  telegram: /(t\.me|telegram\.me|telegram\.org)/i,
  instagram: /instagram\.com/i,
  twitter: /(twitter\.com|x\.com)/i,
  youtube: /(youtube\.com|youtu\.be)/i,
  facebook: /facebook\.com/i,
};

export function detectLinkType(url) {
  if (!url) return 'other';

  for (const [type, regex] of Object.entries(LINK_PATTERNS)) {
    if (regex.test(url)) {
      return type;
    }
  }

  return 'other';
}
