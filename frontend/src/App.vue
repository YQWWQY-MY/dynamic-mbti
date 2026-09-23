<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
// localStorage 非响应式，需在路由切换/登录登出时手动同步
const logged = ref(Boolean(localStorage.getItem('token')))
const username = ref(localStorage.getItem('username') || '')

watch(
  () => route.fullPath,
  () => {
    logged.value = Boolean(localStorage.getItem('token'))
    username.value = localStorage.getItem('username') || ''
  }
)

window.addEventListener('storage', syncFromStorage)

function syncFromStorage() {
  logged.value = Boolean(localStorage.getItem('token'))
  username.value = localStorage.getItem('username') || ''
}

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  logged.value = false
  username.value = ''
  router.push('/')
}
</script>

<template>
  <header v-if="logged" class="header">
    <div class="header-inner">
      <div class="brand" @click="router.push('/test')">AI 动态人格测试</div>
      <nav class="nav">
        <router-link to="/test">开始测试</router-link>
        <router-link to="/history">测试历史</router-link>
      </nav>
      <div class="user-box">
        <span class="username">{{ username }}</span>
        <el-button text size="small" @click="logout">退出</el-button>
      </div>
    </div>
  </header>
  <router-view />
</template>

<style scoped>
.header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-inner {
  max-width: 1080px;
  margin: 0 auto;
  padding: 0 16px;
  height: 56px;
  display: flex;
  align-items: center;
  gap: 32px;
}

.brand {
  font-size: 17px;
  font-weight: 600;
  cursor: pointer;
  color: #409eff;
}

.nav {
  display: flex;
  gap: 20px;
  flex: 1;
}

.nav a {
  color: #606266;
  text-decoration: none;
  font-size: 14px;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
}

.nav a.router-link-active {
  color: #409eff;
  border-bottom-color: #409eff;
}

.user-box {
  display: flex;
  align-items: center;
  gap: 8px;
}

.username {
  font-size: 14px;
  color: #909399;
}
</style>
