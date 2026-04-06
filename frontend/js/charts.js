/**
 * SmartVocab 图表模块
 * 基于 Chart.js 的数据可视化
 */

// 图表配色方案
const CHART_COLORS = {
  primary: '#8b5cf6',
  primaryLight: 'rgba(139, 92, 246, 0.2)',
  secondary: '#06b6d4',
  secondaryLight: 'rgba(6, 182, 212, 0.2)',
  success: '#10b981',
  successLight: 'rgba(16, 185, 129, 0.2)',
  warning: '#f59e0b',
  warningLight: 'rgba(245, 158, 11, 0.2)',
  danger: '#ef4444',
  dangerLight: 'rgba(239, 68, 68, 0.2)',
  gray: '#6b7280',
  grayLight: 'rgba(107, 114, 128, 0.2)'
}

// 渐变色数组
const GRADIENT_COLORS = [
  '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444',
  '#ec4899', '#6366f1', '#14b8a6', '#f97316', '#84cc16'
]

// 全局图表配置
const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: '#e5e7eb',
        font: { family: 'system-ui, sans-serif', size: 12 },
        padding: 15,
        usePointStyle: true
      }
    },
    tooltip: {
      backgroundColor: 'rgba(17, 24, 39, 0.95)',
      titleColor: '#f9fafb',
      bodyColor: '#e5e7eb',
      borderColor: 'rgba(139, 92, 246, 0.3)',
      borderWidth: 1,
      cornerRadius: 8,
      padding: 12,
      displayColors: true
    }
  },
  scales: {
    x: {
      grid: { color: 'rgba(75, 85, 99, 0.2)', drawBorder: false },
      ticks: { color: '#9ca3af', font: { size: 11 } }
    },
    y: {
      grid: { color: 'rgba(75, 85, 99, 0.2)', drawBorder: false },
      ticks: { color: '#9ca3af', font: { size: 11 } }
    }
  }
}

// 存储图表实例（便于销毁和更新）
const chartInstances = new Map()

/**
 * 创建或更新图表
 */
function createChart(canvasId, config) {
  const canvas = document.getElementById(canvasId)
  if (!canvas) {
    console.warn(`Canvas #${canvasId} not found`)
    return null
  }

  // 销毁已存在的图表
  if (chartInstances.has(canvasId)) {
    chartInstances.get(canvasId).destroy()
  }

  // 创建新图表
  const ctx = canvas.getContext('2d')
  const chart = new Chart(ctx, config)
  chartInstances.set(canvasId, chart)

  return chart
}

/**
 * 销毁图表
 */
function destroyChart(canvasId) {
  if (chartInstances.has(canvasId)) {
    chartInstances.get(canvasId).destroy()
    chartInstances.delete(canvasId)
  }
}

/**
 * 销毁所有图表
 */
function destroyAllCharts() {
  chartInstances.forEach(chart => chart.destroy())
  chartInstances.clear()
}

// ==================== 预定义图表类型 ====================

/**
 * 创建学习进度折线图
 */
function createProgressLineChart(canvasId, labels, datasets) {
  return createChart(canvasId, {
    type: 'line',
    data: { labels, datasets },
    options: {
      ...CHART_DEFAULTS,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        ...CHART_DEFAULTS.plugins,
        legend: { display: datasets.length > 1, ...CHART_DEFAULTS.plugins.legend }
      },
      scales: {
        ...CHART_DEFAULTS.scales,
        y: { ...CHART_DEFAULTS.scales.y, beginAtZero: true }
      },
      elements: {
        line: { tension: 0.4, borderWidth: 2 },
        point: { radius: 4, hoverRadius: 6 }
      }
    }
  })
}

/**
 * 创建遗忘曲线面积图
 */
function createForgettingCurveChart(canvasId, labels, data) {
  return createChart(canvasId, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: '待复习单词数',
        data,
        borderColor: CHART_COLORS.primary,
        backgroundColor: CHART_COLORS.primaryLight,
        fill: true,
        tension: 0.4,
        pointBackgroundColor: CHART_COLORS.primary,
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6
      }]
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        legend: { display: false }
      },
      scales: {
        ...CHART_DEFAULTS.scales,
        y: { ...CHART_DEFAULTS.scales.y, beginAtZero: true }
      }
    }
  })
}

/**
 * 创建词性分布饼图
 */
function createPosDistributionChart(canvasId, labels, data) {
  return createChart(canvasId, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: GRADIENT_COLORS.slice(0, data.length),
        borderColor: '#1f2937',
        borderWidth: 2,
        hoverOffset: 10
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#e5e7eb',
            font: { size: 12 },
            padding: 15,
            usePointStyle: true
          }
        },
        tooltip: CHART_DEFAULTS.plugins.tooltip
      }
    }
  })
}

/**
 * 创建难度分布柱状图
 */
function createDifficultyBarChart(canvasId, labels, data) {
  const colors = [
    CHART_COLORS.success,    // 简单
    CHART_COLORS.secondary,  // 基础
    CHART_COLORS.primary,    // 中级
    CHART_COLORS.warning,    // 较难
    CHART_COLORS.danger      // 困难
  ]

  return createChart(canvasId, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: '单词数量',
        data,
        backgroundColor: colors.slice(0, data.length),
        borderRadius: 6,
        borderSkipped: false
      }]
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        legend: { display: false }
      },
      scales: {
        ...CHART_DEFAULTS.scales,
        y: { ...CHART_DEFAULTS.scales.y, beginAtZero: true }
      }
    }
  })
}

/**
 * 创建学习趋势对比图
 */
function createTrendComparisonChart(canvasId, labels, thisWeek, lastWeek) {
  return createChart(canvasId, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: '本周',
          data: thisWeek,
          backgroundColor: CHART_COLORS.primary,
          borderRadius: 4
        },
        {
          label: '上周',
          data: lastWeek,
          backgroundColor: CHART_COLORS.grayLight,
          borderColor: CHART_COLORS.gray,
          borderWidth: 1,
          borderRadius: 4
        }
      ]
    },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        ...CHART_DEFAULTS.scales,
        y: { ...CHART_DEFAULTS.scales.y, beginAtZero: true }
      }
    }
  })
}

/**
 * 创建掌握度雷达图
 */
function createMasteryRadarChart(canvasId, labels, data) {
  return createChart(canvasId, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: '掌握程度',
        data,
        backgroundColor: CHART_COLORS.primaryLight,
        borderColor: CHART_COLORS.primary,
        borderWidth: 2,
        pointBackgroundColor: CHART_COLORS.primary,
        pointBorderColor: '#fff',
        pointBorderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: CHART_DEFAULTS.plugins.tooltip
      },
      scales: {
        r: {
          angleLines: { color: 'rgba(75, 85, 99, 0.3)' },
          grid: { color: 'rgba(75, 85, 99, 0.2)' },
          pointLabels: { color: '#e5e7eb', font: { size: 11 } },
          ticks: { display: false, stepSize: 20 },
          suggestedMin: 0,
          suggestedMax: 100
        }
      }
    }
  })
}

/**
 * 创建遗忘曲线图表（用于统计页面）
 */
function createForgettingCurveChart(canvasId, labels, data) {
  return createChart(canvasId, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: '待复习单词',
        data,
        backgroundColor: data.map((v, i) =>
          i < 3 ? CHART_COLORS.danger :
          i < 7 ? CHART_COLORS.warning :
          CHART_COLORS.success
        ),
        borderRadius: 4,
        borderSkipped: false
      }]
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        legend: { display: false }
      },
      scales: {
        ...CHART_DEFAULTS.scales,
        y: { ...CHART_DEFAULTS.scales.y, beginAtZero: true }
      }
    }
  })
}

/**
 * 创建词性分布饼图
 */
function createPosDistributionChart(canvasId, labels, data) {
  return createChart(canvasId, {
    type: 'pie',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: GRADIENT_COLORS.slice(0, data.length),
        borderColor: '#1f2937',
        borderWidth: 2,
        hoverOffset: 10
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#e5e7eb',
            font: { size: 11 },
            padding: 10,
            usePointStyle: true
          }
        },
        tooltip: CHART_DEFAULTS.plugins.tooltip
      }
    }
  })
}

/**
 * 创建学习热力图数据（用于日历视图）
 */
function createHeatmapData(records, days = 30) {
  const result = []
  const today = new Date()

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(today)
    date.setDate(date.getDate() - i)
    const dateStr = date.toISOString().split('T')[0]

    const dayRecords = records.filter(r =>
      r.created_at && r.created_at.startsWith(dateStr)
    )

    result.push({
      date: dateStr,
      count: dayRecords.length,
      level: Math.min(Math.floor(dayRecords.length / 5), 4)
    })
  }

  return result
}

// 导出模块
window.ChartModule = {
  createChart,
  destroyChart,
  destroyAllCharts,
  createProgressLineChart,
  createForgettingCurveChart,
  createPosDistributionChart,
  createDifficultyBarChart,
  createTrendComparisonChart,
  createMasteryRadarChart,
  createHeatmapData,
  COLORS: CHART_COLORS,
  GRADIENT_COLORS
}
