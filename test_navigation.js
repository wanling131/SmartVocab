const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const config = JSON.parse(fs.readFileSync('./config.json', 'utf8'));
(async () => {
  try {
    const browser = await puppeteer.launch({
      executablePath: 'chromium',
      headless: true,
      args: ['--no-sandbox', '--disable-set-network-sandbox']
    });
    const page = await browser.newPage();
    
    // 访问页面
    await page.goto('http://localhost:5000', { waitUntil: 'networkidle' });
    console.log('页面加载完成');
    
    // 等待导航栏出现
    await page.waitForSelector('.nav-link', { timeout: 10000 });
    console.log('导航栏已出现');
    
    // 装饰等待登录
    await page.waitForSelector('#auth-page.active', { timeout: 5000 });
    console.log('等待登录页面...');
    
    // 检查是否在登录页面
    const authPage = await page.$('#auth-page.active');
    console.log('当前在登录页面');
    
    // 检查导航栏
    const navLinks = await page.$$('.nav-link');
    console.log(`找到 ${navLinks.length} 个导航链接`);
    
    // 截图保存
    const screenshotDir = path.join(__dirname, 'debug_screenshots');
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    
    // 截图
    await page.screenshot({
      path: path.join(screenshotDir, 'before_login.png'),
      fullPage: true
    });
    console.log('登录页面截图已保存');
    
    // 关闭浏览器
    await browser.close();
    console.log('测试完成');
    
  } catch (error) {
    console.error('测试失败:', error);
    if (browser) {
      await browser.close();
    }
  }
})();
main();
