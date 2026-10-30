<template>
  <teleport to="body">
    <button v-if="!open" class="assistant-orb" title="打开学业助手" @click="open = true">
      <span class="orb-ring" />
      <span class="orb-face"><UiIcon name="sparkles" :size="20" /></span>
      <span class="orb-badge">AI</span>
    </button>

    <transition name="assistant">
      <section v-if="open" class="assistant-panel">
        <header class="assistant-head">
          <div class="assistant-brand">
            <span class="assistant-avatar"><UiIcon name="sparkles" :size="18" /></span>
            <div>
              <strong>学业助手</strong>
              <span>审核 · 选课 · 规章问答</span>
            </div>
          </div>
          <div class="assistant-head-actions">
            <span class="chip" :class="meta.llmEnabled ? 'chip-ok' : 'chip-warn'">
              <span class="dot" :class="meta.llmEnabled ? '' : 'warn'" />
              {{ meta.llmEnabled ? '在线模型' : '离线模板' }}
            </span>
            <button class="icon-btn" title="新会话" @click="reset">
              <UiIcon name="refresh" :size="16" />
            </button>
            <button class="icon-btn" title="收起" @click="open = false">
              <UiIcon name="close" :size="17" />
            </button>
          </div>
        </header>

        <div ref="scroller" class="assistant-body">
          <div v-if="!messages.length" class="assistant-welcome">
            <div class="welcome-glow">
              <span class="welcome-icon"><UiIcon name="compass" :size="26" /></span>
            </div>
            <h3>把你的学分账本交给我</h3>
            <p>
              所有数字由确定性引擎计算，我只负责解释。可以问我缺口、选课、方向，或者规章原文。
            </p>
            <div class="suggest-list">
              <button v-for="q in suggestions" :key="q" class="suggestion" @click="send(q)">
                <span>{{ q }}</span>
                <UiIcon name="arrow-right" :size="13" />
              </button>
            </div>
            <div class="welcome-foot">
              <UiIcon name="shield" :size="13" />
              不承诺“一定毕业”，结论均标注“预演，以教务处终审为准”
            </div>
          </div>

          <div v-for="(msg, idx) in messages" :key="idx" class="msg" :class="msg.role">
            <template v-if="msg.role === 'user'">
              <div class="msg-user">{{ msg.content }}</div>
            </template>
            <template v-else>
              <div class="msg-agent">
                <div class="agent-mark"><UiIcon name="sparkles" :size="14" /></div>
                <div class="agent-main">
                  <div v-if="msg.process && msg.process.length" class="process">
                    <button class="process-toggle" @click="msg.showProcess = !msg.showProcess">
                      <span class="process-status">
                        <span v-if="msg.streaming" class="spinner dark" />
                        <UiIcon v-else name="check" :size="12" />
                        {{ msg.streaming ? '正在计算…' : `已完成 ${msg.process.length} 步` }}
                      </span>
                      <UiIcon :name="msg.showProcess ? 'chevron-down' : 'chevron'" :size="12" />
                    </button>
                    <transition name="fade">
                      <div v-if="msg.showProcess || msg.streaming" class="process-list">
                        <div
                          v-for="step in msg.process"
                          :key="step.node + step.status"
                          class="process-step"
                          :class="step.status"
                        >
                          <span class="step-dot" />
                          <span>{{ step.label }}</span>
                        </div>
                      </div>
                    </transition>
                  </div>

                  <div v-if="msg.content" class="agent-bubble">
                    <MarkdownView :content="msg.content" />
                    <span v-if="msg.streaming" class="typing-cursor" />
                  </div>
                  <div v-else-if="msg.streaming" class="agent-bubble thinking">
                    <span class="thinking-dots"><i /><i /><i /></span>
                    正在读取培养方案与成绩…
                  </div>

                  <div v-if="msg.done" class="agent-extras">
                    <div v-if="msg.done.audit_summary" class="mini-stats">
                      <span><em>已获</em><strong>{{ fmt(msg.done.audit_summary.earned) }}</strong></span>
                      <span><em>缺口</em><strong>{{ fmt(msg.done.audit_summary.gap) }}</strong></span>
                      <span><em>在修</em><strong>{{ fmt(msg.done.audit_summary.studying) }}</strong></span>
                      <span><em>完成度</em><strong>{{ fmt(msg.done.audit_summary.percent, 1) }}%</strong></span>
                    </div>
                    <div v-if="msg.done.simulation" class="sim-note">
                      <UiIcon name="alert" :size="13" />
                      {{ msg.done.simulation.verdict }}
                    </div>
                    <div v-if="msg.done.verification" class="verify-line">
                      <UiIcon :name="msg.done.verification.ok ? 'shield' : 'alert'" :size="12" />
                      {{ msg.done.verification.ok ? '数字一致性校验通过' : '数字校验存在偏差，已降级为模板输出' }}
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>

        <footer class="assistant-foot">
          <div class="composer">
            <textarea
              ref="inputRef"
              v-model="draft"
              rows="1"
              placeholder="问：我还差多少学分？这学期该选什么？"
              :disabled="streaming"
              @keydown.enter.exact.prevent="onEnter"
              @input="autoGrow"
            />
            <button v-if="streaming" class="send-btn stop" title="停止生成" @click="stop">
              <UiIcon name="close" :size="16" />
            </button>
            <button v-else class="send-btn" :disabled="!draft.trim()" title="发送" @click="send()">
              <UiIcon name="send" :size="16" />
            </button>
          </div>
          <div class="composer-hint">
            <span>Enter 发送 · Shift+Enter 换行</span>
            <span class="mono">{{ meta.engineVersion }}</span>
          </div>
        </footer>
      </section>
    </transition>
  </teleport>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import MarkdownView from './MarkdownView.vue'
import UiIcon from './UiIcon.vue'
import { streamChat, getErrorMessage } from '@/api'
import { useMetaStore } from '@/stores/meta'
import { useToastStore } from '@/stores/toast'

const open = defineModel('open', { type: Boolean, default: false })
const meta = useMetaStore()
const toast = useToastStore()

const messages = ref([])
const draft = ref('')
const scroller = ref(null)
const inputRef = ref(null)
const streaming = ref(false)
let controller = null
let sessionId = localStorage.getItem('ac_chat_session') || ''

const suggestions = [
  '我还差多少学分？',
  '我这学期该选什么？',
  '专业任选课有什么要求？',
  '如果我挂了编译原理会怎样？',
]

function fmt(value, digits = 1) {
  return Number(value || 0).toFixed(digits)
}

function reset() {
  stop()
  messages.value = []
  draft.value = ''
  sessionId = ''
  localStorage.removeItem('ac_chat_session')
}

function stop() {
  if (controller) {
    controller.abort()
    controller = null
  }
  streaming.value = false
  const last = messages.value[messages.value.length - 1]
  if (last && last.streaming) last.streaming = false
}

function autoGrow() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 140)}px`
}

function onEnter() {
  if (streaming.value) return
  send()
}

async function scrollBottom() {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

async function send(text) {
  const content = (text ?? draft.value).trim()
  if (!content || streaming.value) return
  draft.value = ''
  await nextTick()
  autoGrow()
  messages.value.push({ role: 'user', content })
  const index = messages.value.push({
    role: 'assistant',
    content: '',
    process: [],
    showProcess: true,
    streaming: true,
    done: null,
  }) - 1
  await scrollBottom()

  streaming.value = true
  controller = new AbortController()
  try {
    await streamChat({
      message: content,
      sessionId: sessionId || undefined,
      signal: controller.signal,
      onEvent: (ev) => {
        const msg = messages.value[index]
        if (!msg) return
        if (ev.type === 'meta') {
          if (ev.session_id) {
            sessionId = ev.session_id
            localStorage.setItem('ac_chat_session', sessionId)
          }
        } else if (ev.type === 'node') {
          const existing = msg.process.find((p) => p.node === ev.node)
          if (existing) existing.status = ev.status
          else msg.process.push({ node: ev.node, label: ev.label, status: ev.status })
          if (ev.node === 'compose' && ev.status === 'done') msg.showProcess = false
          scrollBottom()
        } else if (ev.type === 'token') {
          msg.content += ev.content
          scrollBottom()
        } else if (ev.type === 'done') {
          if (ev.answer) msg.content = ev.answer
          msg.done = ev
          msg.streaming = false
        } else if (ev.type === 'error') {
          msg.content = `抱歉，生成失败：${ev.message}`
          msg.streaming = false
        }
      },
    })
  } catch (error) {
    if (error.name !== 'AbortError') {
      toast.error(getErrorMessage(error))
      const msg = messages.value[index]
      if (msg) {
        msg.content = msg.content || `请求失败：${getErrorMessage(error)}`
        msg.streaming = false
      }
    }
  } finally {
    streaming.value = false
    controller = null
    const msg = messages.value[index]
    if (msg) msg.streaming = false
    scrollBottom()
  }
}

watch(open, async (value) => {
  if (value) {
    await nextTick()
    inputRef.value?.focus()
    scrollBottom()
  }
})
</script>

<style scoped>
.assistant-orb {
  position: fixed;
  z-index: 180;
  right: 28px;
  bottom: 28px;
  width: 58px;
  height: 58px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(30, 78, 216, 0.2);
  box-shadow: 0 18px 40px rgba(47, 102, 232, 0.26), 0 2px 8px rgba(12, 22, 48, 0.08);
  backdrop-filter: blur(12px);
  display: grid;
  place-items: center;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.assistant-orb:hover {
  transform: translateY(-3px) scale(1.04);
  box-shadow: 0 24px 50px rgba(47, 102, 232, 0.34);
}

.orb-ring {
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  background: conic-gradient(from 0deg, #1e4ed8, #0b8f7b, #2f66e8, #1e4ed8);
  opacity: 0.32;
  filter: blur(3px);
  animation: spin 6s linear infinite;
}

.orb-face {
  position: relative;
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  color: #fff;
  background: var(--grad);
  box-shadow: inset 0 0 12px rgba(255, 255, 255, 0.25);
}

.orb-badge {
  position: absolute;
  right: -2px;
  top: -2px;
  height: 18px;
  padding: 0 5px;
  border-radius: 6px;
  background: #0b1226;
  color: #9ff5e8;
  font-size: 8.5px;
  font-weight: 800;
  letter-spacing: 0.08em;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.assistant-panel {
  position: fixed;
  z-index: 240;
  right: 26px;
  bottom: 26px;
  width: min(432px, calc(100vw - 32px));
  height: min(690px, calc(100vh - 52px));
  display: flex;
  flex-direction: column;
  border-radius: 24px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 40px 100px rgba(10, 18, 38, 0.28), 0 4px 16px rgba(10, 18, 38, 0.08);
  backdrop-filter: blur(26px) saturate(1.15);
}

.assistant-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 15px 16px;
  color: #e9eeff;
  background: linear-gradient(140deg, #111b38, #1b2a54 55%, #123047);
}

.assistant-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.assistant-avatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: var(--grad);
  display: grid;
  place-items: center;
  color: #fff;
  box-shadow: 0 8px 20px rgba(47, 102, 232, 0.35);
}

.assistant-brand strong {
  display: block;
  font-size: 13.5px;
}

.assistant-brand span {
  display: block;
  color: #8ea0c9;
  font-size: 10.5px;
  margin-top: 2px;
}

.assistant-head-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.assistant-head-actions .chip {
  background: rgba(255, 255, 255, 0.08);
  color: #cdd8f5;
}

.icon-btn {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  color: #a6b4d8;
}

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.assistant-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 16px 8px;
  background: linear-gradient(180deg, rgba(244, 246, 252, 0.5), rgba(255, 255, 255, 0.7));
}

.assistant-welcome {
  padding: 10px 4px;
  text-align: center;
}

.welcome-glow {
  width: 64px;
  height: 64px;
  margin: 4px auto 14px;
  border-radius: 22px;
  display: grid;
  place-items: center;
  background: var(--grad-soft);
  border: 1px solid rgba(30, 78, 216, 0.16);
  animation: floaty 6s ease-in-out infinite;
}

.welcome-icon {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--grad);
}

.assistant-welcome h3 {
  font-size: 16px;
  margin-bottom: 7px;
}

.assistant-welcome p {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.65;
  max-width: 310px;
  margin: 0 auto;
}

.suggest-list {
  display: grid;
  gap: 7px;
  margin: 18px 0 14px;
}

.suggestion {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 11px 13px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid var(--line);
  font-size: 12.5px;
  color: var(--ink-2);
  text-align: left;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.suggestion:hover {
  transform: translateY(-1px);
  border-color: rgba(30, 78, 216, 0.28);
  box-shadow: 0 8px 20px rgba(47, 102, 232, 0.12);
  color: var(--violet);
}

.welcome-foot {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  color: var(--muted-2);
  font-size: 10px;
  line-height: 1.5;
}

.msg {
  margin-bottom: 14px;
  animation: revealUp 0.3s ease both;
}

.msg-user {
  margin-left: auto;
  width: fit-content;
  max-width: 84%;
  padding: 10px 13px;
  border-radius: 16px 16px 4px 16px;
  background: linear-gradient(135deg, #1e4ed8, #2f66e8);
  color: #fff;
  font-size: 13px;
  line-height: 1.6;
  box-shadow: 0 8px 20px rgba(47, 102, 232, 0.22);
}

.msg-agent {
  display: flex;
  gap: 9px;
}

.agent-mark {
  flex: none;
  width: 26px;
  height: 26px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--grad);
  margin-top: 2px;
}

.agent-main {
  min-width: 0;
  flex: 1;
}

.agent-bubble {
  padding: 12px 14px;
  border-radius: 4px 16px 16px 16px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--line);
  box-shadow: 0 4px 14px rgba(12, 22, 48, 0.04);
  font-size: 13px;
}

.agent-bubble.thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 12px;
}

.thinking-dots {
  display: inline-flex;
  gap: 3px;
}

.thinking-dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--violet);
  animation: blink 1.2s infinite ease-in-out;
}

.thinking-dots i:nth-child(2) {
  animation-delay: 0.18s;
}

.thinking-dots i:nth-child(3) {
  animation-delay: 0.36s;
}

@keyframes blink {
  0%, 80%, 100% {
    opacity: 0.25;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-2px);
  }
}

.typing-cursor {
  display: inline-block;
  width: 2px;
  height: 13px;
  margin-left: 2px;
  background: var(--violet);
  vertical-align: -2px;
  animation: blink 0.9s infinite;
}

.process {
  margin-bottom: 6px;
}

.process-toggle {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 3px 0;
  color: var(--muted);
  font-size: 10.5px;
}

.process-toggle:hover {
  color: var(--violet);
}

.process-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.process-status .spinner {
  width: 11px;
  height: 11px;
  border-width: 1.5px;
}

.process-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  padding: 5px 0 7px;
}

.process-step {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 22px;
  padding: 0 8px;
  border-radius: 6px;
  background: rgba(21, 32, 43, 0.04);
  color: var(--muted);
  font-size: 9.5px;
}

.process-step.done {
  color: #0b6b5b;
  background: rgba(18, 131, 111, 0.08);
}

.step-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
}

.agent-extras {
  margin-top: 8px;
  display: grid;
  gap: 6px;
}

.mini-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}

.mini-stats span {
  display: grid;
  gap: 2px;
  padding: 8px 9px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid var(--line);
}

.mini-stats em {
  font-style: normal;
  font-size: 9px;
  color: var(--muted-2);
}

.mini-stats strong {
  font-size: 14px;
  font-family: var(--font-display);
  letter-spacing: -0.02em;
}

.sim-note,
.verify-line {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  padding: 7px 9px;
  border-radius: 9px;
  font-size: 10.5px;
  line-height: 1.5;
}

.sim-note {
  color: #94530f;
  background: rgba(178, 106, 27, 0.09);
}

.verify-line {
  color: var(--muted-2);
  background: rgba(21, 32, 43, 0.03);
}

.assistant-foot {
  padding: 12px 14px 12px;
  border-top: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.85);
}

.composer {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 7px 7px 7px 12px;
  border-radius: 15px;
  border: 1px solid var(--line-strong);
  background: #fff;
  box-shadow: 0 6px 18px rgba(12, 22, 48, 0.05);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.composer:focus-within {
  border-color: rgba(30, 78, 216, 0.4);
  box-shadow: 0 0 0 4px rgba(30, 78, 216, 0.08);
}

.composer textarea {
  flex: 1;
  border: 0;
  outline: 0;
  resize: none;
  background: transparent;
  font-size: 13px;
  line-height: 1.55;
  max-height: 140px;
  padding: 5px 0;
}

.send-btn {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  color: #fff;
  background: var(--grad);
  box-shadow: 0 6px 16px rgba(47, 102, 232, 0.28);
  flex: none;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.send-btn:disabled {
  opacity: 0.35;
  box-shadow: none;
}

.send-btn.stop {
  background: linear-gradient(135deg, #f43f5e, #e11d48);
}

.composer-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 7px;
  padding: 0 3px;
  color: var(--muted-2);
  font-size: 9.5px;
}

.assistant-enter-active,
.assistant-leave-active {
  transition: opacity 0.22s ease, transform 0.32s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.assistant-enter-from,
.assistant-leave-to {
  opacity: 0;
  transform: translateY(18px) scale(0.98);
}

@media (max-width: 640px) {
  .assistant-panel {
    right: 0;
    bottom: 0;
    width: 100vw;
    height: 100dvh;
    border-radius: 0;
  }

  .assistant-orb {
    right: 18px;
    bottom: 18px;
  }
}

/* ---- warm editorial assistant ---- */
.assistant-orb {
  width: 54px;
  height: 54px;
  border-radius: 14px;
  background: var(--ink);
  border: 1px solid var(--ink);
  box-shadow: 0 16px 36px rgba(21, 32, 43, 0.22);
  color: #fbfaf6;
  backdrop-filter: none;
}

.assistant-orb:hover {
  transform: translateY(-2px);
  box-shadow: 0 20px 42px rgba(21, 32, 43, 0.28);
}

.orb-ring {
  display: none;
}

.orb-face {
  width: 46px;
  height: 46px;
  border-radius: 11px;
  background: transparent;
  box-shadow: none;
}

.orb-badge {
  right: -3px;
  top: -3px;
  height: 16px;
  border-radius: 4px;
  background: var(--violet);
  color: #fff;
  border: 2px solid var(--bg);
  font-size: 8px;
  letter-spacing: 0.06em;
}

.assistant-panel {
  width: min(430px, calc(100vw - 32px));
  border-radius: 18px;
  background: var(--card-solid);
  border: 1px solid var(--line-strong);
  box-shadow: 0 36px 90px rgba(21, 32, 43, 0.22), 0 3px 12px rgba(21, 32, 43, 0.06);
  backdrop-filter: none;
}

.assistant-head {
  padding: 14px 15px;
  color: #f7f4ec;
  background: var(--ink);
}

.assistant-avatar {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: rgba(255, 254, 250, 0.12);
  box-shadow: none;
}

.assistant-brand strong {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.assistant-brand span {
  color: rgba(247, 244, 236, 0.58);
  font-size: 10px;
}

.assistant-head-actions .chip {
  background: rgba(255, 254, 250, 0.08);
  border-color: rgba(255, 254, 250, 0.16);
  color: #e7e1d4;
}

.icon-btn {
  border-radius: 6px;
  color: rgba(247, 244, 236, 0.62);
}

.icon-btn:hover {
  background: rgba(255, 254, 250, 0.1);
  color: #fffefa;
}

.assistant-body {
  padding: 20px 16px 10px;
  background: var(--bg);
}

.assistant-welcome {
  text-align: left;
  padding: 6px 2px;
}

.welcome-glow {
  width: 48px;
  height: 48px;
  margin: 2px 0 14px;
  border-radius: 50%;
  background: transparent;
  border: 1px solid var(--line-strong);
  animation: none;
}

.welcome-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--violet);
  color: #fff;
}

.assistant-welcome h3 {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.02em;
  margin-bottom: 6px;
}

.assistant-welcome p {
  max-width: 340px;
  margin: 0;
  font-size: 12px;
  line-height: 1.75;
}

.suggest-list {
  gap: 0;
  margin: 20px 0 16px;
  border-top: 1px solid var(--line);
}

.suggestion {
  padding: 12px 2px;
  border: 0;
  border-bottom: 1px solid var(--line);
  border-radius: 0;
  background: transparent;
  font-size: 12px;
  transition: color 0.18s ease, padding-left 0.18s ease;
}

.suggestion:hover {
  transform: none;
  border-color: var(--line);
  box-shadow: none;
  color: var(--violet);
  padding-left: 5px;
}

.welcome-foot {
  justify-content: flex-start;
  font-size: 9.5px;
}

.msg-user {
  border-radius: 10px 10px 3px 10px;
  background: var(--violet);
  box-shadow: none;
  font-size: 12.5px;
}

.agent-mark {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: var(--ink);
}

.agent-bubble {
  padding: 12px 13px;
  border-radius: 3px 10px 10px 10px;
  background: var(--card-solid);
  border: 1px solid var(--line);
  box-shadow: none;
  font-size: 12.5px;
}

.process-step {
  height: 20px;
  border-radius: 4px;
  font-size: 9px;
}

.mini-stats span {
  border-radius: 6px;
  background: var(--card-solid);
}

.mini-stats strong {
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 500;
}

.sim-note,
.verify-line {
  border-radius: 5px;
}

.assistant-foot {
  padding: 11px 13px;
  background: var(--card-solid);
}

.composer {
  border-radius: 9px;
  background: var(--card-solid);
  box-shadow: none;
}

.composer:focus-within {
  border-color: rgba(30, 78, 216, 0.45);
  box-shadow: 0 0 0 3px rgba(30, 78, 216, 0.08);
}

.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 7px;
  background: var(--violet);
  box-shadow: none;
}

.send-btn.stop {
  background: var(--rose);
}
</style>
