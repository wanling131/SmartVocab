import { apiRequest, setToken, getToken, clearToken } from "./js/api-client.js"
import { getCurrentUser } from "./js/utils.js"
import { getCurrentUser as getStoredUser } from "./js/utils.js"

// Web Worker 客户端（用于大量数据计算)
let workerClient = null

// ==================== 安全工具函数 ====================

/**
 * HTML转义函数，防止XSS攻击
 * @param {string} str - 需要转义的字符串
 * @returns {string} - 转义后的安全字符串
 */
function escapeHtml(str) {
  if (str === null || str === undefined) return ''
  const div = document.createElement('div')
  div.textContent = String(str)
  return div.innerHTML
}

/**
 * 安全地设置元素的innerHTML，自动转义所有变量
 * @param {HTMLElement} element - 目标元素
 * @param {string} html - HTML模板字符串
 * @param {Object} vars - 需要转义的变量对象
 */
function safeHtml(element, html, vars = {}) {
  let result = html
  for (const [key, value] of Object.entries(vars)) {
    const placeholder = new RegExp(`\\$\\{\\s*${key}\\s*\\}`, 'g')
    result = result.replace(placeholder, escapeHtml(value))
  }
  element.innerHTML = result
}

// ==================== UI 组件工具函数 ====================

/**
 * 显示确认对话框
 * @param {string} message - 确认消息
 * @param {Object} options - 配置选项
 * @returns {Promise<boolean>} - 用户选择结果
 */
function showConfirm(message, options = {}) {
  const { title = '确认操作', confirmText = '确定', cancelText = '取消', type = 'warning' } = options

  return new Promise((resolve) => {
    const overlay = document.createElement('div')
    overlay.className = 'confirm-overlay'
    overlay.innerHTML = `
      <div class="confirm-dialog ${type}">
        <div class="confirm-header">
          <span class="confirm-icon">${type === 'danger' ? '⚠️' : type === 'warning' ? '⚡' : 'ℹ️'}</span>
          <h3>${escapeHtml(title)}</h3>
        </div>
        <div class="confirm-body">
          <p>${escapeHtml(message)}</p>
        </div>
        <div class="confirm-footer">
          <button class="btn btn-secondary confirm-cancel">${escapeHtml(cancelText)}</button>
          <button class="btn ${type === 'danger' ? 'btn-danger' : 'btn-primary'} confirm-ok">${escapeHtml(confirmText)}</button>
        </div>
      </div>
    `

    document.body.appendChild(overlay)

    // 动画显示
    requestAnimationFrame(() => {
      overlay.classList.add('show')
    })

    const handleResult = (result) => {
      overlay.classList.remove('show')
      setTimeout(() => overlay.remove(), 300)
      resolve(result)
    }

    overlay.querySelector('.confirm-ok').addEventListener('click', () => handleResult(true))
    overlay.querySelector('.confirm-cancel').addEventListener('click', () => handleResult(false))
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) handleResult(false)
    })

    // ESC 键关闭
    const handleEsc = (e) => {
      if (e.key === 'Escape') {
        document.removeEventListener('keydown', handleEsc)
        handleResult(false)
      }
    }
    document.addEventListener('keydown', handleEsc)
  })
}

// ==================== 例句展示功能 ====================

/**
 * 更新例句展示区域
 * @param {Object} word - 单词对象
 */
function updateExampleSection(word) {
  const exampleSection = document.getElementById("example-section")
  const exampleText = document.getElementById("word-example")

  if (!exampleSection || !exampleText) return

  const example = word.example_sentence || word.example || ""

  if (example && word.question_type !== "spelling") {
    // 高亮当前单词
    const highlighted = example.replace(
      new RegExp(`\\b${word.word}\\b`, "gi"),
      `<span class="highlight">${word.word}</span>`
    )
    exampleText.innerHTML = highlighted
    exampleSection.classList.remove("hidden")
  } else {
    exampleSection.classList.add("hidden")
  }
}

/**
 * 切换例句显示/隐藏
 */
function toggleExample() {
  const section = document.getElementById("example-section")
  const icon = document.getElementById("toggle-example-icon")

  if (section.classList.contains("hidden")) {
    section.classList.remove("hidden")
    if (icon) icon.textContent = "📖"
  } else {
    section.classList.add("hidden")
    if (icon) icon.textContent = "📖"
  }
}

// 暴露给全局
window.toggleExample = toggleExample

/**
 * 获取难度描述
 * @param {number} level - 难度等级 (1-6)
 * @returns {string} 难度描述
 */
function getDifficultyDescription(level) {
  const descriptions = {
    1: "入门",
    2: "基础",
    3: "初级",
    4: "中级",
    5: "高级",
    6: "专业"
  }
  return descriptions[level] || "未知"
}

/**
 * 创建骨架屏加载效果
 * @param {string} type - 骨架屏类型 ('card', 'list', 'text')
 * @param {number} count - 数量
 * @returns {string} - HTML字符串
 */
function createSkeleton(type = 'card', count = 3) {
  const templates = {
    card: '<div class="skeleton skeleton-card"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text" style="width: 60%"></div></div>',
    list: '<div class="skeleton skeleton-list-item"><div class="skeleton skeleton-avatar"></div><div class="skeleton skeleton-content"><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text" style="width: 80%"></div></div></div>',
    text: '<div class="skeleton skeleton-text"></div>'
  }

  const template = templates[type] || templates.card
  return Array(count).fill(template).join('')
}

/**
 * 设置元素加载状态
 * @param {HTMLElement} element - 目标元素
 * @param {boolean} isLoading - 是否加载中
 * @param {string} loadingText - 加载文本
 */
function setElementLoading(element, isLoading, loadingText = '加载中...') {
  if (!element) return

  if (isLoading) {
    element.dataset.originalContent = element.innerHTML
    element.innerHTML = `<div class="loading-inline"><div class="loading-spinner-sm"></div><span>${loadingText}</span></div>`
    element.disabled = true
  } else {
    if (element.dataset.originalContent) {
      element.innerHTML = element.dataset.originalContent
      delete element.dataset.originalContent
    }
    element.disabled = false
  }
}

/**
 * 平滑滚动到元素
 * @param {HTMLElement|string} target - 目标元素或选择器
 * @param {Object} options - 滚动选项
 */
function smoothScrollTo(target, options = {}) {
  const { offset = 0, duration = 500 } = options
  const element = typeof target === 'string' ? document.querySelector(target) : target

  if (!element) return

  const targetPosition = element.getBoundingClientRect().top + window.pageYOffset - offset
  const startPosition = window.pageYOffset
  const distance = targetPosition - startPosition
  let startTime = null

  function animation(currentTime) {
    if (!startTime) startTime = currentTime
    const progress = Math.min((currentTime - startTime) / duration, 1)
    const easeProgress = 1 - Math.pow(1 - progress, 3)

    window.scrollTo(0, startPosition + distance * easeProgress)

    if (progress < 1) requestAnimationFrame(animation)
  }

  requestAnimationFrame(animation)
}

/**
 * 显示内联错误提示
 * @param {HTMLElement} element - 目标元素
 * @param {string} message - 错误消息
 * @param {number} duration - 持续时间
 */
function showInlineError(element, message, duration = 3000) {
  if (!element) return

  // 移除已有错误提示
  const existingError = element.parentElement.querySelector('.inline-error')
  if (existingError) existingError.remove()

  const errorEl = document.createElement('div')
  errorEl.className = 'inline-error'
  errorEl.textContent = message
  element.parentElement.appendChild(errorEl)
  element.classList.add('input-error')

  // 添加抖动动画
  element.classList.add('shake-animate')
  setTimeout(() => element.classList.remove('shake-animate'), 400)

  setTimeout(() => {
    errorEl.classList.add('fade-out')
    element.classList.remove('input-error')
    setTimeout(() => errorEl.remove(), 300)
  }, duration)
}

/**
 * 添加按钮加载状态
 * @param {HTMLElement} button - 按钮元素
 * @param {boolean} loading - 是否加载中
 * @param {string} text - 加载时显示的文本
 */
function setButtonLoading(button, loading, text = '处理中...') {
  if (!button) return

  if (loading) {
    button.dataset.originalText = button.innerHTML
    button.innerHTML = `<span class="loading-spinner-sm"></span><span>${text}</span>`
    button.disabled = true
    button.classList.add('loading')
  } else {
    button.innerHTML = button.dataset.originalText || button.innerHTML
    button.disabled = false
    button.classList.remove('loading')
    delete button.dataset.originalText
  }
}

// ==================== DOM 操作工具函数 ====================

/**
 * 批量设置元素属性
 * @param {HTMLElement} element - 目标元素
 * @param {Object} attrs - 属性对象
 */
function setAttributes(element, attrs) {
  if (!element || !attrs) return
  Object.entries(attrs).forEach(([key, value]) => {
    if (key === 'className') {
      element.className = value
    } else if (key === 'style' && typeof value === 'object') {
      Object.assign(element.style, value)
    } else if (key.startsWith('data')) {
      element.dataset[key.slice(4).toLowerCase()] = value
    } else {
      element.setAttribute(key, value)
    }
  })
}

/**
 * 创建带类名的元素
 * @param {string} tag - 标签名
 * @param {string|Array} classNames - 类名
 * @param {Object} attrs - 属性
 * @param {string} innerHTML - 内部HTML
 * @returns {HTMLElement}
 */
function createElement(tag, classNames = '', attrs = {}, innerHTML = '') {
  const element = document.createElement(tag)
  if (classNames) {
    const classes = Array.isArray(classNames) ? classNames : classNames.split(' ')
    element.classList.add(...classes.filter(Boolean))
  }
  setAttributes(element, attrs)
  if (innerHTML) element.innerHTML = innerHTML
  return element
}

/**
 * 显示/隐藏元素（带动画）
 * @param {HTMLElement} element - 目标元素
 * @param {boolean} show - 是否显示
 * @param {string} animation - 动画类型
 */
function toggleVisibility(element, show, animation = 'fade') {
  if (!element) return

  if (show) {
    element.style.display = ''
    element.classList.remove('hidden', 'fade-out', 'slide-out')
    element.classList.add(`${animation}-in`)
  } else {
    element.classList.add(`${animation}-out`)
    setTimeout(() => {
      element.classList.add('hidden')
      element.classList.remove(`${animation}-out`)
    }, 300)
  }
}

/**
 * 批量查询并操作元素
 * @param {string} selector - 选择器
 * @param {Function} callback - 操作函数
 */
function queryAndExecute(selector, callback) {
  document.querySelectorAll(selector).forEach(callback)
}

/**
 * 安全获取DOM元素
 * @param {string|HTMLElement} target - 选择器或元素
 * @returns {HTMLElement|null}
 */
function getElement(target) {
  return typeof target === 'string' ? document.querySelector(target) : target
}

/**
 * 批量获取DOM元素值
 * @param {Object} fieldMap - 字段映射 {key: selector}
 * @returns {Object}
 */
function getFormValues(fieldMap) {
  const values = {}
  Object.entries(fieldMap).forEach(([key, selector]) => {
    const el = document.querySelector(selector)
    values[key] = el ? el.value.trim() : ''
  })
  return values
}

/**
 * 批量设置DOM元素值
 * @param {Object} valueMap - 值映射 {selector: value}
 */
function setFormValues(valueMap) {
  Object.entries(valueMap).forEach(([selector, value]) => {
    const el = document.querySelector(selector)
    if (el) el.value = value || ''
  })
}

// ==================== 动画工具函数 ====================

/**
 * 数字递增动画
 */
function animateNumber(element, targetValue, duration = 1000) {
  if (!element) return
  const startValue = parseInt(element.textContent) || 0
  const startTime = performance.now()

  function update(currentTime) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    const easeProgress = 1 - Math.pow(1 - progress, 3)
    const currentValue = Math.round(startValue + (targetValue - startValue) * easeProgress)
    element.textContent = currentValue.toLocaleString()
    if (progress < 1) requestAnimationFrame(update)
  }
  requestAnimationFrame(update)
}

/**
 * 元素淡入动画
 */
function fadeIn(element, duration = 300) {
  if (!element) return
  element.style.opacity = '0'
  element.style.display = 'block'
  let start = null
  function animate(timestamp) {
    if (!start) start = timestamp
    const opacity = Math.min((timestamp - start) / duration, 1)
    element.style.opacity = opacity
    if (opacity < 1) requestAnimationFrame(animate)
  }
  requestAnimationFrame(animate)
}

/**
 * 元素淡出动画
 */
function fadeOut(element, duration = 300) {
  return new Promise((resolve) => {
    if (!element) { resolve(); return }
    let start = null
    function animate(timestamp) {
      if (!start) start = timestamp
      const opacity = 1 - Math.min((timestamp - start) / duration, 1)
      element.style.opacity = opacity
      if (opacity > 0) {
        requestAnimationFrame(animate)
      } else {
        element.style.display = 'none'
        resolve()
      }
    }
    requestAnimationFrame(animate)
  })
}

/**
 * 涟漪点击效果
 */
function createRipple(event) {
  const button = event.currentTarget
  const rect = button.getBoundingClientRect()
  const ripple = document.createElement('span')
  const diameter = Math.max(rect.width, rect.height)
  ripple.style.cssText = `
    width: ${diameter}px; height: ${diameter}px;
    left: ${event.clientX - rect.left - diameter/2}px;
    top: ${event.clientY - rect.top - diameter/2}px;
  `
  ripple.className = 'ripple-effect'
  button.querySelector('.ripple-effect')?.remove()
  button.appendChild(ripple)
  setTimeout(() => ripple.remove(), 600)
}

/**
 * 进度条平滑动画
 */
function animateProgress(progressBar, targetPercent, duration = 500) {
  if (!progressBar) return
  const currentWidth = parseFloat(progressBar.style.width) || 0
  const startTime = performance.now()
  function update(currentTime) {
    const progress = Math.min((currentTime - startTime) / duration, 1)
    const easeProgress = 1 - Math.pow(1 - progress, 2)
    progressBar.style.width = `${currentWidth + (targetPercent - currentWidth) * easeProgress}%`
    if (progress < 1) requestAnimationFrame(update)
  }
  requestAnimationFrame(update)
}

/**
 * 打字机效果
 */
function typeWriter(element, text, speed = 50) {
  return new Promise((resolve) => {
    if (!element) { resolve(); return }
    element.textContent = ''
    let i = 0
    function type() {
      if (i < text.length) {
        element.textContent += text.charAt(i++)
        setTimeout(type, speed)
      } else resolve()
    }
    type()
  })
}

/**
 * 初始化所有动画效果
 */
function initAnimations() {
  document.querySelectorAll('.btn, button:not(.ripple-initialized)').forEach(btn => {
    btn.classList.add('ripple-initialized')
    btn.addEventListener('click', createRipple)
  })
}

// DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', initAnimations)

// 全局状态
let currentUser = null
let currentSession = null
let sessionStartTime = null
let correctAnswers = 0
let totalAnswers = 0
let browseMode = false  // 浏览模式标识
let browseWords = []    // 浏览单词列表
let currentBrowseIndex = 0  // 当前浏览索引
let wordStartTime = 0

function showLoading() {
  const existing = document.getElementById("loading-overlay")
  if (existing) return
  const overlay = document.createElement("div")
  overlay.className = "loading-overlay"
  overlay.id = "loading-overlay"
  overlay.innerHTML = `
    <div class="loading-content">
      <div class="loading-spinner"></div>
      <div class="loading-text">加载中...</div>
      <div class="loading-dots">
        <span></span><span></span><span></span>
      </div>
    </div>
  `
  document.body.appendChild(overlay)
  requestAnimationFrame(() => overlay.classList.add('show'))
}

function hideLoading() {
  const overlay = document.getElementById("loading-overlay")
  if (overlay) {
    overlay.classList.remove('show')
    setTimeout(() => overlay.remove(), 300)
  }
}

/**
 * 显示加载骨架屏
 * @param {string} containerId - 容器元素ID
 * @param {string} type - 骨架屏类型
 * @param {number} count - 数量
 */
function showSkeleton(containerId, type = 'card', count = 3) {
  const container = document.getElementById(containerId)
  if (!container) return

  container.innerHTML = createSkeleton(type, count)
}

/**
 * 显示统计卡片骨架屏
 */
function showStatsSkeleton() {
  const grid = document.querySelector('.stats-grid')
  if (!grid) return

  grid.innerHTML = Array(4).fill(0).map(() => `
    <div class="stat-card skeleton">
      <div class="stat-skeleton">
        <div class="skeleton skeleton-icon"></div>
        <div class="skeleton-info">
          <div class="skeleton skeleton-value"></div>
          <div class="skeleton skeleton-label"></div>
        </div>
      </div>
    </div>
  `).join('')
}

/**
 * 显示推荐卡片骨架屏
 */
function showRecommendationsSkeleton() {
  const grid = document.getElementById('recommendations-grid')
  if (!grid) return

  grid.innerHTML = Array(6).fill(0).map(() => `
    <div class="recommendation-skeleton">
      <div class="skeleton skeleton-header"></div>
      <div class="skeleton skeleton-content"></div>
      <div class="skeleton skeleton-text" style="width: 60%"></div>
    </div>
  `).join('')
}

/**
 * 显示列表骨架屏
 */
function showListSkeleton(containerId, count = 5) {
  showSkeleton(containerId, 'list', count)
}

// 统一错误处理函数
function handleError(error, context = "") {
  console.error(`错误 [${context}]:`, error)

  let message = "操作失败"
  if (typeof error === "string") {
    message = error
  } else if (error && error.message) {
    message = error.message
  } else if (error && error.response && error.response.data && error.response.data.message) {
    message = error.response.data.message
  }

  showToast(message, "error")
}

// Toast消息显示函数（增强版）
function showToast(message, type = "success", duration = 3000) {
  // 移除已有的toast
  const existingToasts = document.querySelectorAll(".toast")
  existingToasts.forEach(t => t.remove())

  const toast = document.createElement("div")
  toast.className = `toast ${type}`

  const icons = {
    success: '✓',
    error: '✗',
    info: 'ℹ',
    warning: '⚠'
  }

  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || '•'}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
    <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    <div class="toast-progress"></div>
  `

  document.body.appendChild(toast)

  // 添加入场动画
  requestAnimationFrame(() => toast.classList.add('show'))

  // 自动移除
  const timeoutId = setTimeout(() => {
    toast.classList.remove('show')
    toast.classList.add('hide')
    setTimeout(() => toast.remove(), 300)
  }, duration)
}


// 网络状态检测（供需要时显式调用）
function checkNetworkStatus() {
  if (!navigator.onLine) {
    showToast("网络连接已断开，请检查网络设置", "error")
    return false
  }
  return true
}

// 全局错误处理 - 忽略浏览器扩展相关错误
window.addEventListener('error', function(event) {
  // 忽略浏览器扩展相关的错误
  if (event.error && event.error.message &&
      event.error.message.includes('message channel closed')) {
    event.preventDefault()
    return false
  }
})

// Promise错误处理
window.addEventListener('unhandledrejection', function(event) {
  // 忽略浏览器扩展相关的Promise错误
  if (event.reason && event.reason.message &&
      event.reason.message.includes('message channel closed')) {
    event.preventDefault()
    return false
  }
})

// 推荐缓存
let recommendationCache = {
  data: [],
  timestamp: 0,
  algorithm: '',
  totalAvailable: 0,
  displayedCount: 0
}

// ==================== 单词发音功能 ====================

/**
 * 使用 Web Speech API 播放单词发音
 * @param {string} word - 要发音的单词
 * @param {string} lang - 语言代码 (默认 'en-US')
 */
function speakWord(word, lang = 'en-US') {
  if (!word || !('speechSynthesis' in window)) {
    console.warn('浏览器不支持语音合成')
    return
  }

  // 取消之前的发音
  window.speechSynthesis.cancel()

  const utterance = new SpeechSynthesisUtterance(word)
  utterance.lang = lang
  utterance.rate = 0.9  // 稍慢一点更清晰
  utterance.pitch = 1

  // 尝试使用更自然的声音
  const voices = window.speechSynthesis.getVoices()
  const englishVoice = voices.find(v => v.lang.startsWith('en'))
  if (englishVoice) {
    utterance.voice = englishVoice
  }

  window.speechSynthesis.speak(utterance)
}

/**
 * 添加发音按钮到单词卡片
 * @param {HTMLElement} container - 包含单词的容器
 * @param {string} word - 要发音的单词
 */
function addPronunciationButton(container, word) {
  if (!container || !word) return

  // 检查是否已有发音按钮
  if (container.querySelector('.pronunciation-btn')) return

  const btn = document.createElement('button')
  btn.className = 'pronunciation-btn'
  btn.innerHTML = '🔊'
  btn.title = '播放发音'
  btn.onclick = (e) => {
    e.stopPropagation()
    speakWord(word)
  }

  container.appendChild(btn)
}

// 预加载语音引擎
if ('speechSynthesis' in window) {
  window.speechSynthesis.getVoices()
  window.speechSynthesis.onvoiceschanged = () => {
    window.speechSynthesis.getVoices()
  }
}

// ==================== 学习报告导出 ====================

/**
 * 导出学习报告为 JSON 文件
 */
async function exportLearningReport() {
  if (!currentUser?.id) {
    showToast('请先登录', 'error')
    return
  }

  showLoading()
  try {
    // 获取学习统计
    const [progressRes, statsRes] = await Promise.all([
      apiRequest(`/learning/progress/${currentUser.id}`),
      apiRequest(`/learning/statistics/${currentUser.id}`)
    ])

    const report = {
      exportDate: new Date().toISOString(),
      user: currentUser.username,
      progress: progressRes.data || {},
      statistics: statsRes.data || {}
    }

    // 创建下载
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `smartvocab-report-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    hideLoading()
    showToast('报告导出成功', 'success')
  } catch (err) {
    hideLoading()
    showToast('导出失败: ' + err.message, 'error')
  }
}

/**
 * 导出收藏单词为 CSV
 */
async function exportFavoritesCSV() {
  if (!currentUser?.id) {
    showToast('请先登录', 'error')
    return
  }

  showLoading()
  try {
    const result = await apiRequest(`/favorites/${currentUser.id}`)
    const favorites = result.data?.favorites || []

    if (favorites.length === 0) {
      hideLoading()
      showToast('暂无收藏单词', 'warning')
      return
    }

    // CSV 头
    const headers = ['单词', '音标', '翻译', '难度', '收藏时间']
    const rows = favorites.map(f => [
      f.word || '',
      f.phonetic || '',
      f.translation || '',
      f.difficulty_level || '',
      f.created_at || ''
    ])

    // 构建 CSV 内容
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    ].join('\n')

    // 添加 BOM 以支持中文
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `smartvocab-favorites-${new Date().toISOString().split('T')[0]}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    hideLoading()
    showToast(`已导出 ${favorites.length} 个单词`, 'success')
  } catch (err) {
    hideLoading()
    showToast('导出失败: ' + err.message, 'error')
  }
}

// ==================== 原有缓存代码 ====================

// 推荐缓存持续时间（5分钟）
const CACHE_DURATION = 5 * 60 * 1000

// 通用 API 缓存
const apiCache = new Map()
const API_CACHE_TTL = 2 * 60 * 1000 // 2分钟

// 缓存工具函数
function getCachedApi(key) {
  const cached = apiCache.get(key)
  if (cached && Date.now() - cached.timestamp < API_CACHE_TTL) {
    return cached.data
  }
  return null
}

function setCachedApi(key, data) {
  apiCache.set(key, { data, timestamp: Date.now() })
}

function invalidateUserCache(userId) {
  // 清除与用户相关的缓存
  for (const key of apiCache.keys()) {
    if (key.includes(`/learning/${userId}`) ||
        key.includes(`/recommendations/${userId}`) ||
        key.includes(`/statistics/${userId}`)) {
      apiCache.delete(key)
    }
  }
}

// 防抖函数
function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// 节流函数
function throttle(func, limit) {
  let inThrottle
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args)
      inThrottle = true
      setTimeout(() => inThrottle = false, limit)
    }
  }
}

// 清除推荐缓存（学习完成后调用）
function clearRecommendationCache() {
  recommendationCache = {
    data: [],
    timestamp: 0,
    algorithm: '',
    totalAvailable: 0,
    displayedCount: 0
  }
}



function showPage(pageName) {
  document.querySelectorAll(".page").forEach((page) => {
    page.classList.remove("active")
  })
  const targetPage = document.getElementById(`${pageName}-page`)
  if (targetPage) {
    targetPage.classList.add("active")
  }

  const appNav = document.getElementById("app-navbar")
  if (appNav) {
    const hideMainNav = pageName === "auth" || pageName === "learning"
    appNav.classList.toggle("hidden", hideMainNav)
    if (!hideMainNav) {
      appNav.querySelectorAll(".nav-link[data-page]").forEach((link) => {
        link.classList.toggle("active", link.dataset.page === pageName)
      })
    }
    const menuWrap = document.getElementById("app-nav-menu")
    const toggle = document.getElementById("nav-menu-toggle")
    if (menuWrap) menuWrap.classList.remove("nav-menu-wrap--open")
    if (toggle) {
      toggle.setAttribute("aria-expanded", "false")
    }
  }
}


// 认证相关功能
function initAuth() {
  const tabBtns = document.querySelectorAll(".tab-btn")
  const loginForm = document.getElementById("login-form")
  const registerForm = document.getElementById("register-form")

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab
      tabBtns.forEach((b) => b.classList.remove("active"))
      btn.classList.add("active")

      if (tab === "login") {
        loginForm.classList.add("active")
        registerForm.classList.remove("active")
      } else {
        loginForm.classList.remove("active")
        registerForm.classList.add("active")
      }
    })
  })

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault()
    const username = document.getElementById("login-username").value
    const password = document.getElementById("login-password").value
    const loginError = document.getElementById("login-error")

    // 清除之前的错误信息
    loginError.classList.remove("show")
    loginError.textContent = ""

    showLoading()
    try {
      const result = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      })
      hideLoading()

      if (result.success) {
        // 存储 JWT token
        if (result.data.token) {
          setToken(result.data.token)
        }
        currentUser = { id: result.data.user_id, username: result.data.username }
        localStorage.setItem("currentUser", JSON.stringify(currentUser))
        showToast("登录成功！")
        showPage("dashboard")
        loadDashboard()
      } else {
        const errorMsg = result.message || "登录失败"
        loginError.textContent = errorMsg
        loginError.classList.add("show")
        showToast(errorMsg, "error")
      }
    } catch (error) {
      hideLoading()
      const errorMsg = error.message || "登录失败"
      loginError.textContent = errorMsg
      loginError.classList.add("show")
      handleError(error, "登录")
    }
  })

  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault()
    const username = document.getElementById("register-username").value
    const password = document.getElementById("register-password").value
    const email = document.getElementById("register-email").value
    const registerError = document.getElementById("register-error")

    // 清除之前的错误信息
    registerError.classList.remove("show")
    registerError.textContent = ""

    showLoading()
    try {
      const result = await apiRequest("/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, password, email }),
      })
      hideLoading()

      if (result.success) {
        // 注册成功后自动登录
        if (result.data.token) {
          setToken(result.data.token)
          currentUser = { id: result.data.user_id, username: result.data.username }
          localStorage.setItem("currentUser", JSON.stringify(currentUser))
          showToast("注册成功！")
          showPage("dashboard")
          loadDashboard()
        } else {
          showToast("注册成功！请登录")
          document.querySelector('[data-tab="login"]').click()
          registerForm.reset()
        }
      } else {
        const errorMsg = result.message || "注册失败"
        registerError.textContent = errorMsg
        registerError.classList.add("show")
        showToast(errorMsg, "error")
      }
    } catch (error) {
      hideLoading()
      const errorMsg = error.message || "注册失败"
      registerError.textContent = errorMsg
      registerError.classList.add("show")
      handleError(error, "注册")
    }
  })

  // 检查是否已登录
  const savedUser = localStorage.getItem("currentUser")
  if (savedUser) {
    try {
      currentUser = JSON.parse(savedUser)
      // 验证用户数据完整性
      if (!currentUser || !currentUser.id || !currentUser.username) {
        console.error("localStorage中的用户数据不完整，清除并重新登录")
        localStorage.removeItem("currentUser")
        currentUser = null
      } else {
        showPage("dashboard")
        loadDashboard()
        
        // 检查是否有活跃的学习会话
        checkActiveSession().then(hasActiveSession => {
          if (hasActiveSession) {
            showToast("检测到未完成的学习会话，是否继续？", "info")
            // 可以添加一个确认对话框
            if (confirm("检测到未完成的学习会话，是否继续学习？")) {
              showPage("learning")
              loadCurrentWord()
            }
          }
        }).catch(error => {
          console.error("检查活跃会话失败:", error)
          // 如果检查会话失败，清除用户状态，要求重新登录
          localStorage.removeItem("currentUser")
          currentUser = null
          showPage("auth")
          showToast("会话验证失败，请重新登录", "error")
        })
      }
    } catch (error) {
      console.error("解析localStorage用户数据失败:", error)
      localStorage.removeItem("currentUser")
      currentUser = null
    }
  }
}

// 仪表板功能
async function loadDashboard() {
  if (!currentUser || !currentUser.id) {
    console.error("用户未登录或用户ID无效")
    return
  }

  // 更新用户名显示
  const uname = document.getElementById("username-display")
  if (uname) uname.textContent = currentUser.username

  showLoading()

  try {
    // 加载学习进度
    const progress = await apiRequest(`/learning/progress/${currentUser.id}`)
    if (progress.success) {
      // 使用数字动画效果
      animateNumber(document.getElementById("total-words"), progress.data.total_words)
      animateNumber(document.getElementById("learned-words"), progress.data.learned_words)
      animateNumber(document.getElementById("learning-words"), progress.data.learning_words)

      // 掌握率使用百分比格式
      const masteryEl = document.getElementById("mastery-rate")
      const masteryRate = (progress.data.mastery_rate * 100)
      masteryEl.textContent = masteryRate.toFixed(1) + "%"
      masteryEl.classList.add('count-up-animate')
    }

    // 加载推荐内容
    await loadRecommendations()

    // 加载收藏ID列表
    await loadFavoriteIds()

    // 更新复习数量
    await updateReviewCount()
  } catch (error) {
    handleError(error, "加载仪表板")
  } finally {
    hideLoading()
  }
}

// 更新复习数量
async function updateReviewCount() {
  if (!currentUser?.id) return

  try {
    const result = await apiRequest(`/learning/review-words/${currentUser.id}?limit=100`)
    if (result.success) {
      const reviewCountEl = document.getElementById("review-count")
      if (reviewCountEl) {
        const count = result.data?.words?.length || 0
        reviewCountEl.textContent = count
        if (count > 0) {
          reviewCountEl.classList.add('count-up-animate')
        }
      }
    }
  } catch (e) {
    console.error("获取复习数量失败:", e)
  }
}

async function loadRecommendations(forceRefresh = false) {
  if (!currentUser || !currentUser.id) {
    console.error("用户未登录或用户ID无效")
    return
  }
  
  try {
    // 检查推荐缓存
    const now = Date.now()
    const cacheValid = !forceRefresh && 
                      recommendationCache.data.length > 0 && 
                      (now - recommendationCache.timestamp) < CACHE_DURATION &&
                      recommendationCache.displayedCount < recommendationCache.totalAvailable
    
    if (cacheValid) {
      displayRecommendations(recommendationCache.data.slice(recommendationCache.displayedCount, recommendationCache.displayedCount + 6))
      recommendationCache.displayedCount += 6
      return
    }

    // 第一次加载或强制刷新时，获取50个推荐单词
    const result = await apiRequest(`/recommendations/${currentUser.id}?limit=50&algorithm=mixed`)

    if (result.success) {
      // 缓存所有推荐单词
      recommendationCache = {
        data: result.data,
        timestamp: now,
        algorithm: 'mixed',
        totalAvailable: result.data.length,
        displayedCount: 0
      }
      
      // 显示前6个
      const firstBatch = result.data.slice(0, 6)
      recommendationCache.displayedCount = 6
      displayRecommendations(firstBatch)
    } else {
      handleError(result.message || "获取推荐失败", "推荐")
    }
  } catch (error) {
    handleError(error, "加载推荐")
  }
}

// 显示推荐单词的辅助函数
function displayRecommendations(recommendations) {
  const grid = document.getElementById("recommendations-grid")

  if (recommendations && recommendations.length > 0) {
    grid.innerHTML = ""

    recommendations.forEach((word) => {
      const card = document.createElement("div")
      card.className = "recommendation-card"
      // 使用 escapeHtml 防止 XSS
      card.innerHTML = `
                <h3>${escapeHtml(word.word)}</h3>
                <div class="translation">${escapeHtml(word.translation)}</div>
                <div class="recommendation-reason">${escapeHtml(word.reason || '智能推荐')}</div>
                <div class="meta">
                    <span class="difficulty-badge difficulty-${escapeHtml(String(word.difficulty_level))}">
                        难度 ${escapeHtml(String(word.difficulty_level))}
                    </span>
                    <span>推荐度: ${escapeHtml((word.recommendation_score * 100).toFixed(0))}%</span>
                </div>
            `
      card.addEventListener("click", () => {
        startBrowseLearning(word)
      })
      grid.appendChild(card)
    })
  } else {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📚</div>
        <h3>暂无推荐</h3>
        <p>开始学习后系统会为你推荐合适的单词</p>
      </div>
    `
  }
}

async function startBrowseLearning(startWord) {
  if (!currentUser || !currentUser.id) {
    console.error("用户未登录或用户ID无效")
    return
  }
  
  showLoading()
  
  try {
    // 获取推荐单词列表，增加数量
    const recommendations = await apiRequest(`/recommendations/${currentUser.id}?limit=50&algorithm=mixed`)
    
    if (recommendations.success && recommendations.data.length > 0) {
      // 获取用户已学习的单词ID，过滤掉已浏览过的
      const records = await apiRequest(`/learning/records/${currentUser.id}?limit=1000`)
      const learnedWordIds = new Set()
      if (records.success && records.data.length > 0) {
        records.data.forEach(record => learnedWordIds.add(record.word_id))
      }
      
      // 过滤掉已学习的单词
      browseWords = recommendations.data.filter(word => !learnedWordIds.has(word.id))
      
      if (browseWords.length === 0) {
        showToast("所有推荐单词都已浏览过，请稍后再来！", "info")
        return
      }
      
      browseMode = true
      currentBrowseIndex = browseWords.findIndex(w => w.id === startWord.id)
      
      if (currentBrowseIndex === -1) {
        currentBrowseIndex = 0
      }
      
      showPage("learning")
      loadBrowseWord()
      showToast(`开始浏览式学习，发现${browseWords.length}个新单词`, "success")
    } else {
      showToast("暂无推荐单词", "error")
    }
  } catch (error) {
    handleError(error, "开始浏览学习")
  } finally {
    hideLoading()
  }
}

function loadBrowseWord() {
  if (!browseMode || currentBrowseIndex >= browseWords.length) {
    showBrowseComplete()
    return
  }
  
  const word = browseWords[currentBrowseIndex]
  
  // 浏览模式下不显示进度条
  const progressBar = document.getElementById("learning-progress")
  const statsContainer = document.querySelector(".learning-stats")
  if (progressBar) progressBar.style.display = "none"
  if (statsContainer) statsContainer.style.display = "none"
  
  // 显示单词信息
  document.getElementById("current-word").textContent = word.word
  document.getElementById("word-phonetic").textContent = word.phonetic || ""
  
  // 隐藏选择题、翻译题和拼写题界面
  document.getElementById("choice-section").classList.add("hidden")
  document.getElementById("translation-section").classList.add("hidden")
  const spellingSection = document.getElementById("spelling-section")
  if (spellingSection) spellingSection.classList.add("hidden")
  document.getElementById("feedback-section").classList.add("hidden")
  
  // 显示浏览模式界面
  showBrowseInterface(word)
}

function showBrowseInterface(word) {
  // 创建浏览模式界面
  const browseSection = document.getElementById("browse-section")
  if (!browseSection) {
    const browseDiv = document.createElement("div")
    browseDiv.id = "browse-section"
    browseDiv.className = "browse-section"
    browseDiv.innerHTML = `
      <div class="word-info">
        <div class="word-translation">
          <h3>${word.translation}</h3>
        </div>
        <div class="word-details">
          <div class="detail-item">
            <span class="label">难度等级：</span>
            <span class="difficulty-badge difficulty-${word.difficulty_level}">${word.difficulty_level}</span>
          </div>
          <div class="detail-item">
            <span class="label">推荐度：</span>
            <span class="recommendation-score">${(word.recommendation_score * 100).toFixed(0)}%</span>
          </div>
          <div class="detail-item">
            <span class="label">推荐理由：</span>
            <span class="recommendation-reason">${word.reason || '智能推荐'}</span>
          </div>
        </div>
      </div>
      <div class="browse-actions">
        <button id="mark-learned-btn" class="btn btn-primary">认识</button>
        <button id="mark-unknown-btn" class="btn btn-secondary">不认识</button>
        <button id="finish-browse-btn" class="btn btn-secondary">完成</button>
      </div>
    `
    
    // 插入到单词卡片后面
    const wordCard = document.getElementById("word-card")
    wordCard.appendChild(browseDiv)
  } else {
    // 更新内容
    browseSection.innerHTML = `
      <div class="word-info">
        <div class="word-translation">
          <h3>${word.translation}</h3>
        </div>
        <div class="word-details">
          <div class="detail-item">
            <span class="label">难度等级：</span>
            <span class="difficulty-badge difficulty-${word.difficulty_level}">${word.difficulty_level}</span>
          </div>
          <div class="detail-item">
            <span class="label">推荐度：</span>
            <span class="recommendation-score">${(word.recommendation_score * 100).toFixed(0)}%</span>
          </div>
          <div class="detail-item">
            <span class="label">推荐理由：</span>
            <span class="recommendation-reason">${word.reason || '智能推荐'}</span>
          </div>
        </div>
      </div>
      <div class="browse-actions">
        <button id="mark-learned-btn" class="btn btn-primary">认识</button>
        <button id="mark-unknown-btn" class="btn btn-secondary">不认识</button>
        <button id="finish-browse-btn" class="btn btn-secondary">完成</button>
      </div>
    `
  }
  
  // 添加事件监听
  document.getElementById("mark-learned-btn").addEventListener("click", () => markWordAsLearned(word))
  document.getElementById("mark-unknown-btn").addEventListener("click", () => markWordAsUnknown(word))
  document.getElementById("finish-browse-btn").addEventListener("click", finishBrowse)
}

async function markWordAsLearned(word) {
  try {
    const result = await apiRequest("/vocabulary/submit-answer", {
      method: "POST",
      body: JSON.stringify({
        user_id: currentUser.id,
        word_id: word.id,
        user_answer: word.translation,
        correct_answer: word.translation,
        response_time: 0,
        question_type: "browse",
        mastery_override: 0.2
      })
    })
    
    if (result.success) {
      showToast(`"${word.word}" 已标记为认识 (掌握度: 20%)`, "success")
      // 自动进入下一个单词
      setTimeout(() => {
        nextBrowseWord()
      }, 1000)
    } else {
      showToast("标记失败: " + result.message, "error")
    }
  } catch (error) {
    showToast("标记失败: " + error.message, "error")
  }
}

async function markWordAsUnknown(word) {
  try {
    const result = await apiRequest("/vocabulary/submit-answer", {
      method: "POST",
      body: JSON.stringify({
        user_id: currentUser.id,
        word_id: word.id,
        user_answer: word.translation,
        correct_answer: word.translation,
        response_time: 0,
        question_type: "browse",
        mastery_override: 0.1
      })
    })
    
    if (result.success) {
      showToast(`"${word.word}" 已标记为不认识 (掌握度: 10%)`, "info")
      currentBrowseIndex++
      setTimeout(() => {
        currentBrowseIndex >= browseWords.length ? showBrowseComplete() : loadBrowseWord()
      }, 800)
    } else {
      showToast("标记失败: " + result.message, "error")
    }
  } catch (error) {
    showToast("标记失败: " + error.message, "error")
  }
}

function nextBrowseWord() {
  currentBrowseIndex++
  loadBrowseWord()
}

function showBrowseComplete() {
  document.getElementById("word-card").classList.add("hidden")
  const completeSection = document.getElementById("session-complete")
  completeSection.classList.remove("hidden")

  // 隐藏正确率和用时元素，显示友好提示
  const accuracyContainer = document.getElementById("session-accuracy").parentElement
  const timeContainer = document.getElementById("session-time").parentElement
  accuracyContainer.style.display = "none"
  timeContainer.style.display = "none"

  // 修改完成提示
  const title = completeSection.querySelector("h2")
  if (title) {
    title.textContent = "浏览完成！"
  }

  // 清除浏览模式缓存
  clearRecommendationCache()

  showToast("浏览学习完成！可以继续浏览更多单词", "success")
}

function finishBrowse() {
  browseMode = false
  browseWords = []
  currentBrowseIndex = 0
  
  // 清理浏览界面
  const browseSection = document.getElementById("browse-section")
  if (browseSection) {
    browseSection.remove()
  }
  
  // 恢复进度条显示
  const progressBar = document.getElementById("learning-progress")
  const statsContainer = document.querySelector(".learning-stats")
  if (progressBar) progressBar.style.display = "block"
  if (statsContainer) statsContainer.style.display = "block"
  
  // 重置完成界面显示
  const completeSection = document.getElementById("session-complete")
  const accuracyContainer = document.getElementById("session-accuracy").parentElement
  const timeContainer = document.getElementById("session-time").parentElement
  if (accuracyContainer) accuracyContainer.style.display = "block"
  if (timeContainer) timeContainer.style.display = "block"
  
  showPage("dashboard")
  
  // 浏览完成后强制刷新推荐
  showLoading()
  loadRecommendations(true).then(() => {
    hideLoading()
    showToast("返回首页，推荐已更新", "success")
  })
}


// 检查是否有活跃的学习会话
async function checkActiveSession() {
  if (!currentUser || !currentUser.id) {
    return false
  }
  
  try {
    const result = await apiRequest(`/vocabulary/active-session/${currentUser.id}?session_type=learning`)
    
    if (result.success && result.data) {
      currentSession = result.data
      return true
    } else {
      return false
    }
  } catch (error) {
    console.error("检查活跃会话失败:", error)
    return false
  }
}

/** 安全获取当前学习会话中的单词（避免越界或未定义） */
function getCurrentSessionWord() {
  if (!currentSession?.words?.length) return null
  const idx = currentSession.current_word_index
  if (typeof idx !== "number" || idx < 0 || idx >= currentSession.words.length) return null
  return currentSession.words[idx]
}

// 完成学习会话
async function finishLearningSession() {
  if (currentSession && currentSession.session_id) {
    try {
      await apiRequest("/vocabulary/finish-session", {
        method: "POST",
        body: JSON.stringify({
          session_id: currentSession.session_id
        })
      })
    } catch (error) {
      console.error("完成学习会话失败:", error)
    }
  }
}

async function startLearningSession() {
  const difficultyLevel = Number.parseInt(document.getElementById("difficulty-level").value)
  const wordCount = Number.parseInt(document.getElementById("word-count").value)
  const questionType = document.getElementById("question-type").value

  if (wordCount < 5 || wordCount > 50) {
    showToast("单词数量应在5-50之间", "error")
    return
  }

  showLoading()
  const result = await apiRequest("/vocabulary/start-session", {
    method: "POST",
    body: JSON.stringify({
      user_id: currentUser.id,
      difficulty_level: difficultyLevel,
      word_count: wordCount,
      question_type: questionType,
    }),
  })
  hideLoading()

  if (result.success) {
    currentSession = result.data
    sessionStartTime = Date.now()
    correctAnswers = 0
    totalAnswers = 0
    browseMode = false  // 确保不是浏览模式
    showPage("learning")
    loadCurrentWord()
  } else {
    handleError("开始学习失败: " + result.message, "开始学习")
  }
}

async function startReviewSession() {
  showLoading()
  const result = await apiRequest("/vocabulary/start-review-session", {
    method: "POST",
    body: JSON.stringify({
      user_id: currentUser.id,
      word_count: 20,
    }),
  })
  hideLoading()

  if (result.success) {
    currentSession = result.data
    sessionStartTime = Date.now()
    correctAnswers = 0
    totalAnswers = 0
    browseMode = false  // 确保不是浏览模式
    showPage("learning")
    loadCurrentWord()
    showToast(`开始复习，共${currentSession.total_count}个单词`)
  } else {
    showToast("暂无需要复习的单词", "info")
  }
}

async function loadCurrentWord() {
  // 如果是浏览模式，使用浏览模式加载
  if (browseMode) {
    loadBrowseWord()
    return
  }
  
  if (!currentSession) {
    console.error("currentSession is null or undefined")
    handleError("学习会话已结束，请重新开始", "学习会话")
    showPage("dashboard")
    return
  }

  const result = await apiRequest("/vocabulary/current-word", {
    method: "POST",
    body: JSON.stringify({ session_info: currentSession }),
  })

  if (result.success) {
    const word = result.data
    currentSession.currentWordCache = word

    // 记录单词显示开始时间
    wordStartTime = Date.now()

    document.getElementById("current-word").textContent = word.question_type === "spelling" ? "拼写练习" : word.word
    document.getElementById("word-phonetic").textContent = word.question_type === "spelling" ? "" : (word.phonetic || "")

    // 显示例句（如果有）
    updateExampleSection(word)

    // 更新收藏按钮状态
    updateFavoriteButton(word.word_id)

    // 更新进度（避免 total_count 为 0 时出现 NaN）
    const totalForProgress = Math.max(1, Number(currentSession.total_count) || 1)
    const progress = (currentSession.current_word_index / totalForProgress) * 100
    document.getElementById("learning-progress").style.width = progress + "%"
    document.getElementById("current-word-index").textContent = currentSession.current_word_index + 1
    document.getElementById("total-word-count").textContent = currentSession.total_count

    // 根据题目类型显示不同的界面
    if (word.question_type === "choice") {
      showChoiceQuestion(word)
    } else if (word.question_type === "spelling") {
      showSpellingQuestion(word)
    } else {
      showTranslationQuestion(word)
    }

    // 重置反馈
    document.getElementById("feedback-section").classList.add("hidden")
  } else {
    console.error("Failed to load current word:", result.message)
    handleError("加载单词失败: " + result.message, "加载单词")
    showPage("dashboard")
  }
}

function showChoiceQuestion(word) {
  if (!word || !Array.isArray(word.options) || word.options.length === 0) {
    handleError("选择题数据不完整", "加载题目")
    return
  }
  // 隐藏翻译题和拼写题界面
  document.getElementById("translation-section").classList.add("hidden")
  const spellingSection = document.getElementById("spelling-section")
  if (spellingSection) spellingSection.classList.add("hidden")
  
  // 显示选择题界面
  const choiceSection = document.getElementById("choice-section")
  choiceSection.classList.remove("hidden")
  
  // 设置题目
  document.getElementById("choice-question").textContent = word.question
  
  // 设置选项
  const optionsContainer = document.getElementById("choice-options")
  optionsContainer.innerHTML = ""
  
  word.options.forEach((option, index) => {
    const button = document.createElement("button")
    button.className = "choice-option"
    button.textContent = option
    button.onclick = () => selectChoice(option, word)
    optionsContainer.appendChild(button)
  })
}

function showSpellingQuestion(word) {
  document.getElementById("choice-section").classList.add("hidden")
  document.getElementById("translation-section").classList.add("hidden")
  
  const spellingSection = document.getElementById("spelling-section")
  spellingSection.classList.remove("hidden")
  document.getElementById("spelling-question-text").textContent = word.question || `以下释义对应的英文单词是：${word.translation}`
  document.getElementById("spelling-phonetic-hint").textContent = word.phonetic ? `音标：${word.phonetic}` : ""
  document.getElementById("spelling-answer-input").value = ""
  document.getElementById("spelling-answer-input").disabled = false
  document.getElementById("spelling-submit-btn").disabled = false
  document.getElementById("spelling-answer-input").focus()
}

function showTranslationQuestion(word) {
  // 隐藏选择题和拼写题界面
  document.getElementById("choice-section").classList.add("hidden")
  const spellingSection = document.getElementById("spelling-section")
  if (spellingSection) spellingSection.classList.add("hidden")
  
  // 显示翻译题界面
  const translationSection = document.getElementById("translation-section")
  translationSection.classList.remove("hidden")
  
  // 重置输入
  const answerInput = document.getElementById("answer-input")
  answerInput.value = ""
  answerInput.disabled = false
  answerInput.dataset.showedAnswer = "false"  // 重置显示答案标记
  
  document.getElementById("submit-answer-btn").disabled = false
  answerInput.focus()
}

function selectChoice(selectedOption, word) {
  // 禁用所有选项按钮
  const options = document.querySelectorAll(".choice-option")
  options.forEach(option => {
    option.disabled = true
    if (option.textContent === selectedOption) {
      option.classList.add("selected")
    }
  })
  
  // 提交答案
  submitChoiceAnswer(selectedOption, word)
}

async function submitChoiceAnswer(selectedOption, word) {
  if (!currentSession || !currentUser?.id) {
    handleError("会话无效", "提交选择题")
    return
  }
  const wid = word?.word_id ?? word?.id
  if (wid == null) {
    handleError("题目数据无效", "提交选择题")
    return
  }
  const requestData = {
    user_id: currentUser.id,
    word_id: wid,
    user_answer: selectedOption,
    correct_answer: word.correct_answer,
    response_time: 0,
    question_type: "choice",
    session_info: currentSession  // 添加session_info
  }

  const result = await apiRequest("/vocabulary/submit-answer", {
    method: "POST",
    body: JSON.stringify(requestData),
  })

  if (result.success) {
    totalAnswers++
    if (result.is_correct) {
      correctAnswers++
    }

    // 更新session_info（如果后端返回了更新的session_info）
    if (result.session_info) {
      currentSession = result.session_info
    }

    // 显示反馈
    showChoiceFeedback(result, word)
  } else {
    handleError("提交答案失败: " + result.message, "提交答案")
  }
}

function showChoiceFeedback(result, word) {
  const feedbackSection = document.getElementById("feedback-section")
  const feedbackMessage = document.getElementById("feedback-message")
  const correctAnswerDiv = document.getElementById("correct-answer")
  const expected = word?.correct_answer

  feedbackMessage.textContent = result.message
  feedbackMessage.className = "feedback-message " + (result.is_correct ? "correct" : "incorrect")
  
  // 修复：使用result.data.correct_answer而不是result.correct_answer
  const correctAnswer = result.data ? result.data.correct_answer : result.correct_answer
  correctAnswerDiv.textContent = result.is_correct ? "" : `正确答案: ${correctAnswer}`

  feedbackSection.classList.remove("hidden")

  // 高亮正确答案
  const options = document.querySelectorAll(".choice-option")
  options.forEach(option => {
    if (expected != null && option.textContent === expected) {
      option.classList.add("correct-answer")
    }
    if (expected != null && option.textContent !== expected && option.classList.contains("selected")) {
      option.classList.add("wrong-answer")
    }
  })

  // 延迟显示下一个按钮
  setTimeout(() => {
    document.getElementById("next-word-btn").classList.remove("hidden")
  }, 1500)
}

async function submitSpellingAnswer() {
  const userAnswer = document.getElementById("spelling-answer-input").value.trim()
  if (!userAnswer) {
    handleError("请输入英文单词", "答案验证")
    return
  }
  if (!currentSession?.words?.length) {
    handleError("学习会话无效", "提交拼写答案")
    return
  }
  const currentWord = getCurrentSessionWord()
  const spellingData = currentSession.currentWordCache || currentWord
  const wordId = spellingData?.word_id ?? currentWord?.id
  const correctAns = spellingData?.correct_answer ?? currentWord?.word
  if (wordId == null || correctAns == null) {
    handleError("当前单词数据无效，请刷新页面重试", "提交拼写答案")
    return
  }
  const responseTime = (Date.now() - wordStartTime) / 1000
  const requestData = {
    user_id: currentUser.id,
    word_id: wordId,
    user_answer: userAnswer,
    correct_answer: correctAns,
    response_time: responseTime,
    question_type: "spelling",
    session_info: currentSession
  }
  try {
    const result = await apiRequest("/vocabulary/submit-answer", {
      method: "POST",
      body: JSON.stringify(requestData),
    })
    if (result.success) {
      totalAnswers++
      if (result.is_correct) correctAnswers++
      if (result.session_info) currentSession = result.session_info
      const feedbackSection = document.getElementById("feedback-section")
      const feedbackMessage = document.getElementById("feedback-message")
      const correctAnswerDiv = document.getElementById("correct-answer")
      feedbackMessage.textContent = result.message
      feedbackMessage.className = "feedback-message " + (result.is_correct ? "correct" : "incorrect")
      const correctAnswer = result.data ? result.data.correct_answer : result.correct_answer
      correctAnswerDiv.textContent = result.is_correct ? "" : `正确答案: ${correctAnswer}`
      feedbackSection.classList.remove("hidden")
      document.getElementById("spelling-answer-input").disabled = true
      document.getElementById("spelling-submit-btn").disabled = true
      setTimeout(() => {
        document.getElementById("next-word-btn").classList.remove("hidden")
      }, 1500)
    } else {
      handleError(result.message || "提交答案失败", "提交答案")
    }
  } catch (error) {
    handleError(error, "提交拼写答案")
  }
}

async function submitAnswer() {
  // 如果是闯关模式
  if (currentGate && gateSession) {
    submitGateTranslationAnswer()
    return
  }

  const userAnswer = document.getElementById("answer-input").value.trim()
  if (!userAnswer) {
    handleError("请输入答案", "答案验证")
    return
  }

  const currentWord = getCurrentSessionWord()
  if (!currentWord) {
    handleError("当前单词数据无效，请返回首页重新开始", "提交答案")
    return
  }
  
  // 使用单词显示开始时间计算响应时间
  const responseTime = (Date.now() - wordStartTime) / 1000
  
  // 检查是否显示了答案
  const showedAnswer = document.getElementById("answer-input").dataset.showedAnswer === "true"

  const requestData = {
    user_id: currentUser.id,
    word_id: currentWord.id,
    user_answer: userAnswer,
    correct_answer: currentWord.translation,
    response_time: responseTime,
    question_type: "translation",
    showed_answer: showedAnswer,  // 添加标记
    session_info: currentSession  // 添加session_info
  }

  try {
    const result = await apiRequest("/vocabulary/submit-answer", {
      method: "POST",
      body: JSON.stringify(requestData),
    })

    if (result.success) {
      // 只有在没有显示答案的情况下才计入统计
      if (!showedAnswer) {
        totalAnswers++
        if (result.is_correct) {
          correctAnswers++
        }
      }

      // 更新session_info（如果后端返回了更新的session_info）
      if (result.session_info) {
        currentSession = result.session_info
      }

      // 显示反馈
      const feedbackSection = document.getElementById("feedback-section")
      const feedbackMessage = document.getElementById("feedback-message")
      const correctAnswerDiv = document.getElementById("correct-answer")

      let message = result.message
      if (showedAnswer) {
        message = "已显示答案，不计入正确率统计"
      } else {
        // 添加掌握度反馈
        const masteryLevel = result.mastery_level || 0
        const masteryPercent = (masteryLevel * 100).toFixed(0)
        message = `${result.message} (掌握度: ${masteryPercent}%)`
      }
    
    feedbackMessage.textContent = message
    feedbackMessage.className = "feedback-message " + (result.is_correct ? "correct" : "incorrect")
    // 修复：使用result.data.correct_answer而不是result.correct_answer
    const correctAnswer = result.data ? result.data.correct_answer : result.correct_answer
    correctAnswerDiv.textContent = result.is_correct ? "" : `正确答案: ${correctAnswer}`

    feedbackSection.classList.remove("hidden")
    document.getElementById("answer-input").disabled = true
    document.getElementById("submit-answer-btn").disabled = true
    
    // 延迟显示下一个按钮
    setTimeout(() => {
      document.getElementById("next-word-btn").classList.remove("hidden")
    }, 1500)
  } else {
    handleError(result.message || "提交答案失败", "提交答案")
  }
  } catch (error) {
    handleError(error, "提交答案")
  }
}

function nextWord() {
  // 如果是闯关模式
  if (currentGate && gateSession) {
    nextGateWord()
    return
  }

  // 如果是浏览模式，使用浏览模式的下一个
  if (browseMode) {
    nextBrowseWord()
    return
  }
  
  // 清除输入框内容
  const answerInput = document.getElementById("answer-input")
  if (answerInput) {
    answerInput.value = ""
    answerInput.disabled = false
    answerInput.dataset.showedAnswer = "false"  // 重置显示答案标记
  }
  
  // 重置按钮状态
  const submitBtn = document.getElementById("submit-answer-btn")
  if (submitBtn) {
    submitBtn.disabled = false
  }
  
  // 隐藏反馈区域
  const feedbackSection = document.getElementById("feedback-section")
  if (feedbackSection) {
    feedbackSection.classList.add("hidden")
  }
  
  // 隐藏下一个按钮
  const nextBtn = document.getElementById("next-word-btn")
  if (nextBtn) {
    nextBtn.classList.add("hidden")
  }
  
  // 检查是否需要切换到翻译题阶段
  if (currentSession && currentSession.word_stages) {
    const currentWordData = getCurrentSessionWord()
    if (!currentWordData?.id) {
      handleError("当前单词数据无效", "下一题")
      return
    }
    const wordId = currentWordData.id
    const currentStage = currentSession.word_stages[String(wordId)]  // 转换为字符串
    
    if (currentStage === "choice") {
      // 选择题刚完成，切换到翻译题阶段
      loadCurrentWord()  // 重新加载当前单词，会显示翻译题
      return
    }
  }
  
  // 翻译题完成，移动到下一个单词
  currentSession.current_word_index++

  if (currentSession.current_word_index >= currentSession.total_count) {
    showSessionComplete()
  } else {
    loadCurrentWord()
  }
}

function showSessionComplete() {
  document.getElementById("word-card").classList.add("hidden")
  const completeSection = document.getElementById("session-complete")
  completeSection.classList.remove("hidden")

  const accuracy = totalAnswers > 0 ? ((correctAnswers / totalAnswers) * 100).toFixed(1) : 0
  const timeSpent = Math.floor((Date.now() - sessionStartTime) / 1000)

  document.getElementById("session-accuracy").textContent = accuracy + "%"
  document.getElementById("session-time").textContent = timeSpent
}

function finishSession() {
  // 如果是闯关模式
  if (currentGate && gateSession) {
    showGateComplete()
    return
  }

  // 如果是浏览模式，使用浏览模式的完成
  if (browseMode) {
    finishBrowse()
    return
  }

  // 清除推荐缓存（学习完成后）
  clearRecommendationCache()

  // 完成学习会话
  finishLearningSession()
  
  document.getElementById("word-card").classList.remove("hidden")
  document.getElementById("session-complete").classList.add("hidden")
  currentSession = null
  showPage("dashboard")
  
  // 学习完成后强制刷新推荐
  showLoading()
  loadRecommendations(true).then(() => {
    hideLoading()
    showToast("学习完成！推荐已更新！")
  })
}

// 统计功能
async function loadStatistics(days = 7) {
  if (!currentUser || !currentUser.id) {
    console.error("用户未登录或用户ID无效")
    return
  }

  showLoading()

  try {
    // 并行获取本周和14天数据（用于计算上周对比）
    const [thisWeekStats, twoWeeksStats] = await Promise.all([
      apiRequest(`/learning/statistics/${currentUser.id}?days=7`),
      apiRequest(`/learning/statistics/${currentUser.id}?days=14`)
    ])

    if (thisWeekStats.success) {
      document.getElementById("total-reviews").textContent = thisWeekStats.data.total_reviews
      document.getElementById("new-words").textContent = thisWeekStats.data.new_words
      document.getElementById("learned-words-stats").textContent = thisWeekStats.data.learned_words
      document.getElementById("avg-reviews").textContent = thisWeekStats.data.average_reviews_per_day.toFixed(1)
    }

    // 计算周对比数据
    if (thisWeekStats.success && twoWeeksStats.success) {
      const thisWeek = thisWeekStats.data
      const lastWeek = {
        total_reviews: twoWeeksStats.data.total_reviews - thisWeek.total_reviews,
        new_words: twoWeeksStats.data.new_words - thisWeek.new_words
      }

      // 更新对比显示
      document.getElementById("this-week-reviews").textContent = thisWeek.total_reviews
      document.getElementById("last-week-reviews").textContent = lastWeek.total_reviews
      document.getElementById("this-week-words").textContent = thisWeek.new_words
      document.getElementById("last-week-words").textContent = lastWeek.new_words

      // 计算趋势
      updateTrendArrow("reviews-trend", thisWeek.total_reviews, lastWeek.total_reviews)
      updateTrendArrow("words-trend", thisWeek.new_words, lastWeek.new_words)
    }

    // 加载学习记录
    const records = await apiRequest(`/learning/records/${currentUser.id}?limit=10`)
    const recordsList = document.getElementById("records-list")

    if (records.success && records.data.length > 0) {
      recordsList.innerHTML = ""

      records.data.forEach((record) => {
        const item = document.createElement("div")
        item.className = "record-item"
        item.innerHTML = `
                  <div>
                      <span class="record-word">${escapeHtml(record.word)}</span>
                      <span class="record-result ${record.is_correct ? "correct" : "incorrect"}">
                          ${record.is_correct ? "✓ 正确" : "✗ 错误"}
                      </span>
                  </div>
                  <div style="font-size: 12px; color: var(--text-secondary);">
                      ${formatLearningTime(record.created_at)}
                  </div>
              `
        recordsList.appendChild(item)
      })
    } else {
      recordsList.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📝</div>
          <h3>暂无学习记录</h3>
          <p>开始学习后这里会显示你的学习历史</p>
        </div>
      `
    }

    await loadForgettingCurve()
    await loadAdvancedCharts()
  } catch (error) {
    handleError(error, "加载统计")
  } finally {
    hideLoading()
  }
}

// 加载高级图表（使用 Chart.js）
async function loadAdvancedCharts() {
  if (!window.ChartModule || !currentUser?.id) return

  try {
    // 获取学习统计数据
    const statsResult = await apiRequest(`/learning/statistics/${currentUser.id}?days=30`)
    const recordsResult = await apiRequest(`/learning/records/${currentUser.id}?limit=100`)

    if (!statsResult.success) return

    const stats = statsResult.data
    const records = recordsResult.data || []

    // 1. 学习趋势图（最近7天）
    const trendCanvas = document.getElementById('learning-trend-canvas')
    if (trendCanvas) {
      const last7Days = []
      const reviewCounts = []
      const newWordCounts = []

      for (let i = 6; i >= 0; i--) {
        const date = new Date()
        date.setDate(date.getDate() - i)
        const dateStr = date.toISOString().split('T')[0]
        last7Days.push(date.toLocaleDateString('zh-CN', { weekday: 'short' }))

        // 统计当天记录
        const dayRecords = records.filter(r => r.created_at?.startsWith(dateStr))
        reviewCounts.push(dayRecords.length)
        newWordCounts.push(dayRecords.filter(r => r.is_first_learn).length)
      }

      ChartModule.createProgressLineChart('learning-trend-canvas', last7Days, [
        {
          label: '复习次数',
          data: reviewCounts,
          borderColor: ChartModule.COLORS.primary,
          backgroundColor: ChartModule.COLORS.primaryLight
        },
        {
          label: '新学单词',
          data: newWordCounts,
          borderColor: ChartModule.COLORS.secondary,
          backgroundColor: ChartModule.COLORS.secondaryLight
        }
      ])
    }

    // 2. 难度分布图
    const difficultyCanvas = document.getElementById('difficulty-distribution-canvas')
    if (difficultyCanvas && records.length > 0) {
      const difficultyCounts = [0, 0, 0, 0, 0] // 1-5级
      records.forEach(r => {
        const level = Math.max(1, Math.min(5, r.difficulty_level || 3))
        difficultyCounts[level - 1]++
      })

      ChartModule.createDifficultyBarChart(
        'difficulty-distribution-canvas',
        ['入门', '基础', '中级', '进阶', '高级'],
        difficultyCounts
      )
    }

    // 3. 词性分布图
    const posCanvas = document.getElementById('pos-distribution-canvas')
    if (posCanvas && records.length > 0) {
      const posCounts = {}
      const posLabels = { n: '名词', v: '动词', adj: '形容词', adv: '副词', other: '其他' }

      records.forEach(r => {
        const pos = r.pos || 'other'
        posCounts[pos] = (posCounts[pos] || 0) + 1
      })

      const labels = Object.keys(posCounts).map(p => posLabels[p] || p)
      const data = Object.values(posCounts)

      ChartModule.createPosDistributionChart('pos-distribution-canvas', labels, data)
    }

    // 4. 能力雷达图
    const radarCanvas = document.getElementById('mastery-radar-canvas')
    if (radarCanvas) {
      ChartModule.createMasteryRadarChart(
        'mastery-radar-canvas',
        ['词汇量', '掌握率', '复习频率', '新词进度', '稳定性'],
        [
          Math.min(stats.learned_words / 100 * 100, 100),
          Math.min(stats.mastery_rate * 100 || 0, 100),
          Math.min(stats.average_reviews_per_day * 10 || 0, 100),
          Math.min(stats.new_words / 50 * 100 || 0, 100),
          50 // 默认稳定性
        ]
      )
    }
  } catch (e) {
    console.warn('加载高级图表失败:', e)
  }
}

async function loadForgettingCurve() {
  const chartContainer = document.getElementById("forgetting-curve-chart")
  if (!currentUser || !currentUser.id) return

  try {
    const result = await apiRequest(`/learning/forgetting-curve/${currentUser.id}?days=30`)
    if (result.success && result.data && result.data.length > 0) {
      // 使用 Chart.js 绘制遗忘曲线
      const labels = result.data.map(d => d.date.slice(5)) // MM-DD 格式
      const data = result.data.map(d => d.words_to_review)

      if (window.ChartModule) {
        window.ChartModule.createForgettingCurveChart('forgetting-curve-canvas', labels, data)
      } else {
        // 降级为简单的柱状图
        const maxVal = Math.max(...data, 1)
        chartContainer.innerHTML = `
          <div class="forgetting-curve-bars">
            ${result.data.slice(0, 14).map(d => `
              <div class="curve-bar-wrap">
                <div class="curve-bar" style="height: ${(d.words_to_review / maxVal) * 100}%"
                  title="${d.date}: ${d.words_to_review} 词"></div>
                <span class="curve-label">${d.date.slice(5)}</span>
                <span class="curve-value">${d.words_to_review}</span>
              </div>
            `).join('')}
          </div>
        `
      }
    } else {
      chartContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📊</div>
          <h4>暂无复习计划</h4>
          <p>开始学习后，系统将根据记忆曲线生成未来复习计划</p>
        </div>
      `
    }
  } catch (e) {
    chartContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📊</div>
        <h4>加载失败</h4>
        <p>${e.message || '请稍后重试'}</p>
      </div>
    `
  }
}

// 学习计划页
async function loadPlansPage() {
  if (!currentUser?.id) return

  // 加载当前生效计划
  const activeEl = document.getElementById("active-plan-display")

  try {
    const r = await apiRequest(`/plans/${currentUser.id}/active`)
    if (r.success && r.data) {
      activeEl.innerHTML = `
        <div class="plan-card active">
          <div class="plan-card-header">
            <h3>${r.data.plan_name || r.data.dataset_type.toUpperCase() + ' 学习计划'}</h3>
            <span class="badge badge-success">生效中</span>
          </div>
          <div class="plan-card-body">
            <div class="plan-stat">
              <div class="plan-stat-value">${r.data.dataset_type.toUpperCase()}</div>
              <div class="plan-stat-label">词库</div>
            </div>
            <div class="plan-stat">
              <div class="plan-stat-value">${r.data.daily_new_count}</div>
              <div class="plan-stat-label">每日新学</div>
            </div>
            <div class="plan-stat">
              <div class="plan-stat-value">${r.data.daily_review_count}</div>
              <div class="plan-stat-label">每日复习</div>
            </div>
          </div>
          <div class="plan-actions">
            <button class="btn btn-primary btn-sm" onclick="startPlanLearning(${r.data.id})">开始学习</button>
            <button class="btn btn-secondary btn-sm" onclick="deactivatePlan(${r.data.id})">停用计划</button>
          </div>
        </div>
      `
    } else {
      activeEl.innerHTML = `
        <div class="empty-state">
          <p>暂无生效计划，请创建一个新计划</p>
        </div>
      `
    }

    // 加载历史计划列表
    await loadPlansList()
  } catch (e) {
    activeEl.innerHTML = `<p>加载失败: ${e.message}</p>`
  }
}

async function loadPlansList() {
  const listEl = document.getElementById("plans-list")

  try {
    const r = await apiRequest(`/plans/${currentUser.id}?limit=10`)
    if (r.success && r.data && r.data.length > 0) {
      listEl.innerHTML = r.data.map(plan => `
        <div class="plan-card ${plan.is_active ? 'active' : ''}">
          <div class="plan-card-header">
            <h3>${plan.plan_name || plan.dataset_type.toUpperCase() + ' 计划'}</h3>
            ${plan.is_active ? '<span class="badge badge-success">生效中</span>' : '<span class="badge badge-secondary">已停用</span>'}
          </div>
          <div class="plan-card-body">
            <div class="plan-stat">
              <div class="plan-stat-value">${plan.dataset_type.toUpperCase()}</div>
              <div class="plan-stat-label">词库</div>
            </div>
            <div class="plan-stat">
              <div class="plan-stat-value">${plan.daily_new_count}</div>
              <div class="plan-stat-label">每日新学</div>
            </div>
            <div class="plan-stat">
              <div class="plan-stat-value">${plan.daily_review_count}</div>
              <div class="plan-stat-label">每日复习</div>
            </div>
          </div>
          <div class="plan-actions">
            ${!plan.is_active ? `<button class="btn btn-primary btn-sm" onclick="activatePlan(${plan.id})">启用</button>` : ''}
            <button class="btn btn-secondary btn-sm" data-plan-id="${plan.id}" data-plan-name="${escapeHtml(plan.plan_name || '')}" data-dataset-type="${escapeHtml(plan.dataset_type)}" data-daily-new="${plan.daily_new_count}" data-daily-review="${plan.daily_review_count}" onclick="editPlanFromButton(this)">编辑</button>
            <button class="btn btn-secondary btn-sm" onclick="deletePlan(${plan.id})">删除</button>
          </div>
        </div>
      `).join("")
    } else {
      listEl.innerHTML = `
        <div class="empty-state">
          <p>暂无历史计划</p>
        </div>
      `
    }
  } catch (e) {
    listEl.innerHTML = `<p>加载失败: ${e.message}</p>`
  }
}

async function activatePlan(planId) {
  showLoading()
  const r = await apiRequest(`/plans/${planId}`, {
    method: "PUT",
    body: JSON.stringify({ is_active: true })
  })
  hideLoading()

  if (r.success) {
    showToast("计划已启用")
    loadPlansPage()
  } else {
    showToast(r.message || "启用失败", "error")
  }
}

async function deactivatePlan(planId) {
  showLoading()
  const r = await apiRequest(`/plans/${planId}`, {
    method: "PUT",
    body: JSON.stringify({ is_active: false })
  })
  hideLoading()

  if (r.success) {
    showToast("计划已停用")
    loadPlansPage()
  } else {
    showToast(r.message || "停用失败", "error")
  }
}

async function deletePlan(planId) {
  const confirmed = await showConfirm('确定要删除这个计划吗？此操作不可撤销。', {
    title: '删除计划',
    type: 'danger',
    confirmText: '删除'
  })

  if (!confirmed) return

  showLoading()
  const r = await apiRequest(`/plans/${planId}`, {
    method: "DELETE"
  })
  hideLoading()

  if (r.success) {
    showToast("计划已删除")
    loadPlansPage()
  } else {
    showToast(r.message || "删除失败", "error")
  }
}

// 从按钮读取数据并打开编辑弹窗（安全，避免 XSS）
function editPlanFromButton(btn) {
  const planId = parseInt(btn.dataset.planId)
  const planName = btn.dataset.planName || ''
  const datasetType = btn.dataset.datasetType || ''
  const dailyNew = parseInt(btn.dataset.dailyNew) || 20
  const dailyReview = parseInt(btn.dataset.dailyReview) || 20
  editPlan(planId, planName, datasetType, dailyNew, dailyReview)
}

// 编辑计划
async function editPlan(planId, planName, datasetType, dailyNew, dailyReview) {
  // 创建编辑表单弹窗
  const modal = document.createElement("div")
  modal.className = "modal-overlay"
  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <h3>编辑计划</h3>
        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label>计划名称</label>
          <input type="text" id="edit-plan-name" value="${escapeHtml(planName)}" placeholder="可选">
        </div>
        <div class="form-group">
          <label>词库类型</label>
          <input type="text" value="${escapeHtml(datasetType)}" disabled>
        </div>
        <div class="form-group">
          <label>每日新学单词数</label>
          <input type="number" id="edit-plan-daily-new" value="${dailyNew}" min="5" max="100">
        </div>
        <div class="form-group">
          <label>每日复习单词数</label>
          <input type="number" id="edit-plan-daily-review" value="${dailyReview}" min="5" max="100">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">取消</button>
        <button class="btn btn-primary" id="save-edit-plan-btn">保存</button>
      </div>
    </div>
  `
  document.body.appendChild(modal)

  // 绑定保存按钮
  document.getElementById("save-edit-plan-btn").addEventListener("click", async () => {
    const newName = document.getElementById("edit-plan-name").value.trim()
    const newDailyNew = parseInt(document.getElementById("edit-plan-daily-new").value) || 20
    const newDailyReview = parseInt(document.getElementById("edit-plan-daily-review").value) || 20

    showLoading()
    const r = await apiRequest(`/plans/${planId}`, {
      method: "PUT",
      body: JSON.stringify({
        plan_name: newName || null,
        daily_new_count: newDailyNew,
        daily_review_count: newDailyReview
      })
    })
    hideLoading()

    if (r.success) {
      showToast("计划已更新")
      modal.remove()
      loadPlansPage()
    } else {
      showToast(r.message || "更新失败", "error")
    }
  })
}

// 按计划开始学习
async function startPlanLearning(planId) {
  if (!currentUser?.id) return

  showLoading()
  try {
    // 如果指定了planId，先激活该计划
    if (planId) {
      const activateResult = await apiRequest(`/plans/${planId}`, {
        method: "PUT",
        body: JSON.stringify({ is_active: true })
      })
      if (!activateResult.success) {
        hideLoading()
        showToast(activateResult.message || "激活计划失败", "error")
        return
      }
    }

    const r = await apiRequest(`/plans/${currentUser.id}/start-learning`, {
      method: "POST"
    })
    hideLoading()

    if (r.success && r.data) {
      const { words, plan, dataset_type } = r.data

      if (!words || words.length === 0) {
        showToast("该词库暂无可用单词", "error")
        return
      }

      // 创建学习会话
      currentSession = {
        user_id: currentUser.id,
        words: words,
        current_word_index: 0,
        correct_count: 0,
        total_count: words.length,
        start_time: Date.now(),
        session_type: "plan",
        question_type: "mixed",
        word_stages: {},
        plan_info: plan
      }

      browseMode = false
      sessionStartTime = Date.now()
      correctAnswers = 0
      totalAnswers = 0

      showPage("learning")
      loadCurrentWord()
      showToast(`开始学习 ${dataset_type.toUpperCase()} 词库，共 ${words.length} 词`, "success")
    } else {
      showToast(r.message || "开始学习失败", "error")
    }
  } catch (e) {
    hideLoading()
    showToast(e.message || "开始学习失败", "error")
  }
}

// 个人中心页面
async function loadProfilePage() {
  if (!currentUser?.id) return

  showLoading()

  try {
    // 加载用户信息
    const profileRes = await apiRequest(`/auth/profile/${currentUser.id}`)
    if (profileRes.success && profileRes.data) {
      const profile = profileRes.data

      // 更新头像
      const avatar = document.getElementById("profile-avatar")
      if (avatar) {
        avatar.textContent = profile.username ? profile.username[0].toUpperCase() : "U"
      }

      // 更新用户信息
      document.getElementById("profile-username").textContent = profile.username || "-"
      document.getElementById("profile-email").textContent = profile.email || "未设置邮箱"

      // 填充编辑表单
      document.getElementById("edit-username").value = profile.username || ""
      document.getElementById("edit-email").value = profile.email || ""
      document.getElementById("edit-realname").value = profile.real_name || ""
      document.getElementById("edit-studentno").value = profile.student_no || ""
    }

    // 加载学习统计
    const progressRes = await apiRequest(`/learning/progress/${currentUser.id}`)
    if (progressRes.success && progressRes.data) {
      document.getElementById("profile-total-words").textContent = progressRes.data.total_words || 0
      document.getElementById("profile-mastered-words").textContent = progressRes.data.learned_words || 0
    }

    // 加载连续学习天数（从统计接口获取）
    const statsRes = await apiRequest(`/learning/statistics/${currentUser.id}?days=30`)
    if (statsRes.success && statsRes.data) {
      // 简化计算：有学习记录的天数
      document.getElementById("profile-streak-days").textContent = statsRes.data.active_days || 0
    }

    // 加载成就
    await loadAchievements()

  } catch (e) {
    showToast("加载个人信息失败: " + e.message, "error")
  } finally {
    hideLoading()
  }
}

async function loadAchievements() {
  if (!currentUser?.id) return

  const grid = document.getElementById("achievements-grid")
  if (!grid) return

  try {
    const r = await apiRequest(`/achievements/${currentUser.id}`)
    if (r.success && r.data) {
      const achievements = r.data
      if (achievements.length === 0) {
        grid.innerHTML = `
          <div class="empty-state">
            <p>暂无成就，开始学习解锁更多成就吧！</p>
          </div>
        `
      } else {
        grid.innerHTML = achievements.map(a => `
          <div class="achievement-card" title="${a.achievement_description || ''}">
            <div class="achievement-icon">${a.icon || '🏆'}</div>
            <div class="achievement-info">
              <div class="achievement-name">${a.achievement_name}</div>
              <div class="achievement-desc">${a.achievement_description || ''}</div>
              <div class="achievement-time">${formatTime(a.earned_at)}</div>
            </div>
          </div>
        `).join("")
      }
    }
  } catch (e) {
    grid.innerHTML = `<p>加载成就失败</p>`
  }
}

function formatTime(timeStr) {
  if (!timeStr) return ""
  try {
    const d = new Date(timeStr)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
  } catch {
    return ""
  }
}

async function saveProfile() {
  if (!currentUser?.id) return

  const email = document.getElementById("edit-email").value.trim()
  const realName = document.getElementById("edit-realname").value.trim()
  const studentNo = document.getElementById("edit-studentno").value.trim()

  showLoading()

  try {
    const r = await apiRequest(`/auth/profile/${currentUser.id}`, {
      method: "PUT",
      body: JSON.stringify({
        email: email || null,
        real_name: realName || null,
        student_no: studentNo || null
      })
    })
    hideLoading()

    if (r.success) {
      showToast("保存成功")
      loadProfilePage()
    } else {
      showToast(r.message || "保存失败", "error")
    }
  } catch (e) {
    hideLoading()
    showToast("保存失败: " + e.message, "error")
  }
}

// 闯关模式页
let currentGate = null
let gateSession = null
let gateCorrectCount = 0
let gateStartTime = null

async function loadLevelsPage() {
  if (!currentUser?.id) return
  const listEl = document.getElementById("levels-gates-list")
  try {
    const [gatesRes, progressRes] = await Promise.all([
      apiRequest("/levels/gates"),
      apiRequest(`/levels/progress/${currentUser.id}`)
    ])
    const gates = gatesRes.success ? gatesRes.data : []
    const progress = progressRes.success ? progressRes.data : []
    const progMap = {}
    progress.forEach(p => { progMap[p.level_gate_id] = p })

    if (gates.length === 0) {
      listEl.innerHTML = `
        <div class="empty-state">
          <p>暂无关卡，请先运行数据库迁移</p>
        </div>
      `
      return
    }

    listEl.innerHTML = gates.map(g => {
      const p = progMap[g.id] || {}
      const isUnlocked = p.is_unlocked || g.gate_order === 1
      const isCompleted = p.is_completed
      const masteredCount = p.mastered_count || 0

      // 难度描述
      const difficultyDesc = getDifficultyDescription(g.difficulty_level)
      const difficultyStars = "★".repeat(g.difficulty_level) + "☆".repeat(6 - g.difficulty_level)

      return `
        <div class="gate-card ${!isUnlocked ? 'locked' : ''} ${isCompleted ? 'completed' : ''}">
          <div class="gate-header">
            <span class="gate-order">第 ${g.gate_order} 关</span>
            <span class="gate-difficulty" data-difficulty="${g.difficulty_level}">
              难度 ${difficultyStars}
            </span>
          </div>
          <h3 class="gate-name">${g.gate_name || '关卡 ' + g.gate_order}</h3>
          <p class="gate-desc">${difficultyDesc} · ${g.word_count} 个单词</p>
          <div class="gate-progress">
            <div class="progress-bar">
              <div class="progress-fill" style="width: ${g.word_count > 0 ? (masteredCount / g.word_count * 100) : 0}%"></div>
            </div>
            <span class="progress-text">${masteredCount}/${g.word_count}</span>
          </div>
          <div class="gate-status">
            ${isCompleted ? '<span class="badge badge-success">🏆 已通关</span>' : ''}
            ${!isUnlocked && g.gate_order > 1 ? '<span class="badge badge-secondary">🔒 需完成上一关</span>' : ''}
          </div>
          <div class="gate-actions">
            ${isUnlocked && !isCompleted ? `<button class="btn btn-primary btn-sm" data-gate-id="${g.id}">🚀 开始闯关</button>` : ''}
            ${isCompleted && isUnlocked ? `<button class="btn btn-secondary btn-sm" data-gate-id="${g.id}">🔄 再次挑战</button>` : ''}
          </div>
        </div>
      `
    }).join("")

    // 绑定闯关按钮事件
    listEl.querySelectorAll("[data-gate-id]").forEach(btn => {
      btn.addEventListener("click", () => startGateLearning(parseInt(btn.dataset.gateId)))
    })
  } catch (e) {
    listEl.innerHTML = `<div class="empty-state"><p>加载失败: ${e.message}</p></div>`
  }
}

async function startGateLearning(gateId) {
  if (!currentUser?.id) return
  showLoading()

  try {
    const result = await apiRequest(`/levels/start/${gateId}`, {
      method: "POST",
      body: JSON.stringify({ user_id: currentUser.id })
    })
    hideLoading()

    if (result.success) {
      currentGate = result.data.gate
      gateSession = result.data.session_info
      gateCorrectCount = 0
      gateStartTime = Date.now()
      browseMode = false

      showPage("learning")
      loadGateWord()
      showToast(`开始闯关：${currentGate.gate_name}`, "success")
    } else {
      showToast(result.message || "启动失败", "error")
    }
  } catch (e) {
    hideLoading()
    showToast(e.message || "启动失败", "error")
  }
}

function loadGateWord() {
  if (!gateSession || gateSession.current_word_index >= gateSession.total_count) {
    showGateComplete()
    return
  }

  const word = gateSession.words[gateSession.current_word_index]

  // 显示进度
  const progressBar = document.getElementById("learning-progress")
  const statsContainer = document.querySelector(".learning-stats")
  if (progressBar) {
    progressBar.style.display = "block"
    const progress = (gateSession.current_word_index / gateSession.total_count) * 100
    progressBar.style.width = progress + "%"
  }
  if (statsContainer) statsContainer.style.display = "block"

  document.getElementById("current-word-index").textContent = gateSession.current_word_index + 1
  document.getElementById("total-word-count").textContent = gateSession.total_count

  // 记录开始时间
  wordStartTime = Date.now()

  // 显示单词
  document.getElementById("current-word").textContent = word.word
  document.getElementById("word-phonetic").textContent = word.phonetic || ""

  // 根据阶段显示题目
  const stage = gateSession.word_stages?.[String(word.id)] || "choice"
  if (stage === "choice") {
    showGateChoiceQuestion(word)
  } else {
    showGateTranslationQuestion(word)
  }

  document.getElementById("feedback-section").classList.add("hidden")
}

async function showGateChoiceQuestion(word) {
  // 获取选择题数据
  document.getElementById("choice-section").classList.remove("hidden")
  document.getElementById("translation-section").classList.add("hidden")
  const spellingSection = document.getElementById("spelling-section")
  if (spellingSection) spellingSection.classList.add("hidden")

  // 显示题目
  document.getElementById("choice-question").textContent = `请选择单词 '${word.word}' 的正确释义：`

  // 简化翻译用于选择题
  const correctAnswer = simplifyTranslation(word.translation)

  // 生成选项（正确答案 + 3个干扰项）
  const options = await generateChoiceOptions(word, correctAnswer)

  const optionsContainer = document.getElementById("choice-options")
  optionsContainer.innerHTML = ""
  options.forEach(option => {
    const button = document.createElement("button")
    button.className = "choice-option"
    button.textContent = option
    button.onclick = () => submitGateChoiceAnswer(option, { ...word, correct_answer: correctAnswer })
    optionsContainer.appendChild(button)
  })

  // 缓存当前单词信息
  gateSession.currentWordCache = { ...word, correct_answer: correctAnswer }
}

function simplifyTranslation(translation) {
  if (!translation) return ""
  // 提取第一个主要意思
  const lines = translation.split('\n')
  if (lines.length > 0) {
    const firstLine = lines[0].trim()
    // 提取第一个逗号前的内容
    if (firstLine.includes(',')) {
      return firstLine.split(',')[0].trim()
    }
    return firstLine
  }
  return translation.trim()
}

async function generateChoiceOptions(word, correctAnswer) {
  // 尝试从推荐中获取其他单词作为干扰项
  const otherWords = gateSession.words.filter(w => w.id !== word.id).slice(0, 10)

  if (otherWords.length >= 3) {
    // 随机选择3个作为干扰项
    const shuffled = otherWords.sort(() => Math.random() - 0.5)
    const wrongOptions = shuffled.slice(0, 3).map(w => simplifyTranslation(w.translation))

    // 合并并打乱
    const allOptions = [correctAnswer, ...wrongOptions]
    return allOptions.sort(() => Math.random() - 0.5)
  } else {
    // 使用备用干扰项
    const fallbackOptions = ["n. 时间", "v. 过程", "adj. 重要的", "n. 方法", "v. 开始"]
    const wrongOptions = fallbackOptions.filter(o => o !== correctAnswer).slice(0, 3)
    const allOptions = [correctAnswer, ...wrongOptions]
    return allOptions.sort(() => Math.random() - 0.5)
  }
}

async function submitGateChoiceAnswer(selectedOption, wordData) {
  const responseTime = (Date.now() - wordStartTime) / 1000

  const result = await apiRequest("/vocabulary/submit-answer", {
    method: "POST",
    body: JSON.stringify({
      user_id: currentUser.id,
      word_id: wordData.id || wordData.word_id,
      user_answer: selectedOption,
      correct_answer: wordData.correct_answer,
      response_time: responseTime,
      question_type: "choice",
      session_info: gateSession
    })
  })

  if (result.success) {
    if (result.is_correct) {
      gateCorrectCount++
    }
    showGateFeedback(result, wordData)
  }
}

function showGateTranslationQuestion(word) {
  document.getElementById("choice-section").classList.add("hidden")
  document.getElementById("translation-section").classList.remove("hidden")
  const spellingSection = document.getElementById("spelling-section")
  if (spellingSection) spellingSection.classList.add("hidden")

  const answerInput = document.getElementById("answer-input")
  answerInput.value = ""
  answerInput.disabled = false
  answerInput.dataset.showedAnswer = "false"
  document.getElementById("submit-answer-btn").disabled = false
  answerInput.focus()
}

async function submitGateTranslationAnswer() {
  const userAnswer = document.getElementById("answer-input").value.trim()
  if (!userAnswer) {
    showToast("请输入答案", "error")
    return
  }

  const word = gateSession.words[gateSession.current_word_index]
  const responseTime = (Date.now() - wordStartTime) / 1000

  const result = await apiRequest("/vocabulary/submit-answer", {
    method: "POST",
    body: JSON.stringify({
      user_id: currentUser.id,
      word_id: word.id,
      user_answer: userAnswer,
      correct_answer: word.translation,
      response_time: responseTime,
      question_type: "translation",
      session_info: gateSession
    })
  })

  if (result.success) {
    if (result.is_correct) {
      gateCorrectCount++
    }
    showGateFeedback(result, { ...word, correct_answer: word.translation })
  }
}

function showGateFeedback(result, wordData) {
  const feedbackSection = document.getElementById("feedback-section")
  const feedbackMessage = document.getElementById("feedback-message")
  const correctAnswerDiv = document.getElementById("correct-answer")

  feedbackMessage.textContent = result.message
  feedbackMessage.className = "feedback-message " + (result.is_correct ? "correct" : "incorrect")
  correctAnswerDiv.textContent = result.is_correct ? "" : `正确答案: ${wordData.correct_answer}`

  feedbackSection.classList.remove("hidden")

  // 禁用输入
  const answerInput = document.getElementById("answer-input")
  if (answerInput) answerInput.disabled = true
  document.getElementById("submit-answer-btn").disabled = true

  // 高亮选择题选项
  const options = document.querySelectorAll(".choice-option")
  options.forEach(option => {
    option.disabled = true
    if (option.textContent === wordData.correct_answer) {
      option.classList.add("correct-answer")
    }
    if (!result.is_correct && option.classList.contains("selected")) {
      option.classList.add("wrong-answer")
    }
  })

  setTimeout(() => {
    document.getElementById("next-word-btn").classList.remove("hidden")
  }, 1500)
}

function nextGateWord() {
  // 清理
  const answerInput = document.getElementById("answer-input")
  if (answerInput) {
    answerInput.value = ""
    answerInput.disabled = false
    answerInput.dataset.showedAnswer = "false"
  }
  document.getElementById("submit-answer-btn").disabled = false
  document.getElementById("feedback-section").classList.add("hidden")
  document.getElementById("next-word-btn").classList.add("hidden")
  document.getElementById("choice-section").classList.add("hidden")
  document.getElementById("translation-section").classList.remove("hidden")

  gateSession.current_word_index++

  if (gateSession.current_word_index >= gateSession.total_count) {
    showGateComplete()
  } else {
    loadGateWord()
  }
}

async function showGateComplete() {
  // 提交关卡完成
  const result = await apiRequest(`/levels/complete/${currentGate.id}`, {
    method: "POST",
    body: JSON.stringify({
      user_id: currentUser.id,
      correct_count: gateCorrectCount,
      total_count: gateSession.total_count
    })
  })

  const accuracy = gateSession.total_count > 0 ? (gateCorrectCount / gateSession.total_count * 100).toFixed(1) : 0
  const timeSpent = Math.floor((Date.now() - gateStartTime) / 1000)

  document.getElementById("word-card").classList.add("hidden")
  const completeSection = document.getElementById("session-complete")
  completeSection.classList.remove("hidden")

  document.getElementById("session-accuracy").textContent = accuracy + "%"
  document.getElementById("session-time").textContent = timeSpent

  const title = completeSection.querySelector("h2")
  if (title) {
    title.textContent = result.data?.is_completed ? "🎉 通关成功！" : "继续努力！"
  }

  // 清理状态
  currentGate = null
  gateSession = null
  gateCorrectCount = 0

  showToast(result.data?.is_completed ? "恭喜通关！已解锁下一关" : "再接再厉！", result.data?.is_completed ? "success" : "info")
}

// 等级测试
let evalPaperId = null
let evalQuestions = []
let evalAnswers = {}
let evalStartTime = null

async function loadEvaluationStart() {
  if (!currentUser?.id) return
  document.getElementById("evaluation-start").classList.remove("hidden")
  document.getElementById("evaluation-test").classList.add("hidden")
  document.getElementById("evaluation-result").classList.add("hidden")
}

async function startEvaluation() {
  if (!currentUser?.id) return
  const count = parseInt(document.getElementById("eval-question-count").value) || 10
  showLoading()
  try {
    const r = await apiRequest("/evaluation/start", {
      method: "POST",
      body: JSON.stringify({ user_id: currentUser.id, question_count: count })
    })
    hideLoading()
    if (!r.success || !r.data) {
      showToast(r.message || "启动失败", "error")
      return
    }
    evalPaperId = r.data.paper_id
    evalQuestions = r.data.questions || []
    evalAnswers = {}
    evalStartTime = Date.now()
    document.getElementById("evaluation-start").classList.add("hidden")
    document.getElementById("evaluation-result").classList.add("hidden")
    document.getElementById("evaluation-test").classList.remove("hidden")
    renderEvalQuestions()
  } catch (e) {
    hideLoading()
    showToast(e.message || "启动失败", "error")
  }
}

function renderEvalQuestions() {
  const container = document.getElementById("eval-questions-container")
  document.getElementById("eval-progress").textContent = `1/${evalQuestions.length}`
  const escape = s => String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;")
  container.innerHTML = evalQuestions.map((q, i) => {
    const wid = q.word_id || q.id
    const isChoice = (q.question_type === "choice" || q.question_type === "multiple_choice") && q.options && q.options.length
    const isSpelling = q.question_type === "spelling"
    const placeholder = isSpelling ? "请输入英文单词" : "请输入中文释义"
    const inputHtml = isChoice
      ? q.options.map(opt => `<label><input type="radio" name="q_${wid}" value="${escape(opt)}"> ${escape(opt)}</label>`).join("<br>")
      : `<input type="text" id="q_${wid}" placeholder="${placeholder}">`
    return `
      <div class="eval-question" data-index="${i}">
        <h4>${escape(q.question || "请选择/输入 " + (q.word || "") + " 的释义")}</h4>
        ${inputHtml}
      </div>
    `
  }).join("")
}

async function submitEvaluation() {
  if (!evalPaperId || !currentUser?.id) return
  const answers = evalQuestions.map(q => {
    const wid = q.word_id || q.id
    const radio = document.querySelector(`input[name="q_${wid}"]:checked`)
    const textInp = document.getElementById(`q_${wid}`)
    const userAnswer = radio ? radio.value : (textInp ? textInp.value.trim() : "")
    return {
      word_id: wid,
      user_answer: userAnswer,
      correct_answer: q.correct_answer
    }
  })
  const duration = Math.floor((Date.now() - evalStartTime) / 1000)
  showLoading()
  try {
    const r = await apiRequest("/evaluation/submit", {
      method: "POST",
      body: JSON.stringify({
        user_id: currentUser.id,
        paper_id: evalPaperId,
        answers,
        duration_seconds: duration
      })
    })
    hideLoading()
    if (r.success && r.data) {
      document.getElementById("evaluation-test").classList.add("hidden")
      const sc = typeof r.data.score === "number" ? r.data.score : 0
      document.getElementById("eval-score").textContent = Number.isFinite(sc) ? sc.toFixed(0) : "-"
      document.getElementById("eval-correct").textContent = r.data.correct_count ?? "-"
      document.getElementById("eval-total").textContent = r.data.total_count ?? "-"
      document.getElementById("eval-level").textContent = r.data.assessed_level || "-"
      document.getElementById("evaluation-result").classList.remove("hidden")
    } else {
      showToast(r.message || "提交失败", "error")
    }
  } catch (e) {
    hideLoading()
    showToast(e.message || "提交失败", "error")
  }
}

// 更新趋势箭头
function updateTrendArrow(elementId, current, previous) {
  const el = document.getElementById(elementId)
  if (!el) return

  const diff = current - previous
  if (diff > 0) {
    el.textContent = `↑ +${diff}`
    el.className = "comparison-arrow up"
  } else if (diff < 0) {
    el.textContent = `↓ ${diff}`
    el.className = "comparison-arrow down"
  } else {
    el.textContent = "→ 0"
    el.className = "comparison-arrow same"
  }
}

// 时间格式化函数
function formatLearningTime(timeString) {
  try {
    // 处理时间字符串，确保正确解析
    let date
    if (typeof timeString === 'string') {
      // 如果是ISO格式字符串，直接解析
      if (timeString.includes('T') || timeString.includes('Z')) {
        date = new Date(timeString)
      } else {
        // 如果是其他格式，尝试解析
        date = new Date(timeString)
      }
    } else {
      date = new Date(timeString)
    }
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      return '时间格式错误'
    }
    
    // 使用本地时间格式化，避免时区问题
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    
    return `${year}-${month}-${day} ${hours}:${minutes}`
  } catch (error) {
    console.error('时间格式化错误:', error, '原始时间:', timeString)
    return '时间显示错误'
  }
}

// 通用退出登录函数
function logout() {
  currentUser = null
  currentSession = null
  clearToken()
  localStorage.removeItem("currentUser")
  showPage("auth")
  showToast("已退出登录")
}

// 监听认证过期事件
window.addEventListener('auth:logout', (event) => {
  currentUser = null
  currentSession = null
  showPage("auth")
  showToast("登录已过期，请重新登录", "error")
})

// 页面懒加载状态
const pageLoaded = new Set()

// 事件监听器
function initEventListeners() {
  // 使用事件委托处理所有导航链接
  document.addEventListener("click", (e) => {
    // 检查点击的是否为导航链接
    if (e.target.classList.contains("nav-link")) {
      e.preventDefault()
      const page = e.target.dataset.page

      // 更新所有导航链接的active状态
      document.querySelectorAll(".nav-link").forEach((l) => l.classList.remove("active"))
      e.target.classList.add("active")

      showPage(page)

      // 懒加载：只在首次访问时加载页面数据
      if (!pageLoaded.has(page)) {
        pageLoaded.add(page)
        switch (page) {
          case "statistics":
            loadStatistics()
            break
          case "dashboard":
            loadDashboard()
            updateReviewCount()
            break
          case "plans":
            loadPlansPage()
            break
          case "levels":
            loadLevelsPage()
            break
          case "evaluation":
            loadEvaluationStart()
            break
          case "profile":
            loadProfilePage()
            break
          case "favorites":
            loadFavoritesPage()
            break
        }
      }
      // learning页面只能通过功能按钮进入，不能通过导航进入
    }
  })

  // 退出登录
  document.getElementById("logout-btn").addEventListener("click", logout)

  const navToggle = document.getElementById("nav-menu-toggle")
  const menuWrap = document.getElementById("app-nav-menu")
  if (navToggle && menuWrap) {
    navToggle.addEventListener("click", () => {
      const open = menuWrap.classList.toggle("nav-menu-wrap--open")
      navToggle.setAttribute("aria-expanded", open ? "true" : "false")
    })
  }

  // 刷新推荐
  document.getElementById("refresh-recommendations").addEventListener("click", () => {
    showLoading()
    loadRecommendations(false).then(() => {  // 使用缓存轮转，不强制刷新
      hideLoading()
      showToast("推荐已刷新")
    })
  })

  // 开始学习
  document.getElementById("start-learning-btn").addEventListener("click", startLearningSession)

  document.getElementById("start-review-btn").addEventListener("click", startReviewSession)

  const createPlanBtn = document.getElementById("create-plan-btn")
  if (createPlanBtn) {
    createPlanBtn.addEventListener("click", async () => {
      if (!currentUser?.id) return
      const dataset = document.getElementById("plan-dataset").value
      const dailyNew = parseInt(document.getElementById("plan-daily-new").value) || 20
      const dailyReview = parseInt(document.getElementById("plan-daily-review").value) || 20
      const planName = document.getElementById("plan-name")?.value || ""

      showLoading()
      const r = await apiRequest("/plans", {
        method: "POST",
        body: JSON.stringify({
          user_id: currentUser.id,
          dataset_type: dataset,
          daily_new_count: dailyNew,
          daily_review_count: dailyReview,
          plan_name: planName || `${dataset.toUpperCase()} 学习计划`
        })
      })
      hideLoading()
      if (r.success) {
        showToast("计划创建成功")
        // 清空表单
        document.getElementById("plan-name").value = ""
        loadPlansPage()
      } else {
        showToast(r.message || "创建失败", "error")
      }
    })
  }

  // 刷新计划列表按钮
  const refreshPlansBtn = document.getElementById("refresh-plans-btn")
  if (refreshPlansBtn) {
    refreshPlansBtn.addEventListener("click", () => {
      loadPlansPage()
      showToast("已刷新")
    })
  }

  const startEvalBtn = document.getElementById("start-eval-btn")
  if (startEvalBtn) startEvalBtn.addEventListener("click", startEvaluation)

  const submitEvalBtn = document.getElementById("submit-eval-btn")
  if (submitEvalBtn) submitEvalBtn.addEventListener("click", submitEvaluation)

  const evalAgainBtn = document.getElementById("eval-again-btn")
  if (evalAgainBtn) evalAgainBtn.addEventListener("click", () => {
    loadEvaluationStart()
    document.getElementById("evaluation-start").classList.remove("hidden")
  })

  // 个人中心页面
  const saveProfileBtn = document.getElementById("save-profile-btn")
  if (saveProfileBtn) {
    saveProfileBtn.addEventListener("click", async () => {
      if (!currentUser?.id) return

      const email = document.getElementById("edit-email").value
      const realName = document.getElementById("edit-realname").value
      const studentNo = document.getElementById("edit-studentno").value

      showLoading()
      const r = await apiRequest(`/auth/profile/${currentUser.id}`, {
        method: "PUT",
        body: JSON.stringify({
          email: email || null,
          real_name: realName || null,
          student_no: studentNo || null
        })
      })
      hideLoading()

      if (r.success) {
        showToast("保存成功")
        loadProfilePage()
      } else {
        showToast(r.message || "保存失败", "error")
      }
    })
  }

  // 修改密码按钮
  const changePasswordBtn = document.getElementById("change-password-btn")
  if (changePasswordBtn) {
    changePasswordBtn.addEventListener("click", async () => {
      if (!currentUser?.id) return

      const oldPassword = document.getElementById("old-password").value
      const newPassword = document.getElementById("new-password").value
      const confirmPassword = document.getElementById("confirm-password").value

      // 验证并显示内联错误
      if (!oldPassword) {
        showInlineError(document.getElementById("old-password"), "请输入当前密码")
        return
      }
      if (!newPassword) {
        showInlineError(document.getElementById("new-password"), "请输入新密码")
        return
      }
      if (newPassword.length < 6) {
        showInlineError(document.getElementById("new-password"), "新密码至少需要6个字符")
        return
      }
      if (newPassword !== confirmPassword) {
        showInlineError(document.getElementById("confirm-password"), "两次输入的新密码不一致")
        return
      }

      setButtonLoading(changePasswordBtn, true, "修改中...")

      try {
        const r = await apiRequest(`/auth/password/${currentUser.id}`, {
          method: "PUT",
          body: JSON.stringify({
            old_password: oldPassword,
            new_password: newPassword
          })
        })

        setButtonLoading(changePasswordBtn, false)

        if (r.success) {
          showToast("密码修改成功")
          // 清空密码框
          document.getElementById("old-password").value = ""
          document.getElementById("new-password").value = ""
          document.getElementById("confirm-password").value = ""
        } else {
          showToast(r.message || "密码修改失败", "error")
        }
      } catch (e) {
        setButtonLoading(changePasswordBtn, false)
        showToast("密码修改失败: " + e.message, "error")
      }
    })
  }

  const profileLogoutBtn = document.getElementById("profile-logout-btn")
  if (profileLogoutBtn) {
    profileLogoutBtn.addEventListener("click", logout)
  }

  // 学习页面
  document.getElementById("submit-answer-btn").addEventListener("click", submitAnswer)
  const spellingSubmitBtn = document.getElementById("spelling-submit-btn")
  if (spellingSubmitBtn) {
    spellingSubmitBtn.addEventListener("click", submitSpellingAnswer)
  }
  document.getElementById("next-word-btn").addEventListener("click", nextWord)
  document.getElementById("finish-session-btn").addEventListener("click", finishSession)
  document.getElementById("back-to-dashboard").addEventListener("click", async () => {
    if (currentSession && currentSession.current_word_index < currentSession.total_count) {
      const confirmed = await showConfirm('确定要退出当前学习吗？进度将不会保存。', {
        title: '退出学习',
        type: 'warning',
        confirmText: '确定退出'
      })
      if (confirmed) {
        currentSession = null
        showPage("dashboard")
      }
    } else {
      showPage("dashboard")
    }
  })

  // 发音按钮
  document.getElementById("pronunciation-btn")?.addEventListener("click", () => {
    const word = currentSession?.currentWordCache
    if (word?.word) {
      speakWord(word.word)
    }
  })

  // 收藏按钮
  document.getElementById("favorite-btn")?.addEventListener("click", () => {
    const word = currentSession?.currentWordCache
    if (word) {
      toggleFavorite(word.word_id, word.word, word.translation)
    }
  })

  // 回车提交答案
  document.getElementById("answer-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !document.getElementById("submit-answer-btn").disabled) {
      submitAnswer()
    }
  })
  const spellingInput = document.getElementById("spelling-answer-input")
  if (spellingInput) {
    spellingInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !document.getElementById("spelling-submit-btn").disabled) {
        submitSpellingAnswer()
      }
    })
  }

  // 显示答案
  document.getElementById("show-answer-btn").addEventListener("click", () => {
    const currentWord = getCurrentSessionWord()
    if (!currentWord?.translation) {
      showToast("无法显示答案", "error")
      return
    }
    document.getElementById("answer-input").value = currentWord.translation
    // 标记为显示答案状态，提交时不计入正确率
    document.getElementById("answer-input").dataset.showedAnswer = "true"
  })

  // 统计周期切换
  document.querySelectorAll(".period-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".period-btn").forEach((b) => b.classList.remove("active"))
      btn.classList.add("active")
      const days = Number.parseInt(btn.dataset.days)
      loadStatistics(days)
    })
  })

  // 统计页面刷新按钮
  document.getElementById("refresh-statistics").addEventListener("click", () => {
    const activePeriodBtn = document.querySelector(".period-btn.active")
    const days = activePeriodBtn ? Number.parseInt(activePeriodBtn.dataset.days) : 7
    loadStatistics(days)
    showToast("统计数据已刷新")
  })
}

// 初始化应用
document.addEventListener("DOMContentLoaded", () => {
  initAuth()
  initEventListeners()

  // 添加网络状态监听
  window.addEventListener('online', () => {
    showToast("网络连接已恢复", "success")
  })

  window.addEventListener('offline', () => {
    showToast("网络连接已断开", "error")
  })
})

// 全局函数暴露（供HTML onclick使用）
window.startPlanLearning = startPlanLearning
window.activatePlan = activatePlan
window.deactivatePlan = deactivatePlan
window.deletePlan = deletePlan
window.editPlanFromButton = editPlanFromButton
window.editPlan = editPlan

// ==================== 收藏功能 ====================

// 存储当前用户收藏的单词ID集合
let favoritedWordIds = new Set()

// 加载用户收藏的单词ID列表
async function loadFavoriteIds() {
  const user = getCurrentUser()
  if (!user) return

  try {
    const result = await apiRequest(`/favorites/${user.id}/ids`)
    if (result.success) {
      favoritedWordIds = new Set(result.data.word_ids || [])
    }
  } catch (e) {
    console.error("加载收藏ID失败:", e)
  }
}

// 检查单词是否已收藏
function isWordFavorited(wordId) {
  return favoritedWordIds.has(wordId)
}

// 切换收藏状态
async function toggleFavorite(wordId, word, translation) {
  const user = getCurrentUser()
  if (!user) {
    showToast("请先登录", "error")
    return
  }

  const isFavorited = favoritedWordIds.has(wordId)
  const btn = document.getElementById("favorite-btn")

  try {
    if (isFavorited) {
      // 取消收藏
      const result = await apiRequest(`/favorites/${user.id}/word/${wordId}`, {
        method: "DELETE"
      })
      if (result.success) {
        favoritedWordIds.delete(wordId)
        if (btn) {
          btn.classList.remove("active")
          btn.querySelector(".favorite-icon").textContent = "☆"
        }
        showToast("已取消收藏")
      }
    } else {
      // 添加收藏
      const result = await apiRequest(`/favorites/${user.id}/word/${wordId}`, {
        method: "POST",
        body: JSON.stringify({ note: "" })
      })
      if (result.success) {
        favoritedWordIds.add(wordId)
        if (btn) {
          btn.classList.add("active")
          btn.querySelector(".favorite-icon").textContent = "★"
        }
        showToast("收藏成功 ⭐")
      }
    }
  } catch (e) {
    showToast("操作失败，请重试", "error")
  }
}

// 更新收藏按钮状态
function updateFavoriteButton(wordId) {
  const btn = document.getElementById("favorite-btn")
  if (!btn) return

  const isFavorited = favoritedWordIds.has(wordId)
  btn.classList.toggle("active", isFavorited)
  btn.querySelector(".favorite-icon").textContent = isFavorited ? "★" : "☆"
}

// 加载收藏页面
let allFavorites = [] // 存储所有收藏数据用于筛选

async function loadFavoritesPage() {
  const user = getCurrentUser()
  if (!user) return

  const listEl = document.getElementById("favorites-list")
  const emptyEl = document.getElementById("favorites-empty")
  const totalEl = document.getElementById("favorites-total")

  // 显示骨架屏加载效果
  listEl.innerHTML = createSkeleton('card', 4)
  emptyEl.classList.add("hidden")

  try {
    const result = await apiRequest(`/favorites/${user.id}`)
    if (result.success) {
      allFavorites = result.data.favorites || []
      renderFavorites(allFavorites)
      initFavoritesFilters()
    }
  } catch (e) {
    listEl.innerHTML = '<div class="error-message show">加载失败，请刷新重试</div>'
  }
}

// 渲染收藏列表
function renderFavorites(favorites) {
  const listEl = document.getElementById("favorites-list")
  const emptyEl = document.getElementById("favorites-empty")
  const totalEl = document.getElementById("favorites-total")

  totalEl.textContent = favorites.length

  if (favorites.length === 0) {
    listEl.innerHTML = ""
    emptyEl.classList.remove("hidden")
    return
  }

  listEl.innerHTML = ""
  favorites.forEach((fav, index) => {
    const card = document.createElement("div")
    card.className = "favorite-card list-item-animate"
    card.style.animationDelay = `${index * 0.05}s`
    card.dataset.wordId = fav.word_id
    card.dataset.difficulty = fav.difficulty_level || "0"
    card.dataset.dataset = fav.dataset_type || "other"
    card.innerHTML = `
      <button class="remove-btn" onclick="removeFavoriteFromList(${fav.word_id}, this)">✕</button>
      <div class="word">${escapeHtml(fav.word)}</div>
      <div class="phonetic">${escapeHtml(fav.phonetic || "")}</div>
      <div class="translation">${escapeHtml(fav.translation)}</div>
      ${fav.note ? `<div class="note">${escapeHtml(fav.note)}</div>` : ""}
      <div class="meta">
        <span class="difficulty">难度 ${fav.difficulty_level || "-"}</span>
        <span class="dataset-tag">${fav.dataset_type || "其他"}</span>
        <span class="favorited-at">收藏于 ${fav.favorited_at ? new Date(fav.favorited_at).toLocaleDateString() : "-"}</span>
      </div>
    `
    listEl.appendChild(card)
  })
}

// 初始化筛选器
function initFavoritesFilters() {
  // 难度筛选
  document.querySelectorAll("#difficulty-filters .filter-tag").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#difficulty-filters .filter-tag").forEach(b => b.classList.remove("active"))
      btn.classList.add("active")
      filterFavorites()
    })
  })

  // 词库筛选
  document.querySelectorAll("#dataset-filters .filter-tag").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#dataset-filters .filter-tag").forEach(b => b.classList.remove("active"))
      btn.classList.add("active")
      filterFavorites()
    })
  })
}

// 筛选收藏
function filterFavorites() {
  const difficulty = document.querySelector("#difficulty-filters .filter-tag.active")?.dataset.difficulty || "all"
  const dataset = document.querySelector("#dataset-filters .filter-tag.active")?.dataset.dataset || "all"
  const search = document.getElementById("favorites-search")?.value.toLowerCase() || ""

  const filtered = allFavorites.filter(fav => {
    const matchDifficulty = difficulty === "all" || String(fav.difficulty_level) === difficulty
    const matchDataset = dataset === "all" || fav.dataset_type === dataset
    const matchSearch = !search ||
      (fav.word || "").toLowerCase().includes(search) ||
      (fav.translation || "").toLowerCase().includes(search)
    return matchDifficulty && matchDataset && matchSearch
  })

  renderFavorites(filtered)
}

// 从收藏列表中移除（带动画效果）
async function removeFavoriteFromList(wordId, btnEl) {
  const user = getCurrentUser()
  if (!user) return

  // 获取卡片元素
  const card = btnEl.closest(".favorite-card")

  try {
    const result = await apiRequest(`/favorites/${user.id}/word/${wordId}`, {
      method: "DELETE"
    })
    if (result.success) {
      favoritedWordIds.delete(wordId)

      // 添加淡出动画
      card.style.transition = "all 0.3s ease"
      card.style.transform = "translateX(100%)"
      card.style.opacity = "0"

      setTimeout(() => {
        card.remove()
        const totalEl = document.getElementById("favorites-total")
        totalEl.textContent = parseInt(totalEl.textContent) - 1

        // 如果没有收藏了，显示空状态
        if (document.querySelectorAll(".favorite-card").length === 0) {
          document.getElementById("favorites-empty").classList.remove("hidden")
        }
      }, 300)

      showToast("已取消收藏")
    }
  } catch (e) {
    showToast("操作失败", "error")
  }
}

// 收藏页面搜索 - 使用 Web Worker 优化
document.getElementById("favorites-search")?.addEventListener("input", async (e) => {
  const query = e.target.value
  const cards = document.querySelectorAll(".favorite-card")

  if (!query || cards.length < 50) {
    // 少量数据直接处理
    cards.forEach(card => card.style.display = "")
    return
  }

  // 大量数据使用 Worker
  const items = Array.from(cards).map(card => ({
    element: card,
    word: card.querySelector(".word")?.textContent || "",
    translation: card.querySelector(".translation")?.textContent || ""
  }))

  try {
    const workerClient = window.workerClient
    if (workerClient) {
      const filtered = await workerClient.filter(items, query, ['word', 'translation'])
      items.forEach((item, i) => {
        cards[i].style.display = filtered.includes(item) ? "" : "none"
      })
    } else {
      // 降级处理
      const q = query.toLowerCase()
      cards.forEach(card => {
        const word = card.querySelector(".word")?.textContent.toLowerCase() || ""
        const trans = card.querySelector(".translation")?.textContent.toLowerCase() || ""
        card.style.display = word.includes(q) || trans.includes(q) ? "" : "none"
      })
    }
  } catch (err) {
    console.warn("Worker 搜索失败，降级处理:", err)
    // 降级处理
    const q = query.toLowerCase()
    cards.forEach(card => {
      const word = card.querySelector(".word")?.textContent.toLowerCase() || ""
      const trans = card.querySelector(".translation")?.textContent.toLowerCase() || ""
      card.style.display = word.includes(q) || trans.includes(q) ? "" : "none"
    })
  }
})

// 暴露给全局
window.removeFavoriteFromList = removeFavoriteFromList

// ==================== Service Worker 注册 ====================

/**
 * 注册 Service Worker
 */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js')
      console.log('[SW] 注册成功:', registration.scope)

      // 检查更新
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // 新版本可用，提示用户刷新
            showToast('新版本可用，请刷新页面', 'info')
          }
        })
      })
    } catch (error) {
      console.log('[SW] 注册失败:', error)
    }
  })
}

// ==================== 性能监控 ====================

/**
 * 上报性能指标
 */
function reportPerformance() {
  if (!window.performance || !window.performance.timing) return

  const timing = performance.timing
  const metrics = {
    dns: timing.domainLookupEnd - timing.domainLookupStart,
    tcp: timing.connectEnd - timing.connectStart,
    request: timing.responseStart - timing.requestStart,
    response: timing.responseEnd - timing.responseStart,
    dom: timing.domComplete - timing.domInteractive,
    total: timing.loadEventEnd - timing.navigationStart
  }

  console.log('[性能指标]', metrics)
}

window.addEventListener('load', () => {
  setTimeout(reportPerformance, 0)
})
