<template>
  <div class="history-view">
    <div class="section-head">
      <div>
        <h2>历史对话</h2>
        <p>每次新建行程都会留下一个对话，点开可以接着聊或修改</p>
      </div>
    </div>

    <div v-if="loading" class="empty-state">加载中…</div>

    <div v-else-if="threads.length" class="thread-list">
      <div v-for="t in threads" :key="t.thread_id" class="thread-item">
        <div class="thread-body" @click="$emit('open', t)">
          <h4>{{ t.title }}</h4>
          <p>{{ formatDate(t.updated_at) }} · {{ t.message_count }} 条消息</p>
        </div>
        <button class="thread-del" title="删除对话" @click.stop="remove(t)">
          <BaseIcon name="trash" :size="14" />
        </button>
      </div>
    </div>

    <div v-else class="empty-state">
      <div class="empty-mark"><BaseIcon name="message" :size="26" /></div>
      <h3>还没有历史对话</h3>
      <p>去灵感页输入一句旅行需求，对话就会出现在这里</p>
      <button class="btn btn-primary" @click="$emit('go-home')">去规划行程</button>
    </div>
  </div>
</template>

<script>
import BaseIcon from "./BaseIcon.vue";
import { fetchThreads, deleteThread } from "../utils/threads.js";

export default {
  name: "HistoryView",
  components: { BaseIcon },
  emits: ["open", "go-home"],
  data() {
    return { threads: [], loading: true };
  },
  async mounted() {
    await this.refresh();
  },
  methods: {
    async refresh() {
      this.threads = await fetchThreads();
      this.loading = false;
    },
    formatDate(ts) {
      if (!ts) return "";
      const d = new Date(ts * 1000);
      return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
    },
    async remove(t) {
      await deleteThread(t.thread_id);
      await this.refresh();
    },
  },
};
</script>

<style scoped>
.history-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 36px 32px 56px;
}
.section-head {
  margin-bottom: 22px;
}
.section-head h2 {
  font-size: 22px;
  font-weight: 600;
  color: var(--ink);
}
.section-head p {
  margin-top: 4px;
  font-size: 13.5px;
  color: var(--muted);
}
.thread-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.thread-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--line, #e5e7eb);
  border-radius: 10px;
  background: #fff;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.thread-item:hover {
  border-color: #c7d2fe;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
}
.thread-body {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}
.thread-body h4 {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.thread-body p {
  margin-top: 4px;
  font-size: 12.5px;
  color: var(--muted);
}
.thread-del {
  border: none;
  background: none;
  color: var(--muted);
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
}
.thread-del:hover {
  color: #dc2626;
  background: #fef2f2;
}
</style>
