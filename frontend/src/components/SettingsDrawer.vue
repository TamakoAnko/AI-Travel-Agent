<template>
  <transition name="fade">
    <div v-if="open" class="drawer-mask" @click.self="$emit('close')">
      <aside class="settings-drawer">
        <div class="drawer-head">
          <h3>设置</h3>
          <button class="drawer-close" @click="$emit('close')">
            <BaseIcon name="x" :size="16" />
          </button>
        </div>

        <div class="drawer-body">
          <!-- 账号 -->
          <div class="drawer-section">
            <h4>账号</h4>
            <div class="account-box">
              <div class="account-avatar"><BaseIcon name="user" :size="18" /></div>
              <div class="account-info">
                <span class="account-phone">{{ phone }}</span>
                <span class="account-note">旅行记录与偏好将随账号保存</span>
              </div>
            </div>
            <button class="btn btn-outline btn-sm" @click="$emit('logout')">
              <BaseIcon name="log-out" :size="14" /> 退出登录
            </button>
          </div>

          <div class="drawer-divider"></div>

          <!-- 数据 -->
          <div class="drawer-section">
            <h4>数据</h4>
            <button class="btn btn-outline btn-sm" @click="$emit('clear')">
              <BaseIcon name="trash" :size="14" /> 清空当前对话
            </button>
          </div>

          <div class="drawer-divider"></div>

          <!-- 系统状态（开发信息，仅设置内展示） -->
          <div class="drawer-section">
            <h4>系统状态</h4>
            <div class="status-list">
              <div class="status-row">
                <span class="status-dot" :class="status.deepseek ? 'ok' : 'err'"></span>
                智能规划服务
                <span class="status-val">{{ status.deepseek ? "正常" : "异常" }}</span>
              </div>
              <div class="status-row">
                <span class="status-dot" :class="status.tavily ? 'ok' : 'err'"></span>
                实时搜索
                <span class="status-val">{{ status.tavily ? "正常" : "异常" }}</span>
              </div>
              <div class="status-row">
                <span class="status-dot" :class="status.baidu_map ? 'ok' : 'err'"></span>
                地图服务
                <span class="status-val">{{ status.baidu_map ? "正常" : "异常" }}</span>
              </div>
              <div class="status-row">
                <span class="status-dot" :class="status.redis ? 'ok' : 'err'"></span>
                会话记忆
                <span class="status-val">{{ status.redis ? "正常" : "异常" }}</span>
              </div>
              <div class="status-row">
                <span class="status-dot" :class="status.mysql ? 'ok' : 'err'"></span>
                用户画像
                <span class="status-val">{{ status.mysql ? "正常" : "异常" }}</span>
              </div>
              <div class="status-row">
                <span class="status-dot" :class="status.milvus ? 'ok' : 'err'"></span>
                语义匹配
                <span class="status-val">{{ status.milvus ? "正常" : "异常" }}</span>
              </div>
            </div>
            <p class="status-note">部分服务离线时，相关能力会自动降级，不影响行程规划</p>
          </div>
        </div>
      </aside>
    </div>
  </transition>
</template>

<script>
import BaseIcon from "./BaseIcon.vue";

export default {
  name: "SettingsDrawer",
  components: { BaseIcon },
  props: {
    open: Boolean,
    phone: String,
    status: { type: Object, default: () => ({}) },
  },
};
</script>

<style scoped>
.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  z-index: 60;
  display: flex;
  justify-content: flex-end;
}
.settings-drawer {
  width: 360px;
  max-width: 92vw;
  height: 100%;
  background: var(--bg);
  display: flex;
  flex-direction: column;
  animation: slide-in 0.22s ease;
}
@keyframes slide-in {
  from {
    transform: translateX(24px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
.drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--line-soft);
}
.drawer-head h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}
.drawer-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-xs);
  color: var(--muted);
  transition: all 0.2s ease;
}
.drawer-close:hover {
  background: var(--bg-gray);
  color: var(--ink);
}
.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 20px 24px;
}
.drawer-section {
  padding: 16px 0;
}
.drawer-section h4 {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--faint);
  letter-spacing: 0.5px;
  margin-bottom: 12px;
  text-transform: uppercase;
}
.drawer-divider {
  height: 1px;
  background: var(--line-soft);
}
.account-box {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.account-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--brand-soft);
  color: var(--brand);
  flex-shrink: 0;
}
.account-info {
  display: flex;
  flex-direction: column;
}
.account-phone {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: 0.5px;
}
.account-note {
  font-size: 12px;
  color: var(--faint);
}
.status-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.status-row {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 13.5px;
  color: var(--ink-2);
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.ok {
  background: var(--emerald);
}
.status-dot.err {
  background: var(--rose);
}
.status-val {
  margin-left: auto;
  font-size: 12px;
  color: var(--faint);
}
.status-note {
  margin-top: 12px;
  font-size: 12px;
  color: var(--faint);
  line-height: 1.6;
}
</style>
