import { chromium } from 'playwright-core'

const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  args: ['--no-sandbox', '--disable-gpu'],
})
const page = await browser.newPage({ viewport: { width: 1440, height: 950 }, locale: 'zh-CN' })
await page.goto('http://127.0.0.1:8000/login', { waitUntil: 'networkidle' })
await page.fill('input[placeholder="学号或 admin"]', '2023001')
await page.fill('input[placeholder="演示密码 123456"]', '123456')
await page.click('button[type="submit"]')
await page.waitForURL('http://127.0.0.1:8000/')
await page.goto('http://127.0.0.1:8000/plan', { waitUntil: 'networkidle' })
await page.waitForSelector('.plan-layout')
await page.waitForTimeout(1500)
console.log(
  await page.evaluate(() => ({
    top: document.querySelector('.tree-body')?.scrollTop,
    active: document.querySelector('.tree-body .node-card.active')?.innerText.slice(0, 30),
    activeTop: document.querySelector('.tree-body .node-card.active')?.getBoundingClientRect().top,
  })),
)
await page.screenshot({ path: '../docs/screenshots/03-plan-viewport.png' })
await browser.close()
