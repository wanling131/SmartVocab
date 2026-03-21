/**
 * API 基础地址与请求封装（供 main 模块使用）
 */
export const API_BASE_URL = (() => {
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return "http://localhost:5000/api"
  }
  return `http://${window.location.hostname}:5000/api`
})()

function checkNetworkStatus() {
  if (!navigator.onLine) {
    return false
  }
  return true
}

export async function apiRequest(endpoint, options = {}) {
  if (!checkNetworkStatus()) {
    return { success: false, message: "网络连接不可用" }
  }

  try {
    const url = `${API_BASE_URL}${endpoint}`

    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    })

    const contentType = response.headers.get("content-type") || ""
    let payload = null
    if (contentType.includes("application/json")) {
      try {
        payload = await response.json()
      } catch {
        payload = null
      }
    }

    if (!response.ok) {
      const msg =
        (payload && typeof payload.message === "string" && payload.message) ||
        `HTTP ${response.status} ${response.statusText}`
      console.error("HTTP错误:", msg)
      return { success: false, message: msg, ...((payload && typeof payload === "object") ? payload : {}) }
    }

    if (payload !== null) {
      return payload
    }

    return { success: false, message: "服务器返回非 JSON 响应" }
  } catch (error) {
    console.error("API请求失败:", error)
    if (error.name === "TypeError" && error.message.includes("fetch")) {
      return { success: false, message: "网络请求失败，请检查网络连接" }
    }
    return { success: false, message: "网络请求失败" }
  }
}
