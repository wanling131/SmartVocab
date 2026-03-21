import { apiRequest } from "./js/api-client.js"

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
  const uname = document.getElementById("username-display")
  if (uname) uname.textContent = currentUser.username

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
    // word-pos元素被注释掉了，所以跳过
    // document.getElementById("word-pos").textContent = word.pos || ""

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
  if (!currentUser || !currentUser.id) return

  try {
    const result = await apiRequest(`/learning/forgetting-curve/${currentUser.id}?days=7`)
    if (result.success && result.data && result.data.length > 0) {
      const maxVal = Math.max(...result.data.map(d => d.words_to_review), 1)
      chartContainer.innerHTML = `
        <div class="forgetting-curve-bars">
          ${result.data.map(d => `
            <div class="curve-bar-wrap">
              <div class="curve-bar" style="height: ${(d.words_to_review / maxVal) * 100}%"
                title="${d.date}: ${d.words_to_review} 词"></div>
              <span class="curve-label">${d.date.slice(5)}</span>
              <span class="curve-value">${d.words_to_review}</span>
            </div>
          `).join('')}
        </div>
      `
    } else {
      chartContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">📊</div>
          <h4>暂无复习计划</h4>
          <p>开始学习后，系统将根据记忆曲线生成未来7天复习计划</p>
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
  const activeEl = document.getElementById("active-plan-display")
  try {
    const r = await apiRequest(`/plans/${currentUser.id}/active`)
    if (r.success && r.data) {
      activeEl.innerHTML = `
        <p>词库: ${r.data.dataset_type}</p>
        <p>每日新学: ${r.data.daily_new_count}</p>
        <p>每日复习: ${r.data.daily_review_count}</p>
      `
    } else {
      activeEl.innerHTML = "<p>暂无生效计划，请创建</p>"
    }
  } catch (e) {
    activeEl.innerHTML = `<p>加载失败: ${e.message}</p>`
  }
}

// 闯关模式页
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
          <p>暂无关卡，请先运行数据库迁移并初始化 level_gates 表</p>
        </div>
      `
      return
    }
    listEl.innerHTML = gates.map(g => {
      const p = progMap[g.id] || {}
      const locked = !p.is_unlocked && g.gate_order > 1
      return `
        <div class="recommendation-card ${locked ? 'locked' : ''}">
          <h3>${g.gate_name || '关卡' + g.gate_order}</h3>
          <p>难度 ${g.difficulty_level} · ${g.word_count} 词</p>
          <p>${p.mastered_count || 0}/${g.word_count} 已掌握</p>
          ${locked ? '<span>需完成上一关</span>' : '<button class="btn btn-primary btn-sm" data-gate-id="' + g.id + '">进入</button>'}
        </div>
      `
    }).join("")
    listEl.querySelectorAll("[data-gate-id]").forEach(btn => {
      btn.addEventListener("click", () => showToast("闯关学习功能请从首页「新词学习」选择难度进入", "info"))
    })
  } catch (e) {
    listEl.innerHTML = `<div class="empty-state"><p>加载失败: ${e.message}</p></div>`
  }
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
      } else if (page === "plans") {
        loadPlansPage()
      } else if (page === "levels") {
        loadLevelsPage()
      } else if (page === "evaluation") {
        loadEvaluationStart()
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
      showLoading()
      const r = await apiRequest("/plans", {
        method: "POST",
        body: JSON.stringify({
          user_id: currentUser.id,
          dataset_type: dataset,
          daily_new_count: dailyNew,
          daily_review_count: dailyReview
        })
      })
      hideLoading()
      if (r.success) {
        showToast("计划创建成功")
        loadPlansPage()
      } else {
        showToast(r.message || "创建失败", "error")
      }
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

  // 学习页面
  document.getElementById("submit-answer-btn").addEventListener("click", submitAnswer)
  const spellingSubmitBtn = document.getElementById("spelling-submit-btn")
  if (spellingSubmitBtn) {
    spellingSubmitBtn.addEventListener("click", submitSpellingAnswer)
  }
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
