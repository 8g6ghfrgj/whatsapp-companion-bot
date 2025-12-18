// scripts/backupData.js
const fs = require('fs').promises;
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

class BackupManager {
    constructor() {
        this.backupDir = './backups';
        this.dataDir = './data';
        this.exportsDir = './exports';
    }
    
    async createBackup() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const backupName = `backup_${timestamp}`;
        const backupPath = path.join(this.backupDir, backupName);
        
        console.log(`📦 إنشاء نسخة احتياطية: ${backupName}`);
        
        try {
            // إنشاء مجلد النسخة
            await fs.mkdir(backupPath, { recursive: true });
            
            // نسخ مجلد data
            await this.copyDirectory(this.dataDir, path.join(backupPath, 'data'));
            
            // نسخ مجلد exports إذا كان به بيانات
            try {
                const exportsFiles = await fs.readdir(this.exportsDir);
                if (exportsFiles.length > 0) {
                    await this.copyDirectory(this.exportsDir, path.join(backupPath, 'exports'));
                }
            } catch (error) {
                console.log('⚠️ مجلد exports فارغ أو غير موجود');
            }
            
            // إنشاء ملف معلومات النسخة
            const backupInfo = {
                name: backupName,
                timestamp: new Date().toISOString(),
                files: await this.getDirectoryStats(this.dataDir),
                system: {
                    node: process.version,
                    platform: process.platform,
                    arch: process.arch
                },
                version: '1.0.0'
            };
            
            await fs.writeFile(
                path.join(backupPath, 'backup-info.json'),
                JSON.stringify(backupInfo, null, 2),
                'utf8'
            );
            
            console.log(`✅ تم إنشاء النسخة: ${backupPath}`);
            
            // تنظيف النسخ القديمة
            await this.cleanOldBackups();
            
            return {
                success: true,
                path: backupPath,
                name: backupName,
                size: await this.getFolderSize(backupPath)
            };
            
        } catch (error) {
            console.error('❌ فشل إنشاء النسخة:', error);
            return { success: false, error: error.message };
        }
    }
    
    async copyDirectory(source, target) {
        await fs.mkdir(target, { recursive: true });
        
        const files = await fs.readdir(source);
        
        for (const file of files) {
            const sourcePath = path.join(source, file);
            const targetPath = path.join(target, file);
            
            const stat = await fs.stat(sourcePath);
            
            if (stat.isDirectory()) {
                await this.copyDirectory(sourcePath, targetPath);
            } else {
                await fs.copyFile(sourcePath, targetPath);
            }
        }
    }
    
    async getDirectoryStats(dirPath) {
        try {
            const files = await fs.readdir(dirPath);
            let totalSize = 0;
            const fileList = [];
            
            for (const file of files) {
                const filePath = path.join(dirPath, file);
                const stat = await fs.stat(filePath);
                
                if (stat.isDirectory()) {
                    const subStats = await this.getDirectoryStats(filePath);
                    totalSize += subStats.totalSize;
                } else {
                    totalSize += stat.size;
                    fileList.push({
                        name: file,
                        size: stat.size,
                        modified: stat.mtime
                    });
                }
            }
            
            return {
                totalSize: totalSize,
                fileCount: fileList.length,
                files: fileList.slice(0, 10) // أول 10 ملفات فقط
            };
            
        } catch (error) {
            return { totalSize: 0, fileCount: 0, files: [] };
        }
    }
    
    async getFolderSize(folderPath) {
        try {
            const stats = await this.getDirectoryStats(folderPath);
            const sizeMB = (stats.totalSize / (1024 * 1024)).toFixed(2);
            return `${sizeMB} MB`;
        } catch {
            return '0 MB';
        }
    }
    
    async cleanOldBackups(maxBackups = 10) {
        try {
            const files = await fs.readdir(this.backupDir);
            const backupFolders = files
                .filter(f => f.startsWith('backup_'))
                .sort()
                .reverse();
            
            if (backupFolders.length > maxBackups) {
                const foldersToDelete = backupFolders.slice(maxBackups);
                
                for (const folder of foldersToDelete) {
                    const folderPath = path.join(this.backupDir, folder);
                    await fs.rm(folderPath, { recursive: true });
                    console.log(`🗑️ تم حذف النسخة القديمة: ${folder}`);
                }
                
                console.log(`🧹 تم تنظيف ${foldersToDelete.length} نسخة قديمة`);
            }
            
        } catch (error) {
            console.error('❌ خطأ في تنظيف النسخ:', error);
        }
    }
    
    async listBackups() {
        try {
            const files = await fs.readdir(this.backupDir);
            const backups = files.filter(f => f.startsWith('backup_'));
            
            const backupList = [];
            
            for (const backup of backups) {
                const backupPath = path.join(this.backupDir, backup);
                const infoPath = path.join(backupPath, 'backup-info.json');
                
                try {
                    const infoData = await fs.readFile(infoPath, 'utf8');
                    const info = JSON.parse(infoData);
                    
                    backupList.push({
                        name: backup,
                        path: backupPath,
                        date: info.timestamp,
                        size: await this.getFolderSize(backupPath),
                        files: info.files?.fileCount || 0
                    });
                } catch {
                    backupList.push({
                        name: backup,
                        path: backupPath,
                        date: 'غير معروف',
                        size: await this.getFolderSize(backupPath),
                        files: 'غير معروف'
                    });
                }
            }
            
            // ترتيب حسب التاريخ (الأحدث أولاً)
            return backupList.sort((a, b) => 
                new Date(b.date) - new Date(a.date)
            );
            
        } catch (error) {
            console.error('❌ خطأ في عرض النسخ:', error);
            return [];
        }
    }
    
    async restoreBackup(backupName) {
        try {
            const backupPath = path.join(this.backupDir, backupName);
            
            // التحقق من وجود النسخة
            await fs.access(backupPath);
            
            console.log(`🔄 استعادة النسخة: ${backupName}`);
            
            // إنشاء نسخة احتياطية من البيانات الحالية
            await this.createBackup();
            
            // استعادة مجلد data
            const backupDataPath = path.join(backupPath, 'data');
            await this.copyDirectory(backupDataPath, this.dataDir);
            
            // استعادة مجلد exports إذا موجود
            const backupExportsPath = path.join(backupPath, 'exports');
            try {
                await fs.access(backupExportsPath);
                await this.copyDirectory(backupExportsPath, this.exportsDir);
            } catch {
                console.log('⚠️ لا توجد بيانات exports في النسخة');
            }
            
            console.log(`✅ تم استعادة النسخة بنجاح: ${backupName}`);
            
            return {
                success: true,
                message: `تم استعادة النسخة ${backupName}`
            };
            
        } catch (error) {
            console.error('❌ فشل استعادة النسخة:', error);
            return { success: false, error: error.message };
        }
    }
}

// استخدام السكريبت مباشرة
if (require.main === module) {
    const backupManager = new BackupManager();
    
    async function main() {
        const command = process.argv[2];
        
        switch (command) {
            case 'create':
                await backupManager.createBackup();
                break;
                
            case 'list':
                const backups = await backupManager.listBackups();
                console.log('\n📋 قائمة النسخ الاحتياطية:');
                backups.forEach((backup, index) => {
                    console.log(`${index + 1}. ${backup.name}`);
                    console.log(`   📅 ${backup.date}`);
                    console.log(`   💾 ${backup.size} (${backup.files} ملف)`);
                });
                break;
                
            case 'restore':
                if (!process.argv[3]) {
                    console.log('❌ يجب تحديد اسم النسخة: npm run backup restore backup_2024-01-19T10-30-00');
                    return;
                }
                await backupManager.restoreBackup(process.argv[3]);
                break;
                
            default:
                console.log('🔧 أوامر النسخ الاحتياطي:');
                console.log('npm run backup create    - إنشاء نسخة جديدة');
                console.log('npm run backup list      - عرض النسخ المتاحة');
                console.log('npm run backup restore   - استعادة نسخة');
        }
    }
    
    main().catch(console.error);
}

module.exports = BackupManager;
