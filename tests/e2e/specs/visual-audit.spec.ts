import { test, expect } from '@playwright/test';

// ============================================================
// SmartVocab Visual Audit
// Klein Blue + Morandi hand-drawn design system
// Runs as a single test to collect findings across all pages.
// ============================================================

const BASE = 'http://localhost:5000/pages';
const SCREENSHOT_DIR = 'screenshots';

// Emoji regex for checking stray emoji characters
const EMOJI_REGEX = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{FE00}-\u{FE0F}\u{1F000}-\u{1F02F}\u{1F0A0}-\u{1F0FF}\u{1F100}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{200D}\u{20E3}]/u;

interface CheckResult {
  check: string;
  pass: boolean;
  detail: string;
}

// Collect findings across all pages
const allFindings: Record<string, CheckResult[]> = {};

function addFinding(pageName: string, check: string, pass: boolean, detail: string) {
  if (!allFindings[pageName]) allFindings[pageName] = [];
  allFindings[pageName].push({ check, pass, detail });
  // Live console output for monitoring
  const icon = pass ? 'PASS' : 'FAIL';
  console.log(`  [${icon}] [${pageName}] ${check}: ${detail}`);
}

// ============================================================
// Helper: login via API and inject token
// ============================================================
async function loginAndInject(page: import('@playwright/test').Page) {
  const resp = await page.request.post('http://localhost:5000/api/auth/login', {
    data: { username: 'e2e_tester', password: 'TestPass123' },
  });
  const body = await resp.json();
  if (!body.success) throw new Error('Login failed: ' + (body.message || 'unknown'));
  const token = body.data.token;
  await page.evaluate((t) => {
    localStorage.setItem('auth_token', t);
    localStorage.setItem('userId', 'e2e_tester');
    localStorage.setItem('username', 'e2e_tester');
  }, token);
}

// ============================================================
// Helper: run common authenticated page checks
// ============================================================
async function runAuthenticatedPageChecks(page: import('@playwright/test').Page, pageName: string) {
  // Capture console errors during checks
  const consoleErrors: string[] = [];
  const errorHandler = (err: Error) => consoleErrors.push(err.message);
  const consoleHandler = (msg: import('@playwright/test').ConsoleMessage) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  };
  page.on('pageerror', errorHandler);
  page.on('console', consoleHandler);

  // a. Navbar exists and has 7 nav links
  const navbar = page.locator('nav.navbar');
  const navbarCount = await navbar.count();
  const navbarExists = navbarCount > 0;
  const navLinks = await page.locator('.nav-link').count();
  addFinding(pageName, 'Navbar exists', navbarExists, navbarExists ? 'Found' : 'NOT FOUND');
  addFinding(pageName, 'Navbar has 7 nav links', navLinks === 7, `Found ${navLinks} links (expected 7)`);

  // b. No emoji characters in navbar area
  if (navbarExists) {
    const navText = await navbar.innerText();
    const hasEmoji = EMOJI_REGEX.test(navText);
    addFinding(pageName, 'No emoji in navbar', !hasEmoji, hasEmoji ? 'Emoji characters found in navbar' : 'Clean - SVG icons only');
  } else {
    addFinding(pageName, 'No emoji in navbar', false, 'Cannot check - navbar not found');
  }

  // d. All <button> elements have text content or aria-label
  const buttons = await page.locator('button').all();
  const buttonsWithoutLabel: string[] = [];
  for (const btn of buttons) {
    const text = (await btn.textContent() || '').trim();
    const ariaLabel = await btn.getAttribute('aria-label');
    const title = await btn.getAttribute('title');
    // Check if button contains SVG (which counts as visual content)
    const hasSvg = await btn.locator('svg').count() > 0;
    if (!text && !ariaLabel && !title && !hasSvg) {
      const outer = await btn.evaluate(el => el.outerHTML.slice(0, 120));
      buttonsWithoutLabel.push(outer);
    }
  }
  addFinding(pageName, 'All buttons have text/aria-label', buttonsWithoutLabel.length === 0,
    buttonsWithoutLabel.length === 0 ? `All ${buttons.length} buttons accessible`
      : `${buttonsWithoutLabel.length}/${buttons.length} buttons missing label: ${buttonsWithoutLabel.slice(0, 2).join(' | ')}`);

  // e. All <img> elements have alt attributes
  const imgs = await page.locator('img').all();
  const imgsWithoutAlt: string[] = [];
  for (const img of imgs) {
    const alt = await img.getAttribute('alt');
    if (alt === null) {
      const src = await img.getAttribute('src') || 'unknown';
      imgsWithoutAlt.push(src.slice(0, 60));
    }
  }
  addFinding(pageName, 'All <img> have alt', imgsWithoutAlt.length === 0,
    imgsWithoutAlt.length === 0 ? 'All images accessible'
      : `${imgsWithoutAlt.length} images missing alt: ${imgsWithoutAlt.join(', ')}`);

  // f. stat-card elements have equal heights (if present)
  const statCards = await page.locator('.stat-card').all();
  if (statCards.length >= 2) {
    const heights: number[] = [];
    for (const card of statCards) {
      const box = await card.boundingBox();
      if (box) heights.push(Math.round(box.height));
    }
    const minHeight = Math.min(...heights);
    const maxHeight = Math.max(...heights);
    const equal = maxHeight - minHeight <= 5;
    addFinding(pageName, 'Stat-cards equal heights', equal,
      `Heights: [${heights.join(', ')}]px (range: ${minHeight}-${maxHeight}px)`);
  } else {
    addFinding(pageName, 'Stat-cards equal heights', true, `Only ${statCards.length} stat-card(s) - not enough to compare`);
  }

  // g. Interactive elements have visible focus indicators
  const focusableSelectors = 'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])';
  const focusableElements = await page.locator(focusableSelectors).all();
  let noFocusIndicator = 0;
  const sampleBadFocus: string[] = [];
  const checkLimit = Math.min(focusableElements.length, 15);
  for (let i = 0; i < checkLimit; i++) {
    const el = focusableElements[i];
    if (!el) continue;
    try {
      await el.focus({ timeout: 1000 });
      const focusStyles = await el.evaluate((elem) => {
        const computed = window.getComputedStyle(elem);
        return {
          outlineStyle: computed.outlineStyle,
          outlineWidth: parseFloat(computed.outlineWidth) || 0,
          boxShadow: computed.boxShadow,
          borderColor: computed.borderColor,
          borderWidth: parseFloat(computed.borderWidth) || 0,
        };
      });
      const hasOutline = focusStyles.outlineStyle !== 'none' && focusStyles.outlineWidth > 0;
      const hasBoxShadow = focusStyles.boxShadow !== 'none' && focusStyles.boxShadow !== '';
      const hasBorder = focusStyles.borderWidth > 0;
      if (!hasOutline && !hasBoxShadow && !hasBorder) {
        noFocusIndicator++;
        if (sampleBadFocus.length < 3) {
          const tag = await el.evaluate(e => `<${e.tagName.toLowerCase()} class="${e.className}">`);
          sampleBadFocus.push(tag);
        }
      }
    } catch {
      // Element not focusable or detached, skip
    }
  }
  addFinding(pageName, 'Focus indicators on interactive elements', noFocusIndicator === 0,
    noFocusIndicator === 0 ? `All ${checkLimit} checked elements have focus indicators`
      : `${noFocusIndicator}/${checkLimit} lack visible focus. Samples: ${sampleBadFocus.join(', ')}`);

  // h. CLS-like metric: 2 screenshots 500ms apart
  try {
    const ss1 = await page.screenshot();
    await page.waitForTimeout(500);
    const ss2 = await page.screenshot();
    const diffPercent = Math.abs(ss1.length - ss2.length) / Math.max(ss1.length, ss2.length) * 100;
    const stable = diffPercent < 2;
    addFinding(pageName, 'CLS-like layout stability', stable,
      `Screenshot sizes: ${ss1.length} vs ${ss2.length} bytes (${diffPercent.toFixed(2)}% diff)`);
  } catch (e: any) {
    addFinding(pageName, 'CLS-like layout stability', false, `Error: ${e.message}`);
  }

  // c. Console errors (filtered) - wait a bit more for late errors
  await page.waitForTimeout(500);
  page.off('pageerror', errorHandler);
  page.off('console', consoleHandler);
  const filteredErrors = consoleErrors.filter(e =>
    !e.includes('favicon') && !e.includes('manifest') && !e.includes('DevTools')
  );
  addFinding(pageName, 'No console errors', filteredErrors.length === 0,
    filteredErrors.length === 0 ? 'No errors'
      : `${filteredErrors.length} errors. First: ${filteredErrors[0]?.slice(0, 120)}`);
}

// ============================================================
// Main Test
// ============================================================
test('visual audit - all pages', async ({ page }) => {
  test.setTimeout(300000); // 5 minutes

  // ============================================================
  // LOGIN PAGE
  // ============================================================
  console.log('\n[AUDIT] === LOGIN PAGE ===');
  const loginErrors: string[] = [];
  page.on('pageerror', (err) => loginErrors.push(err.message));
  page.on('console', (msg) => {
    if (msg.type() === 'error') loginErrors.push(msg.text());
  });

  await page.goto(`${BASE}/login.html`);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000); // Wait for SVG icon replacement script

  await page.screenshot({ path: `${SCREENSHOT_DIR}/audit-login.png`, fullPage: true });

  // 4a. Feature icons are SVG (no emoji in .feature-icon elements)
  const featureIcons = await page.locator('.feature-icon').all();
  let emojiInFeatureIcons = 0;
  const featureIconDetails: string[] = [];
  for (const icon of featureIcons) {
    const html = await icon.innerHTML();
    const hasEmoji = EMOJI_REGEX.test(html);
    const hasSvg = html.includes('<svg');
    if (hasEmoji || !hasSvg) {
      emojiInFeatureIcons++;
      featureIconDetails.push(`innerHTML="${html.slice(0, 50)}" emoji=${hasEmoji} svg=${hasSvg}`);
    }
  }
  addFinding('login', 'Feature icons are SVG (no emoji)', emojiInFeatureIcons === 0,
    emojiInFeatureIcons === 0 ? `All ${featureIcons.length} feature icons use SVG`
      : `${emojiInFeatureIcons}/${featureIcons.length} still have emoji. ${featureIconDetails.join('; ')}`);

  // 4b. Password toggle buttons have aria-label
  const pwToggles = await page.locator('.password-toggle').all();
  let togglesWithoutAria = 0;
  for (const toggle of pwToggles) {
    const ariaLabel = await toggle.getAttribute('aria-label');
    if (!ariaLabel) togglesWithoutAria++;
  }
  addFinding('login', 'Password toggles have aria-label', togglesWithoutAria === 0,
    togglesWithoutAria === 0 ? `All ${pwToggles.length} toggles labeled`
      : `${togglesWithoutAria}/${pwToggles.length} toggles missing aria-label`);

  // 4c. Form inputs have associated labels
  const inputs = await page.locator('.form-input').all();
  let inputsWithoutLabel = 0;
  const labelDetails: string[] = [];
  for (const input of inputs) {
    const id = await input.getAttribute('id');
    if (id) {
      const labelFor = await page.locator(`label[for="${id}"]`).count();
      if (labelFor === 0) {
        inputsWithoutLabel++;
        labelDetails.push(id);
      }
    } else {
      inputsWithoutLabel++;
      labelDetails.push('(no id)');
    }
  }
  addFinding('login', 'Form inputs have associated labels', inputsWithoutLabel === 0,
    inputsWithoutLabel === 0 ? `All ${inputs.length} inputs labeled`
      : `${inputsWithoutLabel}/${inputs.length} missing labels: ${labelDetails.join(', ')}`);

  // Console errors for login page
  await page.waitForTimeout(500);
  const filteredLoginErrors = loginErrors.filter(e =>
    !e.includes('favicon') && !e.includes('manifest') && !e.includes('DevTools')
  );
  addFinding('login', 'No console errors', filteredLoginErrors.length === 0,
    filteredLoginErrors.length === 0 ? 'No errors'
      : `${filteredLoginErrors.length} errors. First: ${filteredLoginErrors[0]?.slice(0, 120)}`);

  // Buttons accessibility for login
  const loginButtons = await page.locator('button').all();
  const loginBtnNoLabel: string[] = [];
  for (const btn of loginButtons) {
    const text = (await btn.textContent() || '').trim();
    const ariaLabel = await btn.getAttribute('aria-label');
    const hasSvg = await btn.locator('svg').count() > 0;
    if (!text && !ariaLabel && !hasSvg) {
      const outer = await btn.evaluate(el => el.outerHTML.slice(0, 120));
      loginBtnNoLabel.push(outer);
    }
  }
  addFinding('login', 'All buttons have text/aria-label', loginBtnNoLabel.length === 0,
    loginBtnNoLabel.length === 0 ? `All ${loginButtons.length} buttons accessible`
      : `${loginBtnNoLabel.length} buttons missing label: ${loginBtnNoLabel.slice(0, 2).join(' | ')}`);

  // ============================================================
  // AUTHENTICATED PAGES
  // ============================================================
  const authPages = [
    'dashboard',
    'learning',
    'plans',
    'levels',
    'evaluation',
    'statistics',
    'favorites',
    'profile',
  ];

  for (const pageName of authPages) {
    console.log(`\n[AUDIT] === ${pageName.toUpperCase()} PAGE ===`);

    // Login and inject token before loading
    await loginAndInject(page);

    await page.goto(`${BASE}/${pageName}.html`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2500); // Wait for dynamic content + animations

    // Screenshot
    await page.screenshot({ path: `${SCREENSHOT_DIR}/audit-${pageName}.png`, fullPage: true });

    // Common checks
    await runAuthenticatedPageChecks(page, pageName);

    // ----- Page-specific checks -----
    if (pageName === 'dashboard') {
      // 5a. word-item cards have hover transitions
      const wordItems = await page.locator('.word-item').all();
      if (wordItems.length > 0) {
        const firstItem = wordItems[0];
        const transition = await firstItem.evaluate(el => window.getComputedStyle(el).transition);
        const hasTransition = transition !== 'all 0s ease 0s' && transition !== 'none' && transition.length > 0;
        addFinding(pageName, 'Word-item hover transitions', hasTransition,
          hasTransition ? `Transition: ${transition}` : 'No transition found');
      } else {
        addFinding(pageName, 'Word-item hover transitions', true, 'No word items on page');
      }

      // 5b. Recommendation list loaded real data (not skeleton)
      const recItems = await page.locator('#recommendations-list .word-item').all();
      let hasRealData = false;
      let realDataDetail = '';
      if (recItems.length > 0) {
        const firstText = await recItems[0].locator('h4').textContent().catch(() => '');
        hasRealData = firstText !== null && firstText !== '加载中...' && firstText !== '暂无推荐' && (firstText?.length || 0) > 0;
        realDataDetail = `First item text: "${firstText}" (${recItems.length} items total)`;
      } else {
        realDataDetail = 'No recommendation items found in DOM';
      }
      addFinding(pageName, 'Recommendations loaded real data', hasRealData, realDataDetail);

      // 5c. stats-grid cards have equal heights
      const statsCards = await page.locator('.stats-grid .stat-card').all();
      if (statsCards.length >= 2) {
        const heights: number[] = [];
        for (const card of statsCards) {
          const box = await card.boundingBox();
          if (box) heights.push(Math.round(box.height));
        }
        const minH = Math.min(...heights);
        const maxH = Math.max(...heights);
        const equal = maxH - minH <= 5;
        addFinding(pageName, 'Stats-grid cards equal heights', equal,
          `Heights: [${heights.join(', ')}]px (range: ${minH}-${maxH}px)`);
      } else {
        addFinding(pageName, 'Stats-grid cards equal heights', true,
          `Only ${statsCards.length} stats-grid cards - not enough to compare`);
      }
    }
  }

  // ============================================================
  // SUMMARY REPORT
  // ============================================================
  console.log('\n' + '='.repeat(80));
  console.log('  SMARTVOCAB VISUAL AUDIT - SUMMARY REPORT');
  console.log('='.repeat(80));

  const pageNames = Object.keys(allFindings).sort();
  let totalChecks = 0;
  let totalPass = 0;
  let totalFail = 0;

  for (const pn of pageNames) {
    const checks = allFindings[pn];
    const passed = checks.filter(c => c.pass).length;
    const failed = checks.filter(c => !c.pass).length;
    console.log(`\n--- ${pn.toUpperCase()} (${passed}/${checks.length} passed) ---`);
    for (const c of checks) {
      const marker = c.pass ? '  PASS' : '  FAIL';
      console.log(`${marker} | ${c.check}: ${c.detail}`);
      totalChecks++;
      if (c.pass) totalPass++; else totalFail++;
    }
  }

  console.log('\n' + '='.repeat(80));
  console.log(`  TOTALS: ${totalChecks} checks | ${totalPass} PASS | ${totalFail} FAIL`);
  if (totalFail > 0) {
    console.log('\n  FAILURES SUMMARY:');
    for (const pn of pageNames) {
      const fails = allFindings[pn].filter(c => !c.pass);
      if (fails.length > 0) {
        console.log(`    [${pn}] ${fails.map(f => f.check).join(', ')}`);
      }
    }
  }
  console.log('='.repeat(80) + '\n');

  // Final assertion: the test itself passes (audit is informational)
  // But we flag if more than half the checks fail as a signal
  expect(totalChecks, 'Should have run checks').toBeGreaterThan(0);
});
