const { chromium, devices } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const iphone = devices['iPhone 13'];
  const context = await browser.newContext({ ...iphone });
  const page = await context.newPage();
  await page.goto('https://www.avito.ru', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);

  const result = await page.evaluate(() => {
    function styleOf(el) {
      const cs = getComputedStyle(el);
      return {
        tag: el.tagName,
        class: el.className,
        border: cs.border,
        borderRadius: cs.borderRadius,
        backgroundImage: cs.backgroundImage,
        backgroundColor: cs.backgroundColor,
        boxShadow: cs.boxShadow,
        padding: cs.padding,
      };
    }
    const inputs = Array.from(document.querySelectorAll('input'));
    const searchInput = inputs.find(i => (i.placeholder || '').includes('Поиск')) || inputs[0];
    if (!searchInput) return { error: 'no input found on page' };

    const chain = [];
    let el = searchInput;
    for (let i = 0; i < 6 && el; i++) {
      chain.push(styleOf(el));
      el = el.parentElement;
    }
    return chain;
  });

  console.log(JSON.stringify(result, null, 2));
  await page.screenshot({ path: '/root/avito-inspect/avito-top.png', clip: { x: 0, y: 0, width: 390, height: 520 } });
  await browser.close();
})();
