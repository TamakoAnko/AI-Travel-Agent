<template>
  <div class="chat-view">
    <!-- 正在修改某份已保存行程时，明确提示当前在哪个会话里 -->
    <div v-if="editingTrip" class="chat-editing">
      <span>正在修改：{{ editingTrip }}</span>
      <button class="chat-editing-new" @click="$emit('new-trip')">新建行程</button>
    </div>
    <div class="chat-messages" ref="msgPanel">
      <!-- 空状态欢迎 -->
      <div v-if="messages.length === 0" class="chat-empty">
        <div class="empty-mark"><BaseIcon name="compass" :size="26" /></div>
        <h2>聊聊你的旅行想法</h2>
        <p>告诉我你想去哪里、待几天、预算多少，我来为你规划完整行程。</p>
        <div class="empty-examples">
          <button
            v-for="ex in examples"
            :key="ex"
            class="empty-chip"
            @click="fillExample(ex)"
          >
            {{ ex }}
          </button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        :class="['chat-msg', msg.role]"
      >
        <div class="msg-avatar">
          <BaseIcon :name="msg.role === 'user' ? 'user' : 'plane'" :size="15" />
        </div>
        <div class="msg-body">
          <!-- 思考过程（可折叠） -->
          <div
            v-if="msg.role === 'assistant' && (msg.thinking || msg._progressLabel)"
            class="thinking-section"
          >
            <button
              class="thinking-header"
              @click="msg._thinkingExpanded = !msg._thinkingExpanded"
            >
              <BaseIcon
                name="chevron-down"
                :size="13"
                :class="['thinking-arrow', msg._thinkingExpanded ? '' : 'collapsed']"
              />
              <span v-if="!msg._thinkingDone" class="spinner" style="width: 11px; height: 11px;"></span>
              <span class="thinking-label">
                {{ msg._thinkingDone ? '思考过程' : (msg._progressLabel || '正在规划...') }}
              </span>
              <span class="thinking-duration">{{ msg._thinkingDuration || '' }}</span>
            </button>
            <div v-if="msg._thinkingExpanded && msg.thinking" class="thinking-content md-body" v-html="renderMarkdown(msg.thinking)"></div>
          </div>

          <!-- 主内容 -->
          <div class="msg-content md-body" v-html="renderMarkdown(msg.content)"></div>
        </div>

        <!-- 反馈按钮（最后一条 assistant） -->
        <div
          v-if="msg.role === 'assistant' && idx === messages.length - 1 && !approvalPending && !loading && msg.content.length > 30"
          class="feedback-btns"
        >
          <button
            :class="['fb-btn', feedbackGiven === 'positive' ? 'active' : '']"
            :disabled="!!feedbackGiven"
            title="回答有帮助"
            @click="$emit('feedback', 'positive')"
          >
            <BaseIcon name="thumbs-up" :size="14" />
          </button>
          <button
            :class="['fb-btn', feedbackGiven === 'negative' ? 'active' : '']"
            :disabled="!!feedbackGiven"
            title="回答需要改进"
            @click="$emit('feedback', 'negative')"
          >
            <BaseIcon name="thumbs-down" :size="14" />
          </button>
          <span v-if="feedbackGiven" class="fb-thanks">{{ feedbackGiven === 'positive' ? '感谢反馈' : '感谢反馈，我们会改进' }}</span>
        </div>
      </div>

      <!-- 加载中 -->
      <div v-if="loading && !(messages.length && messages[messages.length-1]._streaming)" class="chat-msg assistant">
        <div class="msg-avatar">
          <BaseIcon name="plane" :size="15" />
        </div>
        <div class="msg-body">
          <div class="msg-content loading-msg">
            <span class="spinner"></span>
            正在协调航班、酒店、行程与天气信息，预计 30-60 秒...
          </div>
        </div>
      </div>

      <!-- Human-in-the-Loop 审批卡片 -->
      <div v-if="approvalPending" :class="['approval-card', hitlStage === 'trip_review' ? 'card-review' : 'card-approval']">
        <div class="approval-header">
          <BaseIcon :name="hitlStage === 'trip_review' ? 'navigation' : 'check-circle'" :size="16" />
          <strong>{{ hitlStage === 'trip_review' ? '行程信息确认' : '旅行计划已生成，请确认' }}</strong>
        </div>
        <div class="approval-preview md-body" v-html="renderMarkdown(approvalPlanPreview)"></div>
        <div class="approval-actions">
          <button class="btn btn-primary btn-sm" :disabled="approvalLoading" @click="$emit('approve')">
            <BaseIcon name="check" :size="14" />
            {{ hitlStage === 'trip_review' ? '确认并开始搜索' : '确认通过' }}
          </button>
          <div class="reject-group">
            <input
              v-model="rejectText"
              :placeholder="hitlStage === 'trip_review' ? '修改意见或补充说明（如：预算增加到15000）' : '请输入修改意见（如：预算太高，换成经济型酒店）'"
              class="reject-input"
              :disabled="approvalLoading"
            />
            <button class="btn btn-outline btn-sm" :disabled="approvalLoading" @click="$emit('reject')">
              <BaseIcon name="refresh" :size="14" />
              {{ hitlStage === 'trip_review' ? '驳回/补充' : '驳回修改' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入栏 -->
    <div class="chat-input-area">
      <div class="chat-input">
        <input
          v-model="inputTextValue"
          @keydown.enter="send"
          :placeholder="approvalPending
            ? '请先处理上方的行程确认，再继续对话'
            : '描述你的旅行想法...'"
          :disabled="loading"
        />
        <button
          v-if="loading"
          class="btn-stop"
          title="停止生成"
          @click="$emit('stop')"
        >
          <BaseIcon name="stop" :size="16" />
        </button>
        <button
          class="btn-send"
          :disabled="loading || approvalPending || !inputTextValue.trim()"
          @click="send"
          title="发送"
        >
          <BaseIcon name="send" :size="16" />
        </button>
      </div>
      <p class="input-note">Enter 发送 · 生成内容由 AI 提供，请以实际预订信息为准</p>
    </div>
  </div>
</template>

<script>
import BaseIcon from "./BaseIcon.vue";
import { renderMarkdown } from "../utils/markdown.js";

export default {
  name: "ChatView",
  components: { BaseIcon },
  props: {
    messages: { type: Array, required: true },
    loading: Boolean,
    approvalPending: Boolean,
    approvalPlanPreview: String,
    hitlStage: String,
    approvalLoading: Boolean,
    rejectFeedback: String,
    feedbackGiven: String,
    inputText: String,
    editingTrip: String,
  },
  data() {
    return {
      examples: [
        "帮我规划一趟 5 天的巴黎之旅，6 月出发，预算 15000 元，我喜欢艺术和美食",
        "周末东京两日游，预算 10000 元，喜欢动漫和街头小吃",
        "意大利 10 天，游览罗马和佛罗伦萨，预算 25000 元，历史爱好者",
      ],
    };
  },
  computed: {
    inputTextValue: {
      get() {
        return this.inputText;
      },
      set(v) {
        this.$emit("update:inputText", v);
      },
    },
    rejectText: {
      get() {
        return this.rejectFeedback;
      },
      set(v) {
        this.$emit("update:rejectFeedback", v);
      },
    },
  },
  mounted() {
    this.scrollToBottom();
  },
  updated() {
    const lastMsg = this.messages[this.messages.length - 1];
    if (this.loading || this.approvalLoading || (lastMsg && lastMsg._streaming)) {
      this.scrollToBottom();
    }
  },
  methods: {
    renderMarkdown,
    send() {
      this.$emit("send");
    },
    fillExample(ex) {
      this.$emit("update:inputText", ex);
      this.$emit("send");
    },
    scrollToBottom() {
      const el = this.$refs.msgPanel;
      if (el) el.scrollTop = el.scrollHeight;
    },
  },
};
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  max-width: 860px;
  margin: 0 auto;
  height: calc(100vh - var(--header-h));
  padding: 0 32px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 28px 0 16px;
  scroll-behavior: smooth;
}

/* 空状态 */
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 64px 24px;
}
.empty-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: var(--brand-soft);
  color: var(--brand);
}
.chat-empty h2 {
  margin-top: 18px;
  font-size: 21px;
  font-weight: 600;
  color: var(--ink);
}
.chat-empty p {
  margin-top: 8px;
  font-size: 14.5px;
  color: var(--muted);
  max-width: 420px;
}
.empty-examples {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 26px;
  width: 100%;
  max-width: 520px;
}
.empty-chip {
  padding: 12px 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--bg);
  color: var(--ink-2);
  font-size: 13.5px;
  text-align: left;
  transition: all 0.2s ease;
}
.empty-chip:hover {
  border-color: var(--brand);
  color: var(--brand);
  background: var(--brand-soft);
}

/* 消息 */
.chat-msg {
  display: flex;
  gap: 12px;
  padding: 14px 0;
}
.chat-msg + .chat-msg {
  border-top: 1px solid var(--line-soft);
}
.msg-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: var(--brand-soft);
  color: var(--brand);
  flex-shrink: 0;
  margin-top: 2px;
}
.chat-msg.user .msg-avatar {
  background: var(--bg-gray);
  color: var(--ink-2);
}
.msg-body {
  flex: 1;
  min-width: 0;
}
.msg-content {
  padding-top: 2px;
}
.chat-msg.user .msg-content {
  color: var(--ink-2);
}
.loading-msg {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 7px;
  color: var(--muted);
  font-size: 14px;
}

/* 思考过程 */
.thinking-section {
  margin-bottom: 10px;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-sm);
  background: var(--bg-soft);
  overflow: hidden;
}
.thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--muted);
  text-align: left;
  transition: background 0.2s ease;
}
.thinking-header:hover {
  background: var(--bg-gray);
}
.thinking-arrow {
  transition: transform 0.2s ease;
  color: var(--faint);
}
.thinking-arrow.collapsed {
  transform: rotate(-90deg);
}
.thinking-label {
  font-weight: 500;
}
.thinking-duration {
  margin-left: auto;
  font-size: 12px;
  color: var(--faint);
}
.thinking-content {
  padding: 4px 12px 12px;
  font-size: 13px;
  border-top: 1px solid var(--line-soft);
}

/* 反馈 */
.feedback-btns {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 8px 0 0 42px;
}
.fb-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--line);
  border-radius: var(--radius-xs);
  background: var(--bg);
  color: var(--muted);
  transition: all 0.2s ease;
}
.fb-btn:hover:not(:disabled) {
  border-color: var(--brand);
  color: var(--brand);
}
.fb-btn.active {
  border-color: var(--brand);
  background: var(--brand-soft);
  color: var(--brand);
}
.fb-thanks {
  margin-left: 4px;
  font-size: 12.5px;
  color: var(--muted);
}

/* 审批卡片 */
.approval-card {
  margin: 16px 0;
  padding: 20px;
  border: 1px solid var(--brand-line);
  border-radius: var(--radius-lg);
  background: var(--brand-soft);
}
.approval-card.card-approval {
  border-color: var(--line);
  background: var(--bg-soft);
}
.approval-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: var(--brand-strong);
  font-size: 14.5px;
}
.card-approval .approval-header {
  color: var(--ink);
}
.approval-preview {
  max-height: 320px;
  overflow-y: auto;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: var(--bg);
  border: 1px solid var(--line-soft);
}
.approval-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-top: 14px;
}
.reject-group {
  display: flex;
  flex: 1;
  gap: 8px;
  min-width: 280px;
}
.reject-input {
  flex: 1;
  padding: 7px 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  outline: none;
  font-size: 13.5px;
  background: var(--bg);
  transition: border-color 0.2s ease;
}
.reject-input:focus {
  border-color: var(--brand);
}

/* 输入栏 */
.chat-editing {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  max-width: 860px;
  margin: 0 auto;
  padding: 9px 14px;
  border: 1px solid #dbe4ff;
  border-radius: 10px;
  background: #eff4ff;
  color: #1e3a8a;
  font-size: 13px;
}
.chat-editing-new {
  border: none;
  background: none;
  color: #2563eb;
  font-size: 13px;
  cursor: pointer;
  padding: 0;
}
.chat-editing-new:hover {
  text-decoration: underline;
}
.chat-input-area {
  padding: 12px 0 20px;
}
.chat-input {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 8px 8px 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--bg);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.chat-input:focus-within {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}
.chat-input input {
  flex: 1;
  border: none;
  outline: none;
  padding: 7px 0;
  color: var(--ink);
  background: none;
}
.chat-input input::placeholder {
  color: var(--faint);
}
.chat-input input:disabled {
  color: var(--faint);
}
.btn-stop {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background: var(--rose-soft);
  color: var(--rose);
}
.btn-send {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background: var(--brand);
  color: #fff;
  transition: background 0.2s ease;
}
.btn-send:hover:not(:disabled) {
  background: var(--brand-strong);
}
.btn-send:disabled {
  background: var(--line);
  color: var(--faint);
  cursor: not-allowed;
}
.input-note {
  margin-top: 8px;
  text-align: center;
  font-size: 12px;
  color: var(--faint);
}

/* 响应式 */
@media (max-width: 639px) {
  .chat-view {
    padding: 0 16px;
  }
  .chat-messages {
    padding-top: 16px;
  }
  .reject-group {
    flex-direction: column;
    min-width: 0;
    width: 100%;
  }
}
</style>
