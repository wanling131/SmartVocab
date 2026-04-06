/**
 * SmartVocab 工具函数模块
 * 包含安全、动画、通用工具函数
 */

// ==================== 用户工具 ====================

/**
 * 获取当前登录用户信息
 * @returns {Object|null} 用户对象或 null
 */
export function getCurrentUser() {
  try {
    const userStr = localStorage.getItem("currentUser")
    if (!userStr) return null
    return JSON.parse(userStr)
  } catch (e) {
    console.error("解析用户信息失败:", e)
    return null
  }
}

// ==================== 安全工具 ====================

/**
 * HTML转义函数，防止XSS攻击
 */
export function escapeHtml(str) {
  if (str === null || str === undefined) return ''
  const div = document.createElement('div')
  div.textContent = String(str)
  return div.innerHTML
}

/**
 * 安全地设置元素的innerHTML
 */
export function safeHtml(element, html, vars = {}) {
  let result = html
  for (const [key, value] of Object.entries(vars)) {
    const placeholder = new RegExp(`\\$\\{\\s*${key}\\s*\\}`, 'g')
    result = result.replace(placeholder, escapeHtml(value))
  }
  element.innerHTML = result
}

// ==================== 动画工具 ====================

/**
 * 数字递增动画
 */
export function animateNumber(element, targetValue, duration = 1000) {
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
 * 淡入动画
 */
export function fadeIn(element, duration = 300) {
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
 * 淡出动画
 */
export function fadeOut(element, duration = 300) {
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
 * 进度条动画
 */
export function animateProgress(progressBar, targetPercent, duration = 500) {
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
export function typeWriter(element, text, speed = 50) {
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

// ==================== UI组件工具 ====================

/**
 * 显示Toast消息
 */
export function showToast(message, type = 'success') {
  const toast = document.createElement('div')
  toast.className = `toast ${type}`
  toast.textContent = message
  document.body.appendChild(toast)

  setTimeout(() => {
    if (toast.parentNode) {
      toast.style.animation = 'toastSlide 0.3s ease reverse'
      setTimeout(() => toast.parentNode?.removeChild(toast), 300)
    }
  }, 3000)
}

/**
 * 显示加载动画
 */
export function showLoading() {
  if (document.getElementById('loading-overlay')) return
  const overlay = document.createElement('div')
  overlay.className = 'loading-overlay'
  overlay.id = 'loading-overlay'
  overlay.innerHTML = `
    <div class="loading-content">
      <div class="loading-spinner"></div>
      <div class="loading-text">加载中...</div>
    </div>
  `
  document.body.appendChild(overlay)
}

/**
 * 隐藏加载动画
 */
export function hideLoading() {
  document.getElementById('loading-overlay')?.remove()
}

/**
 * 错误处理
 */
export function handleError(error, context = '') {
  console.error(`错误 [${context}]:`, error)
  let message = '操作失败'
  if (typeof error === 'string') message = error
  else if (error?.message) message = error.message
  showToast(message, 'error')
}

// ==================== 格式化工具 ====================

/**
 * 格式化日期
 */
export function formatDate(date) {
  if (!date) return ''
  const d = new Date(date)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

/**
 * 格式化时间
 */
export function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

/**
 * 格式化百分比
 */
export function formatPercent(value) {
  return `${Math.round(value * 100)}%`
}
