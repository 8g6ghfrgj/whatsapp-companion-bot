import { db } from '../db.js';

export const SettingsRepo = {
  set(key, value) {
    return new Promise((resolve, reject) => {
      db.run(
        `INSERT OR REPLACE INTO settings (key, value)
         VALUES (?, ?)`,
        [key, value],
        (err) => (err ? reject(err) : resolve())
      );
    });
  },

  get(key) {
    return new Promise((resolve, reject) => {
      db.get(
        `SELECT value FROM settings WHERE key = ?`,
        [key],
        (err, row) => (err ? reject(err) : resolve(row?.value))
      );
    });
  },

  getAll() {
    return new Promise((resolve, reject) => {
      db.all(
        `SELECT key, value FROM settings`,
        [],
        (err, rows) => (err ? reject(err) : resolve(rows))
      );
    });
  }
};
