/**
 * API 基础地址与请求封装（供 main 模块使用）
 * 包含请求缓存优化
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

localStorage.removeItem("auth_token")
}

// 请求缓存
const apiCache = new Map()
const API_CACHE_TTL = 2 * 60 * 1000 // 2分钟缓存

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
 * 核心 API 请求函数
 */
export async function apiRequest(endpoint, options = {}) {
  const token = getToken()
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
    ...options.headers
  }
  // 检查缓存（仅对GET请求且未禁用缓存时）
  const useCache = (!options.method || options.method === "GET") && options.useCache !== false
  if (useCache) {
    const cached = getCachedApiResponse(endpoint)
    if (cached) {
      return cached
    }
  }
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: options.method || "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
      ...options.fetchOptions
    })
    // 夣401处理
    if (response.status === 401) {
      clearToken()
      window.location.reload()
      return { success: false, message: "登录已过期，请重新登录" }
    }
    const payload = await response.json()
    // 错误消息处理
    if (payload && typeof payload.message === "string" && payload.message) {
      if (payload.success === false) {
        console.error("HTTP错误:", payload.message)
      }
    }
    // 缓存成功的GET响应
    if (payload && payload.success && useCache) {
      setCachedApiResponse(endpoint, payload)
    }
    return payload
  } catch (error) {
    console.error("API请求失败:", error)
    if (error.name === "TypeError" && error.message.includes("fetch")) {
      return { success: false, message: "网络请求失败，请检查网络连接" }
    }
    return { success: false, message: "网络请求失败" }
  }
}
