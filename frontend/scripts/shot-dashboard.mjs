import { chromium } from 'playwright-core'
import path from 'node:path'

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
await page.waitForSelector('.hero')
await page.waitForTimeout(1600)
await page.screenshot({ path: path.resolve('../docs/screenshots/02-dashboard.png'), fullPage: true })
console.log('dashboard recaptured')
await browser.close()
