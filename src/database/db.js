import fs from 'fs';
import path from 'path';
import sqlite3 from 'sqlite3';

import { PATHS } from '../config/paths.js';
import { logger } from '../logger/logger.js';

// ================================
// Database File
// ================================
const DB_FILE = PATHS.DATABASE_FILE;

// ================================
// Ensure Database File Exists
// ================================
if (!fs.existsSync(DB_FILE)) {
  fs.writeFileSync(DB_FILE, '');
  logger.info('Database file created');
}

// ================================
// Open Database Connection
// ================================
export const db = new sqlite3.Database(DB_FILE, (err) => {
  if (err) {
    logger.error(`Database connection failed: ${err.message}`);
    process.exit(1);
  }
  logger.info('Database connected');
});

// ================================
// Initialize Schema
// ================================
export function initDatabase() {
  const schemaPath = path.join(PATHS.SRC, 'database', 'schema.sql');

  if (!fs.existsSync(schemaPath)) {
    logger.error('schema.sql not found');
    process.exit(1);
  }

  const schema = fs.readFileSync(schemaPath, 'utf8');

  db.exec(schema, (err) => {
    if (err) {
      logger.error(`Schema initialization failed: ${err.message}`);
      process.exit(1);
    }
    logger.info('Database schema initialized');
  });
}
