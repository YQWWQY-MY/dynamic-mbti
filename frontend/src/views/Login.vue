<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api, { errMsg } from '../api'

const router = useRouter()
const mode = ref('login')
const isRegister = computed(() => mode.value === 'register')
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function submit() {
  if (form.username.trim().length < 2) {
    ElMessage.warning('用户名至少 2 个字符')
    return
  }
  if (form.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  loading.value = true
  try {
    const url = isRegister.value ? '/auth/register' : '/auth/login'
    const { data } = await api.post(url, {
      username: form.username.trim(),
      password: form.password,
    })
    localStorage.setItem('token', data.token)
    localStorage.setItem('username', data.user.username)
    router.push('/test')
  } catch (err) {
    ElMessage.error(errMsg(err))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <h1 class="title">AI 动态人格测试</h1>
      <p class="subtitle">
        AI 实时分析你的回答，动态生成下一道题——
        每一次测试都是为你量身定制的。
      </p>
      <el-tabs v-model="mode" stretch>
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>
      <el-form @submit.prevent="submit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码（至少 6 位）"
            size="large"
            show-password
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="loading"
          @click="submit"
        >
          {{ isRegister ? '注册并开始' : '登录' }}
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 16px;
}

.login-card {
  width: 400px;
  padding: 8px 8px 20px;
}

.title {
  margin: 8px 0 4px;
  font-size: 24px;
  text-align: center;
}

.subtitle {
  margin: 0 0 16px;
  font-size: 13px;
  color: #909399;
  text-align: center;
  line-height: 1.6;
}

.submit-btn {
  width: 100%;
}
</style>
