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
  toast.className = `toast ${type} show`
  toast.textContent = message
  document.body.appendChild(toast)

  setTimeout(() => {
    if (toast.parentNode) {
      toast.classList.remove('show')
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

// ==================== 高级动效工具 ====================

/**
 * 撒花粒子效果（答对时触发）
 * @param {number} count - 粒子数量
 */
export function showConfetti(count = 30) {
  const container = document.createElement('div')
  container.className = 'confetti-container'
  document.body.appendChild(container)

  const colors = ['#002FA7', '#E07A5F', '#F2A03D', '#6B8E6B', '#9B8AA6', '#FFD700', '#FF6B6B']

  for (let i = 0; i < count; i++) {
    const piece = document.createElement('div')
    piece.className = 'confetti-piece'
    const color = colors[Math.floor(Math.random() * colors.length)]
    const left = Math.random() * 100
    const delay = Math.random() * 0.5
    const size = 6 + Math.random() * 8
    piece.style.cssText = `
      left: ${left}%;
      width: ${size}px;
      height: ${size}px;
      background: ${color};
      animation-delay: ${delay}s;
      animation-duration: ${1 + Math.random() * 1}s;
    `
    container.appendChild(piece)
  }

  setTimeout(() => container.remove(), 2500)
}

/**
 * 震动效果（答错时触发）
 * @param {HTMLElement} element - 要震动的元素
 */
export function shakeElement(element) {
  if (!element) return
  element.classList.add('shake-error')
  // 红闪
  const flash = document.createElement('div')
  flash.className = 'flash-error-overlay'
  document.body.appendChild(flash)
  setTimeout(() => flash.remove(), 400)
  setTimeout(() => element.classList.remove('shake-error'), 500)
}

/**
 * 答对闪光效果
 */
export function flashSuccess() {
  const flash = document.createElement('div')
  flash.className = 'flash-success-overlay'
  document.body.appendChild(flash)
  setTimeout(() => flash.remove(), 400)
}

/**
 * 浮动反馈图标（大号对号/错号）
 * @param {'correct'|'wrong'} type
 */
export function showFeedbackIcon(type) {
  const icon = document.createElement('div')
  icon.className = 'answer-feedback-float'
  icon.textContent = type === 'correct' ? '✓' : '✗'
  icon.style.color = type === 'correct' ? '#6B8E6B' : '#E07A5F'
  document.body.appendChild(icon)
  setTimeout(() => icon.remove(), 800)
}

/**
 * Combo 连击特效
 * @param {number} count - 连击次数
 */
export function showCombo(count) {
  if (count < 2) return
  const badge = document.createElement('div')
  badge.className = 'combo-badge'
  badge.innerHTML = `${count}x Combo!`
  document.body.appendChild(badge)
  setTimeout(() => badge.remove(), 1000)
}

/**
 * 增强版 Toast
 * @param {string} message - 消息文本
 * @param {'success'|'error'|'info'} type - 类型
 * @param {number} duration - 显示时长(ms)
 */
export function showToastEnhanced(message, type = 'success', duration = 3000) {
  const icons = { success: '✓', error: '✗', info: 'i' }
  const toast = document.createElement('div')
  toast.className = `toast-enhanced ${type}`
  toast.innerHTML = `<span class="toast-icon">${icons[type] || ''}</span><span>${message}</span>`
  document.body.appendChild(toast)

  setTimeout(() => {
    toast.classList.add('toast-exit')
    setTimeout(() => toast.remove(), 300)
  }, duration)
}

/**
 * 创建 Streak 火焰徽章 HTML
 * @param {number} days - 连续天数
 * @returns {string} HTML
 */
export function createStreakBadge(days) {
  if (days < 1) return ''
  const flames = Math.min(Math.floor(days / 3) + 1, 4)
  const flameEmoji = '🔥'.repeat(flames)
  return `<div class="streak-fire">
    <span class="flame-icon">${flameEmoji}</span>
    <span class="streak-count">${days}天连续学习</span>
  </div>`
}

/**
 * Scroll-triggered reveal animation using IntersectionObserver
 * Adds 'revealed' class to elements with 'scroll-reveal' class when they enter viewport
 */
export function initScrollReveal(options = {}) {
  const { threshold = 0.1, rootMargin = '0px 0px -40px 0px' } = options
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed')
        observer.unobserve(entry.target)
      }
    })
  }, { threshold, rootMargin })

  document.querySelectorAll('.scroll-reveal').forEach(el => {
    observer.observe(el)
  })
  return observer
}

/**
 * Enhanced number animation with spring overshoot
 */
export function animateNumberSpring(element, targetValue, duration = 800) {
  if (!element) return
  const startValue = parseInt(element.textContent) || 0
  const startTime = performance.now()
  const diff = targetValue - startValue

  function easeOutBack(t) {
    const c1 = 1.70158
    const c3 = c1 + 1
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2)
  }

  function update(currentTime) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    const eased = easeOutBack(progress)
    const currentValue = Math.round(startValue + diff * eased)
    element.textContent = currentValue.toLocaleString()
    if (progress < 1) requestAnimationFrame(update)
    else element.textContent = targetValue.toLocaleString()
  }
  requestAnimationFrame(update)
}
