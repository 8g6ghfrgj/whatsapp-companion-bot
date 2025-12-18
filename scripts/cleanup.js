// scripts/cleanup.js
const fs = require('fs').promises;
const path = require('path');

class SystemCleaner {
    constructor() {
        this.config = {
            maxLogAgeDays: 7,
            maxExportsAgeDays: 30,
            maxBackupsAgeDays: 90,
            maxTempFilesAgeHours: 24,
            cleanupSchedule: {
                logs: true,
                exports: true,
                backups: true,
                temp: true,
                cache: true
            }
        };
    }
    
    async cleanupSystem() {
        console.log('🧹 بدء تنظيف النظام...\n');
        
        const results = {
            logs: 0,
            exports: 0,
            backups: 0,
            temp: 0,
            cache: 0,
            total: 0
        };
        
        try {
            // تنظيف السجلات
            if (this.config.cleanupSchedule.logs) {
                results.logs = await this.cleanupLogs();
            }
            
            // تنظيف التصديرات
            if (this.config.cleanupSchedule.exports) {
                results.exports = await this.cleanupExports();
            }
            
            // تنظيف النسخ الاحتياطية
            if (this.config.cleanupSchedule.backups) {
                results.backups = await this.cleanupBackups();
            }
            
            // تنظيف الملفات المؤقتة
            if (this.config.cleanupSchedule.temp) {
                results.temp = await this.cleanupTempFiles();
            }
            
            // تنظيف الذاكرة المؤقتة
            if (this.config.cleanupSchedule.cache) {
                results.cache = await this.cleanupCache();
            }
            
            // حساب الإجمالي
            results.total = Object.values(results).reduce((a, b) => a + b, 0);
            
            // عرض النتائج
            this.displayResults(results);
            
            // إنشاء تقرير التنظيف
            await this.createCleanupReport(results);
            
            return results;
            
        } catch (error) {
            console.error('❌ خطأ في تنظيف النظام:', error);
            return results;
        }
    }
    
    async cleanupLogs() {
        try {
            const logsDir = './logs';
            const files = await fs.readdir(logsDir);
            let deletedCount = 0;
            const now = Date.now();
            const maxAgeMs = this.config.maxLogAgeDays * 24 * 60 * 60 * 1000;
            
            for (const file of files) {
                if (file.endsWith('.log') || file.endsWith('.txt')) {
                    const filePath = path.join(logsDir, file);
                    const stat = await fs.stat(filePath);
                    const fileAge = now - stat.mtime.getTime();
                    
                    if (fileAge > maxAgeMs && file !== 'bot.log') {
                        await fs.unlink(filePath);
                        deletedCount++;
                        console.log(`🗑️ سجل: ${file}`);
                    }
                }
            }
            
            return deletedCount;
            
        } catch (error) {
            console.error('❌ خطأ في تنظيف السجلات:', error);
            return 0;
        }
    }
    
    async cleanupExports() {
        try {
            const exportsDir = './exports';
            const files = await fs.readdir(exportsDir);
            let deletedCount = 0;
            const now = Date.now();
            const maxAgeMs = this.config.maxExportsAgeDays * 24 * 60 * 60 * 1000;
            
            for (const file of files) {
                if (file.startsWith('links_export_') || file.startsWith('report_')) {
                    const filePath = path.join(exportsDir, file);
                    const stat = await fs.stat(filePath);
                    const fileAge = now - stat.mtime.getTime();
                    
                    if (fileAge > maxAgeMs) {
                        await fs.unlink(filePath);
                        deletedCount++;
                        console.log(`🗑️ تصدير: ${file}`);
                    }
                }
            }
            
            return deletedCount;
            
        } catch (error) {
            console.error('❌ خطأ في تنظيف التصديرات:', error);
            return 0;
        }
    }
    
    async cleanupBackups() {
        try {
            const backupsDir = './backups';
            const files = await fs.readdir(backupsDir);
            let deletedCount = 0;
            const now = Date.now();
            const maxAgeMs = this.config.maxBackupsAgeDays * 24 * 60 * 60 * 1000;
            
            for (const file of files) {
                if (file.startsWith('backup_')) {
                    const filePath = path.join(backupsDir, file);
                    const stat = await fs.stat(filePath);
                    const fileAge = now - stat.mtime.getTime();
                    
                    if (fileAge > maxAgeMs) {
                        await fs.rm(filePath, { recursive: true });
                        deletedCount++;
                        console.log(`🗑️ نسخة: ${file}`);
                    }
                }
            }
            
            return deletedCount;
            
        } catch (error) {
            console.error('❌ خطأ في تنظيف النسخ:', error);
            return 0;
        }
    }
    
    async cleanupTempFiles() {
        try {
            const tempFiles = [
                './*.tmp',
                './*.temp',
                './data/*.tmp',
                './data/*.temp',
                './exports/*.tmp'
            ];
            
            let deletedCount = 0;
            
            for (const pattern of tempFiles) {
                const files = await this.glob(pattern);
                
                for (const file of files) {
                    const fileAge = await this.getFileAge(file);
                    
                    if (fileAge > this.config.maxTempFilesAgeHours * 60 * 60 * 1000) {
                        await fs.unlink(file);
                        deletedCount++;
                        console.log(`🗑️ مؤقت: ${path.basename(file)}`);
                    }
                }
            }
            
            return deletedCount;
            
        } catch (error) {
            console.error('❌ خطأ في تنظيف الملفات المؤقتة:', error);
            return 0;
        }
    }
    
    async cleanupCache() {
        try {
            const cacheFiles = [
                './data/cache_*.json',
                './node_modules/.cache',
                './.cache'
            ];
            
            let deletedCount = 0;
            
            for (const pattern of cacheFiles) {
                const files = await this.glob(pattern);
                
                for (const file of files) {
                    try {
                        if ((await fs.stat(file)).isDirectory()) {
                            await fs.rm(file, { recursive: true });
                        } else {
                            await fs.unlink(file);
                        }
                        deletedCount++;
                        console.log(`🗑️ كاش: ${path.basename(file)}`);
                    } catch {
                        // تجاهل الملفات التي لا يمكن حذفها
                    }
                }
            }
            
            return deletedCount;
            
        } catch (error) {
            console.error('❌ خطأ في تنظيف الكاش:', error);
            return 0;
        }
    }
    
    async glob(pattern) {
        try {
            const dir = path.dirname(pattern);
            const filename = path.basename(pattern).replace('*', '.*');
            const regex = new RegExp(`^${filename}$`);
            
            const files = await fs.readdir(dir);
            return files
                .filter(file => regex.test(file))
                .map(file => path.join(dir, file));
        } catch {
            return [];
        }
    }
    
    async getFileAge(filePath) {
        try {
            const stat = await fs.stat(filePath);
            return Date.now() - stat.mtime.getTime();
        } catch {
            return Infinity;
        }
    }
    
    displayResults(results) {
        console.log('\n' + '='.repeat(50));
        console.log('📊 نتائج تنظيف النظام');
        console.log('='.repeat(50));
        
        console.log(`📝 السجلات: ${results.logs} ملف`);
        console.log(`📤 التصديرات: ${results.exports} ملف`);
        console.log(`💾 النسخ الاحتياطية: ${results.backups} ملف`);
        console.log(`⏳ الملفات المؤقتة: ${results.temp} ملف`);
        console.log(`💿 الذاكرة المؤقتة: ${results.cache} ملف/مجلد`);
        console.log('─'.repeat(50));
        console.log(`📈 الإجمالي: ${results.total} ملف`);
        console.log('='.repeat(50));
        
        if (results.total === 0) {
            console.log('✅ النظام نظيف! لا توجد ملفات للحذف.');
        } else {
            console.log('🧹 تم تنظيف النظام بنجاح!');
        }
    }
    
    async createCleanupReport(results) {
        try {
            const reportDir = './logs/cleanup';
            await fs.mkdir(reportDir, { recursive: true });
            
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const reportFile = path.join(reportDir, `cleanup_${timestamp}.json`);
            
            const report = {
                timestamp: new Date().toISOString(),
                results: results,
                config: this.config,
                system: {
                    node: process.version,
                    platform: process.platform,
                    freeMemory: Math.round(process.memoryUsage().heapUsed / 1024 / 1024) + ' MB',
                    totalMemory: Math.round(process.memoryUsage().heapTotal / 1024 / 1024) + ' MB'
                }
            };
            
            await fs.writeFile(reportFile, JSON.stringify(report, null, 2), 'utf8');
            
            console.log(`📄 تم حفظ تقرير التنظيف: ${reportFile}`);
            
        } catch (error) {
            console.error('❌ خطأ في إنشاء تقرير التنظيف:', error);
        }
    }
    
    async analyzeDiskUsage() {
        try {
            const directories = ['./data', './exports', './logs', './backups'];
            const usage = {};
            
            for (const dir of directories) {
                try {
                    usage[dir] = await this.getDirectorySize(dir);
                } catch {
                    usage[dir] = 'غير متوفر';
                }
            }
            
            console.log('\n💾 تحليل استخدام المساحة:');
            console.log('='.repeat(50));
            
            for (const [dir, size] of Object.entries(usage)) {
                console.log(`${dir}: ${size}`);
            }
            
            return usage;
            
        } catch (error) {
            console.error('❌ خطأ في تحليل المساحة:', error);
            return {};
        }
    }
    
    async getDirectorySize(dir) {
        try {
            const files = await fs.readdir(dir);
            let totalSize = 0;
            
            for (const file of files) {
                const filePath = path.join(dir, file);
                const stat = await fs.stat(filePath);
                
                if (stat.isDirectory()) {
                    totalSize += await this.getDirectorySize(filePath);
                } else {
                    totalSize += stat.size;
                }
            }
            
            const sizeMB = (totalSize / (1024 * 1024)).toFixed(2);
            return `${sizeMB} MB`;
            
        } catch {
            return '0 MB';
        }
    }
}

// استخدام المنظف مباشرة
if (require.main === module) {
    const cleaner = new SystemCleaner();
    
    async function main() {
        const command = process.argv[2];
        
        switch (command) {
            case 'clean':
                await cleaner.cleanupSystem();
                break;
                
            case 'analyze':
                await cleaner.analyzeDiskUsage();
                break;
                
            case 'config':
                console.log('⚙️ إعدادات التنظيف:');
                console.log(JSON.stringify(cleaner.config, null, 2));
                break;
                
            default:
                console.log('🧹 أوامر تنظيف النظام:');
                console.log('npm run clean        - تنظيف النظام كاملاً');
                console.log('npm run clean analyze - تحليل استخدام المساحة');
                console.log('npm run clean config  - عرض إعدادات التنظيف');
        }
    }
    
    main().catch(console.error);
}

module.exports = SystemCleaner;
