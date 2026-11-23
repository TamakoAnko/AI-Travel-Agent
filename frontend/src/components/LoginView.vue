<template>
  <div class="login-view">
    <!-- 左侧品牌视觉 -->
    <div class="login-visual">
      <div class="visual-img"></div>
      <div class="visual-overlay"></div>
      <div class="visual-content">
        <div class="visual-brand">
          <span class="brand-mark"><BaseIcon name="plane" :size="20" /></span>
          <span class="brand-name">Voyage</span>
        </div>
        <h1>下一段旅程，<br />从这里开始。</h1>
        <p>告诉我们你想去哪里，剩下的交给我们。</p>
      </div>
    </div>

    <!-- 右侧登录表单 -->
    <div class="login-panel">
      <div class="login-box">
        <div class="login-mobile-brand">
          <span class="brand-mark"><BaseIcon name="plane" :size="20" /></span>
          <span class="brand-name">Voyage</span>
        </div>

        <h2 class="login-title">欢迎回来</h2>
        <p class="login-subtitle">使用手机号登录，你的旅行记录与偏好将自动保存</p>

        <div class="login-field">
          <label>手机号</label>
          <div class="input-wrap">
            <BaseIcon name="phone" :size="16" />
            <input
              v-model="phoneValue"
              type="tel"
              maxlength="11"
              placeholder="请输入 11 位手机号"
              @keydown.enter="emitLogin"
            />
          </div>
        </div>

        <div class="login-field">
          <label>验证码</label>
          <div class="code-row">
            <div class="input-wrap grow">
              <BaseIcon name="lock" :size="16" />
              <input
                v-model="codeValue"
                type="text"
                maxlength="6"
                placeholder="6 位数字验证码"
                @keydown.enter="emitLogin"
              />
            </div>
            <button
              class="btn-code"
              :disabled="sendingCode || countdown > 0"
              @click="$emit('send-code')"
            >
              {{ countdown > 0 ? `${countdown}s 后重发` : sendingCode ? "发送中..." : "获取验证码" }}
            </button>
          </div>
        </div>

        <p v-if="loginError" class="login-error">
          <BaseIcon name="alert" :size="14" /> {{ loginError }}
        </p>
        <p v-if="loginHint" class="login-hint">
          <BaseIcon name="message" :size="14" /> {{ loginHint }}
        </p>

        <button class="btn-login" :disabled="loginLoading" @click="emitLogin">
          <span v-if="loginLoading" class="spinner"></span>
          {{ loginLoading ? "登录中..." : "登 录" }}
        </button>

        <p class="login-foot">未注册的手机号验证后将自动注册</p>
      </div>
    </div>
  </div>
</template>

<script>
import BaseIcon from "./BaseIcon.vue";

export default {
  name: "LoginView",
  components: { BaseIcon },
  props: {
    loginForm: { type: Object, required: true },
    sendingCode: Boolean,
    countdown: Number,
    loginError: String,
    loginHint: String,
    loginLoading: Boolean,
  },
  computed: {
    phoneValue: {
      get() {
        return this.loginForm.phone;
      },
      set(v) {
        this.$emit("update:loginForm", { ...this.loginForm, phone: v });
      },
    },
    codeValue: {
      get() {
        return this.loginForm.code;
      },
      set(v) {
        this.$emit("update:loginForm", { ...this.loginForm, code: v });
      },
    },
  },
  methods: {
    emitLogin() {
      this.$emit("login");
    },
  },
};
</script>

<style scoped>
.login-view {
  display: flex;
  min-height: 100vh;
}

/* 左：品牌视觉 */
.login-visual {
  position: relative;
  flex: 1.1;
  min-height: 100vh;
  overflow: hidden;
  display: none;
}
@media (min-width: 900px) {
  .login-visual {
    display: block;
  }
}
.visual-img {
  position: absolute;
  inset: 0;
  background: linear-gradient(150deg, #16283f 0%, #2b4a73 45%, #4a6f9e 100%);
  background-image: url("https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=1600&q=80");
  background-size: cover;
  background-position: center;
}
.visual-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(12, 22, 38, 0.35) 0%, rgba(12, 22, 38, 0.12) 40%, rgba(12, 22, 38, 0.55) 100%);
}
.visual-content {
  position: relative;
  z-index: 1;
  padding: 48px 56px;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.visual-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #fff;
}
.visual-content h1 {
  margin-top: auto;
  color: #fff;
  font-size: 40px;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: 0.5px;
}
.visual-content p {
  margin-top: 14px;
  color: rgba(255, 255, 255, 0.82);
  font-size: 16px;
}

/* 品牌标记 */
.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: var(--brand);
  color: #fff;
}
.brand-name {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

/* 右：表单 */
.login-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
  background: var(--bg);
}
.login-box {
  width: 380px;
  max-width: 100%;
}
.login-mobile-brand {
  display: none;
  align-items: center;
  gap: 10px;
  margin-bottom: 32px;
}
@media (max-width: 899px) {
  .login-mobile-brand {
    display: flex;
  }
}
.login-title {
  font-size: 26px;
  font-weight: 600;
  color: var(--ink);
}
.login-subtitle {
  margin: 8px 0 28px;
  font-size: 14px;
  color: var(--muted);
}
.login-field {
  margin-bottom: 18px;
}
.login-field label {
  display: block;
  margin-bottom: 7px;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--ink-2);
}
.input-wrap {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 13px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--bg);
  color: var(--faint);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.input-wrap:focus-within {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}
.input-wrap input {
  flex: 1;
  border: none;
  outline: none;
  padding: 11px 0;
  background: none;
  color: var(--ink);
}
.input-wrap input::placeholder {
  color: var(--faint);
}
.code-row {
  display: flex;
  gap: 10px;
}
.input-wrap.grow {
  flex: 1;
}
.btn-code {
  padding: 0 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--bg);
  color: var(--brand);
  font-size: 13.5px;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}
.btn-code:hover:not(:disabled) {
  border-color: var(--brand);
  background: var(--brand-soft);
}
.btn-code:disabled {
  color: var(--faint);
  cursor: not-allowed;
}
.login-error {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 14px;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  background: var(--rose-soft);
  color: var(--rose);
  font-size: 13px;
}
.login-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 14px;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  background: var(--brand-soft);
  color: var(--brand-strong);
  font-size: 13px;
}
.btn-login {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--brand);
  color: #fff;
  font-size: 15px;
  font-weight: 500;
  transition: background 0.2s ease;
}
.btn-login:hover:not(:disabled) {
  background: var(--brand-strong);
}
.btn-login:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.login-foot {
  margin-top: 18px;
  text-align: center;
  font-size: 12.5px;
  color: var(--faint);
}
</style>
