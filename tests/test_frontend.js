// 简单的前端测试脚本
const http = require('http');

const BASE_URL = 'http://localhost:5000';

console.log('=== SmartVocab 前端测试 ===\n');

// 测试1: 检查服务器是否运行
const healthReq = http.request(`${BASE_URL}/api/health`, { method: 'GET' }, (res1) => {
  let data = '';
  res1.on('data', chunk => data += chunk);
  res1.on('end', () => {
    console.log('\n1. 健康检查:');
    try {
      const result = JSON.parse(data);
      console.log('   状态:', result.success ? '✅ 正常' : '❌ 失败');
      if (result.data) {
        console.log('   数据库:', result.data.database?.status || 'N/A');
      }
    } catch (e) {
      console.log('   响应:', data.substring(0, 100));
    }

    // 测试2: 获取首页HTML
    const htmlReq = http.request(BASE_URL, { method: 'GET' }, (res2) => {
      let html = '';
      res2.on('data', chunk => html += chunk);
      res2.on('end', () => {
        console.log('\n2. 首页检查:');
        console.log('   状态码:', res2.statusCode);
        console.log('   包含nav-link:', html.includes('nav-link') ? '✅ 是' : '❌ 否');
        console.log('   包含dashboard-page:', html.includes('dashboard-page') ? '✅ 是' : '❌ 否');
        console.log('   包含auth-page:', html.includes('auth-page') ? '✅ 是' : '❌ 否');
        console.log('   包含styles.css:', html.includes('styles.css') ? '✅ 是' : '❌ 否');
        console.log('   包含main.js:', html.includes('main.js') ? '✅ 是' : '❌ 否');

        // 测试3: 检查JS文件
        const jsReq = http.request(`${BASE_URL}/main.js`, { method: 'GET' }, (res3) => {
          let jsContent = '';
          res3.on('data', chunk => jsContent += chunk);
          res3.on('end', () => {
            console.log('\n3. main.js检查:');
            console.log('   状态码:', res3.statusCode);
            console.log('   文件大小:', jsContent.length, 'bytes');
            console.log('   包含initEventListeners:', jsContent.includes('function initEventListeners') ? '✅ 是' : '❌ 否');
            console.log('   包含showPage:', jsContent.includes('function showPage') ? '✅ 是' : '❌ 否');
            console.log('   包含loadDashboard:', jsContent.includes('async function loadDashboard') ? '✅ 是' : '❌ 否');
            console.log('   包含调试日志:', jsContent.includes('[SmartVocab]') ? '✅ 是' : '❌ 否');

            console.log('\n=== 测试完成 ===');
            console.log('\n请在浏览器中打开 http://localhost:5000 进行手动测试');
            console.log('如果导航仍无反应，请检查浏览器控制台的调试日志');
          });
        });
        jsReq.on('error', e => console.error('JS文件请求失败:', e.message));
        jsReq.end();
      });
    });
    htmlReq.on('error', e => console.error('HTML请求失败:', e.message));
    htmlReq.end();
  });
});
healthReq.on('error', e => console.error('健康检查失败:', e.message));
healthReq.end();
