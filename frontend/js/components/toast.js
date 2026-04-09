/**
 * Toast 通知组件
 */

let toastContainer = null

/**
 * HTML 转义函数
 */
function escapeHtml(str) {
  if (str === null || str === undefined) return ''
  const div = document.createElement('div')
  div.textContent = String(str)
  return div.innerHTML
}

/**
 * 显示 Toast 消息
 * @param {string} message - 消息内容
 * @param {string} type - 类型: success, error, warning, info
 * @param {number} duration - 显示时长(毫秒)
 */
export function showToast(message, type = 'success', duration = 3000) {
  // 创建容器
  if (!toastContainer) {
    toastContainer = document.createElement('div')
    toastContainer.className = 'toast-container'
    document.body.appendChild(toastContainer)
  }

  const toast = document.createElement('div')
  toast.className = `toast ${type}`

  // 添加图标
  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
  }
  toast.innerHTML = `<span class="toast-icon">${icons[type]}</span><span>${escapeHtml(message)}</span>`

  toastContainer.appendChild(toast)

  // 触发动画
  requestAnimationFrame(() => {
    toast.classList.add('show')
  })

  // 自动移除
  setTimeout(() => {
    toast.classList.remove('show')
    toast.classList.add('hide')
    setTimeout(() => toast.remove(), 300)
  }, duration)
}

/**
 * 成功提示
 */
export function success(message) {
  showToast(message, 'success')
}

/**
 * 错误提示
 */
export function error(message) {
  showToast(message, 'error')
}

/**
 * 警告提示
 */
export function warning(message) {
  showToast(message, 'warning')
}

/**
 * 信息提示
 */
export function info(message) {
  showToast(message, 'info')
}
