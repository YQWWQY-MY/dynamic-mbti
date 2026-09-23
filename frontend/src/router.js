import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'login', component: () => import('./views/Login.vue') },
    { path: '/test', name: 'test', component: () => import('./views/Test.vue'), meta: { auth: true } },
    { path: '/result/:id', name: 'result', component: () => import('./views/Result.vue'), meta: { auth: true } },
    { path: '/history', name: 'history', component: () => import('./views/History.vue'), meta: { auth: true } },
  ],
})

router.beforeEach((to) => {
  if (to.meta.auth && !localStorage.getItem('token')) {
    return { name: 'login' }
  }
})

export default router
