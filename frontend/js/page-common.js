/**
 * SmartVocab 页面公共组件
 * 包含导航栏、用户初始化、退出等共享功能
 */

import { apiRequest, clearToken } from './api-client.js'
import { escapeHtml, showToast, showLoading, hideLoading } from './utils.js'

// ==================== 全局函数暴露 ====================
// 暴露给 api-client.js 的 fetchWithState 使用
window.showToast = showToast
window.showLoading = showLoading
window.hideLoading = hideLoading

// ==================== 用户状态管理 ====================

/** 当前登录用户 */
let currentUser = null

/** 获取当前用户 */
export function getCurrentUser() {
  return currentUser
}

/** 初始化用户信息（所有页面通用） */
export async function initUser() {
  const result = await apiRequest('/auth/profile')
  if (!result.success) {
    window.location.href = 'login.html'
    return null
  }
  currentUser = result.data
  const displayName = document.getElementById('username-display')
  if (displayName) {
    displayName.textContent = currentUser.username
  }
  return currentUser
}

/** 退出登录（所有页面通用） */
export function logout() {
  clearToken()
  window.location.href = 'login.html'
}

// ==================== 导航栏组件 ====================

/**
 * 页面导航配置
 */
const NAV_ITEMS = [
  { href: 'dashboard.html', icon: '🏠', label: '首页', page: 'dashboard' },
  { href: 'plans.html', icon: '📋', label: '计划', page: 'plans' },
  { href: 'levels.html', icon: '🎮', label: '闯关', page: 'levels' },
  { href: 'evaluation.html', icon: '📝', label: '测试', page: 'evaluation' },
  { href: 'statistics.html', icon: '📊', label: '统计', page: 'statistics' },
  { href: 'favorites.html', icon: '⭐', label: '收藏', page: 'favorites' },
  { href: 'profile.html', icon: '👤', label: '我的', page: 'profile' }
]

/**
 * 获取当前页面名称
 */
function getCurrentPage() {
  const path = window.location.pathname
  const filename = path.split('/').pop()?.replace('.html', '') || 'dashboard'
  return filename
}

/**
 * 渲染导航栏 HTML
 */
export function renderNavbar() {
  const currentPage = getCurrentPage()
  const navItemsHtml = NAV_ITEMS.map(item => {
    const isActive = item.page === currentPage
    return `
      <a href="${item.href}"
         class="nav-link ${isActive ? 'active' : ''}"
         role="menuitem"
         data-page="${item.page}"
         ${isActive ? 'aria-current="page"' : ''}>
        ${item.icon} ${item.label}
      </a>
    `
  }).join('')

  return `
    <nav class="navbar" role="navigation" aria-label="主导航">
      <a href="dashboard.html" class="nav-brand">
        <div class="nav-logo">SV</div>
        <span class="nav-title">SmartVocab</span>
      </a>
      <div class="nav-menu" role="menubar">
        ${navItemsHtml}
      </div>
      <div class="nav-user">
        <span class="user-name" id="username-display">用户</span>
        <button class="btn btn-ghost" onclick="logout()" aria-label="退出登录">退出</button>
      </div>
    </nav>
  `
}

/**
 * 插入导航栏到页面
 * @param {string|HTMLElement} target - 目标元素或选择器
 */
export function insertNavbar(target = 'body') {
  const container = typeof target === 'string' ? document.querySelector(target) : target
  if (!container) return

  // 在第一个子元素前插入导航栏
  const navHtml = renderNavbar()
  const navFragment = document.createRange().createContextualFragment(navHtml)
  container.insertBefore(navFragment, container.firstChild)
}

/**
 * 完整页面初始化（导航栏 + 用户信息）
 * @param {Object} options - 配置选项
 * @param {string} options.navTarget - 导航栏插入位置
 * @param {Function} options.onReady - 用户信息加载完成回调
 */
export async function initPage(options = {}) {
  const { navTarget = 'body', onReady } = options

  // 插入导航栏
  insertNavbar(navTarget)

  // 初始化用户
  const user = await initUser()

  // 暴露全局函数（供 onclick 使用）
  window.logout = logout
  window.currentUser = currentUser

  // 回调
  if (onReady && user) {
    await onReady(user)
  }

  return user
}

// ==================== 页面头部组件 ====================

/**
 * 渲染页面头部
 */
export function renderPageHeader(title, subtitle, icon) {
  return `
    <header class="page-header">
      <h1 class="page-title">
        ${icon ? `<span class="page-title-icon">${escapeHtml(icon)}</span>` : ''}
        ${escapeHtml(title)}
      </h1>
      ${subtitle ? `<p class="page-subtitle">${escapeHtml(subtitle)}</p>` : ''}
    </header>
  `
}