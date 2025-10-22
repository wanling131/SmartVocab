// API 配置 - 动态检测API地址
const API_BASE_URL = (() => {
  // 如果是localhost访问，使用localhost
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return "http://localhost:5000/api"
  }
  // 否则使用当前主机地址
  return `http://${window.location.hostname}:5000/api`
})()

// 全局状态
let currentUser = null
let currentSession = null
let sessionStartTime = null
let correctAnswers = 0
let totalAnswers = 0
let browseMode = false  // 浏览模式标识
let browseWords = []    // 浏览单词列表
let currentBrowseIndex = 0  // 当前浏览索引

function showLoading() {
  const overlay = document.createElement("div")
  overlay.className = "loading-overlay"
  overlay.id = "loading-overlay"
  overlay.innerHTML = '<div class="loading-spinner"></div>'
  document.body.appendChild(overlay)
}

function hideLoading() {
  const overlay = document.getElementById("loading-overlay")
  if (overlay) {
    overlay.remove()
  }
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

// Toast消息显示函数
function showToast(message, type = "success") {
  // 创建toast元素
  const toast = document.createElement("div")
  toast.className = `toast ${type}`
  toast.textContent = message
  
  // 添加到页面
  document.body.appendChild(toast)
  
  // 自动移除
  setTimeout(() => {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast)
    }
  }, 3000)
}


// 网络状态检测
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
    console.log('忽略浏览器扩展错误:', event.error.message)
    event.preventDefault()
    return false
  }
})

// Promise错误处理
window.addEventListener('unhandledrejection', function(event) {
  // 忽略浏览器扩展相关的Promise错误
  if (event.reason && event.reason.message && 
      event.reason.message.includes('message channel closed')) {
    console.log('忽略浏览器扩展Promise错误:', event.reason.message)
    event.preventDefault()
    return false
  }
})

// 增强的API请求函数，包含网络检测
async function apiRequest(endpoint, options = {}) {
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
    
    // 检查响应状态
    if (!response.ok) {
      const errorMessage = `服务器错误: ${response.status} ${response.statusText}`
      console.error(`HTTP错误: ${errorMessage}`)
      return { success: false, message: errorMessage }
    }
    
    const data = await response.json()
    return data
  } catch (error) {
    console.error("API请求失败:", error)
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return { success: false, message: "网络请求失败，请检查网络连接" }
    }
    return { success: false, message: "网络请求失败" }
  }
}


// 推荐缓存
let recommendationCache = {
  data: [],
  timestamp: 0,
  algorithm: '',
  totalAvailable: 0,
  displayedCount: 0
}

// 推荐缓存持续时间（5分钟）
const CACHE_DURATION = 5 * 60 * 1000



function showPage(pageName) {
  document.querySelectorAll(".page").forEach((page) => {
    page.classList.remove("active")
  })
  document.getElementById(`${pageName}-page`).classList.add("active")
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

    showLoading()
    try {
      const result = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      })
      hideLoading()
      
      if (result.success) {
        currentUser = { id: result.data.user_id, username: result.data.username }
        localStorage.setItem("currentUser", JSON.stringify(currentUser))
        showToast("登录成功！")
        showPage("dashboard")
        loadDashboard()
      } else {
        showToast(result.message || "登录失败", "error")
      }
    } catch (error) {
      hideLoading()
      handleError(error, "登录")
    }
  })

  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault()
    const username = document.getElementById("register-username").value
    const password = document.getElementById("register-password").value
    const email = document.getElementById("register-email").value

    showLoading()
    try {
      const result = await apiRequest("/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, password, email }),
      })
      hideLoading()
      
      if (result.success) {
        showToast("注册成功！请登录")
        document.querySelector('[data-tab="login"]').click()
        registerForm.reset()
      } else {
        showToast(result.message || "注册失败", "error")
      }
    } catch (error) {
      hideLoading()
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
        console.log("从localStorage恢复用户状态:", currentUser)
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
  document.getElementById("username-display").textContent = currentUser.username
  document.getElementById("username-display-stats").textContent = currentUser.username

  showLoading()

  try {
    // 加载学习进度
    const progress = await apiRequest(`/learning/progress/${currentUser.id}`)
    if (progress.success) {
      document.getElementById("total-words").textContent = progress.data.total_words
      document.getElementById("learned-words").textContent = progress.data.learned_words
      document.getElementById("learning-words").textContent = progress.data.learning_words
      document.getElementById("mastery-rate").textContent = (progress.data.mastery_rate * 100).toFixed(1) + "%"
    }

    // 加载推荐内容
    await loadRecommendations()
  } catch (error) {
    handleError(error, "加载仪表板")
  } finally {
    hideLoading()
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
      console.log("使用推荐缓存")
      displayRecommendations(recommendationCache.data.slice(recommendationCache.displayedCount, recommendationCache.displayedCount + 6))
      recommendationCache.displayedCount += 6
      return
    }
    
    // 需要获取新的推荐
    console.log(forceRefresh ? "强制刷新推荐" : "获取新推荐")
    
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
      
      console.log(`缓存了 ${result.data.length} 个推荐单词`)
      
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
      card.innerHTML = `
                <h3>${word.word}</h3>
                <div class="translation">${word.translation}</div>
                <div class="recommendation-reason">${word.reason || '智能推荐'}</div>
                <div class="meta">
                    <span class="difficulty-badge difficulty-${word.difficulty_level}">
                        难度 ${word.difficulty_level}
                    </span>
                    <span>推荐度: ${(word.recommendation_score * 100).toFixed(0)}%</span>
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
  
  // 隐藏选择题和翻译题界面
  document.getElementById("choice-section").classList.add("hidden")
  document.getElementById("translation-section").classList.add("hidden")
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
      console.log("DEBUG: 找到活跃会话，恢复学习状态")
      return true
    } else {
      console.log("DEBUG: 没有活跃会话")
      return false
    }
  } catch (error) {
    console.error("检查活跃会话失败:", error)
    return false
  }
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
      console.log("DEBUG: 学习会话已完成")
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
    
    // 记录单词显示开始时间
    wordStartTime = Date.now()
    
    document.getElementById("current-word").textContent = word.word
    document.getElementById("word-phonetic").textContent = word.phonetic || ""
    // word-pos元素被注释掉了，所以跳过
    // document.getElementById("word-pos").textContent = word.pos || ""

    // 更新进度
    const progress = (currentSession.current_word_index / currentSession.total_count) * 100
    document.getElementById("learning-progress").style.width = progress + "%"
    document.getElementById("current-word-index").textContent = currentSession.current_word_index + 1
    document.getElementById("total-word-count").textContent = currentSession.total_count

    // 根据题目类型显示不同的界面
    if (word.question_type === "choice") {
      showChoiceQuestion(word)
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
  // 隐藏翻译题界面
  document.getElementById("translation-section").classList.add("hidden")
  
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

function showTranslationQuestion(word) {
  // 隐藏选择题界面
  document.getElementById("choice-section").classList.add("hidden")
  
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
  const requestData = {
    user_id: currentUser.id,
    word_id: word.word_id,
    user_answer: selectedOption,
    correct_answer: word.correct_answer,
    response_time: 0,
    question_type: "choice",
    session_info: currentSession  // 添加session_info
  }

  console.log("DEBUG: 提交选择题答案:", requestData)

  const result = await apiRequest("/vocabulary/submit-answer", {
    method: "POST",
    body: JSON.stringify(requestData),
  })

  console.log("DEBUG: 选择题答案结果:", result)

  if (result.success) {
    totalAnswers++
    if (result.is_correct) {
      correctAnswers++
    }

    // 更新session_info（如果后端返回了更新的session_info）
    if (result.session_info) {
      currentSession = result.session_info
      console.log("DEBUG: 更新session_info:", currentSession)
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

  feedbackMessage.textContent = result.message
  feedbackMessage.className = "feedback-message " + (result.is_correct ? "correct" : "incorrect")
  
  // 修复：使用result.data.correct_answer而不是result.correct_answer
  const correctAnswer = result.data ? result.data.correct_answer : result.correct_answer
  correctAnswerDiv.textContent = result.is_correct ? "" : `正确答案: ${correctAnswer}`

  feedbackSection.classList.remove("hidden")

  // 高亮正确答案
  const options = document.querySelectorAll(".choice-option")
  options.forEach(option => {
    if (option.textContent === word.correct_answer) {
      option.classList.add("correct-answer")
    }
    if (option.textContent !== word.correct_answer && option.classList.contains("selected")) {
      option.classList.add("wrong-answer")
    }
  })

  // 延迟显示下一个按钮
  setTimeout(() => {
    document.getElementById("next-word-btn").classList.remove("hidden")
  }, 1500)
}

async function submitAnswer() {
  const userAnswer = document.getElementById("answer-input").value.trim()
  if (!userAnswer) {
    handleError("请输入答案", "答案验证")
    return
  }

  const currentWord = currentSession.words[currentSession.current_word_index]
  
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

  console.log("DEBUG: 提交翻译题答案:", requestData)

  try {
    const result = await apiRequest("/vocabulary/submit-answer", {
      method: "POST",
      body: JSON.stringify(requestData),
    })

    console.log("DEBUG: 翻译题答案结果:", result)

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
        console.log("DEBUG: 更新session_info:", currentSession)
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
    const currentWordData = currentSession.words[currentSession.current_word_index]
    const wordId = currentWordData.id
    const currentStage = currentSession.word_stages[wordId.toString()]  // 转换为字符串
    
    console.log("DEBUG: 学习阶段检查 - wordId:", wordId, "currentStage:", currentStage, "word_stages:", currentSession.word_stages)
    
    if (currentStage === "choice") {
      // 选择题刚完成，切换到翻译题阶段
      console.log("DEBUG: 切换到翻译题阶段，word_id:", wordId)
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
  // 如果是浏览模式，使用浏览模式的完成
  if (browseMode) {
    finishBrowse()
    return
  }
  
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
    const stats = await apiRequest(`/learning/statistics/${currentUser.id}?days=${days}`)

    if (stats.success) {
      document.getElementById("total-reviews").textContent = stats.data.total_reviews
      document.getElementById("new-words").textContent = stats.data.new_words
      document.getElementById("learned-words-stats").textContent = stats.data.learned_words
      document.getElementById("avg-reviews").textContent = stats.data.average_reviews_per_day.toFixed(1)
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
                      <span class="record-word">${record.word}</span>
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
  } catch (error) {
    handleError(error, "加载统计")
  } finally {
    hideLoading()
  }
}

async function loadForgettingCurve() {
  const chartContainer = document.getElementById("forgetting-curve-chart")
  
  // 暂时显示占位内容，等待后续开发
  chartContainer.innerHTML = `
    <div class="empty-state">
      <div class="empty-state-icon">📊</div>
      <h4>复习计划功能开发中</h4>
      <p>该功能正在开发中，敬请期待</p>
    </div>
  `
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
  localStorage.removeItem("currentUser")
  showPage("auth")
  showToast("已退出登录")
}

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

      // 根据页面加载相应数据
      if (page === "statistics") {
        loadStatistics()
      } else if (page === "dashboard") {
        loadDashboard()
      }
      // learning页面只能通过功能按钮进入，不能通过导航进入
    }
  })

  // 退出登录 - 使用通用函数
  document.getElementById("logout-btn").addEventListener("click", logout)
  document.getElementById("logout-btn-stats").addEventListener("click", logout)

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

  // 学习页面
  document.getElementById("submit-answer-btn").addEventListener("click", submitAnswer)
  document.getElementById("next-word-btn").addEventListener("click", nextWord)
  document.getElementById("finish-session-btn").addEventListener("click", finishSession)
  document.getElementById("back-to-dashboard").addEventListener("click", () => {
    if (currentSession && currentSession.current_word_index < currentSession.total_count) {
      if (confirm("确定要退出当前学习吗？进度将不会保存。")) {
        currentSession = null
        showPage("dashboard")
      }
    } else {
      showPage("dashboard")
    }
  })

  // 回车提交答案
  document.getElementById("answer-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !document.getElementById("submit-answer-btn").disabled) {
      submitAnswer()
    }
  })

  // 显示答案
  document.getElementById("show-answer-btn").addEventListener("click", () => {
    const currentWord = currentSession.words[currentSession.current_word_index]
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
