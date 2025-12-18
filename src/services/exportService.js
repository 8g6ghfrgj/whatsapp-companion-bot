import fs from 'fs';
import path from 'path';
import config from '../config.js';
import {
  getAllLinksGrouped
} from '../database/models/links.model.js';

/**
 * التأكد من وجود مجلد التصدير
 */
function ensureExportDir() {
  if (!fs.existsSync(config.paths.exports)) {
    fs.mkdirSync(config.paths.exports, { recursive: true });
  }
}

/**
 * تصدير الروابط إلى ملفات TXT
 */
export async function exportLinksToTxt() {
  ensureExportDir();

  const groupedLinks = await getAllLinksGrouped();
  const exportedFiles = [];

  for (const [type, links] of Object.entries(groupedLinks)) {
    if (!links.length) continue;

    const fileName = `links_${type}.txt`;
    const filePath = path.join(
      config.paths.exports,
      fileName
    );

    const content = links.join('\n');

    fs.writeFileSync(
      filePath,
      content,
      { encoding: 'utf-8' }
    );

    exportedFiles.push({
      type,
      filePath,
      count: links.length
    });
  }

  return exportedFiles;
}
