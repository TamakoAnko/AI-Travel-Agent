<template>
  <div class="home-view">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-left">
        <h1 class="hero-title">下一段旅程，<br />从这里开始。</h1>
        <p class="hero-sub">告诉我们你想去哪里，剩下的交给我们。行程、住宿、预算，一次说清。</p>

        <div class="hero-input">
          <textarea
            v-model="text"
            rows="2"
            placeholder="例如：帮我规划一趟 5 天的巴黎之旅，6 月出发，预算 15000 元，我喜欢艺术和美食"
            @keydown.enter.exact.prevent="submit"
          ></textarea>
          <button class="hero-send" :disabled="!text.trim()" @click="submit" title="开始规划">
            <BaseIcon name="arrow-up" :size="18" />
          </button>
        </div>

        <div class="hero-chips">
          <button
            v-for="chip in chips"
            :key="chip"
            class="chip"
            @click="fillChip(chip)"
          >
            {{ chip }}
          </button>
        </div>
      </div>

      <div class="hero-right">
        <div class="hero-photo"></div>
        <div class="hero-photo-mask"></div>
        <div class="photo-caption">
          <span class="photo-city">巴黎 · Paris</span>
          <span class="photo-note">塞纳河畔的黄昏</span>
        </div>
      </div>
    </section>

    <!-- 灵感目的地 -->
    <section class="destinations">
      <div class="section-head">
        <h2>旅行灵感</h2>
        <p>从这些目的地开始，或者告诉我们你自己的计划</p>
      </div>
      <div class="dest-grid">
        <button
          v-for="d in destinations"
          :key="d.name"
          class="dest-card"
          @click="pickDestination(d)"
        >
          <img :src="d.img" :alt="d.name" loading="lazy" @error="onImgError" />
          <div class="dest-mask"></div>
          <div class="dest-info">
            <span class="dest-name">{{ d.name }}</span>
            <span class="dest-en">{{ d.en }}</span>
          </div>
          <div class="dest-tag">{{ d.tag }}</div>
        </button>
      </div>
    </section>

    <!-- 流程说明 -->
    <section class="how">
      <div class="step">
        <span class="step-num">01</span>
        <h3>说出你的想法</h3>
        <p>目的地、天数、预算、偏好，一句话或一段话都可以。</p>
      </div>
      <div class="step">
        <span class="step-num">02</span>
        <h3>行程自动生成</h3>
        <p>每日路线、景点、住宿与预算，几分钟内为你整理成一份完整计划。</p>
      </div>
      <div class="step">
        <span class="step-num">03</span>
        <h3>随时调整</h3>
        <p>想改路线、换酒店、加餐厅？继续对话，计划实时更新。</p>
      </div>
    </section>
  </div>
</template>

<script>
import BaseIcon from "./BaseIcon.vue";

const DESTINATIONS = [
  { name: "巴黎", en: "Paris", tag: "艺术 · 美食", img: "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800&q=80" },
  { name: "东京", en: "Tokyo", tag: "都市 · 文化", img: "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=800&q=80" },
  { name: "罗马", en: "Rome", tag: "历史 · 建筑", img: "https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=800&q=80" },
  { name: "巴厘岛", en: "Bali", tag: "海岛 · 度假", img: "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=800&q=80" },
  { name: "伦敦", en: "London", tag: "博物馆 · 下午茶", img: "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800&q=80" },
  { name: "京都", en: "Kyoto", tag: "古寺 · 枫叶", img: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&q=80" },
];

export default {
  name: "HomeHero",
  components: { BaseIcon },
  data() {
    return {
      text: "",
      chips: ["5 天 4 晚", "亲子游", "蜜月旅行", "美食之旅", "自然风光"],
      destinations: DESTINATIONS,
    };
  },
  methods: {
    submit() {
      const t = this.text.trim();
      if (!t) return;
      this.$emit("submit", t);
      this.text = "";
    },
    fillChip(chip) {
      this.text = this.text ? `${this.text} · ${chip}` : chip;
    },
    pickDestination(d) {
      this.$emit("submit", `帮我规划一趟${d.name}之旅，预算适中，想体验${d.tag}`);
    },
    onImgError(e) {
      e.target.style.display = "none";
    },
  },
};
</script>

<style scoped>
.home-view {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 32px;
}

/* ── Hero ── */
.hero {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 56px;
  align-items: center;
  padding: 72px 0 64px;
}
.hero-title {
  font-size: 44px;
  font-weight: 600;
  line-height: 1.28;
  letter-spacing: 0.5px;
  color: var(--ink);
}
.hero-sub {
  margin-top: 16px;
  font-size: 16.5px;
  color: var(--muted);
  max-width: 420px;
}
.hero-input {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  margin-top: 32px;
  padding: 12px 12px 12px 18px;
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  background: var(--bg);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.hero-input:focus-within {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}
.hero-input textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 15px;
  line-height: 1.6;
  color: var(--ink);
  background: none;
  min-height: 44px;
  max-height: 120px;
}
.hero-input textarea::placeholder {
  color: var(--faint);
}
.hero-send {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  background: var(--brand);
  color: #fff;
  transition: background 0.2s ease;
  flex-shrink: 0;
}
.hero-send:hover:not(:disabled) {
  background: var(--brand-strong);
}
.hero-send:disabled {
  background: var(--line);
  color: var(--faint);
  cursor: not-allowed;
}
.hero-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}
.chip {
  padding: 6px 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--bg);
  color: var(--muted);
  font-size: 13px;
  transition: all 0.2s ease;
}
.chip:hover {
  border-color: var(--brand);
  color: var(--brand);
  background: var(--brand-soft);
}

/* Hero 右图 */
.hero-right {
  position: relative;
  height: 420px;
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.hero-photo {
  position: absolute;
  inset: 0;
  background: linear-gradient(150deg, #16283f 0%, #2b4a73 50%, #4a6f9e 100%);
  background-image: url("https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=1400&q=80");
  background-size: cover;
  background-position: center;
  transition: transform 0.6s ease;
}
.hero-right:hover .hero-photo {
  transform: scale(1.03);
}
.hero-photo-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(12, 22, 38, 0.05) 40%, rgba(12, 22, 38, 0.55) 100%);
}
.photo-caption {
  position: absolute;
  left: 24px;
  bottom: 22px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: #fff;
}
.photo-city {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.photo-note {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.78);
}

/* ── 灵感目的地 ── */
.destinations {
  padding: 12px 0 40px;
}
.section-head {
  margin-bottom: 20px;
}
.section-head h2 {
  font-size: 22px;
  font-weight: 600;
  color: var(--ink);
}
.section-head p {
  margin-top: 4px;
  font-size: 14px;
  color: var(--muted);
}
.dest-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 14px;
}
.dest-card {
  position: relative;
  aspect-ratio: 3 / 4;
  border-radius: var(--radius-lg);
  overflow: hidden;
  text-align: left;
  background: var(--bg-gray);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: var(--shadow-sm);
}
.dest-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}
.dest-card img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.dest-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(12, 22, 38, 0.02) 45%, rgba(12, 22, 38, 0.62) 100%);
}
.dest-info {
  position: absolute;
  left: 14px;
  bottom: 12px;
  display: flex;
  flex-direction: column;
  color: #fff;
}
.dest-name {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.dest-en {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
}
.dest-tag {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 3px 9px;
  border-radius: var(--radius-xs);
  background: rgba(255, 255, 255, 0.9);
  color: var(--ink-2);
  font-size: 11.5px;
  font-weight: 500;
}

/* ── 流程说明 ── */
.how {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  padding: 40px 0 56px;
  border-top: 1px solid var(--line-soft);
}
.step {
  padding: 4px 8px;
}
.step-num {
  font-size: 13px;
  font-weight: 600;
  color: var(--brand);
  letter-spacing: 1px;
}
.step h3 {
  margin: 10px 0 6px;
  font-size: 16.5px;
  font-weight: 600;
  color: var(--ink);
}
.step p {
  font-size: 14px;
  color: var(--muted);
  line-height: 1.7;
}

/* ── 响应式 ── */
@media (max-width: 1199px) {
  .dest-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 899px) {
  .hero {
    grid-template-columns: 1fr;
    gap: 32px;
    padding: 48px 0 40px;
  }
  .hero-right {
    height: 300px;
  }
  .hero-title {
    font-size: 34px;
  }
}
@media (max-width: 639px) {
  .home-view {
    padding: 0 20px;
  }
  .hero {
    padding: 36px 0 32px;
  }
  .hero-title {
    font-size: 28px;
  }
  .hero-sub {
    font-size: 15px;
  }
  .hero-right {
    height: 220px;
  }
  .dest-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }
  .how {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 28px 0 40px;
  }
}
</style>
