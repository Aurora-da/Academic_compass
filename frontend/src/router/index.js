import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/AppShell.vue'),
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '学业总览', student: true },
      },
      {
        path: 'plan',
        name: 'plan',
        component: () => import('@/views/PlanView.vue'),
        meta: { title: '培养方案', student: true },
      },
      {
        path: 'recommend',
        name: 'recommend',
        component: () => import('@/views/RecommendView.vue'),
        meta: { title: '选课助手', student: true },
      },
      {
        path: 'report',
        name: 'report',
        component: () => import('@/views/ReportView.vue'),
        meta: { title: '学业报告', student: true },
      },
      {
        path: 'second-classroom',
        name: 'second-classroom',
        component: () => import('@/views/SecondClassroomView.vue'),
        meta: { title: '第二课堂', student: true },
      },
      {
        path: 'import',
        name: 'import',
        component: () => import('@/views/ImportView.vue'),
        meta: { title: '数据导入', student: true },
      },
      {
        path: 'admin',
        name: 'admin',
        component: () => import('@/views/AdminView.vue'),
        meta: { title: '教务管理', admin: true },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { public: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  const token = localStorage.getItem('ac_token')
  let user = null
  try {
    user = JSON.parse(localStorage.getItem('ac_user') || 'null')
  } catch {
    user = null
  }
  if (to.meta.public) {
    if (to.path === '/login' && token && user) {
      return user.role === 'admin' ? '/admin' : '/'
    }
    return true
  }
  if (!token) return { path: '/login', query: { redirect: to.fullPath } }
  if (to.meta.admin && user?.role !== 'admin') {
    return user?.role === 'admin' ? '/admin' : '/'
  }
  if (to.meta.student && user?.role === 'admin') return '/admin'
  return true
})

export default router
