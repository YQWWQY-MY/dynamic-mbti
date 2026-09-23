<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api, { errMsg } from '../api'

const route = useRoute()
const router = useRouter()
const report = ref(null)
const loading = ref(true)

const DIM_ORDER = ['EI', 'SN', 'TF', 'JP']

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/reports/${route.params.id}`)
    report.value = data
  } catch (err) {
    ElMessage.error(errMsg(err))
  } finally {
    loading.value = false
  }
}

function fillStyle(dim) {
  // percent 为第二字母方向的百分比（0-100），中心为 50%
  const percent = dim.percent
  if (percent >= 50) {
    return { left: '50%', width: `${percent - 50}%` }
  }
  return { left: `${percent}%`, width: `${50 - percent}%` }
}

function fillClass(dim) {
  return dim.percent >= 50 ? 'pole2' : 'pole1'
}

async function restart() {
  try {
    await api.post('/tests')
    router.push('/test')
  } catch (err) {
    ElMessage.error(errMsg(err))
  }
}

const dims = computed(() =>
  DIM_ORDER.map((d) => report.value?.dimensions?.[d]).filter(Boolean)
)

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <template v-if="report">
      <!-- 类型卡片 -->
      <el-card class="type-card">
        <div class="type-head">
          <div class="type-letters">{{ report.mbti_type }}</div>
          <div class="type-meta">
            <div class="type-name">{{ report.type_name }}</div>
            <div class="type-sub">
              共 {{ report.question_count }} 道动态生成的问题 ·
              {{ new Date(report.created_at).toLocaleString('zh-CN') }}
            </div>
          </div>
        </div>
        <p class="portrait">{{ report.portrait }}</p>
      </el-card>

      <!-- 四维度 -->
      <el-card class="section">
        <template #header><span>维度倾向</span></template>
        <div v-for="dim in dims" :key="dim.name" class="dim-row">
          <div class="dim-labels">
            <span :class="{ strong: dim.dominant_pole === dim.pole1 }">{{ dim.pole1 }}</span>
            <span class="dim-name">{{ dim.name }}</span>
            <span :class="{ strong: dim.dominant_pole === dim.pole2 }">{{ dim.pole2 }}</span>
          </div>
          <div class="bipolar-track">
            <div class="bipolar-fill" :class="fillClass(dim)" :style="fillStyle(dim)"></div>
          </div>
          <div class="dim-result">
            <b>{{ dim.dominant_pole }}</b> {{ dim.dominant_percent }}% ·
            <span class="dim-desc">{{ dim.description }}</span>
          </div>
        </div>
      </el-card>

      <!-- 优势 / 短板 / 职业 / 名人 -->
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12">
          <el-card class="section">
            <template #header><span>核心优势</span></template>
            <ul class="plain-list">
              <li v-for="(item, i) in report.strengths" :key="i">{{ item }}</li>
            </ul>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12">
          <el-card class="section">
            <template #header><span>潜在短板</span></template>
            <ul class="plain-list">
              <li v-for="(item, i) in report.weaknesses" :key="i">{{ item }}</li>
            </ul>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12">
          <el-card class="section">
            <template #header><span>适合的职业方向</span></template>
            <div class="tag-list">
              <el-tag v-for="(item, i) in report.careers" :key="i" type="success" effect="plain">
                {{ item }}
              </el-tag>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12">
          <el-card class="section">
            <template #header><span>同类型名人</span></template>
            <div class="tag-list">
              <el-tag v-for="(item, i) in report.famous" :key="i" effect="plain">{{ item }}</el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 建议 -->
      <el-card class="section">
        <template #header><span>成长建议</span></template>
        <p class="advice">{{ report.advice }}</p>
      </el-card>

      <div class="actions">
        <el-button size="large" @click="router.push('/history')">查看测试历史</el-button>
        <el-button type="primary" size="large" @click="restart">再测一次</el-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.type-card {
  text-align: center;
  margin-bottom: 20px;
}

.type-head {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-top: 8px;
}

.type-letters {
  font-size: 56px;
  font-weight: 700;
  color: #409eff;
  letter-spacing: 4px;
  line-height: 1;
}

.type-name {
  font-size: 22px;
  font-weight: 600;
}

.type-sub {
  font-size: 13px;
  color: #909399;
  margin-top: 6px;
}

.portrait {
  text-align: left;
  line-height: 1.9;
  color: #606266;
  margin: 20px 4px 0;
  font-size: 15px;
}

.section {
  margin-bottom: 20px;
}

.dim-row {
  margin-bottom: 22px;
}

.dim-labels {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 15px;
  margin-bottom: 8px;
}

.dim-labels .strong {
  color: #409eff;
  font-weight: 700;
  font-size: 18px;
}

.dim-name {
  font-size: 12px;
  color: #909399;
}

.dim-result {
  margin-top: 6px;
  font-size: 13px;
  color: #606266;
}

.dim-desc {
  color: #909399;
}

.plain-list {
  margin: 0;
  padding-left: 18px;
  line-height: 2;
  color: #606266;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.advice {
  margin: 0;
  line-height: 1.9;
  color: #606266;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 8px;
}
</style>
