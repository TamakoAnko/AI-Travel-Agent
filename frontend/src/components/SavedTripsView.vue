<template>
  <div class="saved-view">
    <div class="section-head">
      <div>
        <h2>我的旅行</h2>
        <p>行程保存在你的账号中，换设备登录也能看到</p>
      </div>
    </div>

    <div v-if="trips.length" class="trip-grid">
      <div v-for="trip in trips" :key="trip.id" class="trip-card card">
        <div class="trip-cover" :style="coverStyle(trip)">
          <div class="trip-meta">
            <span v-if="meta(trip).duration">{{ meta(trip).duration }} 天</span>
            <span v-if="meta(trip).budget">¥{{ meta(trip).budget }}</span>
            <span v-if="meta(trip).depart">{{ meta(trip).depart }}出发</span>
          </div>
          <span class="trip-city">{{ trip.city || "行程" }}</span>
          <span class="trip-en">{{ tone(trip.city).en }}</span>
        </div>
        <div class="trip-body">
          <div class="trip-title-row">
            <h4>{{ trip.title }}</h4>
            <button class="trip-del" title="删除" @click="remove(trip)">
              <BaseIcon name="trash" :size="14" />
            </button>
          </div>
          <p class="trip-date">{{ formatDate(trip.createdAt) }}</p>
          <div class="trip-actions">
            <button class="btn btn-outline btn-sm" @click="view(trip)">
              <BaseIcon name="eye" :size="14" /> 查看
            </button>
            <button class="btn btn-ghost btn-sm" @click="copy(trip)">
              <BaseIcon name="copy" :size="14" /> 复制
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <div class="empty-mark"><BaseIcon name="suitcase" :size="26" /></div>
      <h3>还没有保存的行程</h3>
      <p>生成旅行计划后，点击行程页右上角的「保存行程」即可收藏到这里</p>
      <button class="btn btn-primary" @click="$emit('go-plan')">
        <BaseIcon name="plane" :size="14" /> 去规划行程
      </button>
    </div>
  </div>
</template>

<script>
import BaseIcon from "./BaseIcon.vue";
import { getSavedTrips, removeSavedTrip, getCityVisual, fetchServerTrips, deleteServerTrip, parsePlan, formatStartDate } from "../utils/plan.js";

export default {
  name: "SavedTripsView",
  components: { BaseIcon },
  data() {
    return {
      trips: getSavedTrips(),
    };
  },
  async mounted() {
    await this.refresh();
  },
  methods: {
    // 账号行程 + 本机缓存合并（同一份 plan 以服务端为准）
    async refresh() {
      const local = getSavedTrips();
      const remote = await fetchServerTrips();
      const seen = new Set(remote.map((t) => t.raw));
      this.trips = [...remote, ...local.filter((t) => !seen.has(t.raw))]
        .sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0));
    },
    meta(trip) {
      const plan = parsePlan(trip.raw) || {};
      return {
        duration: plan.duration || "",
        budget: plan.budget || plan.budgetTotal || "",
        // 优先具体日期（11月25日），行程里只有月份时退回月份
        depart: formatStartDate(plan.startDate, plan.month),
      };
    },
    // 图片做背景、渐变做遮罩；图片加载失败时 backgroundColor 兜底，不会白屏
    coverStyle(trip) {
      const visual = this.tone(trip.city);
      const [c1, c2] = visual.tone || ["#1E3A5F", "#5B7C99"];
      const layers = [`linear-gradient(160deg, ${c1}dd 0%, ${c2}aa 55%, #0f172ad9 100%)`];
      if (visual.img) layers.push(`url("${visual.img}")`);
      return {
        backgroundColor: c1,
        backgroundImage: layers.join(", "),
        backgroundSize: "cover",
        backgroundPosition: "center",
      };
    },
    tone(city) {
      const v = getCityVisual(city);
      return { ...v, en: v.en };
    },
    formatDate(ts) {
      if (!ts) return "";
      const d = new Date(ts);
      return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
    },
    async remove(trip) {
      if (trip.serverId) await deleteServerTrip(trip.serverId);
      removeSavedTrip(trip.id);
      // 同一份行程可能还有本地缓存副本，一并清掉
      getSavedTrips()
        .filter((t) => t.raw === trip.raw)
        .forEach((t) => removeSavedTrip(t.id));
      await this.refresh();
    },
    view(trip) {
      this.$emit("view-trip", trip);
    },
    copy(trip) {
      this.$emit("copy-trip", trip);
    },
  },
};
</script>

<style scoped>
.saved-view {
  max-width: 1180px;
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
.trip-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 18px;
}
.trip-card {
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.trip-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
.trip-cover {
  position: relative;
  height: 150px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 14px 16px;
  color: #fff;
}
.trip-meta {
  position: absolute;
  top: 12px;
  left: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.trip-meta span {
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(6px);
  font-size: 11.5px;
  color: #fff;
}
.trip-city {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.trip-en {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
}
.trip-body {
  padding: 14px 16px 16px;
}
.trip-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}
.trip-title-row h4 {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--ink);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.trip-del {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--radius-xs);
  color: var(--faint);
  flex-shrink: 0;
  transition: all 0.2s ease;
}
.trip-del:hover {
  color: var(--rose);
  background: var(--rose-soft);
}
.trip-date {
  margin-top: 4px;
  font-size: 12px;
  color: var(--faint);
}
.trip-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 72px 24px;
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
.empty-state h3 {
  margin-top: 18px;
  font-size: 18px;
  font-weight: 600;
  color: var(--ink);
}
.empty-state p {
  margin: 8px 0 22px;
  font-size: 14px;
  color: var(--muted);
  max-width: 380px;
}

@media (max-width: 639px) {
  .saved-view {
    padding: 24px 16px 40px;
  }
}
</style>
