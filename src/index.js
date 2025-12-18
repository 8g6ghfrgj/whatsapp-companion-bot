// ============================================
// WhatsApp Companion Bot - Main Entry Point
// Core: Connects to WhatsApp via WebSocket
// Version: 1.0.0
// ============================================

require('dotenv').config();
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, makeCacheableSignalKeyStore } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const qrcode = require('qrcode-terminal');
const fs = require('fs').promises;
const path = require('path');

// Import custom modules
const QRManager = require('./qrManager');
const AuthStateManager = require('./authStateManager');
const MessageHandler = require('./messageHandler');
const LinkCollector = require('./linkCollector');
const AutoPublisher = require('./autoPublisher');
const GroupJoiner = require('./groupJoiner');
const AutoReplier = require('./autoReplier');

class WhatsAppCompanionBot {
    constructor() {
        this.sock = null;
        this.isConnected = false;
        this.connectionRetries = 0;
        this.maxRetries = 5;
        
        // Initialize modules
        this.initModules();
        
        // Bot configuration
        this.config = {
            maxLinkedAccounts: 4,
            collectionActive: false,
            publishingActive: false,
            joinInterval: 120000, // 2 minutes
            sessionFile: './data/auth_info_multi.json'
        };
        
        console.log('✅ WhatsApp Companion Bot Initialized');
    }
    
    initModules() {
        this.qrManager = new QRManager();
        this.authManager = new AuthStateManager(this.config.sessionFile);
        this.linkCollector = new LinkCollector();
        this.autoPublisher = new AutoPublisher();
        this.groupJoiner = new GroupJoiner(this.config.joinInterval);
        this.autoReplier = new AutoReplier();
        this.messageHandler = new MessageHandler(
            this.linkCollector,
            this.autoReplier
        );
    }
    
    async start() {
        console.log('🚀 Starting WhatsApp Companion Bot...');
        
        try {
            // Load or create auth state
            const { state, saveCreds } = await this.authManager.loadAuthState();
            
            // Fetch latest version of Baileys
            const { version, isLatest } = await fetchLatestBaileysVersion();
            console.log(`📦 Using WA version ${version.join('.')}, latest: ${isLatest}`);
            
            // Create WhatsApp socket connection
            this.sock = makeWASocket({
                version,
                printQRInTerminal: false, // We'll handle QR ourselves
                auth: {
                    creds: state.creds,
                    keys: makeCacheableSignalKeyStore(state.keys, this.logger),
                },
                logger: this.logger,
                browser: ['WhatsApp Companion Bot', 'Chrome', '3.0'],
                markOnlineOnConnect: true,
                generateHighQualityLinkPreview: true,
                syncFullHistory: true, // See old and new messages
                retryRequestDelayMs: 1000,
                maxMsgRetryCount: 3,
            });
            
            // Handle credentials update
            this.sock.ev.on('creds.update', saveCreds);
            
            // Handle connection events
            this.setupConnectionHandlers();
            
            // Handle incoming messages
            this.setupMessageHandlers();
            
            // Setup command handlers
            this.setupCommandHandlers();
            
            console.log('🤖 Bot is ready for connection...');
            
        } catch (error) {
            console.error('❌ Failed to start bot:', error);
            await this.handleConnectionFailure(error);
        }
    }
    
    logger = {
        level: 'silent',
        info: (...args) => console.log('[INFO]', ...args),
        debug: (...args) => console.log('[DEBUG]', ...args),
        warn: (...args) => console.warn('[WARN]', ...args),
        error: (...args) => console.error('[ERROR]', ...args),
        trace: (...args) => console.log('[TRACE]', ...args)
    };
    
    setupConnectionHandlers() {
        this.sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            
            // QR Code handling
            if (qr) {
                console.log('🔗 QR Code Received');
                this.qrManager.displayQR(qr);
                this.isConnected = false;
            }
            
            // Connection status handling
            if (connection) {
                if (connection === 'open') {
                    this.isConnected = true;
                    this.connectionRetries = 0;
                    console.log('✅ Successfully connected to WhatsApp!');
                    await this.onConnected();
                } else if (connection === 'close') {
                    this.isConnected = false;
                    await this.handleConnectionClose(lastDisconnect);
                }
                
                console.log(`📡 Connection status: ${connection}`);
            }
        });
    }
    
    setupMessageHandlers() {
        this.sock.ev.on('messages.upsert', async ({ messages, type }) => {
            try {
                if (type === 'notify') {
                    for (const message of messages) {
                        // Handle only messages that aren't from the bot itself
                        if (!message.key.fromMe) {
                            await this.messageHandler.processMessage(message, this.sock);
                            
                            // Collect links if collection is active
                            if (this.config.collectionActive) {
                                await this.linkCollector.processMessage(message);
                            }
                        }
                    }
                }
            } catch (error) {
                console.error('❌ Error processing message:', error);
            }
        });
        
        // Handle group joins
        this.sock.ev.on('group-participants.update', async (update) => {
            await this.messageHandler.handleGroupUpdate(update, this.sock);
        });
    }
    
    setupCommandHandlers() {
        // Handle commands via messages
        this.messageHandler.setCommandHandlers({
            // Link account (manual QR display)
            '!ربط': async (jid, sock) => {
                console.log('🔄 Manual QR generation requested');
                // Force new QR generation by clearing auth state
                await this.authManager.clearAuthState();
                await sock.logout();
                console.log('🔄 Please restart the bot to get new QR code');
            },
            
            // Show linked accounts
            '!الحسابات': async (jid, sock) => {
                const accounts = await this.getLinkedAccounts();
                const msg = `📱 الحسابات المرتبطة:\n${accounts.join('\n')}`;
                await sock.sendMessage(jid, { text: msg });
            },
            
            // Start link collection
            '!جمع': async (jid, sock) => {
                this.config.collectionActive = true;
                await sock.sendMessage(jid, { 
                    text: '✅ تم تفعيل تجميع الروابط' 
                });
                console.log('🔗 Link collection activated');
            },
            
            // Stop link collection
            '!ايقاف-جمع': async (jid, sock) => {
                this.config.collectionActive = false;
                await sock.sendMessage(jid, { 
                    text: '⏹️ تم إيقاف تجميع الروابط' 
                });
                console.log('⏹️ Link collection deactivated');
            }
        });
    }
    
    async onConnected() {
        console.log('🎉 Bot is fully operational!');
        
        // Send welcome message to console
        console.log(`
        ========================================
        WhatsApp Companion Bot - Connected!
        Available Commands:
        1. ربط حساب واتساب
        2. عرض الحسابات المرتبطة
        3. تجميع الروابط
        4. توقيف الجمع
        5. عرض الروابط المجمعة
        6. تصدير الروابط المجمعة
        7. نشر تلقائي
        8. ايقاف النشر التلقائي
        9. الردود
        10. الانظمام الى المجموعات
        ========================================
        `);
        
        // Load previous state
        await this.loadBotState();
    }
    
    async handleConnectionClose(lastDisconnect) {
        const shouldReconnect = 
            (lastDisconnect?.error instanceof Boom)?.output?.statusCode !== 
            DisconnectReason.loggedOut;
        
        console.log(`🔌 Connection closed. Reconnect: ${shouldReconnect}`);
        
        if (shouldReconnect && this.connectionRetries < this.maxRetries) {
            this.connectionRetries++;
            console.log(`🔄 Reconnecting... Attempt ${this.connectionRetries}`);
            setTimeout(() => this.start(), 5000);
        } else {
            console.log('❌ Max reconnection attempts reached or logged out');
            process.exit(1);
        }
    }
    
    async handleConnectionFailure(error) {
        console.error('💥 Connection failure:', error.message);
        
        if (this.connectionRetries < this.maxRetries) {
            this.connectionRetries++;
            console.log(`🔄 Retrying connection... Attempt ${this.connectionRetries}`);
            setTimeout(() => this.start(), 10000);
        } else {
            console.log('❌ Maximum retry attempts reached');
            process.exit(1);
        }
    }
    
    async getLinkedAccounts() {
        try {
            // This would typically check the actual linked devices
            // For now, returning basic info
            return [
                `1. جهاز البوت (متصل: ${this.isConnected ? 'نعم' : 'لا'})`,
                '2. هاتف أساسي (مفترض)'
            ];
        } catch (error) {
            console.error('Error getting linked accounts:', error);
            return ['⚠️ تعذر جلب المعلومات'];
        }
    }
    
    async loadBotState() {
        try {
            // Load link collection state
            await this.linkCollector.loadFromFile();
            console.log('📂 Bot state loaded successfully');
        } catch (error) {
            console.log('📂 No previous bot state found, starting fresh');
        }
    }
    
    // Public methods for external control (Telegram, etc.)
    async startLinkCollection() {
        this.config.collectionActive = true;
        console.log('🔗 Link collection started via external command');
        return { success: true, message: 'Link collection started' };
    }
    
    async stopLinkCollection() {
        this.config.collectionActive = false;
        console.log('⏹️ Link collection stopped via external command');
        return { success: true, message: 'Link collection stopped' };
    }
    
    async exportLinks(format = 'txt') {
        return await this.linkCollector.exportLinks(format);
    }
    
    async startAutoPublish(content) {
        return await this.autoPublisher.start(content, this.sock);
    }
    
    async stopAutoPublish() {
        return await this.autoPublisher.stop();
    }
    
    async joinGroups(links) {
        return await this.groupJoiner.start(links, this.sock);
    }
    
    async getStats() {
        return {
            connected: this.isConnected,
            linkCollectionActive: this.config.collectionActive,
            publishingActive: this.autoPublisher.isActive,
            joiningActive: this.groupJoiner.isActive,
            linksCollected: this.linkCollector.getStats(),
            connectionRetries: this.connectionRetries
        };
    }
}

// Handle process termination
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down bot gracefully...');
    
    // Save current state
    try {
        const bot = global.botInstance;
        if (bot) {
            await bot.linkCollector.saveToFile();
        }
    } catch (error) {
        console.error('Error saving state on shutdown:', error);
    }
    
    console.log('👋 Bot shutdown complete');
    process.exit(0);
});

// Start the bot if this file is run directly
if (require.main === module) {
    const bot = new WhatsAppCompanionBot();
    global.botInstance = bot; // Make accessible globally
    
    bot.start().catch(console.error);
    
    // Export for external use (Telegram bot integration)
    module.exports = bot;
} else {
    module.exports = WhatsAppCompanionBot;
}
