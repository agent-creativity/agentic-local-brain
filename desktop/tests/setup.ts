import { config } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import en from '../src/i18n/en'
import zh from '../src/i18n/zh'

const i18n = createI18n({
  legacy: false,
  locale: 'zh',
  fallbackLocale: 'en',
  messages: { en, zh },
})

config.global.plugins = [
  createTestingPinia({ createSpy: vi.fn }),
  i18n,
]
