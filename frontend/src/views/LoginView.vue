<template>
  <div class="login-page">
    <section class="login-hero">
      <div class="hero-brand">
        <div class="brand-mark">
          <span class="brand-core">学</span>
        </div>
        <div class="brand-text">
          <strong>学业罗盘</strong>
          <span>Academic Compass</span>
        </div>
      </div>

      <div class="hero-copy">
        <div class="eyebrow">Academic Compass · 2024</div>
        <h1>
          看清每一分，<br />
          走稳<span class="accent">每一步</span>。
        </h1>
        <p>
          把培养方案、已修课程和当学期开课放在同一张图上。数字由约束引擎计算，
          学业助手只负责把结果讲清楚。
        </p>

        <ol class="hero-list">
          <li>
            <span class="num">01</span>
            <div><strong>算得准</strong><p>模块、子项、选修模式逐层核对，学分可复现。</p></div>
          </li>
          <li>
            <span class="num">02</span>
            <div><strong>说得清</strong><p>每个数字都能追溯到具体课程与规则。</p></div>
          </li>
          <li>
            <span class="num">03</span>
            <div><strong>接得进</strong><p>文件、插件、API 多种方式接入已有数据。</p></div>
          </li>
        </ol>
      </div>

      <div class="hero-foot">
        <span>学业预演 · 最终以教务处审核为准</span>
      </div>
    </section>

    <section class="login-side">
      <div class="login-card reveal">
        <div class="login-head">
          <h2>登录学业罗盘</h2>
          <p>登录后查看你的学分账本与选课建议。</p>
        </div>

        <form class="login-form" @submit.prevent="submit">
          <div class="field">
            <label>账号</label>
            <div class="input-with-icon">
              <UiIcon name="user" :size="16" />
              <input v-model.trim="form.username" class="input" placeholder="学号或 admin" autocomplete="username" />
            </div>
          </div>
          <div class="field">
            <label>密码</label>
            <div class="input-with-icon">
              <UiIcon name="lock" :size="16" />
              <input
                v-model="form.password"
                class="input"
                :type="showPassword ? 'text' : 'password'"
                placeholder="演示密码 123456"
                autocomplete="current-password"
              />
              <button type="button" class="pwd-toggle" @click="showPassword = !showPassword">
                <UiIcon :name="showPassword ? 'eye-off' : 'eye'" :size="14" />
              </button>
            </div>
          </div>

          <transition name="fade">
            <div v-if="error" class="login-error">
              <UiIcon name="alert" :size="14" />
              {{ error }}
            </div>
          </transition>

          <button class="btn btn-primary login-submit" type="submit" :disabled="auth.loading || !form.username || !form.password">
            <span v-if="auth.loading" class="spinner" />
            {{ auth.loading ? '正在进入…' : '进入学业罗盘' }}
            <UiIcon v-if="!auth.loading" name="arrow-right" :size="16" />
          </button>
        </form>

        <div class="demo-block" v-if="demos.length">
          <div class="demo-title">
            <span>演示账号</span>
            <span class="muted small">点击直接进入</span>
          </div>
          <div class="demo-list">
            <button
              v-for="account in demos"
              :key="account.username"
              class="demo-item"
              :disabled="auth.loading"
              @click="quickLogin(account)"
            >
              <span class="demo-meta">
                <strong>{{ account.display_name }}</strong>
                <small>{{ account.role === 'admin' ? '管理员账号' : '学生账号' }}</small>
              </span>
              <UiIcon name="arrow-right" :size="14" />
            </button>
          </div>
        </div>

        <p class="login-note">
          本项目仅用于学业预演，最终结果以教务处审核为准。
        </p>
      </div>
    </section>

    <ToastHost />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ToastHost from '@/components/ToastHost.vue'
import UiIcon from '@/components/UiIcon.vue'
import { api, getErrorMessage } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useMetaStore } from '@/stores/meta'

const auth = useAuthStore()
const meta = useMetaStore()
const router = useRouter()
const route = useRoute()

const form = reactive({ username: '', password: '' })
const showPassword = ref(false)
const error = ref('')
const demos = ref([])

function go() {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  if (auth.isAdmin) {
    router.replace(redirect.startsWith('/admin') ? redirect : '/admin')
  } else {
    router.replace(redirect && !redirect.startsWith('/admin') ? redirect : '/')
  }
}

async function submit() {
  error.value = ''
  try {
    await auth.login(form.username, form.password)
    go()
  } catch (e) {
    error.value = getErrorMessage(e)
  }
}

async function quickLogin(account) {
  form.username = account.username
  form.password = account.password || '123456'
  await submit()
}

onMounted(async () => {
  meta.fetchMeta()
  try {
    const data = await api.demoAccounts()
    demos.value = (data.accounts || []).filter((a) => a.role === 'student').slice(0, 3)
    const admin = (data.accounts || []).find((a) => a.role === 'admin')
    if (admin) demos.value.push(admin)
  } catch {
    demos.value = []
  }
})
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.16fr) minmax(400px, 0.84fr);
  background: url('/images/login-bg.webp') 82% center / cover no-repeat, var(--bg);
}

.login-page::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: linear-gradient(
    90deg,
    rgba(244, 243, 238, 0.86) 0%,
    rgba(244, 243, 238, 0.48) 40%,
    rgba(244, 243, 238, 0.08) 66%,
    rgba(244, 243, 238, 0.32) 100%
  );
}

.login-hero {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  padding: 42px 60px 30px 64px;
  min-height: 100vh;
}

.hero-brand {
  display: flex;
  align-items: center;
  gap: 11px;
}

.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: #fbfaf6;
  background: var(--ink);
}

.brand-core {
  font-family: var(--font-serif);
  font-size: 20px;
  font-weight: 500;
  line-height: 1;
}

.brand-text {
  display: grid;
}

.brand-text strong {
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -0.01em;
}

.brand-text span {
  font-family: var(--font-serif);
  font-size: 8.5px;
  letter-spacing: 0.18em;
  color: var(--muted-2);
  text-transform: uppercase;
  margin-top: 2px;
}

.hero-copy {
  margin-top: clamp(54px, 11vh, 112px);
  max-width: 620px;
}

.hero-copy .eyebrow {
  margin-bottom: 22px;
}

.hero-copy h1 {
  margin: 0 0 20px;
  font-size: clamp(44px, 5vw, 60px);
  line-height: 1.1;
  font-weight: 600;
  letter-spacing: -0.04em;
}

.hero-copy h1 .accent {
  color: var(--violet);
}

.hero-copy > p {
  color: var(--muted);
  font-size: 15px;
  line-height: 1.9;
  max-width: 500px;
}

.hero-list {
  margin-top: 42px;
  max-width: 560px;
  border-top: 1px solid var(--line);
  list-style: none;
  padding: 0;
}

.hero-list li {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 16px;
  padding: 17px 0;
  border-bottom: 1px solid var(--line);
}

.hero-list .num {
  font-family: var(--font-serif);
  font-size: 13px;
  color: var(--muted-2);
  line-height: 1.5;
}

.hero-list strong {
  display: block;
  font-size: 13.5px;
  font-weight: 650;
}

.hero-list p {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.7;
  color: var(--muted);
}

.hero-foot {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-top: auto;
  padding-top: 28px;
  color: var(--muted-2);
  font-size: 10.5px;
  letter-spacing: 0.02em;
}

.login-side {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  padding: 36px 54px 36px 24px;
}

.login-card {
  width: min(400px, 100%);
  padding: 34px 30px 26px;
  border-radius: 18px;
  background: var(--card-solid);
  border: 1px solid var(--line-strong);
  box-shadow: var(--shadow-sm);
}

.login-head h2 {
  margin: 0 0 7px;
  font-size: 24px;
  font-weight: 650;
  letter-spacing: -0.03em;
}

.login-head p {
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.7;
  margin-bottom: 26px;
}

.login-form {
  display: grid;
  gap: 15px;
}

.input-with-icon {
  position: relative;
}

.input-with-icon > svg {
  position: absolute;
  left: 13px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--muted-2);
}

.input-with-icon .input {
  padding-left: 39px;
  padding-right: 38px;
}

.pwd-toggle {
  position: absolute;
  right: 7px;
  top: 50%;
  transform: translateY(-50%);
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  color: var(--muted-2);
  border-radius: 6px;
}

.pwd-toggle:hover {
  background: rgba(21, 32, 43, 0.05);
}

.login-error {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 9px 11px;
  border-radius: 8px;
  background: rgba(184, 69, 63, 0.08);
  color: #96332e;
  font-size: 11.5px;
}

.login-submit {
  height: 44px;
  margin-top: 3px;
  border-radius: 9px;
  font-size: 13.5px;
}

.demo-block {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
}

.demo-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 9.5px;
  font-weight: 650;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted-2);
}

.demo-list {
  display: grid;
}

.demo-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 2px;
  border: 0;
  border-bottom: 1px solid var(--line);
  background: transparent;
  border-radius: 0;
  text-align: left;
  transition: color 0.18s ease, padding-left 0.18s ease;
}

.demo-item:last-child {
  border-bottom: 0;
}

.demo-item:hover {
  color: var(--violet);
  padding-left: 5px;
}

.demo-meta {
  display: grid;
  flex: 1;
  min-width: 0;
}

.demo-meta strong {
  font-size: 12.5px;
  font-weight: 600;
}

.demo-meta small {
  font-size: 10px;
  color: var(--muted-2);
  margin-top: 1px;
}

.demo-item svg {
  color: var(--muted-2);
}

.login-note {
  margin-top: 16px;
  color: var(--muted-2);
  font-size: 10px;
  line-height: 1.7;
}

@media (max-width: 1080px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .login-hero {
    display: none;
  }

  .login-side {
    min-height: 100vh;
    padding: 24px;
  }

  .login-page::before {
    background: rgba(244, 243, 238, 0.78);
  }

  .login-card {
    width: min(400px, 100%);
  }
}
</style>