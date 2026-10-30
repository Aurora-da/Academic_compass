<template>
  <div class="app-shell">
    <a class="skip-link" href="#main">跳到主要内容</a>
    <AuroraBackground />

    <header class="app-header">
      <div class="header-main">
        <router-link to="/" class="brand" @click="userOpen = false">
          <div class="brand-mark">
            <span class="brand-core">学</span>
          </div>
          <div class="brand-text">
            <strong>学业罗盘</strong>
            <span>Academic Compass</span>
          </div>
        </router-link>

        <div class="header-actions">
          <nav class="top-nav" aria-label="主导航">
            <div class="nav-inner">
              <router-link
                v-for="item in navItems"
                :key="item.to"
                :to="item.to"
                class="nav-link"
                :class="{ active: isActive(item) }"
                @click="userOpen = false"
              >
                <UiIcon :name="item.icon" :size="15" />
                <span>{{ item.label }}</span>
                <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
              </router-link>
            </div>
          </nav>

          <div
            class="user-menu"
            :class="{ open: userOpen }"
            @mouseleave="userOpen = false"
          >
            <button
              class="user-trigger"
              type="button"
              aria-haspopup="true"
              :aria-expanded="userOpen"
              @click="userOpen = !userOpen"
            >
              <span class="avatar">{{ initials }}</span>
              <span class="user-trigger-text">
                <strong>{{ auth.displayName }}</strong>
                <small>{{ auth.isAdmin ? '教务管理员' : `${auth.student?.grade || ''} 级 · ${auth.student?.student_no || ''}` }}</small>
              </span>
              <UiIcon name="chevron-down" :size="13" class="user-chevron" />
            </button>

            <div class="user-popover">
              <div class="popover-head">
                <span class="avatar">{{ initials }}</span>
                <div>
                  <strong>{{ auth.displayName }}</strong>
                  <span>{{ auth.isAdmin ? '教务管理员' : '学生账号' }}</span>
                </div>
              </div>
              <div class="popover-note">2024 版培养方案 · 预演口径</div>
              <button class="user-logout" type="button" @click="logout">
                <UiIcon name="logout" :size="15" />
                退出登录
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>

    <main id="main" class="app-main" tabindex="-1">
      <nav v-if="route.meta.title" class="page-crumb" aria-label="面包屑">
        <router-link to="/">首页</router-link>
        <span class="crumb-sep">/</span>
        <span aria-current="page">{{ route.meta.title }}</span>
      </nav>
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <AssistantPanel v-model:open="assistantOpen" />
    <ToastHost />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AuroraBackground from '@/components/AuroraBackground.vue'
import AssistantPanel from '@/components/AssistantPanel.vue'
import ToastHost from '@/components/ToastHost.vue'
import UiIcon from '@/components/UiIcon.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const assistantOpen = ref(false)
const userOpen = ref(false)

const STUDENT_NAV = [
  { to: '/', label: '学业总览', icon: 'grid', exact: true },
  { to: '/plan', label: '培养方案', icon: 'tree' },
  { to: '/recommend', label: '选课助手', icon: 'compass' },
  { to: '/report', label: '学业报告', icon: 'report' },
  { to: '/second-classroom', label: '第二课堂', icon: 'medal' },
  { to: '/import', label: '数据导入', icon: 'upload' },
]

const ADMIN_NAV = [
  { to: '/admin', label: '管理概览', icon: 'chart' },
]

const navItems = computed(() => (auth.isAdmin ? ADMIN_NAV : STUDENT_NAV))

const initials = computed(() => (auth.isAdmin ? '管' : (auth.displayName || '学').slice(0, 1)))

function isActive(item) {
  if (item.exact) return route.path === item.to
  return route.path.startsWith(item.to)
}

function logout() {
  userOpen.value = false
  auth.logout()
  router.replace('/login')
}

function closeUserMenu(event) {
  if (!event.target.closest?.('.user-menu')) userOpen.value = false
}

watch(() => route.path, () => {
  userOpen.value = false
})

onMounted(() => {
  document.addEventListener('click', closeUserMenu)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeUserMenu)
})
</script>

<style scoped>
.app-shell {
  min-height: 100dvh;
  position: relative;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 40;
  background: rgba(244, 243, 238, 0.9);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(18px) saturate(1.05);
  -webkit-backdrop-filter: blur(18px) saturate(1.05);
}

.header-main {
  width: 100%;
  max-width: var(--page-max);
  height: 68px;
  margin: 0 auto;
  padding: 0 32px;
  display: flex;
  align-items: center;
  gap: 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: none;
  text-decoration: none;
}

.brand-mark {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: var(--ink);
  color: #fbfaf6;
  flex: none;
}

.brand-core {
  font-family: var(--font-serif);
  font-weight: 500;
  font-size: 19px;
  line-height: 1;
}

.brand-text {
  display: grid;
}

.brand-text strong {
  color: var(--ink);
  font-size: 14.5px;
  font-weight: 650;
  letter-spacing: -0.01em;
}

.brand-text span {
  font-family: var(--font-serif);
  font-size: 8px;
  letter-spacing: 0.17em;
  text-transform: uppercase;
  color: var(--muted-2);
  margin-top: 2px;
}

.header-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 18px;
  min-width: 0;
}

.user-menu {
  position: relative;
  flex: none;
  margin-left: 2px;
  padding-left: 14px;
  border-left: 1px solid var(--line);
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 7px 0 4px;
  border-radius: 8px;
  transition: background 0.18s ease;
}

.user-trigger:hover,
.user-menu.open .user-trigger {
  background: rgba(21, 32, 43, 0.045);
}

.avatar {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  flex: none;
  border-radius: 7px;
  background: var(--ink);
  color: #fbfaf6;
  font-size: 10.5px;
  font-weight: 650;
}

.user-trigger-text {
  display: grid;
  min-width: 0;
  text-align: left;
}

.user-trigger-text strong {
  color: var(--ink);
  font-size: 11.5px;
  font-weight: 600;
  line-height: 1.3;
  white-space: nowrap;
}

.user-trigger-text small {
  color: var(--muted-2);
  font-size: 9px;
  line-height: 1.35;
  white-space: nowrap;
}

.user-chevron {
  color: var(--muted-2);
  transition: transform 0.18s ease;
}

.user-menu:hover .user-chevron,
.user-menu.open .user-chevron {
  transform: rotate(180deg);
}

.user-popover {
  position: absolute;
  z-index: 60;
  top: calc(100% + 8px);
  right: 0;
  width: 224px;
  padding: 7px;
  border-radius: 11px;
  background: var(--card-solid);
  border: 1px solid var(--line-strong);
  box-shadow: var(--shadow-md);
  opacity: 0;
  visibility: hidden;
  transform: translateY(-4px);
  transition: opacity 0.16s ease, transform 0.16s ease, visibility 0.16s;
}

.user-popover::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: -12px;
  height: 12px;
}

.user-menu:hover .user-popover,
.user-menu.open .user-popover,
.user-menu:focus-within .user-popover {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.popover-head {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 7px 7px 10px;
  border-bottom: 1px solid var(--line);
}

.popover-head .avatar {
  width: 32px;
  height: 32px;
  font-size: 11px;
}

.popover-head div {
  display: grid;
  min-width: 0;
}

.popover-head strong {
  color: var(--ink);
  font-size: 12px;
  font-weight: 600;
}

.popover-head span {
  color: var(--muted-2);
  font-size: 9.5px;
  margin-top: 1px;
}

.popover-note {
  padding: 9px 7px 7px;
  color: var(--muted-2);
  font-family: var(--font-serif);
  font-size: 9px;
  letter-spacing: 0.02em;
}

.user-logout {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 9px 7px;
  border-radius: 6px;
  color: var(--rose);
  font-size: 11.5px;
  font-weight: 600;
  text-align: left;
}

.user-logout:hover {
  background: rgba(184, 69, 63, 0.075);
}

.top-nav {
  min-width: 0;
}

.nav-inner {
  width: 100%;
  display: flex;
  align-items: stretch;
  justify-content: flex-end;
  gap: 1px;
  overflow-x: auto;
  scrollbar-width: none;
}

.nav-inner::-webkit-scrollbar {
  display: none;
}

.nav-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 68px;
  padding: 0 10px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  transition: color 0.18s ease;
}

.nav-link::after {
  content: '';
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: 0;
  height: 2px;
  background: transparent;
  transition: background 0.18s ease;
}

.nav-link:hover {
  color: var(--ink);
}

.nav-link.active {
  color: var(--violet);
}

.nav-link.active::after {
  background: var(--violet);
}

.nav-badge {
  min-width: 16px;
  height: 16px;
  display: grid;
  place-items: center;
  padding: 0 4px;
  border-radius: 4px;
  background: var(--rose);
  color: #fff;
  font-size: 8.5px;
  font-weight: 650;
}

.app-main {
  position: relative;
  z-index: 1;
  min-height: calc(100dvh - 69px);
}

.page-crumb {
  display: flex;
  align-items: center;
  gap: 7px;
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 13px 40px 0;
  color: var(--muted-2);
  font-size: 11px;
}

.page-crumb a {
  color: var(--muted);
  transition: color 0.15s ease;
}

.page-crumb a:hover {
  color: var(--violet);
}

.page-crumb [aria-current='page'] {
  color: var(--ink);
  font-weight: 600;
}

.crumb-sep {
  color: var(--line-strong);
}

@media (max-width: 640px) {
  .page-crumb {
    padding: 10px 18px 0;
    font-size: 10.5px;
  }
}

@media (max-width: 1120px) {
  .user-trigger-text {
    display: none;
  }

  .user-trigger {
    padding-right: 4px;
  }

  .nav-link {
    padding: 0 8px;
  }

  .nav-link::after {
    left: 8px;
    right: 8px;
  }
}

@media (max-width: 900px) {
  .header-main {
    height: auto;
    padding: 10px 18px 0;
    flex-wrap: wrap;
  }

  .header-actions {
    display: contents;
  }

  .user-menu {
    order: 1;
    margin-left: auto;
    padding-left: 0;
    border-left: 0;
  }

  .top-nav {
    order: 2;
    width: 100%;
    margin-top: 8px;
    border-top: 1px solid var(--line);
  }

  .nav-inner {
    justify-content: flex-start;
  }

  .nav-link {
    height: 46px;
    padding: 0 10px;
  }

  .nav-link::after {
    left: 10px;
    right: 10px;
  }

  .app-main {
    min-height: calc(100dvh - 95px);
  }
}

@media (max-width: 640px) {
  .header-main {
    padding: 9px 14px 0;
    gap: 10px;
  }

  .brand-text span {
    display: none;
  }

  .brand-text strong {
    font-size: 13.5px;
  }

  .user-trigger {
    padding: 0 2px;
  }

  .user-chevron {
    display: none;
  }

  .nav-link {
    height: 44px;
    padding: 0 7px;
    gap: 0;
    font-size: 11.5px;
  }

  .nav-link::after {
    left: 7px;
    right: 7px;
  }

  .nav-link svg {
    display: none;
  }

  .app-main {
    min-height: calc(100dvh - 92px);
  }
}

@media (max-width: 420px) {
  .nav-link {
    padding: 0 5px;
    font-size: 11px;
  }

  .nav-link::after {
    left: 5px;
    right: 5px;
  }
}
</style>
