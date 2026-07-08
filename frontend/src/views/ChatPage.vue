<template>
  <div class="chat-page">
    <!-- 左侧：会话列表 -->
    <aside class="chat-sessions" :class="{ collapsed: sidebarCollapsed }">
      <div class="sessions-header">
        <span v-show="!sidebarCollapsed" class="sessions-title">对话历史</span>
        <el-button
          :icon="sidebarCollapsed ? Expand : Fold"
          size="small"
          text
          @click="sidebarCollapsed = !sidebarCollapsed"
        />
      </div>
      <div v-show="!sidebarCollapsed" class="sessions-body">
        <el-button
          type="primary"
          size="small"
          style="width: 100%; margin-bottom: 12px"
          @click="handleNewChat"
        >
          <el-icon><Plus /></el-icon>
          新建对话
        </el-button>
        <div class="sessions-list">
          <div
            v-for="session in store.sessions"
            :key="session.id"
            class="session-item"
            :class="{ active: session.id === store.currentSessionId }"
            @click="handleSwitchSession(session)"
          >
            <el-icon><ChatDotRound /></el-icon>
            <span class="session-title">{{ session.title || '新对话' }}</span>
          </div>
          <el-empty
            v-if="store.sessions.length === 0"
            description="暂无对话记录"
            :image-size="60"
          />
        </div>
      </div>
    </aside>

    <!-- 右侧：对话主区域 -->
    <div class="chat-main">
      <!-- 对话顶部信息 -->
      <header class="chat-header">
        <div class="chat-header-left">
          <el-button
            v-if="sidebarCollapsed"
            :icon="Expand"
            size="small"
            text
            @click="sidebarCollapsed = false"
          />
          <span class="chat-title">
            {{ currentSessionTitle || '智能对话' }}
          </span>
          <el-tag v-if="store.currentSessionId" size="small" type="info">
            {{ store.messages.length }} 条消息
          </el-tag>
        </div>
        <div class="chat-header-right">
          <el-button size="small" text @click="handleNewChat">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
      </header>

      <!-- 消息列表 -->
      <div ref="messageContainer" class="chat-messages" @scroll="onScroll">
        <!-- 空状态 -->
        <div v-if="store.messages.length === 0 && !store.isLoading" class="chat-empty">
          <div class="empty-icon">
            <el-icon :size="64"><ChatDotRound /></el-icon>
          </div>
          <h3>RSOD 智能助手</h3>
          <p>基于 LangGraph 多 Agent 架构，支持目标检测、结果分析、专业问答</p>
          <div class="quick-prompts">
            <div
              v-for="prompt in quickPrompts"
              :key="prompt.text"
              class="quick-prompt-card"
              @click="handleQuickPrompt(prompt.text)"
            >
              <el-icon :size="18"><component :is="prompt.icon" /></el-icon>
              <span>{{ prompt.label }}</span>
            </div>
          </div>
        </div>

        <!-- 消息气泡 -->
        <div
          v-for="(msg, index) in store.messages"
          :key="index"
          class="message-row"
          :class="msg.role"
        >
          <!-- 助手头像 -->
          <div v-if="msg.role === 'assistant'" class="message-avatar">
            <el-avatar :size="36" :icon="Cpu" />
          </div>

          <div class="message-body">
            <!-- Agent 标识 -->
            <div v-if="msg.agent_used" class="message-agent-tag">
              <el-tag size="small" type="warning" effect="plain">
                {{ msg.agent_used }}
              </el-tag>
            </div>

            <!-- 消息内容 -->
            <div
              class="message-bubble"
              :class="{
                'is-user': msg.role === 'user',
                'is-assistant': msg.role === 'assistant',
                'is-streaming': msg.isStreaming,
              }"
            >
              <!-- 工具调用展示 -->
              <div v-if="msg.tool_calls && msg.tool_calls.length > 0" class="tool-calls">
                <el-collapse>
                  <el-collapse-item
                    v-for="(tc, ti) in msg.tool_calls"
                    :key="ti"
                    :title="`调用工具: ${tc.tool || tc.name || '未知'}`"
                  >
                    <div class="tool-call-detail">
                      <div v-if="tc.args" class="tool-section">
                        <span class="tool-label">参数:</span>
                        <pre>{{ JSON.stringify(tc.args, null, 2) }}</pre>
                      </div>
                      <div v-if="tc.result" class="tool-section">
                        <span class="tool-label">结果:</span>
                        <pre>{{ tc.result }}</pre>
                      </div>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </div>

              <!-- 文本内容（Markdown 渲染） -->
              <div
                v-if="msg.role === 'assistant'"
                class="markdown-body"
                v-html="renderMarkdown(msg.content)"
              />
              <template v-else>
                {{ msg.content }}
              </template>

              <!-- 流式输出光标 -->
              <span v-if="msg.isStreaming" class="streaming-cursor">|</span>
            </div>

            <!-- 消息元信息 -->
            <div v-if="msg.tokens_used || msg.latency_ms" class="message-meta">
              <span v-if="msg.tokens_used">{{ msg.tokens_used }} tokens</span>
              <span v-if="msg.latency_ms">{{ (msg.latency_ms / 1000).toFixed(1) }}s</span>
            </div>
          </div>

          <!-- 用户头像 -->
          <div v-if="msg.role === 'user'" class="message-avatar">
            <el-avatar :size="36" :src="userAvatar || undefined">
              {{ userStore.username?.charAt(0)?.toUpperCase() }}
            </el-avatar>
          </div>
        </div>

        <!-- 加载中（等待首字节） -->
        <div v-if="store.isLoading && waitingFirstToken" class="message-row assistant">
          <div class="message-avatar">
            <el-avatar :size="36" :icon="Cpu" />
          </div>
          <div class="message-body">
            <div class="message-bubble is-assistant">
              <div class="typing-indicator">
                <span class="dot" />
                <span class="dot" />
                <span class="dot" />
              </div>
            </div>
          </div>
        </div>

        <!-- 回到底部按钮 -->
        <transition name="fade">
          <div v-if="!atBottom" class="scroll-to-bottom" @click="scrollToBottom()">
            <el-icon><ArrowDown /></el-icon>
          </div>
        </transition>
      </div>

      <!-- 底部输入区 -->
      <footer class="chat-input-area">
        <div class="input-wrapper">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 5 }"
            placeholder="输入消息，Enter 发送，Shift+Enter 换行"
            :disabled="store.isLoading"
            resize="none"
            @keydown="onKeydown"
          />
          <el-button
            v-if="!store.isLoading"
            type="primary"
            :disabled="!inputText.trim()"
            :icon="Promotion"
            class="send-btn"
            @click="handleSend"
          />
          <el-button
            v-else
            type="danger"
            :icon="VideoPause"
            class="send-btn"
            @click="handleStop"
          >
          </el-button>
        </div>
        <p class="input-hint">回答由 AI 生成，请谨慎甄别</p>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import {
  Plus, Expand, Fold, Promotion, VideoPause, ArrowDown,
  ChatDotRound, Cpu, Camera, DataAnalysis, QuestionFilled,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useAgentStore } from '@/stores/agent'
import { streamChat } from '@/utils/stream'
import { renderMarkdown } from '@/utils/markdown'
import request from '@/utils/request'

const userStore = useUserStore()
const store = useAgentStore()

// ── 本地状态 ──────────────────────────────────────────
const messageContainer = ref(null)
const inputText = ref('')
const sidebarCollapsed = ref(false)
const atBottom = ref(true)
const waitingFirstToken = ref(false)
let stopStream = null

// ── 计算属性 ──────────────────────────────────────────
const userAvatar = computed(() => userStore.user?.avatar || '')

const currentSessionTitle = computed(() => {
  if (!store.currentSessionId) return ''
  const session = store.sessions.find(s => s.id === store.currentSessionId)
  return session?.title || ''
})

const quickPrompts = [
  { label: '目标检测', text: '请帮我检测这张遥感图像中的飞机和储油罐', icon: Camera },
  { label: '模型分析', text: '分析当前模型的检测精度和优化建议', icon: DataAnalysis },
  { label: '专业问答', text: 'YOLOv11 相比 YOLOv8 有哪些改进？', icon: QuestionFilled },
]

// ── 滚动控制 ──────────────────────────────────────────
function scrollToBottom() {
  nextTick(() => {
    const el = messageContainer.value
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    }
  })
}

function onScroll() {
  const el = messageContainer.value
  if (!el) return
  const threshold = 60
  atBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < threshold
}

watch(() => store.messages.length, () => {
  if (atBottom.value) scrollToBottom()
})

watch(() => store.messages, () => {
  if (atBottom.value) scrollToBottom()
}, { deep: true })

// ── 键盘事件 ──────────────────────────────────────────
function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

// ── 新建对话 ──────────────────────────────────────────
function handleNewChat() {
  if (store.isLoading) {
    handleStop()
  }
  store.newChat()
  inputText.value = ''
}

// ── 切换会话 ──────────────────────────────────────────
async function handleSwitchSession(session) {
  if (store.isLoading) return
  store.currentSessionId = session.id
  store.messages = []
  try {
    const res = await request.get(`/chat/sessions/${session.id}/messages`)
    store.messages = res.messages || res.data || []
    scrollToBottom()
  } catch {
    // 会话消息加载失败
  }
}

// ── 快捷提示 ──────────────────────────────────────────
function handleQuickPrompt(text) {
  inputText.value = text
  handleSend()
}

// ── 发送消息 ──────────────────────────────────────────
async function handleSend() {
  const content = inputText.value.trim()
  if (!content || store.isLoading) return

  inputText.value = ''
  waitingFirstToken.value = true

  // 添加用户消息
  store.addMessage({
    role: 'user',
    content,
    agent_used: null,
    tool_calls: null,
    tokens_used: null,
    latency_ms: null,
    created_at: new Date().toISOString(),
  })

  // 准备 AI 消息占位
  store.addMessage({
    role: 'assistant',
    content: '',
    agent_used: null,
    tool_calls: [],
    tokens_used: null,
    latency_ms: null,
    isStreaming: true,
  })

  store.setLoading(true)
  scrollToBottom()

  const startTime = Date.now()

  stopStream = streamChat(
    '/api/chat/stream',
    {
      session_id: store.currentSessionId,
      message: content,
    },
    {
      onMessage(chunk) {
        waitingFirstToken.value = false

        const lastMsg = store.messages[store.messages.length - 1]
        if (!lastMsg || lastMsg.role !== 'assistant') return

        switch (chunk.type) {
          case 'text':
            lastMsg.content += chunk.content || ''
            break

          case 'agent':
            lastMsg.agent_used = chunk.agent
            break

          case 'tool_start':
            if (!lastMsg.tool_calls) lastMsg.tool_calls = []
            lastMsg.tool_calls.push({
              tool: chunk.tool,
              args: chunk.args,
              result: null,
            })
            break

          case 'tool_end':
            if (lastMsg.tool_calls && lastMsg.tool_calls.length > 0) {
              const tc = lastMsg.tool_calls[lastMsg.tool_calls.length - 1]
              tc.result = chunk.result
            }
            break

          case 'token_info':
            lastMsg.tokens_used = chunk.tokens
            lastMsg.latency_ms = Date.now() - startTime
            break

          default:
            // 兼容纯文本 SSE（非 JSON chunk 已在 stream.js 中作为字符串传给 onMessage）
            if (typeof chunk === 'string') {
              lastMsg.content += chunk
            }
        }

        if (atBottom.value) scrollToBottom()
      },

      onDone() {
        const lastMsg = store.messages[store.messages.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.isStreaming = false
          lastMsg.latency_ms = Date.now() - startTime
        }
        store.setLoading(false)
        waitingFirstToken.value = false
        stopStream = null

        // 更新当前会话 ID
        if (!store.currentSessionId && lastMsg?.content) {
          // 新会话创建成功后会由后端返回 session_id
          // store.currentSessionId = ...
        }
      },

      onError(err) {
        store.setLoading(false)
        waitingFirstToken.value = false

        const lastMsg = store.messages[store.messages.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.isStreaming = false
          if (!lastMsg.content) {
            lastMsg.content = '抱歉，请求遇到问题，请稍后重试。'
          }
        }
        stopStream = null
        ElMessage.error('连接失败: ' + (err.message || '未知错误'))
      },
    }
  )
}

// ── 停止生成 ──────────────────────────────────────────
function handleStop() {
  if (stopStream) {
    stopStream()
    stopStream = null
  }
  store.setLoading(false)
  waitingFirstToken.value = false

  const lastMsg = store.messages[store.messages.length - 1]
  if (lastMsg && lastMsg.role === 'assistant') {
    lastMsg.isStreaming = false
    if (!lastMsg.content) {
      lastMsg.content = '(已中断)'
    }
  }
}

// ── 加载会话列表（首次进入） ──────────────────────────
async function loadSessions() {
  try {
    const res = await request.get('/chat/sessions')
    store.sessions = res.sessions || res.data || []
  } catch {
    // 会话列表接口尚未就绪
  }
}

loadSessions()

// ── 组件卸载时清理 ────────────────────────────────────
onBeforeUnmount(() => {
  if (stopStream) {
    stopStream()
    stopStream = null
  }
})
</script>

<style lang="scss" scoped>
.chat-page {
  display: flex;
  height: calc(100vh - #{$header-height} - #{$spacing-lg} * 2);
  background: #fff;
  border-radius: $border-radius-md;
  overflow: hidden;
  box-shadow: $shadow-sm;
}

// ── 左侧会话列表 ──────────────────────────────────────
.chat-sessions {
  width: 260px;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  background: #fafbfc;
  transition: width 0.2s;

  &.collapsed {
    width: 48px;
  }
}

.sessions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
  min-height: 48px;
}

.sessions-title {
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
}

.sessions-body {
  flex: 1;
  padding: 12px;
  overflow-y: auto;
}

.sessions-list {
  .session-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    border-radius: $border-radius-sm;
    cursor: pointer;
    font-size: 13px;
    color: $text-regular;
    transition: background 0.15s;

    &:hover {
      background: #e8ecf1;
    }

    &.active {
      background: rgba($primary-color, 0.1);
      color: $primary-color;
    }
  }

  .session-title {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

// ── 右侧对话主区域 ────────────────────────────────────
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 16px;
  border-bottom: 1px solid #ebeef5;
  background: #fafbfc;
}

.chat-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-title {
  font-weight: 600;
  font-size: 14px;
}

// ── 消息区域 ──────────────────────────────────────────
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  position: relative;
}

// ── 空状态 ────────────────────────────────────────────
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;

  .empty-icon {
    width: 96px;
    height: 96px;
    border-radius: 50%;
    background: linear-gradient(135deg, #e8f4fd 0%, #d4e8fa 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: $primary-color;
    margin-bottom: 20px;
  }

  h3 {
    font-size: 20px;
    color: $text-primary;
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: $text-secondary;
    margin-bottom: 28px;
  }
}

.quick-prompts {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

.quick-prompt-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border: 1px solid #e0e4ea;
  border-radius: $border-radius-md;
  cursor: pointer;
  font-size: 13px;
  color: $text-regular;
  transition: all 0.2s;

  &:hover {
    border-color: $primary-color;
    color: $primary-color;
    background: rgba($primary-color, 0.04);
  }
}

// ── 消息行 ────────────────────────────────────────────
.message-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 85%;

  &.user {
    margin-left: auto;
    flex-direction: row-reverse;
  }

  &.assistant {
    margin-right: auto;
  }
}

.message-avatar {
  flex-shrink: 0;
}

.message-body {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.message-agent-tag {
  margin-bottom: 4px;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: $border-radius-md;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;

  &.is-user {
    background: $primary-color;
    color: #fff;
    border-bottom-right-radius: 4px;
  }

  &.is-assistant {
    background: #f4f6f8;
    color: $text-primary;
    border-bottom-left-radius: 4px;

    // Markdown 内容样式
    :deep(.markdown-body) {
      h1, h2, h3, h4, h5, h6 {
        margin: 12px 0 8px;
        font-weight: 600;
        line-height: 1.4;
      }
      h1 { font-size: 1.4em; }
      h2 { font-size: 1.2em; }
      h3 { font-size: 1.1em; }

      p { margin: 6px 0; }

      ul, ol {
        padding-left: 20px;
        margin: 6px 0;
      }

      li { margin: 2px 0; }

      code {
        background: rgba(0, 0, 0, 0.06);
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 0.9em;
        font-family: 'Menlo', 'Consolas', monospace;
      }

      pre {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 12px 16px;
        border-radius: $border-radius-sm;
        overflow-x: auto;
        margin: 8px 0;

        code {
          background: none;
          padding: 0;
          color: inherit;
        }
      }

      blockquote {
        border-left: 3px solid $primary-color;
        padding-left: 12px;
        color: $text-secondary;
        margin: 8px 0;
      }

      table {
        border-collapse: collapse;
        margin: 8px 0;
        width: 100%;

        th, td {
          border: 1px solid #ddd;
          padding: 6px 10px;
          text-align: left;
        }

        th {
          background: #f5f7fa;
          font-weight: 600;
        }
      }

      a {
        color: $primary-color;
        &:hover { text-decoration: underline; }
      }

      img { max-width: 100%; border-radius: 4px; }
    }
  }
}

.streaming-cursor {
  animation: blink 0.8s infinite;
  color: $primary-color;
  font-weight: bold;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

// ── 打字指示器 ────────────────────────────────────────
.typing-indicator {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 4px 0;

  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #b0b8c4;
    animation: dotPulse 1.2s infinite ease-in-out;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes dotPulse {
  0%, 60%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  30% {
    opacity: 1;
    transform: scale(1.2);
  }
}

// ── 工具调用展示 ──────────────────────────────────────
.tool-calls {
  margin-bottom: 8px;

  :deep(.el-collapse) {
    border: none;
    --el-collapse-header-bg-color: rgba(0, 0, 0, 0.03);
    --el-collapse-content-bg-color: rgba(0, 0, 0, 0.01);
    border-radius: $border-radius-sm;
    overflow: hidden;
  }

  :deep(.el-collapse-item__header) {
    font-size: 12px;
    padding: 0 10px;
    height: 32px;
    line-height: 32px;
    color: $text-secondary;
  }

  :deep(.el-collapse-item__content) {
    font-size: 12px;
    padding: 8px 10px;
  }
}

.tool-call-detail {
  .tool-section {
    margin-bottom: 6px;
  }
  .tool-label {
    font-weight: 600;
    color: $text-secondary;
  }
  pre {
    background: rgba(0, 0, 0, 0.04);
    padding: 6px 8px;
    border-radius: 3px;
    font-size: 12px;
    overflow-x: auto;
    max-height: 120px;
    overflow-y: auto;
    margin-top: 2px;
  }
}

// ── 消息元信息 ────────────────────────────────────────
.message-meta {
  font-size: 11px;
  color: $text-placeholder;
  margin-top: 4px;
  padding: 0 8px;
  display: flex;
  gap: 12px;
}

// ── 回到底部 ──────────────────────────────────────────
.scroll-to-bottom {
  position: sticky;
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #fff;
  box-shadow: $shadow-md;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: $text-secondary;
  transition: all 0.2s;

  &:hover {
    color: $primary-color;
    box-shadow: $shadow-lg;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// ── 底部输入区 ────────────────────────────────────────
.chat-input-area {
  border-top: 1px solid #ebeef5;
  padding: 14px 20px;
  background: #fafbfc;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 10px;

  :deep(.el-textarea__inner) {
    border-radius: $border-radius-md;
    padding-right: 12px;
    line-height: 1.5;
  }
}

.send-btn {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  border-radius: 50%;
}

.input-hint {
  text-align: center;
  font-size: 11px;
  color: $text-placeholder;
  margin-top: 8px;
}
</style>
