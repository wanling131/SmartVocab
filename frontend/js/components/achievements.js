/**
 * 成就系统组件
 * 显示成就解锁动画
 */

/**
 * 显示成就解锁
 */
export function showAchievement(achievement) {
  const popup = document.createElement('div')
  popup.className = 'achievement-popup'
  popup.innerHTML = `
    <div class="achievement-icon">${achievement.icon || '🏆'}</div>
    <div class="achievement-content">
      <div class="achievement-title">成就解锁!</div>
      <div class="achievement-name">${achievement.name}</div>
      <div class="achievement-desc">${achievement.description}</div>
    </div>
  `
  document.body.appendChild(popup)

  // 触发动画
  requestAnimationFrame(() => {
    popup.classList.add('show')
  })

  // 播放音效（如果有）
  playSound('achievement')

  // 3秒后移除
  setTimeout(() => {
    popup.classList.remove('show')
    popup.classList.add('hide')
    setTimeout(() => popup.remove(), 500)
  }, 3000)
}

/**
 * 显示连击提示
 */
export function showStreak(count) {
  if (count < 3) return

  const streak = document.createElement('div')
  streak.className = 'streak-popup'

  const messages = {
    3: '三连击! 🔥',
    5: '五连击! 🔥🔥',
    7: '七连击! 🔥🔥🔥',
    10: '完美十连! 🌟'
  }

  streak.textContent = messages[count] || `${count}连击! 🎯`
  document.body.appendChild(streak)

  requestAnimationFrame(() => streak.classList.add('show'))
  setTimeout(() => {
    streak.classList.remove('show')
    setTimeout(() => streak.remove(), 300)
  }, 1500)
}

/**
 * 播放音效
 */
function playSound(type) {
  // 使用Web Audio API播放简单音效
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)()
    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()

    const sounds = {
      achievement: { freq: 880, duration: 0.2 },
      correct: { freq: 660, duration: 0.1 },
      wrong: { freq: 220, duration: 0.2 },
      streak: { freq: 1000, duration: 0.15 }
    }

    const sound = sounds[type] || sounds.correct

    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)

    oscillator.frequency.value = sound.freq
    oscillator.type = 'sine'

    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + sound.duration)

    oscillator.start(audioContext.currentTime)
    oscillator.stop(audioContext.currentTime + sound.duration)
  } catch (e) {
    // 静默失败，不影响用户体验
  }
}

/**
 * 正确答案音效
 */
export function playCorrectSound() {
  playSound('correct')
}

/**
 * 错误答案音效
 */
export function playWrongSound() {
  playSound('wrong')
}
