/**
 * WhatsApp Account – FINAL STABLE VERSION
 * حل نهائي لمشكلة إغلاق الاتصال قبل الربط
 */

const path = require('path');
const fs = require('fs-extra');
const Pino = require('pino');

const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason
} = require('@whiskeysockets/baileys');

const logger = require('../../utils/logger');
const { registerWhatsAppEvents } = require('../events');
const { processGroupQueue } = require('../joiner');

class WhatsAppAccount {
  constructor({ id }) {
    this.id = id;
    this.sock = null;
    this.connected = false;
    this.isLinking = true; // ⛔ يمنع reconnect أثناء الربط

    this.sessionPath = path.join(
      __dirname,
      `../../storage/accounts/sessions/${id}`
    );

    this.dataPath = path.join(
      __dirname,
      `../../storage/accounts/data/${id}`
    );

    this._ensureStorage();
  }

  _ensureStorage() {
    fs.ensureDirSync(this.sessionPath);
    fs.ensureDirSync(this.dataPath);
    fs.ensureDirSync(path.join(this.dataPath, 'links'));
    fs.ensureDirSync(path.join(this.dataPath, 'ads'));
    fs.ensureDirSync(path.join(this.dataPath, 'replies'));
    fs.ensureDirSync(path.join(this.dataPath, 'groups'));

    this._ensureFile('ads/current.json', {
      type: null,
      content: null,
      caption: ''
    });

    this._ensureFile('replies/config.json', {
      enabled: false,
      private_reply: 'مرحباً 👋\nتم استلام رسالتك.',
      group_reply: '📌 للتواصل يرجى مراسلتنا خاص'
    });

    this._ensureFile('groups/queue.json', { links: [] });
    this._ensureFile('groups/report.json', {
      joined: [],
      pending: [],
      failed: []
    });
  }

  _ensureFile(relativePath, content) {
    const file = path.join(this.dataPath, relativePath);
    if (!fs.existsSync(file)) {
      fs.writeFileSync(file, JSON.stringify(content, null, 2));
    }
  }

  // =========================
  // الاتصال (الحل النهائي هنا)
  // =========================
  async connect() {
    logger.info(`🔗 بدء ربط حساب واتساب: ${this.id}`);

    const { state, saveCreds } = await useMultiFileAuthState(
      this.sessionPath
    );

    this.sock = makeWASocket({
      auth: state,
      logger: Pino({ level: 'silent' }),

      // ✅ إعدادات حاسمة لمنع الإغلاق المبكر
      browser: ['WhatsApp Companion', 'Chrome', '120.0'],
      keepAliveIntervalMs: 30000,
      connectTimeoutMs: 60000,
      qrTimeout: 60000,

      // لا نطبع QR ولا نعيد الاتصال تلقائيًا
      emitOwnEvents: true,
      shouldIgnoreJid: () => false
    });

    this.sock.ev.on('creds.update', saveCreds);

    this.sock.ev.on('connection.update', (update) => {
      const { connection, lastDisconnect, qr } = update;

      // ===== QR تم إنشاؤه =====
      if (qr) {
        logger.info('📲 تم إنشاء QR – بانتظار المسح (حتى 60 ثانية)');
        // لا نغلق الاتصال ولا نعيد المحاولة
        return;
      }

      // ===== تم الربط بنجاح =====
      if (connection === 'open') {
        this.connected = true;
        this.isLinking = false;

        logger.info(`✅ تم ربط الحساب بنجاح: ${this.id}`);

        registerWhatsAppEvents(this.sock, this.id);
        processGroupQueue(this.sock, this.id);
        return;
      }

      // ===== تم إغلاق الاتصال =====
      if (connection === 'close') {
        this.connected = false;

        // ⛔ أثناء الربط: لا نعيد الاتصال
        if (this.isLinking) {
          logger.warn('⏳ انتهت مهلة الربط بدون مسح QR');
          return;
        }

        const reason =
          lastDisconnect?.error?.output?.statusCode;

        if (reason === DisconnectReason.loggedOut) {
          logger.warn(`🚪 تم تسجيل خروج الحساب: ${this.id}`);
          return;
        }

        logger.warn('🔁 انقطع الاتصال – إعادة المحاولة');
        this.reconnect();
      }
    });
  }

  async reconnect() {
    try {
      await this.connect();
    } catch (err) {
      logger.error(`❌ فشل إعادة الاتصال للحساب ${this.id}`, err);
    }
  }

  async logout() {
    try {
      if (this.sock) {
        await this.sock.logout();
        this.sock = null;
        this.connected = false;
        logger.info(`🚪 تم تسجيل خروج الحساب: ${this.id}`);
      }
    } catch (err) {
      logger.error(`❌ خطأ أثناء تسجيل خروج الحساب ${this.id}`, err);
    }
  }
}

module.exports = WhatsAppAccount;
