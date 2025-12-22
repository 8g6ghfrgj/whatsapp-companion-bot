import { db } from '../db.js';

export const AutoRepliesRepo = {
  create(scope, keyword, replyText) {
    return new Promise((resolve, reject) => {
      db.run(
        `INSERT INTO auto_replies (scope, keyword, reply_text)
         VALUES (?, ?, ?)`,
        [scope, keyword, replyText],
        function (err) {
          if (err) return reject(err);
          resolve(this.lastID);
        }
      );
    });
  },

  getAll(scope) {
    return new Promise((resolve, reject) => {
      db.all(
        `SELECT * FROM auto_replies WHERE scope = ?`,
        [scope],
        (err, rows) => (err ? reject(err) : resolve(rows))
      );
    });
  }
};
