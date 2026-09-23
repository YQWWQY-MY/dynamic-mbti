<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import api, { errMsg } from '../api'

const router = useRouter()
const reports = ref([])
const loading = ref(true)
const chartEl = ref(null)
let chart = null
let trendPoints = []

const DIMENSIONS = [
  { key: 'EI', name: '外向 E — 内向 I' },
  { key: 'SN', name: '实感 S — 直觉 N' },
  { key: 'TF', name: '思考 T — 情感 F' },
  { key: 'JP', name: '判断 J — 知觉 P' },
]

async function load() {
  loading.value = true
  try {
    const [listRes, trendRes] = await Promise.all([
      api.get('/reports'),
      api.get('/reports/trend'),
    ])
    reports.value = listRes.data
    trendPoints = trendRes.data
  } catch (err) {
    ElMessage.error(errMsg(err))
  } finally {
    loading.value = false
  }
}

// 图表容器在 v-if 分支内，数据就绪后等 DOM 渲染完成再画图
watch(
  () => [reports.value.length, chartEl.value],
  async () => {
    if (!chartEl.value) return
    await nextTick()
    renderChart(trendPoints)
  },
  { flush: 'post' }
)

function renderChart(points) {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  if (points.length < 2) {
    chart.clear()
    return
  }

  const labels = points.map((p) => {
    const d = new Date(p.date)
    return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  })

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter(params) {
        const idx = params[0].dataIndex
        const lines = [points[idx].mbti_type, ...params.map(
          (p) => `${p.seriesName}: ${p.value > 0 ? '+' : ''}${p.value}`
        )]
        return lines.join('<br/>')
      },
    },
    legend: { bottom: 0 },
    grid: { left: 40, right: 20, top: 30, bottom: 60 },
    xAxis: { type: 'category', data: labels },
    yAxis: {
      type: 'value',
      min: -8,
      max: 8,
      interval: 4,
      name: '得分',
    },
    series: DIMENSIONS.map((dim, i) => ({
      name: dim.name,
      type: 'line',
      smooth: true,
      symbolSize: 8,
      data: points.map((p) => p.scores[dim.key]),
      itemStyle: { color: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c'][i] },
      markLine:
        i === 0
          ? { silent: true, symbol: 'none', lineStyle: { color: '#c0c4cc', type: 'dashed' }, data: [{ yAxis: 0 }] }
          : undefined,
    })),
  })
}

function onResize() {
  chart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
})
</script>

<template>
  <div class="page" v-loading="loading">
    <el-card v-if="!loading && reports.length === 0" class="empty-card">
      <el-empty description="还没有完成过测试，先来测一次吧">
        <el-button type="primary" @click="router.push('/test')">开始测试</el-button>
      </el-empty>
    </el-card>

    <template v-if="reports.length">
      <el-card class="section">
        <template #header>
          <span>性格变化曲线</span>
          <span class="chart-hint">得分越正越偏向第二字母（I/N/F/P），越负越偏向第一字母（E/S/T/J）</span>
        </template>
        <div ref="chartEl" class="chart"></div>
        <el-alert
          v-if="reports.length < 2"
          class="chart-tip"
          type="info"
          :closable="false"
          title="完成两次及以上测试后，曲线才能展示性格随时间的变化"
          show-icon
        />
      </el-card>

      <el-card>
        <template #header><span>历史报告</span></template>
        <el-table :data="reports" stripe>
          <el-table-column label="时间">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString('zh-CN') }}
            </template>
          </el-table-column>
          <el-table-column label="人格类型">
            <template #default="{ row }">
              <el-tag type="primary" effect="dark">{{ row.mbti_type }}</el-tag>
              <span class="type-name">{{ row.type_name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="question_count" label="题目数" width="90" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click="router.push(`/result/${row.id}`)">
                查看报告
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.empty-card {
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.section {
  margin-bottom: 20px;
}

.chart {
  height: 360px;
  width: 100%;
}

.chart-hint {
  font-size: 12px;
  color: #909399;
  margin-left: 12px;
  font-weight: normal;
}

.chart-tip {
  margin-top: 8px;
}

.type-name {
  margin-left: 8px;
}
</style>
