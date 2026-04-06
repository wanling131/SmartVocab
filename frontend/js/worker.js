/**
 * SmartVocab Web Worker - 后台计算线程
 * 处理耗时操作，避免阻塞主线程
 */

// 缓存存储
const cacheStore = new Map()

// 消息处理
self.onmessage = function(e) {
  const { type, data, taskId } = e.data

  try {
    let result
    switch (type) {
      case 'filter':
        result = filterData(data.items, data.query, data.fields)
        break
      case 'stats':
        result = calcStats(data.records)
        break
      case 'sort':
        result = sortData(data.items, data.key, data.desc)
        break
      case 'cache':
        result = handleCache(data.op, data.key, data.value)
        break
      default:
        result = null
    }
    self.postMessage({ success: true, result, taskId })
  } catch (err) {
    self.postMessage({ success: false, error: err.message, taskId })
  }
}

// 过滤数据
function filterData(items, query, fields = ['word', 'translation']) {
  if (!items || !query) return items || []
  const q = query.toLowerCase()
  return items.filter(item =>
    fields.some(f => (item[f] || '').toLowerCase().includes(q))
  )
}

// 计算统计
function calcStats(records) {
  if (!records?.length) return { total: 0, mastered: 0, learning: 0, avg: 0 }

  let mastered = 0, learning = 0, sum = 0
  for (const r of records) {
    const m = r.mastery_level || 0
    sum += m
    if (m >= 0.8) mastered++
    else if (m > 0) learning++
  }

  return {
    total: records.length,
    mastered,
    learning,
    newWords: records.length - mastered - learning,
    avg: (sum / records.length).toFixed(2)
  }
}

// 排序数据
function sortData(items, key, desc = false) {
  if (!items) return []
  return [...items].sort((a, b) => {
    const va = a[key] ?? ''
    const vb = b[key] ?? ''
    const cmp = typeof va === 'string' ? va.localeCompare(vb) : va - vb
    return desc ? -cmp : cmp
  })
}

// 缓存操作
function handleCache(op, key, value) {
  switch (op) {
    case 'get': return cacheStore.get(key) || null
    case 'set': cacheStore.set(key, { value, ts: Date.now() }); return true
    case 'del': cacheStore.delete(key); return true
    case 'clear': cacheStore.clear(); return true
    default: return null
  }
}

self.postMessage({ type: 'ready' })
