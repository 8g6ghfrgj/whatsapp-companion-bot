PRAGMA foreign_keys = ON;

-- =========================
-- WhatsApp Accounts
-- =========================
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  chrome_profile TEXT NOT NULL UNIQUE,
  is_active INTEGER DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- Groups
-- =========================
CREATE TABLE IF NOT EXISTS groups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  group_name TEXT,
  group_jid TEXT UNIQUE,
  join_status TEXT,
  joined_at DATETIME,
  FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- =========================
-- Collected Links
-- =========================
CREATE TABLE IF NOT EXISTS links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL,
  group_jid TEXT,
  url TEXT NOT NULL,
  type TEXT NOT NULL,
  hash TEXT NOT NULL UNIQUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- =========================
-- App Settings
-- =========================
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);

-- =========================
-- Group Join Requests
-- =========================
CREATE TABLE IF NOT EXISTS join_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  group_link TEXT NOT NULL,
  group_name TEXT,
  requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  status TEXT DEFAULT 'pending'
);

-- =========================
-- Ads (Auto Posting)
-- =========================
CREATE TABLE IF NOT EXISTS ads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,         -- text | image | video | contact
  content TEXT,
  file_path TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- Auto Replies Rules
-- =========================
CREATE TABLE IF NOT EXISTS auto_replies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scope TEXT NOT NULL,        -- private | group
  keyword TEXT,               -- NULL = any message
  reply_text TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
