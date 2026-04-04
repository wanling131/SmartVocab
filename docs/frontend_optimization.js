/**
 * SmartVocab 前端性能优化建议
 *
 * 当前状态：
 * - main.js: ~82KB (2478行)
 * - api-client.js: ~2.6KB
 *
 * 优化建议：
 */

// ==================== 1. 代码拆分方案 ====================

/**
 * 建议将 main.js 拆分为多个模块：
 *
 * frontend/js/
 *   ├── api-client.js      # API 请求封装（已有）
 *   ├── auth.js            # 认证相关（登录/注册/Token管理）
 *   ├── learning.js        # 学习模块（学习会话、答题逻辑）
 *   ├── statistics.js      # 统计模块（进度、图表）
 *   ├── vocabulary.js      # 词库模块（浏览、搜索）
 *   ├── profile.js         # 个人中心
 *   ├── utils.js           # 工具函数（escapeHtml, toast等）
 *   └── app.js             # 主入口（路由、初始化）
 */

// ==================== 2. 动态导入实现 ====================

// 在 index.html 中添加
/*
<script type="module">
  // 核心模块立即加载
  import { initAuth } from './js/auth.js';
  import { showLoading, hideLoading } from './js/utils.js';

  // 根据当前页面动态加载模块
  const page = detectCurrentPage();

  if (page === 'learning') {
    import('./js/learning.js').then(m => m.initLearning());
  } else if (page === 'statistics') {
    import('./js/statistics.js').then(m => m.initStatistics());
  }
</script>
*/

// ==================== 3. 懒加载实现示例 ====================

// utils.js - 添加懒加载工具
export function lazyLoadModule(moduleName, initFunction) {
  return new Promise((resolve, reject) => {
    // 检查是否已加载
    if (window[moduleName]) {
      resolve(window[moduleName]);
      return;
    }

    // 动态导入
    import(`./${moduleName}.js`)
      .then(module => {
        window[moduleName] = module;
        if (initFunction && module[initFunction]) {
          module[initFunction]();
        }
        resolve(module);
      })
      .catch(reject);
  });
}

// 使用示例
// 点击"统计"按钮时才加载统计模块
document.getElementById('nav-statistics')?.addEventListener('click', () => {
  lazyLoadModule('statistics', 'initStatistics');
});

// ==================== 4. 图片/资源懒加载 ====================

// 添加图片懒加载（如果有图片）
/*
<img src="placeholder.png" data-src="actual-image.png" class="lazy" alt="...">

<script>
const lazyImages = document.querySelectorAll('img.lazy');
const imageObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const img = entry.target;
      img.src = img.dataset.src;
      img.classList.remove('lazy');
      imageObserver.unobserve(img);
    }
  });
});
lazyImages.forEach(img => imageObserver.observe(img));
</script>
*/

// ==================== 5. 缓存策略优化 ====================

// 在 api-client.js 中添加请求缓存
const apiCache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5分钟

export async function cachedApiRequest(endpoint, options = {}) {
  const cacheKey = `${endpoint}:${JSON.stringify(options)}`;
  const cached = apiCache.get(cacheKey);

  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data;
  }

  const data = await apiRequest(endpoint, options);
  apiCache.set(cacheKey, { data, timestamp: Date.now() });
  return data;
}

// 清除特定用户缓存
export function invalidateUserCache() {
  for (const key of apiCache.keys()) {
    if (key.includes('/learning/') || key.includes('/recommendations/')) {
      apiCache.delete(key);
    }
  }
}

// ==================== 6. 防抖/节流优化 ====================

// 添加到 utils.js
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

export function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// 使用示例：搜索输入防抖
// searchInput.addEventListener('input', debounce(handleSearch, 300));

// ==================== 7. 虚拟列表（大数据量） ====================

// 如果词汇列表很长，使用虚拟列表
class VirtualList {
  constructor(container, itemHeight, renderItem) {
    this.container = container;
    this.itemHeight = itemHeight;
    this.renderItem = renderItem;
    this.visibleStart = 0;
    this.visibleEnd = 0;
    this.items = [];

    this.container.addEventListener('scroll', throttle(() => this.onScroll(), 50));
  }

  setItems(items) {
    this.items = items;
    this.updateVisibleItems();
  }

  onScroll() {
    this.updateVisibleItems();
  }

  updateVisibleItems() {
    const scrollTop = this.container.scrollTop;
    const viewportHeight = this.container.clientHeight;

    const newStart = Math.floor(scrollTop / this.itemHeight);
    const newEnd = Math.min(
      this.items.length,
      newStart + Math.ceil(viewportHeight / this.itemHeight) + 1
    );

    if (newStart !== this.visibleStart || newEnd !== this.visibleEnd) {
      this.visibleStart = newStart;
      this.visibleEnd = newEnd;
      this.render();
    }
  }

  render() {
    const fragment = document.createDocumentFragment();
    for (let i = this.visibleStart; i < this.visibleEnd; i++) {
      const element = this.renderItem(this.items[i], i);
      element.style.transform = `translateY(${i * this.itemHeight}px)`;
      fragment.appendChild(element);
    }
    this.container.innerHTML = '';
    this.container.appendChild(fragment);
  }
}

// ==================== 8. 构建优化建议 ====================

/**
 * 生产环境建议使用构建工具：
 *
 * 1. 使用 Vite 或 Webpack 进行打包
 * 2. 启用代码压缩和 Tree Shaking
 * 3. 使用 HTTP/2 Push 或预加载关键资源
 *
 * package.json 示例：
 * {
 *   "scripts": {
 *     "build": "vite build",
 *     "preview": "vite preview"
 *   },
 *   "devDependencies": {
 *     "vite": "^5.0.0",
 *     "terser": "^5.0.0"
 *   }
 * }
 *
 * vite.config.js 示例：
 * export default {
 *   build: {
 *     rollupOptions: {
 *       output: {
 *         manualChunks: {
 *           'auth': ['js/auth.js'],
 *           'learning': ['js/learning.js'],
 *           'statistics': ['js/statistics.js']
 *         }
 *       }
 *     }
 *   }
 * }
 */

export { lazyLoadModule };
