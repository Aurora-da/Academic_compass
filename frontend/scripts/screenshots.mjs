import { chromium } from 'playwright-core'
import fs from 'node:fs'
import path from 'node:path'

const OUT = path.resolve('../docs/screenshots')
fs.mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({
  headless: true,
  executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  args: ['--no-sandbox', '--disable-gpu', '--font-render-hinting=none'],
})

const context = await browser.newContext({
  viewport: { width: 1440, height: 950 },
  deviceScaleFactor: 1,
  locale: 'zh-CN',
})
const page = await context.newPage()
const errors = []
page.on('pageerror', (e) => errors.push(`PAGEERROR: ${e.message}`))
page.on('console', (m) => {
  if (m.type() === 'error') errors.push(`CONSOLE: ${m.text()}`)
})

async function shot(name, fullPage = true) {
  await page.waitForTimeout(1400)
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage })
  console.log('shot', name)
}

await page.goto('http://127.0.0.1:8000/login', { waitUntil: 'networkidle' })
await page.waitForTimeout(1200)
await shot('01-login', false)

await page.fill('input[placeholder="学号或 admin"]', '2023001')
await page.fill('input[placeholder="演示密码 123456"]', '123456')
await page.click('button[type="submit"]')
await page.waitForURL('http://127.0.0.1:8000/', { timeout: 30000 })
await page.waitForSelector('.hero', { timeout: 30000 })
await shot('02-dashboard')

await page.goto('http://127.0.0.1:8000/plan', { waitUntil: 'networkidle' })
await page.waitForSelector('.plan-layout', { timeout: 30000 })
await page.waitForTimeout(800)
const treeInfo = await page.evaluate(() => ({
  top: document.querySelector('.tree-body')?.scrollTop,
  height: document.querySelector('.tree-body')?.clientHeight,
  scrollHeight: document.querySelector('.tree-body')?.scrollHeight,
  active: document.querySelector('.tree-body .node-card.active')?.innerText.slice(0, 24),
}))
console.log('tree', JSON.stringify(treeInfo))
await shot('03-plan')

await page.goto('http://127.0.0.1:8000/recommend', { waitUntil: 'networkidle' })
await page.waitForSelector('.direction-grid', { timeout: 30000 })
await shot('04-recommend')

await page.goto('http://127.0.0.1:8000/report', { waitUntil: 'networkidle' })
await page.waitForSelector('.report-sheet', { timeout: 30000 })
await shot('05-report')

await page.goto('http://127.0.0.1:8000/second-classroom', { waitUntil: 'networkidle' })
await page.waitForSelector('.sc-grid', { timeout: 30000 })
await shot('06-second-classroom')

await page.goto('http://127.0.0.1:8000/import', { waitUntil: 'networkidle' })
await page.waitForSelector('.dropzone', { timeout: 30000 })
await shot('07-import')

await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' })
await page.waitForSelector('.hero', { timeout: 30000 })
await page.click('.assistant-orb')
await page.waitForSelector('.assistant-panel', { timeout: 15000 })
await page.fill('.composer textarea', '我还差多少学分？')
await page.click('.send-btn')
await page.waitForSelector('.agent-extras', { timeout: 60000 })
await page.waitForTimeout(1200)
await page.evaluate(() => {
  const el = document.querySelector('.assistant-body')
  if (el) el.scrollTop = 0
})
await page.waitForTimeout(500)
await shot('08-assistant', false)

// admin
const admin = await browser.newContext({ viewport: { width: 1440, height: 950 }, locale: 'zh-CN' })
const ap = await admin.newPage()
ap.on('pageerror', (e) => errors.push(`ADMIN PAGEERROR: ${e.message}`))
await ap.goto('http://127.0.0.1:8000/login', { waitUntil: 'networkidle' })
await ap.fill('input[placeholder="学号或 admin"]', 'admin')
await ap.fill('input[placeholder="演示密码 123456"]', '123456')
await ap.click('button[type="submit"]')
await ap.waitForURL('**/admin', { timeout: 30000 })
await ap.waitForSelector('.admin-tabs', { timeout: 30000 })
await ap.waitForTimeout(1500)
await ap.screenshot({ path: path.join(OUT, '09-admin.png'), fullPage: true })
console.log('shot 09-admin')

await ap.click('button:has-text("方案试算")')
await ap.waitForTimeout(700)
await ap.click('button:has-text("运行试算")')
await ap.waitForSelector('.trial-results', { timeout: 30000 })
await ap.waitForTimeout(1200)
await ap.screenshot({ path: path.join(OUT, '10-admin-trial.png'), fullPage: true })
console.log('shot 10-admin-trial')

fs.writeFileSync(path.join(OUT, 'console-errors.txt'), errors.join('\n'), 'utf-8')
console.log('errors', errors.length)
for (const e of errors.slice(0, 20)) console.log(e)
await browser.close()
