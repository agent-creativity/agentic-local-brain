# Settings UI Redesign - Tab Layout Implementation Guide

## Overview
Redesign the settings page to use a tabbed interface with three sections:
1. **Model Configuration** - LLM and Embedding settings
2. **Backup Configuration** - Backup settings
3. **System Diagnostics** - System health checks

## Changes Required

### 1. Add Vue Data Properties

In the `data()` section (around line 6322), add:

```javascript
// Settings tab state
settingsTab: 'models',  // 'models', 'backup', 'diagnostics'

// Backup settings
backupSettings: {
    enabled: false,
    schedule: '0 2 * * *',
    retention_days: 30,
    backup_dir: '~/.knowledge-base/backups',
    include_db: true,
    include_files: true,
    compression: true,
    cloud_provider: 'oss',  // 'oss' or 's3'
    oss: {
        endpoint: 'oss-cn-hangzhou.aliyuncs.com',
        access_key_id: '',
        access_key_secret: '',
        bucket: 'localbrain-backups',
    },
    s3: {
        region: 'us-west-2',
        access_key_id: '',
        secret_access_key: '',
        bucket: 'localbrain-backups',
    },
},
backupSettingsSaving: false,
backupSettingsSaved: false,
backupSettingsError: '',
```

### 2. Add Methods

Add these methods to the Vue instance:

```javascript
async fetchBackupSettings() {
    try {
        const res = await fetch('/api/settings/backup');
        if (!res.ok) throw new Error('Failed to fetch backup settings');
        const data = await res.json();
        this.backupSettings = {
            enabled: data.backup?.enabled || false,
            schedule: data.backup?.schedule || '0 2 * * *',
            retention_days: data.backup?.retention_days || 30,
            backup_dir: data.backup?.backup_dir || '~/.knowledge-base/backups',
            include_db: data.backup?.include_db !== false,
            include_files: data.backup?.include_files !== false,
            compression: data.backup?.compression !== false,
            cloud_provider: data.backup?.cloud_provider || 'oss',
            oss: {
                endpoint: data.backup?.oss?.endpoint || 'oss-cn-hangzhou.aliyuncs.com',
                access_key_id: data.backup?.oss?.access_key_id || '',
                access_key_secret: data.backup?.oss?.access_key_secret || '',
                bucket: data.backup?.oss?.bucket || 'localbrain-backups',
            },
            s3: {
                region: data.backup?.s3?.region || 'us-west-2',
                access_key_id: data.backup?.s3?.access_key_id || '',
                secret_access_key: data.backup?.s3?.secret_access_key || '',
                bucket: data.backup?.s3?.bucket || 'localbrain-backups',
            },
        };
    } catch (e) {
        console.error('Failed to load backup settings:', e);
    }
},

async saveBackupSettings() {
    this.backupSettingsSaving = true;
    this.backupSettingsSaved = false;
    this.backupSettingsError = '';
    try {
        const body = {
            enabled: this.backupSettings.enabled,
            schedule: this.backupSettings.schedule.trim(),
            retention_days: this.backupSettings.retention_days,
            backup_dir: this.backupSettings.backup_dir.trim(),
            include_db: this.backupSettings.include_db,
            include_files: this.backupSettings.include_files,
            compression: this.backupSettings.compression,
            cloud_provider: this.backupSettings.cloud_provider,
            oss: {
                endpoint: this.backupSettings.oss.endpoint.trim(),
                access_key_id: this.backupSettings.oss.access_key_id.trim(),
                access_key_secret: this.backupSettings.oss.access_key_secret.trim(),
                bucket: this.backupSettings.oss.bucket.trim(),
            },
            s3: {
                region: this.backupSettings.s3.region.trim(),
                access_key_id: this.backupSettings.s3.access_key_id.trim(),
                secret_access_key: this.backupSettings.s3.secret_access_key.trim(),
                bucket: this.backupSettings.s3.bucket.trim(),
            },
        };
        const res = await fetch('/api/settings/backup', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (!res.ok) {
            this.backupSettingsError = data.detail || 'Failed to save settings';
        } else {
            this.backupSettingsSaved = true;
            setTimeout(() => { this.backupSettingsSaved = false; }, 3000);
        }
    } catch (e) {
        this.backupSettingsError = e.message || 'Failed to save settings';
    } finally {
        this.backupSettingsSaving = false;
    }
},
```

### 3. Update fetchSettings Method

Modify the existing `fetchSettings()` method to also load backup settings:

```javascript
async fetchSettings() {
    // ... existing code ...
    await this.fetchBackupSettings();
}
```

### 4. Replace Settings Page HTML

Replace the entire Settings Page section (lines 4708-5098) with:

```html
<!-- Settings Page -->
<div v-if="currentPage === 'settings'">
    <div class="page-header">
        <div>
            <h1 class="page-title">{{ t('nav.settings') }}</h1>
            <p class="page-subtitle">{{ locale === 'en' ? 'Configure your knowledge base settings' : '配置你的知识库设置' }}</p>
        </div>
    </div>

    <!-- Tab Navigation -->
    <div style="margin-top: 20px; border-bottom: 2px solid var(--border);">
        <div style="display: flex; gap: 8px;">
            <button @click="settingsTab = 'models'"
                    :style="{
                        padding: '10px 20px',
                        border: 'none',
                        background: settingsTab === 'models' ? 'var(--primary)' : 'transparent',
                        color: settingsTab === 'models' ? 'white' : 'var(--text)',
                        borderRadius: '6px 6px 0 0',
                        cursor: 'pointer',
                        fontWeight: '500',
                        fontSize: '14px',
                        transition: 'all 0.2s'
                    }">
                {{ locale === 'en' ? 'Model Configuration' : '模型配置' }}
            </button>
            <button @click="settingsTab = 'backup'"
                    :style="{
                        padding: '10px 20px',
                        border: 'none',
                        background: settingsTab === 'backup' ? 'var(--primary)' : 'transparent',
                        color: settingsTab === 'backup' ? 'white' : 'var(--text)',
                        borderRadius: '6px 6px 0 0',
                        cursor: 'pointer',
                        fontWeight: '500',
                        fontSize: '14px',
                        transition: 'all 0.2s'
                    }">
                {{ locale === 'en' ? 'Backup Configuration' : '备份配置' }}
            </button>
            <button @click="settingsTab = 'diagnostics'"
                    :style="{
                        padding: '10px 20px',
                        border: 'none',
                        background: settingsTab === 'diagnostics' ? 'var(--primary)' : 'transparent',
                        color: settingsTab === 'diagnostics' ? 'white' : 'var(--text)',
                        borderRadius: '6px 6px 0 0',
                        cursor: 'pointer',
                        fontWeight: '500',
                        fontSize: '14px',
                        transition: 'all 0.2s'
                    }">
                {{ locale === 'en' ? 'System Diagnostics' : '系统诊断' }}
            </button>
        </div>
    </div>

    <!-- Tab Content -->
    <div style="margin-top: 20px;">
        <!-- Models Tab -->
        <div v-if="settingsTab === 'models'">
            <!-- Guidance Info Box -->
            <div class="card" style="background: linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%); border: 1px solid #bae6fd;">
                <!-- ... existing guidance content ... -->
            </div>

            <!-- LLM Model Service Configuration -->
            <div class="card" style="margin-top: 16px;">
                <!-- ... existing LLM config content ... -->
            </div>

            <!-- Embedding Model Service Configuration -->
            <div class="card" style="margin-top: 16px;">
                <!-- ... existing embedding config content ... -->
            </div>
        </div>

        <!-- Backup Tab -->
        <div v-if="settingsTab === 'backup'">
            <div class="card">
                <div class="card-body">
                    <h3 style="margin-bottom: 4px;">{{ locale === 'en' ? 'Backup Configuration' : '备份配置' }}</h3>
                    <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 20px;">
                        {{ locale === 'en'
                            ? 'Configure automatic backup settings for your knowledge base.'
                            : '配置知识库的自动备份设置。' }}
                    </p>

                    <!-- Enable Backup -->
                    <div style="margin-bottom: 16px;">
                        <label style="display: flex; align-items: center; cursor: pointer;">
                            <input type="checkbox" v-model="backupSettings.enabled"
                                   style="margin-right: 8px; width: 16px; height: 16px; cursor: pointer;" />
                            <span style="font-weight: 500;">{{ locale === 'en' ? 'Enable Automatic Backup' : '启用自动备份' }}</span>
                        </label>
                    </div>

                    <!-- Schedule -->
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-weight: 500; margin-bottom: 6px;">
                            {{ locale === 'en' ? 'Backup Schedule (Cron)' : '备份计划（Cron 表达式）' }}
                        </label>
                        <input type="text" v-model="backupSettings.schedule"
                               :placeholder="locale === 'en' ? 'e.g. 0 2 * * * (daily at 2 AM)' : '如 0 2 * * *（每天凌晨2点）'"
                               style="width: 100%; max-width: 400px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                    </div>

                    <!-- Retention Days -->
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-weight: 500; margin-bottom: 6px;">
                            {{ locale === 'en' ? 'Retention Days' : '保留天数' }}
                        </label>
                        <input type="number" v-model.number="backupSettings.retention_days" min="1"
                               style="width: 100%; max-width: 200px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                    </div>

                    <!-- Backup Directory -->
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-weight: 500; margin-bottom: 6px;">
                            {{ locale === 'en' ? 'Backup Directory' : '备份目录' }}
                        </label>
                        <input type="text" v-model="backupSettings.backup_dir"
                               style="width: 100%; max-width: 500px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                    </div>

                    <!-- Include Options -->
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-weight: 500; margin-bottom: 8px;">
                            {{ locale === 'en' ? 'Backup Content' : '备份内容' }}
                        </label>
                        <div style="display: flex; flex-direction: column; gap: 8px;">
                            <label style="display: flex; align-items: center; cursor: pointer;">
                                <input type="checkbox" v-model="backupSettings.include_db"
                                       style="margin-right: 8px; width: 16px; height: 16px; cursor: pointer;" />
                                <span>{{ locale === 'en' ? 'Include Database' : '包含数据库' }}</span>
                            </label>
                            <label style="display: flex; align-items: center; cursor: pointer;">
                                <input type="checkbox" v-model="backupSettings.include_files"
                                       style="margin-right: 8px; width: 16px; height: 16px; cursor: pointer;" />
                                <span>{{ locale === 'en' ? 'Include Files' : '包含文件' }}</span>
                            </label>
                            <label style="display: flex; align-items: center; cursor: pointer;">
                                <input type="checkbox" v-model="backupSettings.compression"
                                       style="margin-right: 8px; width: 16px; height: 16px; cursor: pointer;" />
                                <span>{{ locale === 'en' ? 'Enable Compression' : '启用压缩' }}</span>
                            </label>
                        </div>
                    </div>

                    <!-- Cloud Storage Provider -->
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-weight: 500; margin-bottom: 8px;">
                            {{ locale === 'en' ? 'Cloud Storage Provider' : '云存储提供商' }}
                        </label>
                        <select v-model="backupSettings.cloud_provider"
                                style="width: 100%; max-width: 300px; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;">
                            <option value="oss">{{ locale === 'en' ? 'Alibaba Cloud OSS' : '阿里云 OSS' }}</option>
                            <option value="s3">{{ locale === 'en' ? 'AWS S3' : 'AWS S3' }}</option>
                        </select>
                    </div>

                    <!-- OSS Configuration -->
                    <div v-if="backupSettings.cloud_provider === 'oss'" style="margin-bottom: 16px; padding: 16px; background: var(--bg-secondary); border-radius: 8px;">
                        <h4 style="margin-bottom: 12px; font-size: 14px; font-weight: 600;">
                            {{ locale === 'en' ? 'Alibaba Cloud OSS Configuration' : '阿里云 OSS 配置' }}
                        </h4>
                        <div style="display: flex; flex-direction: column; gap: 12px;">
                            <div>
                                <label style="display: block; font-weight: 500; margin-bottom: 4px; font-size: 13px;">
                                    {{ locale === 'en' ? 'Endpoint' : '端点' }}
                                </label>
                                <input type="text" v-model="backupSettings.oss.endpoint"
                                       placeholder="oss-cn-hangzhou.aliyuncs.com"
                                       style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                            </div>
                            <div>
                                <label style="display: block; font-weight: 500; margin-bottom: 4px; font-size: 13px;">
                                    {{ locale === 'en' ? 'Access Key ID' : '访问密钥 ID' }}
                                </label>
                                <input type="text" v-model="backupSettings.oss.access_key_id"
                                       placeholder="${OSS_ACCESS_KEY_ID}"
                                       style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                            </div>
                            <div>
                                <label style="display: block; font-weight: 500; margin-bottom: 4px; font-size: 13px;">
                                    {{ locale === 'en' ? 'Access Key Secret' : '访问密钥密码' }}
                                </label>
                                <input type="password" v-model="backupSettings.oss.access_key_secret"
                                       placeholder="${OSS_ACCESS_KEY_SECRET}"
                                       style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                            </div>
                            <div>
                                <label style="display: block; font-weight: 500; margin-bottom: 4px; font-size: 13px;">
                                    {{ locale === 'en' ? 'Bucket Name' : '存储桶名称' }}
                                </label>
                                <input type="text" v-model="backupSettings.oss.bucket"
                                       placeholder="localbrain-backups"
                                       style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                            </div>
                        </div>
                    </div>

                    <!-- S3 Configuration -->
                    <div v-if="backupSettings.cloud_provider === 's3'" style="margin-bottom: 16px; padding: 16px; background: var(--bg-secondary); border-radius: 8px;">
                        <h4 style="margin-bottom: 12px; font-size: 14px; font-weight: 600;">
                            {{ locale === 'en' ? 'AWS S3 Configuration' : 'AWS S3 配置' }}
                        </h4>
                        <div style="display: flex; flex-direction: column; gap: 12px;">
                            <div>
                                <label style="display: block; font-weight: 500; margin-bottom: 4px; font-size: 13px;">
                                    {{ locale === 'en' ? 'Region' : '区域' }}
                                </label>
                                <input type="text" v-model="backupSettings.s3.region"
                                       placeholder="us-west-2"
                                       style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                            </div>
                            <div>
                                <label style="display: block; font-weight: 500; margin-bottom: 4px; font-size: 13px;">
                                    {{ locale === 'en' ? 'Access Key ID' : '访问密钥 ID' }}
                                </label>
                                <input type="text" v-model="backupSettings.s3.access_key_id"
                                       placeholder="${AWS_ACCESS_KEY_ID}"
                                       style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                            </div>
                            <div>
                                <label style="display: block; font-weight: 500; margin-bottom: 4px; font-size: 13px;">
                                    {{ locale === 'en' ? 'Secret Access Key' : '访问密钥密码' }}
                                </label>
                                <input type="password" v-model="backupSettings.s3.secret_access_key"
                                       placeholder="${AWS_SECRET_ACCESS_KEY}"
                                       style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                            </div>
                            <div>
                                <label style="display: block; font-weight: 500; margin-bottom: 4px; font-size: 13px;">
                                    {{ locale === 'en' ? 'Bucket Name' : '存储桶名称' }}
                                </label>
                                <input type="text" v-model="backupSettings.s3.bucket"
                                       placeholder="localbrain-backups"
                                       style="width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); font-size: 14px;" />
                            </div>
                        </div>
                    </div>

                    <!-- Save Button -->
                    <div style="margin-top: 20px;">
                        <button @click="saveBackupSettings" :disabled="backupSettingsSaving"
                                style="padding: 10px 24px; background: var(--primary); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 14px;">
                            {{ backupSettingsSaving ? (locale === 'en' ? 'Saving...' : '保存中...') : (locale === 'en' ? 'Save Settings' : '保存设置') }}
                        </button>
                        <span v-if="backupSettingsSaved" style="margin-left: 12px; color: var(--success); font-size: 14px;">
                            ✓ {{ locale === 'en' ? 'Saved successfully' : '保存成功' }}
                        </span>
                        <span v-if="backupSettingsError" style="margin-left: 12px; color: var(--danger); font-size: 14px;">
                            {{ backupSettingsError }}
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Diagnostics Tab -->
        <div v-if="settingsTab === 'diagnostics'">
            <!-- System Diagnostics -->
            <div class="card">
                <!-- ... existing diagnostics content ... -->
            </div>
        </div>
    </div>
</div>
```

## Testing

After implementing these changes:

1. Navigate to Settings page
2. Verify three tabs are visible: Model Configuration, Backup Configuration, System Diagnostics
3. Test switching between tabs
4. Test saving backup configuration
5. Verify all existing model configuration functionality still works
6. Verify system diagnostics still works

## API Endpoints

The following endpoints are already implemented:
- `GET /api/settings/backup` - Get backup settings
- `PUT /api/settings/backup` - Update backup settings

## Notes

- The tab state (`settingsTab`) is stored in Vue data and defaults to 'models'
- Tab switching is instant with no page reload
- All existing functionality is preserved, just reorganized into tabs
- The backup configuration uses the same styling as other settings sections
