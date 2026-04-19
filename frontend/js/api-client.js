/**
 * API 基础地址与请求封装（供 main 模块使用）
 * 包含请求缓存优化、请求去重、错误处理
 */

// API 基础地址
export const API_BASE_URL = (() => {
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return "http://localhost:5000/api"
  }
  return `http://${window.location.hostname}:5000/api`
})()

// Token 管理
export function getToken() {
  return localStorage.getItem("auth_token")
}

export function setToken(token) {
  localStorage.setItem("auth_token", token)
}

export function clearToken() {
  localStorage.removeItem("auth_token")
}

// 请求缓存
const apiCache = new Map()
const API_CACHE_TTL = 2 * 60 * 1000 // 2分钟缓存

// 请求去重：防止同时发出多个相同请求
const pendingRequests = new Map()

/**
 * 获取缓存的 API 响应
 */
export function getCachedApiResponse(endpoint) {
  const cached = apiCache.get(endpoint)
  if (cached && Date.now() - cached.timestamp < API_CACHE_TTL) {
    return cached.data
  }
  apiCache.delete(endpoint)
  return null
}

/**
 * 设置 API 响应缓存
 */
export function setCachedApiResponse(endpoint, data) {
  apiCache.set(endpoint, { data, timestamp: Date.now() })
}

/**
 * 清除用户相关的所有缓存
 */
export function invalidateUserCache(userId) {
  for (const key of apiCache.keys()) {
    if (key.includes(`/${userId}`) ||
        key.includes(`/${userId}/`) ||
        key.includes(`user_id=${userId}`)) {
      apiCache.delete(key)
    }
  }
}

/**
 * 清除所有缓存
 */
export function clearAllCache() {
  apiCache.clear()
}

/**
 * 核心 API 请求函数（带请求去重）
 * @param {string} endpoint - API路径
 * @param {object} options - 请求选项
 * @param {boolean} options.forceRefresh - 强制刷新，跳过缓存
 */
export async function apiRequest(endpoint, options = {}) {
  const forceRefresh = options.forceRefresh || false
  const token = getToken()
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    ...options.headers
  }

  // 检查缓存（仅对GET请求且未禁用缓存时）
  const useCache = (!options.method || options.method === "GET") && options.useCache !== false && !forceRefresh

  if (useCache) {
    const cached = getCachedApiResponse(endpoint)
    if (cached) {
      return cached
    }
  }

  // 强制刷新时清除缓存
  if (forceRefresh) {
    apiCache.delete(endpoint)
  }

  // 请求去重：检查是否有相同的请求正在进行中
  const requestKey = `${options.method || "GET"}:${endpoint}`
  if (pendingRequests.has(requestKey)) {
    return pendingRequests.get(requestKey)
  }

  // 发起请求
  const requestPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: options.method || "GET",
        headers,
        body: options.body ? (typeof options.body === 'string' ? options.body : JSON.stringify(options.body)) : undefined,
        ...options.fetchOptions
      })

      // 处理401
      if (response.status === 401) {
        clearToken()
        window.dispatchEvent(new CustomEvent('auth:logout'))
        return { success: false, message: "登录已过期，请重新登录" }
      }

      const payload = await response.json()

      // 错误消息处理
      if (payload && typeof payload.message === "string" && payload.message) {
        if (payload.success === false) {
          console.error("API错误:", payload.message)
        }
      }

      // 缓存成功的GET响应
      if (payload && payload.success && useCache) {
        setCachedApiResponse(endpoint, payload)
      }

      // 非GET请求成功后，自动清除该用户相关的GET缓存
      if (payload && payload.success && options.method && options.method !== "GET") {
        const currentUserId = JSON.parse(localStorage.getItem("currentUser") || "{}").id
        if (currentUserId) {
          invalidateUserCache(currentUserId)
        }
      }

      return payload
    } catch (error) {
      console.error("API请求失败:", error)
      if (error.name === "TypeError" && error.message.includes("fetch")) {
        return { success: false, message: "网络请求失败，请检查网络连接" }
      }
      return { success: false, message: "网络请求失败" }
    } finally {
      // 请求完成后从pending中移除
      pendingRequests.delete(requestKey)
    }
  })()

  // 将请求加入pending
  pendingRequests.set(requestKey, requestPromise)

  return requestPromise
}

// ==================== 高级封装 ====================

/**
 * 通用API调用封装（带加载状态和错误处理）
 * @param {string} endpoint - API端点
 * @param {Object} options - 配置选项
 * @returns {Promise<Object>} API响应
 */
export async function fetchWithState(endpoint, options = {}) {
  const { showSpinner = true, errorMessage = '操作失败' } = options

  if (showSpinner && typeof window.showLoading === 'function') {
    window.showLoading()
  }

  try {
    const result = await apiRequest(endpoint, options)

    // 显示错误提示
    if (!result.success && result.message && typeof window.showToast === 'function') {
      window.showToast(result.message, 'error')
    }

    return result
  } catch (error) {
    if (typeof window.showToast === 'function') {
      window.showToast(error.message || errorMessage, 'error')
    }
    return { success: false, message: error.message || errorMessage }
  } finally {
    if (showSpinner && typeof window.hideLoading === 'function') {
      window.hideLoading()
    }
  }
}

/**
 * 用户相关API快捷方法集合
 */
export const userApi = {
  // 学习进度
  getProgress: (userId) => fetchWithState(`/learning/progress/${userId}`),

  // 学习统计
  getStats: (userId) => fetchWithState(`/learning/statistics/${userId}`),

  // 学习记录
  getRecords: (userId, limit = 1000) =>
    fetchWithState(`/learning/records/${userId}?limit=${limit}`),

  // 复习单词
  getReviewWords: (userId, limit = 100) =>
    fetchWithState(`/learning/review-words/${userId}?limit=${limit}`),

  // 收藏列表
  getFavorites: (userId) => fetchWithState(`/favorites/${userId}`),

  // 收藏ID列表（轻量）
  getFavoriteIds: (userId) => fetchWithState(`/favorites/${userId}/ids`),

  // 推荐单词
  getRecommendations: (userId, limit = 50, algorithm = 'mixed') =>
    fetchWithState(`/recommendations/${userId}?limit=${limit}&algorithm=${algorithm}`),

  // 用户成就
  getAchievements: (userId) => fetchWithState(`/achievements/${userId}`),

  // 学习计划
  getPlans: (userId) => fetchWithState(`/plans?user_id=${userId}`),

  // 等级进度
  getLevelProgress: (userId) => fetchWithState(`/levels/progress/${userId}`)
}

// ==================== 缓存预热 ====================

/**
 * 预热用户常用数据缓存
 * @param {number} userId - 用户ID
 */
export async function warmupUserCache(userId) {
  const endpoints = [
    `/learning/progress/${userId}`,
    `/learning/statistics/${userId}`,
    `/recommendations/${userId}?limit=50`,
    `/favorites/${userId}/ids`
  ]

  // 并行预加载，不阻塞UI，静默失败
  Promise.all(
    endpoints.map(ep =>
      apiRequest(ep, { useCache: true }).catch(() => null)
    )
  ).then(() => {
    console.log('[Cache] 用户数据预热完成')
  })
}

/**
 * 登录成功后的初始化
 * @param {Object} user - 用户对象
 */
export function onLoginSuccess(user) {
  // 保存用户信息
  if (user) {
    localStorage.setItem('currentUser', JSON.stringify(user))
  }

  // 预热缓存
  if (user?.id) {
    warmupUserCache(user.id)
  }
}
