import { describe, it, expect, vi, beforeEach } from 'vitest'
import { cached, invalidate } from '../../../src/api/cache'

describe('API Cache', () => {
  beforeEach(() => {
    invalidate()
  })

  it('calls fetcher on first request', async () => {
    const fetcher = vi.fn().mockResolvedValue({ data: 'fresh' })
    const result = await cached('test-key', 5000, fetcher)

    expect(fetcher).toHaveBeenCalledOnce()
    expect(result).toEqual({ data: 'fresh' })
  })

  it('returns cached data on subsequent requests within TTL', async () => {
    const fetcher = vi.fn().mockResolvedValue({ data: 'fresh' })

    await cached('key1', 5000, fetcher)
    const result2 = await cached('key1', 5000, fetcher)

    expect(fetcher).toHaveBeenCalledOnce()
    expect(result2).toEqual({ data: 'fresh' })
  })

  it('re-fetches after TTL expires', async () => {
    vi.useFakeTimers()

    const fetcher = vi.fn()
      .mockResolvedValueOnce({ data: 'v1' })
      .mockResolvedValueOnce({ data: 'v2' })

    await cached('key2', 1000, fetcher)
    expect(fetcher).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(1500)
    const result = await cached('key2', 1000, fetcher)
    expect(fetcher).toHaveBeenCalledTimes(2)
    expect(result).toEqual({ data: 'v2' })

    vi.useRealTimers()
  })

  it('invalidate() clears all cache', async () => {
    const fetcher = vi.fn().mockResolvedValue('data')

    await cached('a', 5000, fetcher)
    await cached('b', 5000, fetcher)
    expect(fetcher).toHaveBeenCalledTimes(2)

    invalidate()

    await cached('a', 5000, fetcher)
    expect(fetcher).toHaveBeenCalledTimes(3)
  })

  it('invalidate(prefix) clears only matching keys', async () => {
    const fetcherA = vi.fn().mockResolvedValue('A')
    const fetcherB = vi.fn().mockResolvedValue('B')

    await cached('tags:list', 5000, fetcherA)
    await cached('dashboard:stats', 5000, fetcherB)

    invalidate('tags:')

    await cached('tags:list', 5000, fetcherA)
    await cached('dashboard:stats', 5000, fetcherB)

    expect(fetcherA).toHaveBeenCalledTimes(2)
    expect(fetcherB).toHaveBeenCalledTimes(1)
  })

  it('different keys are cached independently', async () => {
    const f1 = vi.fn().mockResolvedValue('result1')
    const f2 = vi.fn().mockResolvedValue('result2')

    const r1 = await cached('key-x', 5000, f1)
    const r2 = await cached('key-y', 5000, f2)

    expect(r1).toBe('result1')
    expect(r2).toBe('result2')
    expect(f1).toHaveBeenCalledOnce()
    expect(f2).toHaveBeenCalledOnce()
  })
})
