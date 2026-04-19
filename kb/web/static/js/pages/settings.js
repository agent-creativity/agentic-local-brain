// Settings Page Component
// Fetch template at module load time
const templatePromise = fetch('/static/templates/pages/settings.html').then(r => r.text());
const template = await templatePromise;

export default {
    name: 'SettingsPage',
    template,
    data() {
        return {
            // Tab state
            settingsTab: 'models',

            // LLM Settings
            llmSettings: {
                provider: 'dashscope',
                model: '',
                api_key: '',
                base_url: ''
            },
            llmSettingsSaving: false,
            llmSettingsSaved: false,
            llmSettingsError: '',
            testingLLM: false,
            llmTestResult: null,

            // Embedding Settings
            embeddingSettings: {
                provider: 'dashscope',
                model: '',
                api_key: '',
                base_url: ''
            },
            embeddingSettingsSaving: false,
            embeddingSettingsSaved: false,
            embeddingSettingsError: '',
            testingEmbedding: false,
            embeddingTestResult: null,

            // Backup Settings
            backupSettings: {
                enabled: false,
                schedule: '0 2 * * *',
                retention_days: 30,
                storage_location: 'local',
                oss_endpoint: '',
                oss_access_key_id: '',
                oss_access_key_secret: '',
                oss_bucket: '',
                s3_region: '',
                s3_access_key_id: '',
                s3_secret_access_key: '',
                s3_bucket: ''
            },
            backupSettingsSaving: false,
            backupSettingsSaved: false,
            backupSettingsError: '',

            // Diagnostics
            runningDoctor: false,
            doctorResults: null,

            // Installation Info
            version: '',
            settingsPaths: {
                data_dir: '',
                install_dir: ''
            }
        };
    },
    computed: {
        locale() {
            return this.$root.locale;
        }
    },
    methods: {
        t(key) {
            return this.$root.t(key);
        },

        async fetchSettings() {
            try {
                const res = await fetch('/api/settings');
                if (!res.ok) throw new Error('Failed to fetch settings');
                const data = await res.json();

                // LLM settings
                if (data.llm) {
                    this.llmSettings = {
                        provider: data.llm.provider || 'dashscope',
                        model: data.llm.model || '',
                        api_key: data.llm.api_key || '',
                        base_url: data.llm.base_url || ''
                    };
                }

                // Embedding settings
                if (data.embedding) {
                    this.embeddingSettings = {
                        provider: data.embedding.provider || 'dashscope',
                        model: data.embedding.model || '',
                        api_key: data.embedding.api_key || '',
                        base_url: data.embedding.base_url || ''
                    };
                }

                // Paths
                if (data.paths) {
                    this.settingsPaths = {
                        data_dir: data.paths.data_dir || '',
                        install_dir: data.paths.install_dir || ''
                    };
                }
            } catch (e) {
                console.error('Failed to load settings:', e);
            }

            // Fetch version from stats API
            try {
                const res = await fetch('/api/stats');
                if (res.ok) {
                    const data = await res.json();
                    if (data.version) {
                        this.version = data.version;
                    }
                }
            } catch (e) {
                console.error('Failed to load version:', e);
            }

            // Fetch backup settings
            await this.fetchBackupSettings();
        },

        async fetchBackupSettings() {
            try {
                const res = await fetch('/api/settings/backup');
                if (!res.ok) throw new Error('Failed to fetch backup settings');
                const data = await res.json();

                if (data.backup) {
                    this.backupSettings = { ...data.backup };
                }
            } catch (e) {
                console.error('Failed to load backup settings:', e);
            }
        },

        async saveLLMSettings() {
            this.llmSettingsSaving = true;
            this.llmSettingsSaved = false;
            this.llmSettingsError = '';
            try {
                const res = await fetch('/api/settings/llm', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.llmSettings)
                });
                const data = await res.json();
                if (!res.ok) {
                    this.llmSettingsError = data.detail || 'Failed to save settings';
                } else {
                    this.llmSettingsSaved = true;
                    setTimeout(() => { this.llmSettingsSaved = false; }, 3000);
                }
            } catch (e) {
                this.llmSettingsError = e.message || 'Failed to save settings';
            } finally {
                this.llmSettingsSaving = false;
            }
        },

        async saveEmbeddingSettings() {
            this.embeddingSettingsSaving = true;
            this.embeddingSettingsSaved = false;
            this.embeddingSettingsError = '';
            try {
                const res = await fetch('/api/settings/embedding', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.embeddingSettings)
                });
                const data = await res.json();
                if (!res.ok) {
                    this.embeddingSettingsError = data.detail || 'Failed to save settings';
                } else {
                    this.embeddingSettingsSaved = true;
                    setTimeout(() => { this.embeddingSettingsSaved = false; }, 3000);
                }
            } catch (e) {
                this.embeddingSettingsError = e.message || 'Failed to save settings';
            } finally {
                this.embeddingSettingsSaving = false;
            }
        },

        async saveBackupSettings() {
            this.backupSettingsSaving = true;
            this.backupSettingsSaved = false;
            this.backupSettingsError = '';

            try {
                const res = await fetch('/api/settings/backup', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.backupSettings)
                });

                const data = await res.json();

                if (res.ok) {
                    this.backupSettingsSaved = true;
                    setTimeout(() => {
                        this.backupSettingsSaved = false;
                    }, 3000);
                } else {
                    this.backupSettingsError = data.detail || 'Failed to save settings';
                }
            } catch (e) {
                this.backupSettingsError = e.message;
            } finally {
                this.backupSettingsSaving = false;
            }
        },

        async testLLM() {
            this.testingLLM = true;
            this.llmTestResult = null;
            try {
                const res = await fetch('/api/settings/test-llm', { method: 'POST' });
                const data = await res.json();
                this.llmTestResult = data;
            } catch (e) {
                this.llmTestResult = { success: false, error: e.message };
            } finally {
                this.testingLLM = false;
            }
        },

        async testEmbedding() {
            this.testingEmbedding = true;
            this.embeddingTestResult = null;
            try {
                const res = await fetch('/api/settings/test-embedding', { method: 'POST' });
                const data = await res.json();
                this.embeddingTestResult = data;
            } catch (e) {
                this.embeddingTestResult = { success: false, error: e.message };
            } finally {
                this.testingEmbedding = false;
            }
        },

        async runDoctor() {
            this.runningDoctor = true;
            this.doctorResults = null;
            try {
                const res = await fetch('/api/settings/doctor');
                const data = await res.json();
                this.doctorResults = data;
            } catch (e) {
                console.error('Failed to run doctor:', e);
            } finally {
                this.runningDoctor = false;
            }
        }
    },
    async mounted() {
        await this.fetchSettings();
    }
};
