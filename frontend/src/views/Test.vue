<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api, { errMsg } from '../api'

const router = useRouter()

const loading = ref(true)
const submitting = ref(false)
const question = ref(null)
const questionNum = ref(0)
const maxQuestions = ref(20)
const progress = ref({})
const transcript = ref([])
const selectedOption = ref(null)
const freeText = ref('')
const currentCard = ref(null)

const DIM_ORDER = ['EI', 'SN', 'TF', 'JP']
const DIM_COLORS = { EI: '#409eff', SN: '#67c23a', TF: '#e6a23c', JP: '#f56c6c' }

async function init() {
  loading.value = true
  try {
    let { data } = await api.get('/tests/current').catch(async (err) => {
      if (err.response?.status === 404) {
        return await api.post('/tests')
      }
      throw err
    })
    if (data.status === 'completed') {
      router.replace(`/result/${data.report.id}`)
      return
    }
    applyState(data)
  } catch (err) {
    ElMessage.error(errMsg(err))
  } finally {
    loading.value = false
  }
}

function applyState(data) {
  question.value = data.question
  questionNum.value = data.question_num
  maxQuestions.value = data.max_questions
  progress.value = data.progress || {}
  if (data.transcript) transcript.value = data.transcript
  selectedOption.value = null
  freeText.value = ''
  nextTick(() => {
    currentCard.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  })
}

async function answer() {
  if (!question.value || submitting.value) return
  const content = selectedOption.value ?? freeText.value.trim()
  if (!content) {
    ElMessage.warning('请选择一个选项，或输入你自己的回答')
    return
  }
  submitting.value = true
  startPhaseText()
  try {
    const { data } = await api.post('/tests/current/answer', {
      question_id: question.value.id,
      content,
    })
    if (data.status === 'completed') {
      router.push(`/result/${data.report.id}`)
      return
    }
    transcript.value.push({
      question: question.value,
      answer:
        content.length === 1
          ? `${content}. ${question.value.options['ABCD'.indexOf(content)]}`
          : content,
    })
    applyState(data)
  } catch (err) {
    ElMessage.error(errMsg(err))
  } finally {
    stopPhaseText()
    submitting.value = false
  }
}

// 等待 AI 时按时间切换提示文案，缓解等待焦虑
const phaseText = ref('')
let phaseTimer = null

function startPhaseText() {
  phaseText.value = '正在分析你的回答…'
  phaseTimer = setInterval(() => {
    if (phaseText.value === '正在分析你的回答…') {
      phaseText.value = 'AI 正在为你构思下一道题…'
    } else if (phaseText.value === 'AI 正在为你构思下一道题…') {
      phaseText.value = '四维度已收敛，AI 正在撰写你的专属报告（约 20 秒）…'
    }
  }, 5000)
}

function stopPhaseText() {
  if (phaseTimer) clearInterval(phaseTimer)
  phaseTimer = null
}

onMounted(init)
</script>

<template>
  <div class="page" v-loading="loading">
    <el-row :gutter="20">
      <!-- 主区：对话式答题 -->
      <el-col :xs="24" :md="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>第 {{ questionNum }} / {{ maxQuestions }} 题</span>
              <el-progress
                :percentage="Math.round((questionNum / maxQuestions) * 100)"
                :stroke-width="10"
                class="header-progress"
              />
            </div>
          </template>

          <!-- 历史问答（可滚动） -->
          <div v-if="transcript.length" class="transcript">
            <div v-for="(item, i) in transcript" :key="i" class="transcript-item">
              <div class="bubble q">
                <div class="bubble-meta">{{ item.question.dimension_name }}</div>
                {{ item.question.content }}
              </div>
              <div class="bubble a">{{ item.answer }}</div>
            </div>
          </div>

          <!-- AI 处理中 -->
          <div v-if="question && submitting" class="ai-waiting">
            <div class="ai-pulse"></div>
            <div class="ai-waiting-text">
              <div class="ai-waiting-title">{{ phaseText }}</div>
              <div class="ai-waiting-sub">AI 正在实时工作，通常 5~10 秒，最后一题生成报告约 25 秒</div>
            </div>
          </div>

          <!-- 当前题目 -->
          <div v-else-if="question" ref="currentCard" class="current-question">
            <div class="q-tag" :style="{ background: DIM_COLORS[question.dimension] }">
              {{ question.dimension_name }}
            </div>
            <h3 class="q-content">{{ question.content }}</h3>
            <div class="options">
              <div
                v-for="(opt, i) in question.options"
                :key="i"
                class="option"
                :class="{ active: selectedOption === 'ABCD'[i] }"
                @click="selectedOption = 'ABCD'[i]; freeText = ''"
              >
                <span class="option-letter">{{ 'ABCD'[i] }}</span>
                <span>{{ opt }}</span>
              </div>
            </div>

            <el-divider>或者，用自己的话回答</el-divider>
            <el-input
              v-model="freeText"
              type="textarea"
              :rows="2"
              maxlength="500"
              show-word-limit
              placeholder="自由回答会被 AI 语义分析，信息量比选择题更大"
              @focus="selectedOption = null"
            />
            <el-button
              type="primary"
              size="large"
              class="answer-btn"
              :loading="submitting"
              :disabled="!selectedOption && !freeText.trim()"
              @click="answer"
            >
              提交回答
            </el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 侧栏：四维度收敛进度 -->
      <el-col :xs="24" :md="8">
        <el-card class="side-card">
          <template #header>
            <span>AI 测量进度</span>
          </template>
          <div v-for="d in DIM_ORDER" :key="d" class="dim-item">
            <div class="dim-head">
              <span>{{ progress[d]?.name || d }}</span>
              <el-tag v-if="progress[d]?.converged" type="success" size="small">已收敛</el-tag>
              <el-tag v-else type="info" size="small" effect="plain">测量中</el-tag>
            </div>
            <el-progress
              :percentage="progress[d]?.confidence_percent || 0"
              :color="DIM_COLORS[d]"
              :stroke-width="12"
            />
          </div>
          <el-alert
            class="tip"
            type="info"
            :closable="false"
            title="自适应机制"
            description="AI 会优先针对置信度最低的维度追问，四个维度全部收敛后即生成报告。"
            show-icon
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 14px;
}

.header-progress {
  flex: 1;
}

.transcript {
  max-height: 300px;
  overflow-y: auto;
  padding: 4px 8px;
  margin-bottom: 16px;
  background: #fafbfc;
  border-radius: 8px;
}

.transcript-item {
  margin-bottom: 12px;
}

.bubble {
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 14px;
  line-height: 1.6;
  max-width: 92%;
}

.bubble.q {
  background: #f0f2f5;
  color: #606266;
}

.bubble-meta {
  font-size: 12px;
  color: #a8abb2;
  margin-bottom: 2px;
}

.bubble.a {
  background: #ecf5ff;
  color: #303133;
  margin-left: 36px;
  margin-top: 6px;
}

.current-question {
  padding-top: 4px;
}

.ai-waiting {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 36px 12px;
}

.ai-pulse {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #409eff;
  animation: ai-pulse 1.4s ease-in-out infinite;
}

@keyframes ai-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.45);
  }
  70% {
    box-shadow: 0 0 0 16px rgba(64, 158, 255, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(64, 158, 255, 0);
  }
}

.ai-waiting-title {
  font-size: 15px;
  font-weight: 600;
  color: #409eff;
}

.ai-waiting-sub {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

.q-tag {
  display: inline-block;
  color: #fff;
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 10px;
}

.q-content {
  margin: 12px 0 16px;
  font-size: 17px;
  line-height: 1.6;
}

.options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1.5;
  transition: all 0.15s;
}

.option:hover {
  border-color: #409eff;
  color: #409eff;
}

.option.active {
  border-color: #409eff;
  background: #ecf5ff;
  color: #409eff;
}

.option-letter {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  line-height: 24px;
  text-align: center;
  border-radius: 50%;
  border: 1px solid currentColor;
  font-size: 13px;
}

.answer-btn {
  width: 100%;
  margin-top: 16px;
}

.side-card :deep(.el-card__body) {
  padding: 16px;
}

.dim-item {
  margin-bottom: 18px;
}

.dim-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 13px;
}

.tip {
  margin-top: 4px;
}
</style>
