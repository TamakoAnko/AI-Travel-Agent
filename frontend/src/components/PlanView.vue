<template>
  <div class="plan-view">
    <!-- ── 行程头部 ── -->
    <section class="plan-hero">
      <img
        v-if="visual.img"
        class="hero-bg"
        :src="visual.img"
        alt=""
        @error="imgFailed = true"
      />
      <div
        class="hero-bg-fallback"
        :style="{ background: `linear-gradient(135deg, ${visual.tone[0]} 0%, ${visual.tone[1]} 100%)` }"
        :class="{ show: imgFailed || !visual.img }"
      ></div>
      <div class="hero-mask"></div>

      <div class="hero-content">
        <div class="hero-kicker">
          <BaseIcon name="plane" :size="14" />
          <span v-if="plan.city">{{ plan.city }}</span>
          <span v-if="visual.en">{{ visual.en }}</span>
        </div>
        <h1 class="hero-title">
          {{ plan.city || "我的行程" }}
          <span v-if="plan.duration" class="hero-days">{{ plan.duration }}天</span>
        </h1>
        <div class="hero-meta">
          <span v-if="plan.startDate || plan.month" class="meta-item">
            <BaseIcon name="calendar" :size="14" /> {{ startDateLabel }}出发
          </span>
          <span class="meta-item">
            <BaseIcon name="wallet" :size="14" />
            {{ plan.budget ? "¥" + plan.budget.toLocaleString() : "未具体给出金额" }}
          </span>
          <span v-for="s in plan.styles" :key="s" class="meta-tag">{{ s }}</span>
        </div>

        <div class="hero-actions no-print">
          <button class="btn btn-outline btn-sm" @click="$emit('edit')">
            <BaseIcon name="edit" :size="14" /> 修改需求
          </button>
          <button class="btn btn-outline btn-sm" @click="toggleSave">
            <BaseIcon :name="saved ? 'heart' : 'heart'" :size="14" :class="saved ? 'saved-heart' : ''" /> {{ saved ? "已保存" : "保存行程" }}
          </button>
          <button class="btn btn-outline btn-sm" @click="copyPlan">
            <BaseIcon name="copy" :size="14" /> 复制
          </button>
          <button class="btn btn-outline btn-sm" @click="sharePlan">
            <BaseIcon name="share" :size="14" /> 分享
          </button>
          <button class="btn btn-primary btn-sm" @click="exportPlan">
            <BaseIcon name="download" :size="14" /> 导出行程
          </button>
        </div>
      </div>
    </section>

    <!-- ── 主内容：行程 + 地图 ── -->
    <section class="plan-main">
      <!-- 左：每日行程 -->
      <div class="plan-left">
        <div class="section-head">
          <h2>每日行程</h2>
          <span v-if="plan.days.length" class="section-note">点击日期切换地图路线</span>
        </div>

        <template v-if="plan.hasDays">
          <div
            v-for="day in plan.days"
            :key="day.num"
            :class="['day-card', 'card', activeDay === day.num ? 'active' : '']"
            @click="$emit('day-change', day.num)"
          >
            <div class="day-head">
              <div class="day-badge" :style="dayStyle(day.num)">DAY {{ String(day.num).padStart(2, "0") }}</div>
              <div class="day-title-wrap">
                <h3 class="day-title">{{ day.title || `第 ${day.num} 天` }}</h3>
                <span class="day-count">{{ dayDate(day.num) ? dayDate(day.num) + " · " : "" }}{{ day.points.length }} 个地点{{ day.schedule.length ? ` · ${day.schedule.length} 个时段` : "" }}</span>
              </div>
              <BaseIcon name="chevron-right" :size="16" class="day-arrow" />
            </div>

            <!-- 景点路线流 -->
            <div v-if="day.points.length" class="day-route">
              <template v-for="(p, i) in day.points" :key="i">
                <div class="route-point">
                  <span class="route-num" :style="{ background: dayStyle(day.num).background }">{{ i + 1 }}</span>
                  <span class="route-name">{{ p }}</span>
                </div>
                <div v-if="i < day.points.length - 1" class="route-connector"></div>
              </template>
            </div>

            <!-- 时刻表 -->
            <div v-if="day.schedule.length" class="day-schedule">
              <div v-for="(s, i) in day.schedule" :key="i" class="schedule-row">
                <span class="schedule-time">{{ s.time }}</span>
                <span class="schedule-line"></span>
                <span class="schedule-item">{{ s.item }}</span>
              </div>
            </div>
          </div>
        </template>

        <!-- 未解析出行程结构 → Markdown 兜底 -->
        <div v-else class="card fallback-card">
          <div class="md-body" v-html="renderMarkdown(rawContent)"></div>
        </div>
      </div>

      <!-- 右：地图 + 预算 -->
      <div class="plan-right">
        <TripMap
          :city="plan.city"
          :spots="spots"
          :active-day="activeDay"
          @day-change="(d) => $emit('day-change', d)"
        />

        <!-- 预算概览 -->
        <div class="budget-card card">
          <div class="budget-head">
            <h3><BaseIcon name="wallet" :size="15" /> 预算概览</h3>
            <span class="budget-total-label">
              {{ plan.budget ? "预算 ¥" + plan.budget.toLocaleString() : "未具体给出金额" }}
            </span>
          </div>

          <template v-if="plan.budgetItems.length">
            <div v-for="item in plan.budgetItems" :key="item.label" class="budget-row">
              <div class="budget-row-head">
                <span class="budget-label">{{ item.label }}</span>
                <span class="budget-amount">¥{{ item.amount.toLocaleString() }}</span>
              </div>
              <div class="budget-bar">
                <div
                  class="budget-bar-fill"
                  :style="{ width: barWidth(item.amount) }"
                ></div>
              </div>
            </div>
            <div class="budget-summary">
              <div class="summary-row total">
                <span>预计总计</span>
                <span>¥{{ plan.budgetTotal.toLocaleString() }}</span>
              </div>
              <div class="summary-row remain">
                <span>预算剩余</span>
                <span
                  v-if="plan.budget"
                  :class="remaining > 0 ? 'remain-ok' : 'remain-over'"
                >
                  {{ remaining >= 0 ? "¥" + remaining.toLocaleString() : "超 ¥" + Math.abs(remaining).toLocaleString() }}
                </span>
                <span v-else class="remain-none">未具体给出金额</span>
              </div>
            </div>
          </template>
          <p v-else class="budget-empty">行程生成后，这里会展示交通、住宿、餐饮等费用明细</p>
        </div>
      </div>
    </section>

    <!-- ── 推荐模块 ── -->
    <section class="plan-recommend" v-if="hasRecommend">
      <div class="section-head">
        <h2>出行推荐</h2>
      </div>
      <div class="rec-tabs">
        <button
          v-for="tab in recTabs"
          :key="tab.key"
          :class="['rec-tab', recTab === tab.key ? 'active' : '']"
          @click="recTab = tab.key"
        >
          <BaseIcon :name="tab.icon" :size="14" /> {{ tab.label }}
        </button>
      </div>

      <!-- 景点推荐 -->
      <div v-if="recTab === 'attractions' && plan.attractions.length" class="rec-grid">
        <div v-for="(a, i) in plan.attractions" :key="i" class="rec-card card">
          <div class="rec-img" :style="recImgStyle(i, 'attractions')">
            <BaseIcon name="landmark" :size="26" />
          </div>
          <div class="rec-body">
            <div class="rec-name-row">
              <h4>{{ a.name }}</h4>
              <button class="fav-btn" :class="{ active: favSet.has('a' + i) }" @click="toggleFav('a' + i)">
                <BaseIcon name="heart" :size="15" />
              </button>
            </div>
            <p class="rec-detail">{{ a.detail }}</p>
            <span v-if="a.price" class="rec-price">门票约 ¥{{ a.price }}</span>
          </div>
        </div>
      </div>

      <!-- 餐厅推荐 -->
      <div v-if="recTab === 'restaurants' && plan.restaurants.length" class="rec-grid">
        <div v-for="(r, i) in plan.restaurants" :key="i" class="rec-card card">
          <div class="rec-img" :style="recImgStyle(i, 'restaurants')">
            <BaseIcon name="utensils" :size="26" />
          </div>
          <div class="rec-body">
            <div class="rec-name-row">
              <h4>{{ r.name }}</h4>
              <button class="fav-btn" :class="{ active: favSet.has('r' + i) }" @click="toggleFav('r' + i)">
                <BaseIcon name="heart" :size="15" />
              </button>
            </div>
            <p class="rec-detail">{{ r.detail }}</p>
            <span v-if="r.price" class="rec-price">人均约 ¥{{ r.price }}</span>
          </div>
        </div>
      </div>

      <!-- 住宿推荐 -->
      <div v-if="recTab === 'hotels' && plan.hotels.length" class="rec-grid">
        <div v-for="(h, i) in plan.hotels" :key="i" class="rec-card card">
          <div class="rec-img" :style="recImgStyle(i, 'hotels')">
            <BaseIcon name="building" :size="26" />
          </div>
          <div class="rec-body">
            <div class="rec-name-row">
              <h4>{{ h.name }}</h4>
              <button class="fav-btn" :class="{ active: favSet.has('h' + i) }" @click="toggleFav('h' + i)">
                <BaseIcon name="heart" :size="15" />
              </button>
            </div>
            <p class="rec-detail">{{ h.detail }}</p>
            <span v-if="h.price" class="rec-price">每晚约 ¥{{ h.price }}</span>
          </div>
        </div>
      </div>

      <p v-if="!currentRecItems.length" class="rec-empty">当前分类暂无推荐，可以在对话中让我补充</p>
    </section>

    <!-- ── 追问输入 ── -->
    <section class="plan-ask card">
      <div class="ask-head">
        <h3>还有什么想调整的？</h3>
        <p>继续对话即可实时更新行程</p>
      </div>
      <div class="ask-input-row">
        <input
          v-model="askText"
          class="text-input"
          placeholder="例如：把第三天安排得轻松一些"
          :disabled="approvalPending"
          @keydown.enter="submitAsk"
        />
        <button class="btn btn-primary ask-send" :disabled="!askText.trim() || approvalPending" @click="submitAsk">
          <BaseIcon name="arrow-up" :size="16" />
        </button>
      </div>
      <div class="ask-chips">
        <button v-for="chip in quickActions" :key="chip.label" class="ask-chip" @click="askText = chip.prefill">
          <BaseIcon :name="chip.icon" :size="14" /> {{ chip.label }}
        </button>
      </div>
    </section>
  </div>
</template>

<script>
import BaseIcon from "./BaseIcon.vue";
import TripMap from "./TripMap.vue";
import { renderMarkdown } from "../utils/markdown.js";
import { formatDayDate, formatStartDate, getCityVisual, isTripSaved } from "../utils/plan.js";

const DAY_COLORS = ["#2563eb", "#0d9488", "#b45309", "#7c3aed", "#be185d", "#0369a1", "#4d7c0f"];
const REC_TONES = [
  ["#dbeafe", "#1d4ed8"], ["#cffafe", "#0e7490"], ["#dcfce7", "#15803d"],
  ["#fef3c7", "#b45309"], ["#ede9fe", "#6d28d9"], ["#ffe4e6", "#be123c"],
];

export default {
  name: "PlanView",
  components: { BaseIcon, TripMap },
  props: {
    plan: { type: Object, required: true },
    rawContent: { type: String, default: "" },
    activeDay: { type: Number, default: 1 },
    approvalPending: Boolean,
  },
  data() {
    return {
      saved: false,
      imgFailed: false,
      recTab: "attractions",
      askText: "",
      favSet: new Set(),
      quickActions: [
        { label: "添加地点", icon: "plus", prefill: "帮我在行程中增加一个地点：" },
        { label: "调整日期", icon: "calendar", prefill: "我想调整出行日期，" },
        { label: "调整预算", icon: "wallet", prefill: "预算调整为" },
        { label: "调整餐饮", icon: "utensils", prefill: "推荐几家当地的特色餐厅" },
        { label: "更换住宿", icon: "building", prefill: "住宿换成离市中心近一点的" },
      ],
    };
  },
  computed: {
    startDateLabel() {
      return formatStartDate(this.plan.startDate, this.plan.month);
    },
    visual() {
      return getCityVisual(this.plan.city);
    },
    remaining() {
      if (!this.plan.budget) return 0;
      return this.plan.budget - (this.plan.budgetTotal || 0);
    },
    spots() {
      const list = [];
      let num = 1;
      for (const day of this.plan.days) {
        for (const p of day.points) {
          if (!list.some((s) => s.name === p)) {
            list.push({ name: p, num, day: day.num });
            num += 1;
          }
        }
      }
      return list;
    },
    hasRecommend() {
      return this.plan.attractions.length || this.plan.restaurants.length || this.plan.hotels.length;
    },
    recTabs() {
      const tabs = [];
      if (this.plan.attractions.length) tabs.push({ key: "attractions", label: "景点推荐", icon: "landmark" });
      if (this.plan.restaurants.length) tabs.push({ key: "restaurants", label: "餐厅推荐", icon: "utensils" });
      if (this.plan.hotels.length) tabs.push({ key: "hotels", label: "住宿建议", icon: "building" });
      return tabs;
    },
    currentRecItems() {
      if (this.recTab === "attractions") return this.plan.attractions;
      if (this.recTab === "restaurants") return this.plan.restaurants;
      return this.plan.hotels;
    },
  },
  watch: {
    plan: {
      immediate: true,
      handler(p) {
        if (p && p.raw) this.saved = isTripSaved(p.raw);
      },
    },
    recTabs: {
      immediate: true,
      handler(tabs) {
        if (tabs.length && !tabs.some((t) => t.key === this.recTab)) {
          this.recTab = tabs[0].key;
        }
      },
    },
  },
  methods: {
    renderMarkdown,
    dayDate(num) {
      return formatDayDate(this.plan.startDate, num);
    },
    dayStyle(num) {
      const color = DAY_COLORS[(num - 1) % DAY_COLORS.length];
      return { background: color, color };
    },
    barWidth(amount) {
      const max = Math.max(...this.plan.budgetItems.map((i) => i.amount), 1);
      return `${Math.max(8, Math.round((amount / max) * 100))}%`;
    },
    recImgStyle(i, type) {
      const tones = {
        attractions: 0,
        restaurants: 2,
        hotels: 1,
      };
      const [bg, color] = REC_TONES[(i + (tones[type] || 0)) % REC_TONES.length];
      return { background: bg, color };
    },
    toggleFav(key) {
      if (this.favSet.has(key)) this.favSet.delete(key);
      else this.favSet.add(key);
      this.favSet = new Set(this.favSet);
    },
    toggleSave() {
      this.saved = !this.saved;
      this.$emit("save", this.saved);
    },
    copyPlan() {
      this.$emit("copy");
    },
    sharePlan() {
      this.$emit("share");
    },
    exportPlan() {
      this.$emit("export");
    },
    submitAsk() {
      const t = this.askText.trim();
      if (!t) return;
      this.$emit("ask", t);
      this.askText = "";
    },
  },
};
</script>

<style scoped>
.plan-view {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 32px 56px;
}

/* ── 行程头部 ── */
.plan-hero {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  min-height: 300px;
  display: flex;
  align-items: flex-end;
  margin-top: 20px;
}
.hero-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.hero-bg-fallback {
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 0.4s ease;
}
.hero-bg-fallback.show {
  opacity: 1;
}
.hero-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(12, 22, 38, 0.12) 0%, rgba(12, 22, 38, 0.05) 45%, rgba(12, 22, 38, 0.6) 100%);
}
.hero-content {
  position: relative;
  z-index: 1;
  padding: 28px 32px;
  color: #fff;
  width: 100%;
}
.hero-kicker {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.5px;
}
.hero-title {
  margin-top: 8px;
  font-size: 36px;
  font-weight: 600;
  letter-spacing: 1px;
}
.hero-days {
  margin-left: 10px;
  font-size: 20px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.85);
}
.hero-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}
.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  color: rgba(255, 255, 255, 0.92);
}
.meta-tag {
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(4px);
  font-size: 12.5px;
  color: #fff;
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}
.hero-actions .btn {
  background: rgba(255, 255, 255, 0.92);
  border-color: transparent;
  color: var(--ink-2);
}
.hero-actions .btn:hover {
  background: #fff;
  color: var(--ink);
}
.hero-actions .btn-primary {
  background: var(--brand);
  color: #fff;
}
.hero-actions .btn-primary:hover {
  background: var(--brand-strong);
}
.saved-heart {
  color: var(--rose) !important;
}

/* ── 主内容 ── */
.plan-main {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 24px;
  margin-top: 28px;
  align-items: start;
}
.section-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 14px;
}
.section-head h2 {
  font-size: 19px;
  font-weight: 600;
  color: var(--ink);
}
.section-note {
  font-size: 12.5px;
  color: var(--faint);
}

/* Day 卡片 */
.day-card {
  padding: 18px 20px;
  margin-bottom: 14px;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.day-card:hover {
  border-color: #c7d7f5;
}
.day-card.active {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}
.day-head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.day-badge {
  flex-shrink: 0;
  padding: 5px 10px;
  border-radius: var(--radius-xs);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
  background: var(--bg-gray);
  color: var(--ink-2);
}
.day-card.active .day-badge {
  background: var(--brand-soft);
  color: var(--brand);
}
.day-title-wrap {
  flex: 1;
  min-width: 0;
}
.day-title {
  font-size: 15.5px;
  font-weight: 600;
  color: var(--ink);
}
.day-count {
  font-size: 12px;
  color: var(--faint);
}
.day-arrow {
  color: var(--faint);
  transition: transform 0.2s ease;
}
.day-card.active .day-arrow {
  color: var(--brand);
  transform: translateX(2px);
}

/* 路线流 */
.day-route {
  margin-top: 14px;
}
.route-point {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 3px 0;
}
.route-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--bg-gray);
  color: var(--ink-2);
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}
.route-name {
  font-size: 14px;
  color: var(--ink-2);
}
.route-connector {
  width: 1px;
  height: 12px;
  margin: 2px 0 2px 9.5px;
  border-left: 1.5px dashed var(--line);
}

/* 时刻表 */
.day-schedule {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--line-soft);
}
.schedule-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
}
.schedule-time {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--brand);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
  width: 44px;
}
.schedule-line {
  flex-shrink: 0;
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--faint);
}
.schedule-item {
  font-size: 13.5px;
  color: var(--muted);
}

/* 兜底卡片 */
.fallback-card {
  padding: 20px 24px;
}

/* 右侧 */
.plan-right {
  position: sticky;
  top: calc(var(--header-h) + 20px);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 预算 */
.budget-card {
  padding: 18px 20px;
}
.budget-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.budget-head h3 {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}
.budget-total-label {
  font-size: 13px;
  color: var(--muted);
}
.budget-row {
  margin-bottom: 12px;
}
.budget-row-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}
.budget-label {
  font-size: 13px;
  color: var(--ink-2);
}
.budget-amount {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}
.budget-bar {
  height: 6px;
  border-radius: 3px;
  background: var(--bg-gray);
  overflow: hidden;
}
.budget-bar-fill {
  height: 100%;
  border-radius: 3px;
  background: var(--brand);
  transition: width 0.4s ease;
}
.budget-summary {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--line-soft);
}
.summary-row {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  font-size: 13.5px;
  color: var(--muted);
}
.summary-row.total {
  font-weight: 600;
  color: var(--ink);
  font-size: 14.5px;
}
.remain-ok {
  color: var(--emerald);
  font-weight: 600;
}
.remain-over {
  color: var(--rose);
  font-weight: 600;
}
.remain-none {
  color: var(--faint);
  font-size: 12.5px;
}
.budget-empty {
  font-size: 13px;
  color: var(--faint);
}

/* 推荐 */
.plan-recommend {
  margin-top: 36px;
}
.rec-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  padding: 4px;
  background: var(--bg-gray);
  border-radius: var(--radius-md);
  width: fit-content;
}
.rec-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: var(--radius-sm);
  font-size: 13.5px;
  font-weight: 500;
  color: var(--muted);
  transition: all 0.2s ease;
}
.rec-tab:hover {
  color: var(--ink);
}
.rec-tab.active {
  background: var(--bg);
  color: var(--brand);
  box-shadow: var(--shadow-sm);
}
.rec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.rec-card {
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.rec-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
.rec-img {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 120px;
}
.rec-body {
  padding: 14px 16px 16px;
}
.rec-name-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.rec-name-row h4 {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
}
.fav-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-xs);
  color: var(--faint);
  transition: all 0.2s ease;
  flex-shrink: 0;
}
.fav-btn:hover {
  color: var(--rose);
  background: var(--rose-soft);
}
.fav-btn.active {
  color: var(--rose);
}
.rec-detail {
  margin-top: 6px;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.rec-price {
  display: inline-block;
  margin-top: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--brand);
}
.rec-empty {
  padding: 24px;
  text-align: center;
  font-size: 13.5px;
  color: var(--faint);
  border: 1px dashed var(--line);
  border-radius: var(--radius-md);
}

/* 追问输入 */
.plan-ask {
  margin-top: 36px;
  padding: 22px 24px;
}
.ask-head h3 {
  font-size: 16.5px;
  font-weight: 600;
  color: var(--ink);
}
.ask-head p {
  margin-top: 2px;
  font-size: 13px;
  color: var(--faint);
}
.ask-input-row {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}
.ask-send {
  flex-shrink: 0;
  padding: 0 18px;
}
.ask-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.ask-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 13px;
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 13px;
  color: var(--muted);
  transition: all 0.2s ease;
}
.ask-chip:hover {
  border-color: var(--brand);
  color: var(--brand);
  background: var(--brand-soft);
}

/* 响应式 */
@media (max-width: 1023px) {
  .plan-main {
    grid-template-columns: 1fr;
  }
  .plan-right {
    position: static;
  }
  .plan-right {
    order: -1;
  }
}
@media (max-width: 639px) {
  .plan-view {
    padding: 0 16px 40px;
  }
  .plan-hero {
    min-height: 220px;
    margin-top: 12px;
  }
  .hero-content {
    padding: 18px 18px 20px;
  }
  .hero-title {
    font-size: 26px;
  }
  .rec-grid {
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
}
</style>
