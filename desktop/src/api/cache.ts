interface CacheEntry<T> {
  data: T
  expiresAt: number
}

const store = new Map<string, CacheEntry<unknown>>()

export function cached<T>(key: string, ttlMs: number, fetcher: () => Promise<T>): Promise<T> {
  const entry = store.get(key) as CacheEntry<T> | undefined
  if (entry && Date.now() < entry.expiresAt) {
    return Promise.resolve(entry.data)
  }
  return fetcher().then((data) => {
    store.set(key, { data, expiresAt: Date.now() + ttlMs })
    return data
  })
}

export function invalidate(keyPrefix?: string) {
  if (!keyPrefix) {
    store.clear()
    return
  }
  for (const key of store.keys()) {
    if (key.startsWith(keyPrefix)) store.delete(key)
  }
}
