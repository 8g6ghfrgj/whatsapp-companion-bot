// ============================================
// Auto Publisher Module
// Handles automatic publishing of content to groups
// Version: 1.0.0
// ============================================

const fs = require('fs').promises;
const path = require('path');

class AutoPublisher {
    constructor() {
        this.isActive = false;
        this.currentCampaign = null;
        this.publishQueue = [];
        this.publishedGroups = new Set();
        this.failedGroups = new Map();
        this.stats = {
            totalPublished: 0,
            successful: 0,
            failed: 0,
            skipped: 0,
            lastPublished: null,
            startTime: null,
            endTime: null
        };
        
        this.config = {
            maxGroupsPerHour: 100,
            delayBetweenGroups: 30000, // 30 seconds
            maxRetries: 3,
            skipExisting: true,
            contentTypes: ['text', 'image', 'video', 'document', 'contact']
        };
        
        this.contentLibrary = [];
        this.campaignsFile = './data/adCampaigns.json';
        this.scheduleFile = './data/publishSchedule.json';
        
        // Initialize
        this.init();
        
        console.log('✅ Auto Publisher Initialized');
    }
    
    /**
     * Initialize publisher
     */
    async init() {
        try {
            await fs.mkdir(path.dirname(this.campaignsFile), { recursive: true });
            
            // Load existing campaigns
            await this.loadCampaigns();
            await this.loadSchedule();
            
            console.log(`📊 Loaded ${this.contentLibrary.length} campaigns`);
            
        } catch (error) {
            console.log('📝 Starting with empty campaign library');
        }
    }
    
    /**
     * Start auto publishing
     * @param {Object} content - Content to publish
     * @param {Object} sock - WhatsApp socket connection
     */
    async start(content, sock) {
        if (this.isActive) {
            console.warn('⚠️ Publishing is already active');
            return { success: false, message: 'Publishing already active' };
        }
        
        try {
            // Validate content
            const validatedContent = this.validateContent(content);
            if (!validatedContent) {
                return { success: false, message: 'Invalid content format' };
            }
            
            // Create campaign
            this.currentCampaign = this.createCampaign(validatedContent);
            
            // Get target groups
            const groups = await this.getTargetGroups(sock);
            if (groups.length === 0) {
                return { success: false, message: 'No groups available for publishing' };
            }
            
            // Prepare publish queue
            this.preparePublishQueue(groups);
            
            // Start publishing
            this.isActive = true;
            this.stats.startTime = new Date();
            this.stats.totalPublished = 0;
            this.stats.successful = 0;
            this.stats.failed = 0;
            
            console.log(`🚀 Starting auto-publish campaign: "${this.currentCampaign.title}"`);
            console.log(`📢 Target groups: ${groups.length}`);
            
            // Start publishing loop
            this.publishLoop(sock);
            
            // Save campaign
            await this.saveCampaign(this.currentCampaign);
            
            return {
                success: true,
                message: `Auto-publishing started for ${groups.length} groups`,
                campaignId: this.currentCampaign.id,
                groups: groups.length
            };
            
        } catch (error) {
            console.error('❌ Failed to start publishing:', error);
            return { success: false, message: error.message };
        }
    }
    
    /**
     * Stop auto publishing
     */
    async stop() {
        if (!this.isActive) {
            console.warn('⚠️ Publishing is not active');
            return { success: false, message: 'Publishing not active' };
        }
        
        this.isActive = false;
        this.stats.endTime = new Date();
        
        const duration = this.stats.endTime - this.stats.startTime;
        const durationMinutes = Math.floor(duration / 60000);
        
        console.log(`⏹️ Auto-publishing stopped`);
        console.log(`📊 Results: ${this.stats.successful} successful, ${this.stats.failed} failed`);
        console.log(`⏱️ Duration: ${durationMinutes} minutes`);
        
        // Generate report
        const report = await this.generateReport();
        
        return {
            success: true,
            message: 'Auto-publishing stopped',
            stats: this.stats,
            report: report
        };
    }
    
    /**
     * Publish loop
     */
    async publishLoop(sock) {
        while (this.isActive && this.publishQueue.length > 0) {
            const group = this.publishQueue.shift();
            
            try {
                // Check rate limiting
                if (this.isRateLimited()) {
                    console.log('⏳ Rate limit reached, pausing for 1 hour...');
                    await this.delay(3600000); // 1 hour
                    continue;
                }
                
                // Publish to group
                const result = await this.publishToGroup(group, sock);
                
                if (result.success) {
                    this.stats.successful++;
                    this.publishedGroups.add(group.id);
                    console.log(`✅ Published to ${group.name || group.id}`);
                } else {
                    this.stats.failed++;
                    this.failedGroups.set(group.id, {
                        group: group,
                        error: result.error,
                        attempts: 1
                    });
                    console.log(`❌ Failed to publish to ${group.name || group.id}: ${result.error}`);
                }
                
                this.stats.totalPublished++;
                this.stats.lastPublished = new Date();
                
                // Save progress every 10 groups
                if (this.stats.totalPublished % 10 === 0) {
                    await this.saveProgress();
                }
                
                // Delay between groups
                if (this.publishQueue.length > 0) {
                    await this.delay(this.config.delayBetweenGroups);
                }
                
            } catch (error) {
                console.error(`❌ Error in publish loop for group ${group.id}:`, error);
                this.stats.failed++;
                await this.delay(5000); // Short delay on error
            }
        }
        
        // All groups processed
        if (this.publishQueue.length === 0 && this.isActive) {
            console.log('🎉 Auto-publishing completed for all groups');
            await this.stop();
        }
    }
    
    /**
     * Publish content to a single group
     */
    async publishToGroup(group, sock) {
        try {
            // Check if already published to this group
            if (this.config.skipExisting && this.publishedGroups.has(group.id)) {
                console.log(`⏭️ Skipping ${group.name || group.id} (already published)`);
                this.stats.skipped++;
                return { success: true, skipped: true };
            }
            
            console.log(`📤 Publishing to ${group.name || group.id}...`);
            
            // Prepare message based on content type
            const message = this.prepareMessage(this.currentCampaign.content);
            
            // Send message
            await sock.sendMessage(group.id, message);
            
            // Log success
            console.log(`✅ Successfully published to ${group.name || group.id}`);
            
            return { success: true };
            
        } catch (error) {
            console.error(`❌ Failed to publish to ${group.name || group.id}:`, error.message);
            
            // Check if it's a recoverable error
            if (this.isRecoverableError(error)) {
                // Add back to queue for retry
                const attempts = this.failedGroups.get(group.id)?.attempts || 0;
                if (attempts < this.config.maxRetries) {
                    this.publishQueue.push(group);
                    this.failedGroups.set(group.id, {
                        group: group,
                        error: error.message,
                        attempts: attempts + 1
                    });
                    console.log(`🔄 Retrying ${group.name || group.id} (attempt ${attempts + 1})`);
                }
            }
            
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Prepare message based on content type
     */
    prepareMessage(content) {
        switch (content.type) {
            case 'text':
                return { text: content.text };
                
            case 'image':
                return {
                    image: { url: content.url },
                    caption: content.caption || '',
                    mimetype: content.mimetype || 'image/jpeg'
                };
                
            case 'video':
                return {
                    video: { url: content.url },
                    caption: content.caption || '',
                    mimetype: content.mimetype || 'video/mp4'
                };
                
            case 'document':
                return {
                    document: { url: content.url },
                    caption: content.caption || '',
                    mimetype: content.mimetype || 'application/pdf',
                    fileName: content.fileName || 'document.pdf'
                };
                
            case 'contact':
                return {
                    contacts: {
                        displayName: content.name,
                        contacts: [{
                            displayName: content.name,
                            vcard: `BEGIN:VCARD\nVERSION:3.0\nFN:${content.name}\nTEL:${content.phone}\nEND:VCARD`
                        }]
                    }
                };
                
            default:
                return { text: content.text || 'Advertisement' };
        }
    }
    
    /**
     * Get target groups for publishing
     */
    async getTargetGroups(sock) {
        try {
            const groups = await sock.groupFetchAllParticipating();
            const groupList = Object.values(groups);
            
            // Filter groups (optional: exclude certain groups)
            const targetGroups = groupList.filter(group => {
                // Add filtering logic here if needed
                return true; // Include all groups by default
            });
            
            console.log(`👥 Found ${targetGroups.length} groups for publishing`);
            
            return targetGroups.map(group => ({
                id: group.id,
                name: group.subject,
                participants: group.participants.length,
                createdAt: group.creation,
                isAnnouncement: group.announce
            }));
            
        } catch (error) {
            console.error('❌ Error fetching groups:', error);
            return [];
        }
    }
    
    /**
     * Prepare publish queue
     */
    preparePublishQueue(groups) {
        // Shuffle groups to avoid pattern detection
        const shuffled = [...groups].sort(() => Math.random() - 0.5);
        
        // Apply limits if needed
        const limitedGroups = shuffled.slice(0, this.config.maxGroupsPerHour);
        
        this.publishQueue = limitedGroups;
        console.log(`📋 Prepared queue with ${this.publishQueue.length} groups`);
    }
    
    /**
     * Create campaign
     */
    createCampaign(content) {
        return {
            id: `campaign_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            title: content.title || `Campaign ${new Date().toLocaleDateString()}`,
            content: content,
            createdAt: new Date().toISOString(),
            status: 'active',
            schedule: null,
            stats: {
                targetGroups: 0,
                publishedGroups: 0,
                successRate: 0
            }
        };
    }
    
    /**
     * Validate content
     */
    validateContent(content) {
        if (!content || typeof content !== 'object') {
            return null;
        }
        
        // Validate based on type
        switch (content.type) {
            case 'text':
                if (!content.text || typeof content.text !== 'string') {
                    return null;
                }
                break;
                
            case 'image':
            case 'video':
            case 'document':
                if (!content.url || typeof content.url !== 'string') {
                    return null;
                }
                break;
                
            case 'contact':
                if (!content.name || !content.phone) {
                    return null;
                }
                break;
                
            default:
                // Default to text if type not specified
                if (content.text) {
                    content.type = 'text';
                } else {
                    return null;
                }
        }
        
        // Add default values
        return {
            type: content.type || 'text',
            text: content.text || '',
            url: content.url || '',
            caption: content.caption || '',
            title: content.title || `Ad ${new Date().toLocaleDateString()}`,
            mimetype: content.mimetype || this.getDefaultMimeType(content.type),
            fileName: content.fileName || '',
            name: content.name || '',
            phone: content.phone || ''
        };
    }
    
    /**
     * Get default MIME type
     */
    getDefaultMimeType(type) {
        const mimeTypes = {
            image: 'image/jpeg',
            video: 'video/mp4',
            document: 'application/pdf'
        };
        
        return mimeTypes[type] || '';
    }
    
    /**
     * Check rate limiting
     */
    isRateLimited() {
        // Implement rate limiting logic
        // For now, simple hourly limit
        if (this.stats.totalPublished >= this.config.maxGroupsPerHour) {
            return true;
        }
        
        return false;
    }
    
    /**
     * Check if error is recoverable
     */
    isRecoverableError(error) {
        const recoverableErrors = [
            'timeout',
            'network',
            'temporarily',
            'rate limit',
            'too many requests',
            'connection'
        ];
        
        const errorMsg = error.message.toLowerCase();
        return recoverableErrors.some(keyword => errorMsg.includes(keyword));
    }
    
    /**
     * Delay function
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Save campaign to library
     */
    async saveCampaign(campaign) {
        try {
            // Add to library
            this.contentLibrary.push(campaign);
            
            // Save to file
            const data = {
                campaigns: this.contentLibrary,
                lastUpdated: new Date().toISOString()
            };
            
            await fs.writeFile(this.campaignsFile, JSON.stringify(data, null, 2), 'utf8');
            
            console.log(`💾 Campaign saved: ${campaign.id}`);
            return true;
            
        } catch (error) {
            console.error('❌ Failed to save campaign:', error);
            return false;
        }
    }
    
    /**
     * Load campaigns from file
     */
    async loadCampaigns() {
        try {
            const data = await fs.readFile(this.campaignsFile, 'utf8');
            const parsed = JSON.parse(data);
            
            this.contentLibrary = parsed.campaigns || [];
            console.log(`📂 Loaded ${this.contentLibrary.length} campaigns`);
            
        } catch (error) {
            // File doesn't exist or is invalid
            this.contentLibrary = [];
        }
    }
    
    /**
     * Load schedule from file
     */
    async loadSchedule() {
        try {
            const data = await fs.readFile(this.scheduleFile, 'utf8');
            const parsed = JSON.parse(data);
            
            // Load scheduled campaigns
            // Implementation depends on schedule structure
            
        } catch (error) {
            // No schedule file
        }
    }
    
    /**
     * Save progress
     */
    async saveProgress() {
        try {
            const progress = {
                campaign: this.currentCampaign,
                stats: this.stats,
                publishedGroups: Array.from(this.publishedGroups),
                failedGroups: Array.from(this.failedGroups.entries()).map(([id, data]) => ({
                    groupId: id,
                    attempts: data.attempts,
                    error: data.error
                })),
                savedAt: new Date().toISOString()
            };
            
            const progressFile = `./data/publish_progress_${this.currentCampaign.id}.json`;
            await fs.writeFile(progressFile, JSON.stringify(progress, null, 2), 'utf8');
            
            console.log(`💾 Progress saved for campaign ${this.currentCampaign.id}`);
            
        } catch (error) {
            console.error('❌ Failed to save progress:', error);
        }
    }
    
    /**
     * Generate report
     */
    async generateReport() {
        const duration = this.stats.endTime - this.stats.startTime;
        const durationText = this.formatDuration(duration);
        
        const successRate = this.stats.totalPublished > 0 ? 
            (this.stats.successful / this.stats.totalPublished * 100).toFixed(1) : 0;
        
        const report = {
            campaignId: this.currentCampaign?.id,
            title: this.currentCampaign?.title,
            contentType: this.currentCampaign?.content.type,
            startTime: this.stats.startTime,
            endTime: this.stats.endTime,
            duration: durationText,
            stats: this.stats,
            successRate: `${successRate}%`,
            publishedGroups: this.publishedGroups.size,
            failedGroups: this.failedGroups.size,
            failedDetails: Array.from(this.failedGroups.entries()).map(([id, data]) => ({
                groupId: id,
                groupName: data.group?.name,
                error: data.error,
                attempts: data.attempts
            }))
        };
        
        // Save report to file
        const reportFile = `./data/publish_report_${this.currentCampaign?.id || Date.now()}.json`;
        await fs.writeFile(reportFile, JSON.stringify(report, null, 2), 'utf8');
        
        console.log(`📄 Report saved: ${reportFile}`);
        
        return report;
    }
    
    /**
     * Format duration
     */
    formatDuration(ms) {
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    }
    
    /**
     * Get all campaigns
     */
    getCampaigns() {
        return this.contentLibrary;
    }
    
    /**
     * Get campaign by ID
     */
    getCampaign(id) {
        return this.contentLibrary.find(campaign => campaign.id === id);
    }
    
    /**
     * Delete campaign
     */
    async deleteCampaign(id) {
        const index = this.contentLibrary.findIndex(campaign => campaign.id === id);
        
        if (index !== -1) {
            this.contentLibrary.splice(index, 1);
            
            // Save updated library
            const data = {
                campaigns: this.contentLibrary,
                lastUpdated: new Date().toISOString()
            };
            
            await fs.writeFile(this.campaignsFile, JSON.stringify(data, null, 2), 'utf8');
            
            console.log(`🗑️ Campaign deleted: ${id}`);
            return true;
        }
        
        return false;
    }
    
    /**
     * Schedule campaign
     */
    async scheduleCampaign(campaignId, scheduleTime) {
        try {
            const campaign = this.getCampaign(campaignId);
            if (!campaign) {
                return { success: false, message: 'Campaign not found' };
            }
            
            campaign.schedule = scheduleTime;
            
            // Save schedule
            const scheduleData = {
                scheduledCampaigns: this.contentLibrary.filter(c => c.schedule),
                lastUpdated: new Date().toISOString()
            };
            
            await fs.writeFile(this.scheduleFile, JSON.stringify(scheduleData, null, 2), 'utf8');
            
            console.log(`📅 Campaign ${campaignId} scheduled for ${scheduleTime}`);
            return { success: true };
            
        } catch (error) {
            console.error('❌ Failed to schedule campaign:', error);
            return { success: false, message: error.message };
        }
    }
    
    /**
     * Get current status
     */
    getStatus() {
        return {
            isActive: this.isActive,
            currentCampaign: this.currentCampaign ? {
                id: this.currentCampaign.id,
                title: this.currentCampaign.title,
                type: this.currentCampaign.content.type
            } : null,
            stats: this.stats,
            queueSize: this.publishQueue.length,
            publishedCount: this.publishedGroups.size,
            failedCount: this.failedGroups.size,
            rateLimit: this.config.maxGroupsPerHour - this.stats.totalPublished
        };
    }
    
    /**
     * Pause publishing
     */
    pause() {
        if (!this.isActive) {
            return { success: false, message: 'Publishing not active' };
        }
        
        this.isActive = false;
        console.log('⏸️ Publishing paused');
        
        return { success: true, message: 'Publishing paused' };
    }
    
    /**
     * Resume publishing
     */
    resume() {
        if (this.isActive) {
            return { success: false, message: 'Publishing already active' };
        }
        
        if (!this.currentCampaign) {
            return { success: false, message: 'No active campaign' };
        }
        
        this.isActive = true;
        console.log('▶️ Publishing resumed');
        
        // Note: Need to pass sock to continue
        return { success: true, message: 'Publishing resumed' };
    }
    
    /**
     * Create text ad
     */
    createTextAd(text, title = null) {
        return {
            type: 'text',
            text: text,
            title: title || `Text Ad ${new Date().toLocaleDateString()}`
        };
    }
    
    /**
     * Create image ad
     */
    createImageAd(imageUrl, caption = '', title = null) {
        return {
            type: 'image',
            url: imageUrl,
            caption: caption,
            title: title || `Image Ad ${new Date().toLocaleDateString()}`
        };
    }
    
    /**
     * Create video ad
     */
    createVideoAd(videoUrl, caption = '', title = null) {
        return {
            type: 'video',
            url: videoUrl,
            caption: caption,
            title: title || `Video Ad ${new Date().toLocaleDateString()}`
        };
    }
    
    /**
     * Create contact ad
     */
    createContactAd(name, phone, title = null) {
        return {
            type: 'contact',
            name: name,
            phone: phone,
            title: title || `Contact ${name}`
        };
    }
    
    /**
     * Get publisher configuration
     */
    getConfig() {
        return { ...this.config };
    }
    
    /**
     * Update configuration
     */
    updateConfig(newConfig) {
        this.config = { ...this.config, ...newConfig };
        console.log('⚙️ Publisher configuration updated');
        return { success: true };
    }
}

// Export the class
module.exports = AutoPublisher;

// Test the module if run directly
if (require.main === module) {
    console.log('🧪 Testing Auto Publisher...\n');
    
    const autoPublisher = new AutoPublisher();
    
    // Test 1: Create text ad
    console.log('1. Creating text ad...');
    const textAd = autoPublisher.createTextAd('Hello from Auto Publisher!', 'Test Campaign');
    console.log('Text ad created:', textAd.title);
    
    // Test 2: Validate content
    console.log('\n2. Validating content...');
    const validated = autoPublisher.validateContent(textAd);
    console.log('Validation result:', validated ? '✅ Valid' : '❌ Invalid');
    
    // Test 3: Create campaign
    console.log('\n3. Creating campaign...');
    const campaign = autoPublisher.createCampaign(validated);
    console.log('Campaign created:', campaign.id);
    
    // Test 4: Get status
    console.log('\n4. Getting status...');
    const status = autoPublisher.getStatus();
    console.log('Status:', status);
    
    // Test 5: Get campaigns
    console.log('\n5. Getting campaigns...');
    const campaigns = autoPublisher.getCampaigns();
    console.log('Campaigns count:', campaigns.length);
    
    console.log('\n🧪 Test completed successfully');
                  }
