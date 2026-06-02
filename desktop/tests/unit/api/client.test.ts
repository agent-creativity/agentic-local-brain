import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { get, post, put, del, healthCheck, ApiError, setBaseUrl, getBaseUrl } from '../../../src/api/client'

const MOCK_BASE = 'http://localhost:9999/api'

describe('API Client', () => {
  beforeEach(() => {
    setBaseUrl(MOCK_BASE)
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('get()', () => {
    it('sends GET request to correct URL', async () => {
      const mockData = { id: 1, name: 'test' }
      vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify(mockData), { status: 200 }))

      const result = await get('/items')
      expect(fetch).toHaveBeenCalledWith(`${MOCK_BASE}/items`)
      expect(result).toEqual(mockData)
    })

    it('appends query params correctly', async () => {
      vi.mocked(fetch).mockResolvedValue(new Response('[]', { status: 200 }))

      await get('/items', { limit: 10, offset: 0, search: 'test' })
      const calledUrl = vi.mocked(fetch).mock.calls[0][0] as string
      expect(calledUrl).toContain('limit=10')
      expect(calledUrl).toContain('offset=0')
      expect(calledUrl).toContain('search=test')
    })

    it('skips undefined params', async () => {
      vi.mocked(fetch).mockResolvedValue(new Response('[]', { status: 200 }))

      await get('/items', { limit: 10, search: undefined })
      const calledUrl = vi.mocked(fetch).mock.calls[0][0] as string
      expect(calledUrl).toContain('limit=10')
      expect(calledUrl).not.toContain('search')
    })
  })

  describe('post()', () => {
    it('sends POST request with JSON body', async () => {
      const body = { title: 'new item' }
      vi.mocked(fetch).mockResolvedValue(new Response('{"id":"1"}', { status: 200 }))

      await post('/items', body)
      expect(fetch).toHaveBeenCalledWith(`${MOCK_BASE}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
    })

    it('sends POST without body when none provided', async () => {
      vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 200 }))

      await post('/action')
      expect(fetch).toHaveBeenCalledWith(`${MOCK_BASE}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: undefined,
      })
    })
  })

  describe('put()', () => {
    it('sends PUT request with JSON body', async () => {
      const body = { title: 'updated' }
      vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 200 }))

      await put('/items/1', body)
      expect(fetch).toHaveBeenCalledWith(`${MOCK_BASE}/items/1`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
    })
  })

  describe('del()', () => {
    it('sends DELETE request', async () => {
      vi.mocked(fetch).mockResolvedValue(new Response('{}', { status: 200 }))

      await del('/items/1')
      expect(fetch).toHaveBeenCalledWith(`${MOCK_BASE}/items/1`, { method: 'DELETE' })
    })
  })

  describe('error handling', () => {
    it('throws ApiError on non-OK response', async () => {
      vi.mocked(fetch).mockResolvedValue(new Response('Not Found', { status: 404, statusText: 'Not Found' }))

      await expect(get('/missing')).rejects.toThrow(ApiError)
      await expect(get('/missing')).rejects.toMatchObject({ status: 404 })
    })

    it('ApiError contains status and message', async () => {
      vi.mocked(fetch).mockResolvedValue(new Response('Server Error', { status: 500, statusText: 'Internal Server Error' }))

      try {
        await get('/fail')
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError)
        expect((e as ApiError).status).toBe(500)
        expect((e as ApiError).statusText).toBe('Internal Server Error')
      }
    })
  })

  describe('healthCheck()', () => {
    it('returns true when server is healthy', async () => {
      vi.mocked(fetch).mockResolvedValue(new Response('ok', { status: 200 }))

      const result = await healthCheck()
      expect(result).toBe(true)
    })

    it('returns false when server is down', async () => {
      vi.mocked(fetch).mockRejectedValue(new Error('Connection refused'))

      const result = await healthCheck()
      expect(result).toBe(false)
    })
  })

  describe('baseUrl management', () => {
    it('getBaseUrl returns current base URL', () => {
      setBaseUrl('http://custom:1234/api')
      expect(getBaseUrl()).toBe('http://custom:1234/api')
    })
  })
})
