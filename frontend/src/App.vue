<template>
  <div class="app">
    <!-- ══════════ 未登录：登录页 ══════════ -->
    <LoginView
      v-if="!isLoggedIn"
      :login-form="loginForm"
      :sending-code="sendingCode"
      :countdown="countdown"
      :login-error="loginError"
      :login-hint="loginHint"
      :login-loading="loginLoading"
      @update:loginForm="loginForm = $event"
      @send-code="sendCode"
      @login="login"
    />

    <!-- ══════════ 已登录：主界面 ══════════ -->
    <div v-else class="app-shell">
      <!-- 顶部导航 -->
      <header class="site-header no-print">
        <div class="header-inner">
          <button class="brand" @click="goHome">
            <span class="brand-mark"><BaseIcon name="plane" :size="17" /></span>
            <span class="brand-name">Voyage</span>
            <span class="brand-sub">旅行规划</span>
          </button>

          <nav class="header-nav">
            <button :class="['nav-item', view === 'plan' ? 'active' : '']" @click="goPlan">行程</button>
            <button :class="['nav-item', view === 'home' ? 'active' : '']" @click="goHome">灵感</button>
            <button :class="['nav-item', view === 'saved' ? 'active' : '']" @click="goSaved">我的旅行</button>
            <button class="nav-item" @click="showHelp = true">帮助</button>
          </nav>

          <div class="header-right">
            <button class="btn btn-primary btn-sm new-trip-btn" @click="newTrip">
              <BaseIcon name="plus" :size="14" /> 新行程
            </button>
            <button class="avatar-btn" title="账号与设置" @click="showSettings = true">
              <span class="avatar"><BaseIcon name="user" :size="16" /></span>
            </button>
            <button class="menu-btn" title="菜单" @click="mobileMenu = !mobileMenu">
              <BaseIcon :name="mobileMenu ? 'x' : 'menu'" :size="19" />
            </button>
          </div>
        </div>

        <!-- 移动端导航面板 -->
        <transition name="fade">
          <nav v-if="mobileMenu" class="mobile-nav">
            <button :class="['mobile-nav-item', view === 'plan' ? 'active' : '']" @click="goPlan(); mobileMenu = false">行程</button>
            <button :class="['mobile-nav-item', view === 'home' ? 'active' : '']" @click="goHome(); mobileMenu = false">灵感</button>
            <button :class="['mobile-nav-item', view === 'saved' ? 'active' : '']" @click="goSaved(); mobileMenu = false">我的旅行</button>
            <button class="mobile-nav-item" @click="showHelp = true; mobileMenu = false">帮助</button>
            <button class="mobile-nav-item" @click="showSettings = true; mobileMenu = false">设置</button>
          </nav>
        </transition>
      </header>

      <!-- 主内容 -->
      <main class="site-main">
        <!-- 灵感首页 -->
        <HomeHero v-if="view === 'home'" @submit="submitFromHero" />

        <!-- 行程视图 -->
        <PlanView
          v-else-if="view === 'plan' && displayPlan"
          :plan="displayPlan"
          :raw-content="displayPlan ? displayPlan.raw : ''"
          :active-day="activeDay"
          :approval-pending="approvalPending"
          @day-change="activeDay = $event"
          @edit="editPlan"
          @save="handleSaveTrip"
          @copy="copyPlan"
          @share="sharePlan"
          @export="exportPlan"
          @ask="askFromPlan"
        />

        <!-- 对话视图 -->
        <ChatView
          v-else-if="view === 'chat'"
          ref="chatView"
          :messages="messages"
          :loading="loading"
          :approval-pending="approvalPending"
          :approval-plan-preview="approvalPlanPreview"
          :hitl-stage="hitlStage"
          :approval-loading="approvalLoading"
          :reject-feedback="rejectFeedback"
          :feedback-given="feedbackGiven"
          :input-text="inputText"
          @update:inputText="inputText = $event"
          @update:rejectFeedback="rejectFeedback = $event"
          @send="sendMessage"
          @stop="stopGeneration"
          @approve="handleApprove"
          @reject="handleReject"
          @feedback="submitFeedback"
        />

        <!-- 我的旅行 -->
        <SavedTripsView
          v-else-if="view === 'saved'"
          @go-plan="goPlan"
          @view-trip="viewSavedTrip"
          @copy-trip="copySavedTrip"
        />
      </main>

      <!-- 设置抽屉 -->
      <SettingsDrawer
        :open="showSettings"
        :phone="phone"
        :status="status"
        @close="showSettings = false"
        @logout="logout"
        @clear="handleClearChat"
      />

      <!-- 帮助弹窗 -->
      <transition name="fade">
        <div v-if="showHelp" class="modal-mask" @click.self="showHelp = false">
          <div class="help-modal">
            <div class="modal-head">
              <h3>使用帮助</h3>
              <button class="modal-close" @click="showHelp = false">
                <BaseIcon name="x" :size="16" />
              </button>
            </div>
            <div class="modal-body">
              <div class="help-item">
                <h4>如何开始规划？</h4>
                <p>在首页输入你的想法，例如「帮我规划一趟 5 天的巴黎之旅，6 月出发，预算 15000 元，我喜欢艺术和美食」。生成过程约需 30-60 秒。</p>
              </div>
              <div class="help-item">
                <h4>如何调整行程？</h4>
                <p>在行程页底部输入调整意见，或点击「修改需求」回到对话模式继续沟通，行程会实时更新。</p>
              </div>
              <div class="help-item">
                <h4>如何保存与导出？</h4>
                <p>行程页顶部提供保存、复制、分享与导出按钮。保存的行程可在「我的旅行」中查看。</p>
              </div>
              <div class="help-item">
                <h4>行程信息准确吗？</h4>
                <p>行程由 AI 基于实时搜索生成，价格与开放时间仅供参考，请以实际预订信息为准。</p>
              </div>
            </div>
          </div>
        </div>
      </transition>

      <!-- 轻提示 -->
      <transition name="fade">
        <div v-if="toast" class="toast">{{ toast }}</div>
      </transition>
    </div>
  </div>
</template>

<script>
import BaseIcon from "./components/BaseIcon.vue";
import LoginView from "./components/LoginView.vue";
import HomeHero from "./components/HomeHero.vue";
import ChatView from "./components/ChatView.vue";
import PlanView from "./components/PlanView.vue";
import SavedTripsView from "./components/SavedTripsView.vue";
import SettingsDrawer from "./components/SettingsDrawer.vue";
import { parsePlan, saveTrip, removeSavedTrip, getSavedTrips, fetchServerTrips } from "./utils/plan.js";
import { sanitizeJson } from "./utils/markdown.js";

// crypto.randomUUID 仅在安全上下文（HTTPS/localhost）可用；
// 公网 IP 走纯 HTTP 访问时不存在该方法，会导致 sendMessage 崩溃，故用 getRandomValues 兜底
function genUUID() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

export default {
  name: "App",
  components: {
    BaseIcon,
    LoginView,
    HomeHero,
    ChatView,
    PlanView,
    SavedTripsView,
    SettingsDrawer,
  },
  data() {
    return {
      // ── 视图路由 ──
      view: "home", // home | plan | chat | saved
      activeDay: 1,
      showSettings: false,
      showHelp: false,
      mobileMenu: false,
      toast: "",
      _toastTimer: null,
      _savedTripIds: {}, // raw -> id（用于取消保存）
      viewedTrip: null, // 从「我的旅行」查看的行程

      // ── 聊天状态（原逻辑完整保留） ──
      messages: [],
      inputText: "",
      loading: false,
      loadingStage: "",
      sessionId: null,
      userId: "",
      // 审批相关
      approvalPending: false,
      approvalPlanPreview: "",
      approvalLoading: false,
      rejectFeedback: "",
      hitlStage: "",
      feedbackGiven: null,
      _approvalAnchorIdx: -1, // 审批卡片对应的原消息索引（恢复流思考合并进该消息）
      _resumeFinalMsgIdx: null,
      // API 基础 URL
      apiBase: import.meta.env?.VITE_API_BASE || "",
      // API 状态（仅设置抽屉内展示）
      status: {
        deepseek: false,
        tavily: false,
        baidu_map: false,
        langsmith: false,
        redis: false,
        mysql: false,
        milvus: false,
      },
      // ── 登录鉴权状态 ──
      isLoggedIn: false,
      token: "",
      phone: "",
      loginForm: { phone: "", code: "" },
      sendingCode: false,
      countdown: 0,
      countdownTimer: null,
      loginError: "",
      loginHint: "",
      loginLoading: false,
      isNewUser: false,
    };
  },
  computed: {
    // 从最新一条含行程的 assistant 消息解析结构化行程
    currentPlan() {
      for (let i = this.messages.length - 1; i >= 0; i--) {
        const m = this.messages[i];
        if (m.role === "assistant" && m.content) {
          const p = parsePlan(m.content);
          if (p && (p.hasDays || (p.city && p.duration))) return p;
        }
      }
      return null;
    },
    displayPlan() {
      return this.viewedTrip || this.currentPlan;
    },
    hasTrip() {
      return !!this.currentPlan;
    },
  },
  mounted() {
    this._restoreSession(); // 刷新后恢复对话与行程（sessionStorage）
    this.checkAuth();
    this.fetchStatus();
  },
  watch: {
    // 会话状态持久化：刷新页面后仍能恢复聊天记录、行程与审批卡片
    messages: {
      deep: true,
      handler() {
        this._saveSession();
      },
    },
    approvalPending() {
      this._saveSession();
    },
    view() {
      this._saveSession();
    },
  },
  methods: {
    // ══════════════════════════════════════════════════
    // 视图路由
    // ══════════════════════════════════════════════════
    goHome() {
      this.view = "home";
    },
    async goPlan() {
      // 有行程看行程
      if (this.viewedTrip || this.hasTrip) {
        this.view = "plan";
        return;
      }
      // 有对话但还没出计划：回对话页，不丢进度
      if (this.messages.length) {
        this.view = "chat";
        return;
      }
      // 本页没有行程：取账号里最新的一份展示；没有才回灵感页
      const trips = await fetchServerTrips();
      if (trips.length) {
        this.viewSavedTrip(trips[0]);
        return;
      }
      this.view = "home";
    },
    goSaved() {
      this.view = "saved";
    },
    newTrip() {
      this.viewedTrip = null;
      this.clearChat();
      this.view = "home";
      this._toast("已开始新的行程规划");
    },
    editPlan() {
      // 从「我的旅行」打开的行程要接回原会话，否则会当成新建行程
      const saved = this.viewedTrip;
      if (saved) {
        // 切到另一份行程：先清掉当前会话，否则聊天区会残留上一个行程的对话
        this.clearChat();
        if (saved.threadId) this.sessionId = saved.threadId;
        this.messages = [{ role: "assistant", content: saved.raw, _thinkingDone: true }];
        this.viewedTrip = null;
      }
      this.view = "chat";
      this.$nextTick(() => {
        const cv = this.$refs.chatView;
        if (cv && cv.$el) {
          const input = cv.$el.querySelector(".chat-input input");
          if (input) input.focus();
        }
      });
    },
    submitFromHero(text) {
      // 灵感页提交一律开新会话：否则会接在上一份行程的线程后面（甚至撞上未处理的审批）
      this.clearChat();
      this.inputText = text;
      this.sendMessage();
    },
    askFromPlan(text) {
      this.inputText = text;
      this.sendMessage();
    },
    _maybeEnterPlan() {
      // 流结束后：有行程则自动切行程视图（审批待处理时留在对话）
      if (!this.approvalPending && this.hasTrip && !this.loading) {
        this.view = "plan";
      }
    },
    _toast(text) {
      this.toast = text;
      if (this._toastTimer) clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => {
        this.toast = "";
      }, 2200);
    },

    // ══════════════════════════════════════════════════
    // 保存 / 复制 / 分享 / 导出
    // ══════════════════════════════════════════════════
    handleSaveTrip(saved) {
      const plan = this.displayPlan;
      if (!plan) return;
      if (saved) {
        const trip = {
          id: genUUID(),
          title: `${plan.city || "行程"}${plan.duration ? " · " + plan.duration + "天" : ""}`,
          city: plan.city,
          createdAt: Date.now(),
          raw: plan.raw,
        };
        saveTrip(trip);
        this._savedTripIds[plan.raw] = trip.id;
        this._toast("行程已保存到「我的旅行」");
      } else {
        let id = this._savedTripIds[plan.raw];
        if (!id) {
          const found = getSavedTrips().find((t) => t.raw === plan.raw);
          if (found) id = found.id;
        }
        if (id) {
          removeSavedTrip(id);
          delete this._savedTripIds[plan.raw];
          this._toast("已取消保存");
        }
      }
    },
    async copyPlan() {
      const plan = this.displayPlan;
      if (!plan) return;
      try {
        await navigator.clipboard.writeText(plan.raw);
        this._toast("行程已复制到剪贴板");
      } catch {
        this._toast("复制失败，请手动选择文本复制");
      }
    },
    async sharePlan() {
      const plan = this.displayPlan;
      if (!plan) return;
      const text = `${plan.city || "旅行"}行程 · Voyage 旅行规划\n${location.origin}`;
      try {
        if (navigator.share) {
          await navigator.share({ title: "Voyage 旅行行程", text });
        } else {
          await navigator.clipboard.writeText(text);
          this._toast("分享信息已复制到剪贴板");
        }
      } catch {
        // 用户取消分享
      }
    },
    exportPlan() {
      this._toast("正在准备打印导出...");
      setTimeout(() => window.print(), 400);
    },
    viewSavedTrip(trip) {
      this.viewedTrip = parsePlan(trip.raw) || {
        raw: trip.raw,
        city: "",
        duration: "",
        month: "",
        budget: null,
        styles: [],
        days: [],
        budgetItems: [],
        budgetTotal: null,
        hotels: [],
        restaurants: [],
        attractions: [],
        hasDays: false,
      };
      this.viewedTrip.threadId = trip.threadId; // 供「修改需求」接回原会话
      this.activeDay = 1;
      this.view = "plan";
    },
    async copySavedTrip(trip) {
      try {
        await navigator.clipboard.writeText(trip.raw);
        this._toast("行程已复制到剪贴板");
      } catch {
        this._toast("复制失败，请手动选择文本复制");
      }
    },
    handleClearChat() {
      this.clearChat();
      this.showSettings = false;
      this._toast("对话已清空");
    },

    // ══════════════════════════════════════════════════
    // 登录鉴权（原逻辑完整保留）
    // ══════════════════════════════════════════════════
    async checkAuth() {
      const token = localStorage.getItem("travel_token");
      const phone = localStorage.getItem("travel_phone");
      if (!token || !phone) return;

      try {
        const res = await fetch(`${this.apiBase}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          this.token = token;
          this.phone = data.phone || phone;
          this.userId = this.phone;
          this.isLoggedIn = true;
        } else if (res.status === 401) {
          this._clearAuth();
          this.loginError = "登录已过期，请重新验证手机号登录";
        } else {
          this._clearAuth();
          this.loginError = "服务异常，请稍后重试";
        }
      } catch {
        this._clearAuth();
        this.loginError = "无法连接服务器，请确认服务已启动后重试";
      }
    },
    async sendCode() {
      const phone = this.loginForm.phone;
      if (!/^1[3-9]\d{9}$/.test(phone)) {
        this.loginError = "请输入正确的 11 位手机号";
        return;
      }
      this.loginError = "";
      this.sendingCode = true;
      try {
        const res = await fetch(`${this.apiBase}/api/auth/send-code`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phone }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data.detail || "验证码发送失败，请稍后重试");
        }
        if (data.dev_mode && data.dev_code) {
          this.loginHint = `开发模式验证码：${data.dev_code}（5 分钟内有效，请手动输入）`;
        } else {
          this.loginHint = `${data.message || "验证码已发送"}，请查收短信并输入`;
        }
        this.countdown = 60;
        this.countdownTimer = setInterval(() => {
          this.countdown -= 1;
          if (this.countdown <= 0) {
            clearInterval(this.countdownTimer);
            this.countdownTimer = null;
          }
        }, 1000);
      } catch (e) {
        this.loginError = e.message || "验证码发送失败";
      } finally {
        this.sendingCode = false;
      }
    },
    async login() {
      const phone = this.loginForm.phone;
      const code = this.loginForm.code;
      if (!/^1[3-9]\d{9}$/.test(phone)) {
        this.loginError = "请输入正确的 11 位手机号";
        return;
      }
      if (!/^\d{6}$/.test(code)) {
        this.loginError = "请输入 6 位数字验证码";
        return;
      }
      this.loginError = "";
      this.loginLoading = true;
      try {
        const res = await fetch(`${this.apiBase}/api/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ phone, code }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data.detail || "登录失败，请重试");
        }
        this.token = data.token;
        this.phone = data.phone;
        this.isNewUser = !!data.is_new_user;
        this.userId = data.phone;
        localStorage.setItem("travel_token", data.token);
        localStorage.setItem("travel_phone", data.phone);
        this.isLoggedIn = true;
        this.view = "home";
        this.loginForm.code = "";
        this.loginHint = "";
        if (this.isNewUser) {
          this._toast("欢迎加入 Voyage，说说你想去哪里吧");
        }
      } catch (e) {
        this.loginError = e.message || "登录失败，请重试";
      } finally {
        this.loginLoading = false;
      }
    },
    async logout() {
      try {
        await fetch(`${this.apiBase}/api/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${this.token}` },
        });
      } catch {
        // 后端不可达时也继续本地登出
      }
      this._clearAuth();
      this.clearChat();
    },
    _clearAuth() {
      this.token = "";
      this.phone = "";
      this.userId = "";
      this.isLoggedIn = false;
      this.loginForm.phone = "";
      this.loginForm.code = "";
      this.loginHint = "";
      localStorage.removeItem("travel_token");
      localStorage.removeItem("travel_phone");
    },
    _handle401() {
      this._clearAuth();
      this.clearChat();
      this.loginError = "登录已过期，请重新获取验证码登录";
    },
    _authHeaders(extra) {
      return { Authorization: `Bearer ${this.token}`, ...(extra || {}) };
    },
    _detectDevice() {
      const ua = navigator.userAgent || "";
      const isTablet = /iPad|Tablet|PlayBook|Silk/i.test(ua)
        || (/Android/i.test(ua) && !/Mobile/i.test(ua));
      const isMobile = !isTablet && /Mobi|iPhone|Android|Windows Phone/i.test(ua);
      let os = "Unknown";
      if (/Windows NT/i.test(ua)) os = "Windows";
      else if (/Mac OS X|Macintosh/i.test(ua)) os = "macOS";
      else if (/Android/i.test(ua)) os = "Android";
      else if (/iPhone|iPad|iPod/i.test(ua)) os = "iOS";
      else if (/Linux/i.test(ua)) os = "Linux";
      let browser = "Unknown";
      if (/Edg\//i.test(ua)) browser = "Edge";
      else if (/Chrome|CriOS/i.test(ua)) browser = "Chrome";
      else if (/Firefox|FxiOS/i.test(ua)) browser = "Firefox";
      else if (/Safari/i.test(ua)) browser = "Safari";
      return {
        deviceType: isTablet ? "tablet" : isMobile ? "mobile" : "desktop",
        os,
        browser,
      };
    },
    async fetchStatus() {
      try {
        const res = await fetch(`${this.apiBase}/api/status`);
        if (res.ok) this.status = await res.json();
      } catch {
        // 后端未启动则使用默认状态
      }
    },

    // ══════════════════════════════════════════════════
    // 流式聊天（原逻辑完整保留，仅追加视图切换）
    // ══════════════════════════════════════════════════
    async sendMessage() {
      const text = this.inputText.trim();
      if (!text || this.loading) return;

      if (this.approvalPending) {
        this.inputText = text;
        return;
      }

      this.viewedTrip = null;
      this.messages.push({ role: "user", content: text });
      this.inputText = "";
      this.loading = true;
      this.approvalPending = false;
      this.view = "chat"; // 流式期间展示对话视图

      const threadId = this.sessionId || genUUID();
      this.sessionId = threadId;

      const msgIdx = this.messages.length;
      this.messages.push({
        role: "assistant",
        content: "",
        thinking: "",
        _thinkingExpanded: true,
        _streaming: true,
        _thinkingDone: false,
      });

      this._abortController = new AbortController();

      try {
        const d = this._detectDevice();
        const url = `${this.apiBase}/api/stream/${threadId}?message=${encodeURIComponent(text)}`
          + `&user_id=${encodeURIComponent(this.phone)}`
          + `&device_type=${d.deviceType}&os=${encodeURIComponent(d.os)}&browser=${encodeURIComponent(d.browser)}`;
        const response = await fetch(url, { headers: this._authHeaders(), signal: this._abortController.signal });

        if (!response.ok) {
          if (response.status === 401) {
            this._handle401();
            throw new Error("登录已过期，请重新登录");
          }
          const err = await response.json().catch(() => ({ detail: "流式连接失败" }));
          throw new Error(err.detail || "请求失败");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const raw = line.slice(6).trim();
              if (!raw || raw === "[DONE]") continue;
              try {
                const event = JSON.parse(raw);
                this._handleSSEEvent(event, msgIdx);
              } catch (e) {
                // 跳过解析失败的片段
              }
            }
          }
        }

        // 流结束 → 清理心跳定时器
        const msg = this.messages[msgIdx];
        if (msg) {
          if (msg._gapTimer) {
            clearTimeout(msg._gapTimer);
            msg._gapTimer = null;
          }
          this._removeGapIndicator(msg, "thinking");
          msg._streaming = false;
          msg._thinkingDone = true;
          if (msg.thinking) this._scheduleCollapse(msgIdx);
        }
        this.loading = false;
        this._maybeEnterPlan();
      } catch (e) {
        const msg = this.messages[msgIdx];
        if (e.name === "AbortError") {
          if (msg) {
            if (msg._gapTimer) {
              clearTimeout(msg._gapTimer);
              msg._gapTimer = null;
            }
            this._removeGapIndicator(msg, "thinking");
            msg._streaming = false;
            msg._thinkingDone = true;
            if (msg.content) {
              msg.content += "\n\n---\n\n> 已停止生成（内容不完整，可继续发送消息）";
            }
          }
        } else {
          if (msg) {
            if (msg._gapTimer) {
              clearTimeout(msg._gapTimer);
              msg._gapTimer = null;
            }
            this._removeGapIndicator(msg, "thinking");
            msg.content = msg.content || `出错了：${e.message}。请确保后端服务已启动。`;
            msg._streaming = false;
          }
        }
        this.loading = false;
      }
    },
    stopGeneration() {
      if (this._abortController) {
        this._abortController.abort();
        this._abortController = null;
      }
      this.loading = false;
    },
    _handleSSEEvent(event, msgIdx) {
      const msg = this.messages[msgIdx];
      if (!msg) return;

      if (msg._gapTimer) {
        clearTimeout(msg._gapTimer);
        msg._gapTimer = null;
      }
      this._removeGapIndicator(msg, "thinking");

      switch (event.type) {
        case "progress":
          msg._progressLabel = event.content;
          msg._thinkingExpanded = true;
          msg._thinkingDone = false;
          if (!msg._nodeLabels) msg._nodeLabels = {};
          msg._nodeLabels[event.node] = event.content;
          break;

        case "thinking":
          // 内容去重：同一节点的思考重复推送时（如事件重复消费）直接跳过
          if (event.content && (msg._thinkBuf || "").includes(event.content)) break;
          msg._thinkBuf = (msg._thinkBuf || "") + event.content;
          if (msg.thinking && msg._lastThinkingNode && msg._lastThinkingNode !== event.node) {
            const label = (msg._nodeLabels && msg._nodeLabels[event.node]) || event.node;
            msg.thinking = (msg.thinking || "") + "\n\n> " + label + "...\n";
          }
          msg._lastThinkingNode = event.node;
          msg.thinking = (msg.thinking || "") + event.content;
          msg._thinkingExpanded = true;
          msg._thinkingDone = false;
          msg._progressLabel = "";
          break;

        case "message":
          msg.content = (msg.content || "") + (msg.content ? "\n\n" : "") + event.content;
          if (!msg._thinkingDone && msg.thinking) {
            msg._thinkingDone = true;
            this._scheduleCollapse(msgIdx);
          }
          break;

        case "message_token":
          msg.content = (msg.content || "") + event.content;
          if (!msg._thinkingDone && msg.thinking) {
            msg._thinkingDone = true;
            this._scheduleCollapse(msgIdx);
          }
          break;

        case "approval_required":
          msg._thinkingDone = true;
          msg._streaming = false;
          msg._thinkingExpanded = false;
          this.loading = false;

          this.approvalPending = true;
          this._approvalAnchorIdx = msgIdx; // 恢复流的思考合并进该消息
          this.hitlStage = event.hitl_stage || "plan_approval";
          this.approvalPlanPreview = this._formatPlanPreview(event.plan_preview || "");

          if (!msg.content) {
            msg.content = event.hitl_stage === "trip_review"
              ? "已解析你的旅行需求，请确认以下信息是否正确，确认后将开始搜索。"
              : "旅行计划已生成，请查看完整方案后确认或驳回修改。";
          }
          break;

        case "complete":
          msg.content = event.content || msg.content;
          msg._thinkingDone = true;
          msg._streaming = false;
          this.loading = false;
          this._scheduleCollapse(msgIdx);
          this._maybeEnterPlan();
          break;

        case "error":
          msg.content = event.content;
          msg._streaming = false;
          this.loading = false;
          break;
      }

      if (!msg._thinkingDone && msg.thinking) {
        msg._gapTimer = setTimeout(() => {
          this._injectGapIndicator(msg, "thinking");
        }, 1500);
      }
    },
    _scheduleCollapse(msgIdx) {
      setTimeout(() => {
        const m = this.messages[msgIdx];
        if (m && m._thinkingDone) {
          m._thinkingExpanded = false;
        }
      }, 2500);
    },
    async handleApprove() {
      if (!this.sessionId || this.approvalLoading) return;
      this.approvalLoading = true;
      this._resumeFinalMsgIdx = null;

      try {
        const url = `${this.apiBase}/api/stream/resume/${this.sessionId}?action=approve`;
        const response = await fetch(url, { headers: this._authHeaders() });
        if (!response.ok) {
          if (response.status === 401) {
            this._handle401();
            throw new Error("登录已过期，请重新登录");
          }
          const err = await response.json().catch(() => ({ detail: "请求失败" }));
          throw new Error(err.detail || "请求失败");
        }

        // 确认后立即收起审批卡片：搜索阶段的思考统一合并进上方 anchor 消息，
        // 避免思考块与卡片分离显示
        this.approvalPending = false;
        this.approvalPlanPreview = "";
        this.hitlStage = "";

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const raw = line.slice(6).trim();
              if (!raw || raw === "[DONE]") continue;
              try {
                const event = JSON.parse(raw);
                this._handleResumeEvent(event);
              } catch (e) {
                // skip
              }
            }
          }
        }

        this._clearResumeGapTimer();
        if (this._resumeFinalMsgIdx != null) {
          const m = this.messages[this._resumeFinalMsgIdx];
          if (m) this._removeGapIndicator(m, "content");
        }
        const anchorDone = this._anchorMsg();
        if (anchorDone) this._removeGapIndicator(anchorDone, "thinking");
        this.approvalLoading = false;
        this._maybeEnterPlan();
      } catch (e) {
        this._clearResumeGapTimer();
        this.approvalPending = false;
        this.approvalPlanPreview = "";
        this.hitlStage = "";
        this.messages.push({
          role: "assistant",
          content: `审批出错：${e.message}`,
        });
        this.approvalLoading = false;
      }
    },
    // 审批预览兜底：后端若直接输出 JSON，转为中文可读格式
    _formatPlanPreview(raw) {
      return sanitizeJson(raw || "");
    },
    // 恢复流锚点消息（审批卡片对应的原消息，思考统一合并到它身上）
    _anchorMsg() {
      let anchor = this.messages[this._approvalAnchorIdx];
      if (!anchor) {
        for (let i = this.messages.length - 1; i >= 0; i--) {
          if (this.messages[i].role === "assistant") {
            anchor = this.messages[i];
            this._approvalAnchorIdx = i;
            break;
          }
        }
      }
      return anchor;
    },
    _handleResumeEvent(event) {
      this._clearResumeGapTimer();
      const anchor = this._anchorMsg();
      const target = this._resumeFinalMsgIdx != null
        ? this.messages[this._resumeFinalMsgIdx] : null;
      const src = target || anchor || this;
      const key = target ? "content" : anchor ? "thinking" : "content";
      this._removeGapIndicator(src, key);

      switch (event.type) {
        case "progress":
          if (anchor) {
            this._removeGapIndicator(anchor, "thinking");
            anchor._progressLabel = event.content;
            anchor._thinkingExpanded = true;
            anchor._thinkingDone = false;
            if (!anchor._nodeLabels) anchor._nodeLabels = {};
            anchor._nodeLabels[event.node] = event.content;
          }
          break;

        case "thinking":
          if (anchor) {
            this._removeGapIndicator(anchor, "thinking");
            // 内容去重：同一节点的思考重复推送时直接跳过
            if (event.content && (anchor._thinkBuf || "").includes(event.content)) break;
            anchor._thinkBuf = (anchor._thinkBuf || "") + event.content;
            if (anchor.thinking && anchor._lastThinkingNode && anchor._lastThinkingNode !== event.node) {
              const label = (anchor._nodeLabels && anchor._nodeLabels[event.node]) || event.node;
              anchor.thinking = anchor.thinking + "\n\n> " + label + "...\n";
            }
            anchor._lastThinkingNode = event.node;
            anchor.thinking = (anchor.thinking || "") + event.content;
            anchor._thinkingExpanded = true;
            anchor._thinkingDone = false;
            anchor._progressLabel = "";
          }
          break;

        case "message":
        case "message_token": {
          if (this._resumeFinalMsgIdx == null) {
            this.approvalPending = false;
            this.approvalPlanPreview = "";
            this.hitlStage = "";
            if (anchor) {
              this._removeGapIndicator(anchor, "thinking");
              anchor._thinkingDone = true;
              anchor._streaming = false;
              anchor._thinkingExpanded = false;
            }
            this.messages.push({
              role: "assistant",
              content: "",
              _streaming: true,
            });
            this._resumeFinalMsgIdx = this.messages.length - 1;
          }
          const msg = this.messages[this._resumeFinalMsgIdx];
          if (msg) {
            const sep = event.type === "message" && msg.content ? "\n\n" : "";
            msg.content = (msg.content || "") + sep + event.content;
          }
          break;
        }

        case "approval_required":
          this.approvalPending = true;
          if (anchor) {
            anchor._thinkingDone = true;
            anchor._thinkingExpanded = false;
          }
          this.hitlStage = event.hitl_stage || "trip_review";
          this.approvalPlanPreview = this._formatPlanPreview(event.plan_preview || "");
          break;

        case "complete":
          if (this._resumeFinalMsgIdx != null) {
            const msg = this.messages[this._resumeFinalMsgIdx];
            if (msg) {
              msg._streaming = false;
              msg.content = event.content || msg.content || "旅行计划已生成";
            }
            this._resumeFinalMsgIdx = null;
          } else {
            this.approvalPending = false;
            this.approvalPlanPreview = "";
            this.hitlStage = "";
            if (anchor) {
              anchor._thinkingDone = true;
              anchor._thinkingExpanded = false;
            }
            this.messages.push({
              role: "assistant",
              content: event.content || "旅行计划已生成",
            });
          }
          this._maybeEnterPlan();
          break;

        case "error":
          this.approvalPending = false;
          this.approvalPlanPreview = "";
          this.hitlStage = "";
          this.messages.push({
            role: "assistant",
            content: `${event.content}`,
          });
          this._resumeFinalMsgIdx = null;
          break;
      }
      this._scheduleResumeGap(src, key);
    },
    // 心跳检测：输出停顿时自动注入"搜索中"
    _injectGapIndicator(src, key) {
      const text = src[key];
      if (!text) return;
      const marker = "\n\n\u23F3SEARCHING\n";
      if (!text.endsWith(marker)) {
        src[key] = text + marker;
      }
    },
    _removeGapIndicator(src, key) {
      const text = src[key];
      if (!text) return;
      const marker = "\n\n\u23F3SEARCHING\n";
      if (text.endsWith(marker)) {
        src[key] = text.slice(0, -marker.length);
      }
    },
    _scheduleResumeGap(src, key) {
      const isDone = this._resumeFinalMsgIdx != null
        ? !(this.messages[this._resumeFinalMsgIdx] || {})._streaming
        : !!((this._anchorMsg() || {})._thinkingDone);
      if (isDone) return;
      this._resumeGapTimer = setTimeout(() => {
        this._injectGapIndicator(src, key);
      }, 1500);
    },
    _clearResumeGapTimer() {
      if (this._resumeGapTimer) {
        clearTimeout(this._resumeGapTimer);
        this._resumeGapTimer = null;
      }
    },
    async handleReject() {
      if (!this.sessionId || this.approvalLoading) return;
      const feedback = this.rejectFeedback.trim() || "用户希望调整计划";
      this.approvalLoading = true;
      this._resumeFinalMsgIdx = null;

      try {
        const params = new URLSearchParams({ action: "reject", feedback });
        const url = `${this.apiBase}/api/stream/resume/${this.sessionId}?${params}`;
        const response = await fetch(url, { headers: this._authHeaders() });
        if (!response.ok) {
          if (response.status === 401) {
            this._handle401();
            throw new Error("登录已过期，请重新登录");
          }
          const err = await response.json().catch(() => ({ detail: "请求失败" }));
          throw new Error(err.detail || "请求失败");
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const raw = line.slice(6).trim();
              if (!raw || raw === "[DONE]") continue;
              try {
                const event = JSON.parse(raw);
                this._handleResumeEvent(event);
              } catch (e) {
                // skip
              }
            }
          }
        }

        this.rejectFeedback = "";
        this.approvalLoading = false;
      } catch (e) {
        this.approvalPending = false;
        this.approvalPlanPreview = "";
        this.hitlStage = "";
        this.messages.push({
          role: "assistant",
          content: `审批出错：${e.message}`,
        });
        this.approvalLoading = false;
      }
    },
    clearChat() {
      this.messages = [];
      this.sessionId = null;
      this.approvalPending = false;
      this.approvalPlanPreview = "";
      this.rejectFeedback = "";
      this.hitlStage = "";
      this.feedbackGiven = null;
      this._approvalAnchorIdx = -1;
      this._resumeFinalMsgIdx = null;
      this.activeDay = 1;
      try {
        sessionStorage.removeItem("voyage_session");
      } catch {
        // 忽略
      }
    },
    // 会话持久化：序列化时过滤定时器/流式标记等不可恢复的临时字段
    _saveSession() {
      try {
        // 空对话不持久化（清空对话/新行程后刷新应回到首页）
        if (!this.messages.length) {
          sessionStorage.removeItem("voyage_session");
          return;
        }
        sessionStorage.setItem(
          "voyage_session",
          JSON.stringify({
            view: this.view,
            sessionId: this.sessionId,
            activeDay: this.activeDay,
            approvalPending: this.approvalPending,
            approvalPlanPreview: this.approvalPlanPreview,
            hitlStage: this.hitlStage,
            messages: this.messages.map((m) => {
              const { _gapTimer, _abortTimer, ...rest } = m;
              return { ...rest, _streaming: false, _thinkingDone: true };
            }),
          })
        );
      } catch {
        // 序列化失败不影响主流程
      }
    },
    _restoreSession() {
      try {
        const raw = sessionStorage.getItem("voyage_session");
        if (!raw) return;
        const data = JSON.parse(raw);
        if (!data || !Array.isArray(data.messages) || !data.messages.length) return;
        this.messages = data.messages.map((m) => ({
          ...m,
          _streaming: false,
          _thinkingDone: true,
          _thinkingExpanded: false,
          _gapTimer: null,
        }));
        this.sessionId = data.sessionId || null;
        this.activeDay = data.activeDay || 1;
        this.approvalPending = !!data.approvalPending;
        this.approvalPlanPreview = data.approvalPlanPreview || "";
        this.hitlStage = data.hitlStage || "";
        // 有对话内容则不再停留首页（首页空对话无意义）
        if (data.view && data.view !== "home") this.view = data.view;
        else this.view = "chat";
      } catch {
        // 损坏的会话数据直接忽略
      }
    },
    async submitFeedback(rating) {
      if (!this.sessionId || this.feedbackGiven) return;
      this.feedbackGiven = rating;
      try {
        await fetch(`${this.apiBase}/api/feedback/${this.sessionId}`, {
          method: "POST",
          headers: this._authHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({ rating, comment: "" }),
        });
      } catch {
        // 静默失败，不影响用户体验
      }
    },
  },
};
</script>

<style scoped>
.app {
  min-height: 100vh;
}
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ── 顶部导航 ── */
.site-header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: var(--bg);
  border-bottom: 1px solid var(--line);
}
.header-inner {
  max-width: 1180px;
  margin: 0 auto;
  height: var(--header-h);
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 0 32px;
}
.brand {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-shrink: 0;
}
.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--brand);
  color: #fff;
  align-self: center;
}
.brand-name {
  font-size: 19px;
  font-weight: 600;
  letter-spacing: 0.3px;
  color: var(--ink);
}
.brand-sub {
  font-size: 12.5px;
  color: var(--faint);
}
.header-nav {
  display: flex;
  gap: 4px;
  margin-left: 8px;
}
.nav-item {
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  color: var(--muted);
  transition: all 0.2s ease;
}
.nav-item:hover {
  color: var(--ink);
  background: var(--bg-gray);
}
.nav-item.active {
  color: var(--brand);
  background: var(--brand-soft);
}
.header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}
.avatar-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid var(--line);
  transition: all 0.2s ease;
}
.avatar-btn:hover {
  border-color: var(--brand);
}
.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
}
.menu-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  color: var(--ink-2);
}
.menu-btn:hover {
  background: var(--bg-gray);
}
.mobile-nav {
  display: none;
  flex-direction: column;
  gap: 2px;
  padding: 8px 16px 14px;
  border-top: 1px solid var(--line-soft);
}
.mobile-nav-item {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  font-size: 14.5px;
  text-align: left;
  color: var(--ink-2);
}
.mobile-nav-item:hover {
  background: var(--bg-gray);
}
.mobile-nav-item.active {
  color: var(--brand);
  background: var(--brand-soft);
  font-weight: 500;
}

/* ── 主内容 ── */
.site-main {
  flex: 1;
}

/* ── 帮助弹窗 ── */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  z-index: 70;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.help-modal {
  width: 480px;
  max-width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  background: var(--bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--line-soft);
}
.modal-head h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}
.modal-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-xs);
  color: var(--muted);
}
.modal-close:hover {
  background: var(--bg-gray);
  color: var(--ink);
}
.modal-body {
  padding: 8px 22px 22px;
}
.help-item {
  padding: 14px 0;
  border-bottom: 1px solid var(--line-soft);
}
.help-item:last-child {
  border-bottom: none;
}
.help-item h4 {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--ink);
}
.help-item p {
  margin-top: 5px;
  font-size: 13.5px;
  color: var(--muted);
  line-height: 1.7;
}

/* ── Toast ── */
.toast {
  position: fixed;
  left: 50%;
  bottom: 36px;
  transform: translateX(-50%);
  z-index: 80;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  background: var(--ink);
  color: #fff;
  font-size: 13.5px;
  box-shadow: var(--shadow-md);
}

/* ── 响应式 ── */
@media (max-width: 767px) {
  .header-inner {
    padding: 0 16px;
    gap: 12px;
  }
  .brand-sub {
    display: none;
  }
  .header-nav {
    display: none;
  }
  .menu-btn {
    display: flex;
  }
  .mobile-nav {
    display: flex;
  }
  .new-trip-btn {
    padding: 6px 10px;
  }
}
</style>

