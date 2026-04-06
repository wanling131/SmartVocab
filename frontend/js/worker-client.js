/**
 * Web Worker 客户端 - 简化版
 * 自动降级，无缝集成
 */

class WorkerClient {
  constructor() {
    this.worker = null
    this.tasks = new Map()
    this.id = 0
    this._init()
  }

  _init() {
    if (typeof Worker === 'undefined') return
    try {
      this.worker = new Worker('/js/worker.js')
      this.worker.onmessage = (e) => {
        const { success, result, error, taskId } = e.data
        const task = this.tasks.get(taskId)
        if (task) {
          this.tasks.delete(taskId)
          success ? task.resolve(result) : task.reject(new Error(error))
        }
      }
    } catch (e) { /* Worker 不可用 */ }
  }

  _send(type, data, timeout = 5000) {
    return new Promise((resolve, reject) => {
      if (!this.worker) {
        resolve(this._fallback(type, data))
        return
      }
      const id = ++this.id
      const timer = setTimeout(() => {
        this.tasks.delete(id)
        reject(new Error('超时'))
      }, timeout)
      this.tasks.set(id, {
        resolve: v => { clearTimeout(timer); resolve(v) },
        reject: e => { clearTimeout(timer); reject(e) }
      })
      this.worker.postMessage({ type, data, taskId: id })
    })
  }

  _fallback(type, data) {
    if (type === 'filter') {
      const { items, query, fields } = data
      if (!items || !query) return items || []
      const q = query.toLowerCase()
      return items.filter(i => (fields || ['word', 'translation'])
        .some(f => (i[f] || '').toLowerCase().includes(q)))
    }
    if (type === 'stats') {
      const { records } = data
      if (!records?.length) return { total: 0, mastered: 0, learning: 0, avg: 0 }
      let mastered = 0, learning = 0, sum = 0
      for (const r of records) {
        const m = r.mastery_level || 0
        sum += m
        if (m >= 0.8) mastered++
        else if (m > 0) learning++
      }
      return { total: records.length, mastered, learning, avg: (sum / records.length).toFixed(2) }
    }
    return null
  }

  // 公开 API
  filter(items, query, fields) { return this._send('filter', { items, query, fields }) }
  stats(records) { return this._send('stats', { records }) }
  sort(items, key, desc) { return this._send('sort', { items, key, desc }) }
}

// 全局实例
window.workerClient = new WorkerClient()
