<template>
  <div class="map-shell">
    <!-- 地图头部 -->
    <div class="map-top">
      <div class="map-title">
        <span class="map-title-icon"><BaseIcon name="map" :size="14" /></span>
        <span>{{ city ? city + " · 行程地图" : "行程地图" }}</span>
      </div>
      <div v-if="days.length > 1" class="map-day-tabs">
        <button
          v-for="d in days"
          :key="d"
          :class="['map-day-tab', activeDay === d ? 'active' : '']"
          @click="$emit('day-change', d)"
        >
          Day {{ d }}
        </button>
      </div>
    </div>

    <!-- 地图主体 -->
    <div class="map-canvas" @click="clearSelection">
      <!-- 百度真实地图（SDK 就绪后显示） -->
      <div v-show="sdkStatus === 'ready'" ref="mapEl" class="bd-map"></div>

      <!-- 真实地图增强控件：卫星视图 + 全屏查看 -->
      <div v-if="sdkStatus === 'ready'" class="map-ctrl">
        <button
          :class="{ active: isSatellite }"
          :title="isSatellite ? '切换街道地图' : '切换卫星视图'"
          @click="toggleSatellite"
        >
          <BaseIcon name="layers" :size="14" />
        </button>
        <button
          :title="isFullscreen ? '退出全屏' : '全屏查看（Esc 退出）'"
          @click="toggleFullscreen"
        >
          <BaseIcon :name="isFullscreen ? 'x' : 'external-link'" :size="14" />
        </button>
      </div>

      <!-- SDK 加载中 / 加载失败 → SVG 示意地图兜底 -->
      <svg
        v-show="sdkStatus !== 'ready'"
        :viewBox="`0 0 ${W} ${H}`"
        preserveAspectRatio="xMidYMid slice"
      >
        <!-- 底色 -->
        <rect :width="W" :height="H" fill="#eef1f5" />
        <!-- 区块色块（公园/水面） -->
        <g opacity="0.9">
          <rect x="56" y="80" width="120" height="92" rx="14" fill="#ddefe4" />
          <rect x="600" y="330" width="150" height="104" rx="14" fill="#ddefe4" />
          <rect x="330" y="420" width="110" height="72" rx="12" fill="#e2ecf7" />
        </g>
        <!-- 河流 -->
        <path
          d="M -20 330 C 180 260, 340 420, 520 350 S 760 240, 840 300"
          fill="none"
          stroke="#c9ddef"
          stroke-width="26"
          stroke-linecap="round"
        />
        <path
          d="M -20 330 C 180 260, 340 420, 520 350 S 760 240, 840 300"
          fill="none"
          stroke="#ffffff"
          stroke-width="2"
          stroke-dasharray="1 10"
          stroke-linecap="round"
        />
        <!-- 道路 -->
        <g stroke="#ffffff" stroke-linecap="round" fill="none">
          <path d="M 0 200 H 800" stroke-width="14" />
          <path d="M 0 470 H 800" stroke-width="10" />
          <path d="M 170 0 V 520" stroke-width="14" />
          <path d="M 480 0 V 520" stroke-width="10" />
          <path d="M 660 0 V 520" stroke-width="6" />
          <path d="M 300 0 V 520" stroke-width="6" />
        </g>
        <g stroke="#d7dde6" stroke-width="1.2" fill="none">
          <path d="M 0 200 H 800" stroke-dasharray="0" />
          <path d="M 0 470 H 800" />
          <path d="M 170 0 V 520" />
          <path d="M 480 0 V 520" />
          <path d="M 660 0 V 520" />
          <path d="M 300 0 V 520" />
        </g>

        <!-- 路线（当前 Day） -->
        <g v-if="routePoints.length > 1">
          <polyline
            :points="routePoints.map((p) => `${p.x},${p.y}`).join(' ')"
            fill="none"
            stroke="#ffffff"
            stroke-width="7"
            stroke-linecap="round"
            stroke-linejoin="round"
            opacity="0.9"
          />
          <polyline
            :points="routePoints.map((p) => `${p.x},${p.y}`).join(' ')"
            fill="none"
            :stroke="routeColor"
            stroke-width="2.4"
            stroke-dasharray="2 7"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </g>

        <!-- POI 标记 -->
        <g v-for="p in visibleSpots" :key="p.num">
          <g
            class="spot-group"
            :class="{ dimmed: activeDay !== p.day }"
            @click.stop="selectSpot(p)"
          >
            <circle
              :cx="p.x"
              :cy="p.y"
              :r="p.selected ? 17 : 13"
              :fill="activeDay === p.day ? routeColor : '#94a3b8'"
              :opacity="p.selected ? 1 : 0.94"
            />
            <circle
              :cx="p.x"
              :cy="p.y"
              :r="p.selected ? 13.5 : 10"
              fill="#ffffff"
            />
            <text
              :x="p.x"
              :y="p.y + 4"
              text-anchor="middle"
              :font-size="p.selected ? 13 : 11"
              :font-weight="600"
              :fill="activeDay === p.day ? routeColor : '#64748b'"
              style="font-family: var(--font)"
            >
              {{ p.num }}
            </text>
          </g>
        </g>
      </svg>

      <!-- 兜底提示（真实地图加载失败） -->
      <div v-if="sdkStatus === 'failed'" class="map-fallback-tip">
        <BaseIcon name="map" :size="13" /> 真实地图暂不可用，当前为示意地图
      </div>

      <!-- POI tooltip（SVG 模式） -->
      <div
        v-if="sdkStatus !== 'ready' && selectedSpot"
        class="map-tooltip"
        :style="tooltipStyle"
      >
        <strong>{{ selectedSpot.name }}</strong>
        <span>Day {{ selectedSpot.day }} · 第 {{ selectedSpot.num }} 站</span>
      </div>

      <!-- 缩放控件（两种模式通用：真实地图调用百度 API，SVG 模式缩放画布） -->
      <div class="map-zoom">
        <button title="放大" @click="zoomIn"><BaseIcon name="plus" :size="14" /></button>
        <button title="缩小" @click="zoomOut"><BaseIcon name="minus" :size="14" /></button>
        <button title="复位全景" @click="resetZoom"><BaseIcon name="navigation" :size="14" /></button>
      </div>

      <!-- 比例尺（SVG 模式装饰；真实地图使用百度自带比例尺） -->
      <div v-if="sdkStatus !== 'ready'" class="map-scale">500 m</div>
    </div>

    <!-- 图例 -->
    <div class="map-legend">
      <div class="legend-item">
        <span class="legend-dot current"></span> 当日路线
      </div>
      <div class="legend-item">
        <span class="legend-dot spot"></span> 行程景点
      </div>
      <div v-if="!spots.length" class="legend-hint">生成行程后，这里会显示每日路线与景点位置</div>
    </div>
  </div>
</template>

<script>
import BaseIcon from "./BaseIcon.vue";
import { CITY_CENTERS, CN_CITIES, getSpotCoords, getSpotCoordInfo } from "../utils/plan.js";

const W = 800;
const H = 520;
const DAY_PALETTE = ["#2563eb", "#0d9488", "#b45309", "#7c3aed", "#be185d"];
// SDK 已在 index.html 中同步引入（见 frontend/index.html），ak 由 Vite 从 frontend/.env 注入
const SDK_POLL_MS = 2000;
const SDK_POLL_LIMIT = 5;

export default {
  name: "TripMap",
  components: { BaseIcon },
  props: {
    city: { type: String, default: "" },
    spots: { type: Array, default: () => [] }, // [{name, num, day}]
    activeDay: { type: Number, default: 1 },
  },
  data() {
    return {
      W,
      H,
      // SVG 兜底交互状态
      selectedSpot: null,
      scale: 1,
      // 百度地图状态：loading（SDK 加载中，先展示 SVG 兜底）→ ready / failed
      sdkStatus: "loading",
      map: null,
      BMapGL: null,
      markerMap: {}, // key -> { label, pt }
      routeLine: null,
      infoWindow: null,
      resolved: {}, // name -> {lat, lng, found}（百度地理编码修正结果）
      geoLoading: false,
      apiBase: import.meta.env?.VITE_API_BASE || "",
      _sdkTimer: null,
      // 增强交互状态
      isFullscreen: false,
      isSatellite: false,
    };
  },
  computed: {
    days() {
      const set = new Set(this.spots.map((s) => s.day));
      return Array.from(set).sort((a, b) => a - b);
    },
    routeColor() {
      return DAY_PALETTE[(this.activeDay - 1) % DAY_PALETTE.length];
    },
    // 景点坐标：百度地理编码 > 内置地标 > 确定性哈希近似
    spotCoords() {
      const map = {};
      for (const s of this.spots) {
        const geo = this.resolved[s.name];
        if (geo && geo.found) {
          map[this.keyOf(s)] = { lat: geo.lat, lng: geo.lng };
          continue;
        }
        const info = getSpotCoordInfo(s.name, this.city, s.num);
        map[this.keyOf(s)] = { lat: info.lat, lng: info.lng };
      }
      return map;
    },
    // ── SVG 兜底投影 ──
    projected() {
      const center = CITY_CENTERS[this.city] || null;
      return this.spots.map((s) => {
        let coord;
        if (center) {
          coord = getSpotCoords(s.name, this.city, s.num);
          const clat = center[0];
          const clng = center[1];
          const dLat = coord[0] - clat;
          const dLng = (coord[1] - clng) * Math.cos((clat * Math.PI) / 180);
          // 归一化：约 0.05° 半径映射到画布
          const x = W / 2 + (dLng / 0.055) * (W * 0.36);
          const y = H / 2 - (dLat / 0.04) * (H * 0.38);
          return {
            ...s,
            x: Math.max(40, Math.min(W - 40, x)),
            y: Math.max(40, Math.min(H - 40, y)),
          };
        }
        // 无城市坐标：环形布局
        const n = Math.max(this.spots.length, 1);
        const angle = ((s.num - 1) / n) * Math.PI * 2 - Math.PI / 2;
        const rx = W * 0.34;
        const ry = H * 0.32;
        return { ...s, x: W / 2 + rx * Math.cos(angle), y: H / 2 + ry * Math.sin(angle) };
      });
    },
    visibleSpots() {
      return this.projected;
    },
    routePoints() {
      return this.projected
        .filter((p) => p.day === this.activeDay)
        .sort((a, b) => a.num - b.num)
        .map((p) => ({ x: p.x, y: p.y }));
    },
    tooltipStyle() {
      if (!this.selectedSpot) return {};
      const p = this.projected.find((s) => s.num === this.selectedSpot.num);
      if (!p) return {};
      const left = Math.min(Math.max((p.x / W) * 100, 8), 72);
      const top = Math.max((p.y / H) * 100 - 14, 6);
      return { left: `${left}%`, top: `${top}%` };
    },
  },
  watch: {
    activeDay() {
      this.clearSelection();
      this.refreshMapDay();
    },
    city() {
      this.resolved = {};
      if (this.sdkStatus === "ready") this.rebuildMarkers();
    },
    spots() {
      this.resolved = {};
      if (this.sdkStatus === "ready") this.rebuildMarkers();
    },
  },
  mounted() {
    this.loadSdk();
    document.addEventListener("fullscreenchange", this.onFullscreenChange);
  },
  beforeUnmount() {
    if (this._sdkTimer) clearTimeout(this._sdkTimer);
    document.removeEventListener("fullscreenchange", this.onFullscreenChange);
    this.closeInfoWindow();
    this.map = null;
  },
  methods: {
    keyOf(s) {
      return `${s.day}-${s.num}-${s.name}`;
    },
    escapeHtml(str) {
      return String(str).replace(/[&<>"']/g, (ch) => (
        { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]
      ));
    },
    // ── SDK 就绪检测（index.html 同步加载，此处轮询等待）──
    loadSdk() {
      this._sdkPollCount = 0;
      this.pollSdk();
    },
    pollSdk() {
      if (window.BMapGL) {
        this.sdkStatus = "ready";
        this.$nextTick(this.initMap);
        return;
      }
      this._sdkPollCount += 1;
      if (this._sdkPollCount >= SDK_POLL_LIMIT) {
        this.failSdk();
        return;
      }
      this._sdkTimer = setTimeout(this.pollSdk, SDK_POLL_MS);
    },
    failSdk() {
      this.sdkStatus = "failed";
      console.warn("[TripMap] 百度地图 SDK 加载失败，回退为示意地图");
    },
    // ── 地图初始化 ──
    initMap() {
      const BMapGL = window.BMapGL;
      const el = this.$refs.mapEl;
      if (!el || !BMapGL) return;
      try {
        const map = new BMapGL.Map(el, { enableMapClick: true, minZoom: 3 });
        this.map = map;
        this.BMapGL = BMapGL;
        // 比例尺（左下角，避开版权信息）
        map.addControl(
          new BMapGL.ScaleControl({
            anchor: window.BMAP_ANCHOR_BOTTOM_LEFT,
            offset: new BMapGL.Size(10, 30),
          })
        );
        this.rebuildMarkers();
      } catch (e) {
        console.warn("[TripMap] 百度地图初始化失败:", e);
        this.failSdk();
      }
    },
    // ── 打点与视野 ──
    rebuildMarkers() {
      const BMapGL = this.BMapGL;
      if (!this.map || !BMapGL) return;
      this.closeInfoWindow();
      this.map.clearOverlays();
      this.markerMap = {};
      this.routeLine = null;

      const points = [];
      for (const s of this.spots) {
        const key = this.keyOf(s);
        const c = this.spotCoords[key];
        if (!c) continue;
        const pt = new BMapGL.Point(c.lng, c.lat);
        points.push(pt);
        const active = s.day === this.activeDay;
        const label = new BMapGL.Label(String(s.num), {
          position: pt,
          offset: new BMapGL.Size(-12, -34),
        });
        label.setStyle(this.markerStyle(active ? this.routeColor : "#94a3b8", active ? 1 : 0.45));
        label.addEventListener("click", (e) => {
          // 阻止冒泡，避免触发容器的 clearSelection 关闭逻辑
          if (e.domEvent) e.domEvent.stopPropagation();
          this.openInfoWindow(s, pt);
        });
        this.map.addOverlay(label);
        this.markerMap[key] = { label, pt };
      }

      if (points.length) {
        this.map.setViewport(points, { margins: [80, 80, 80, 80] });
      } else {
        const c = CITY_CENTERS[this.city];
        if (c) this.map.centerAndZoom(new BMapGL.Point(c[1], c[0]), 12);
        else this.map.centerAndZoom(new BMapGL.Point(108.5, 35.5), 4); // 无城市信息 → 全国视野
      }
      this.redrawRoute();
      // 异步获取百度精确坐标修正非地标景点
      this.resolveGeo();
    },
    markerStyle(color, opacity) {
      return {
        color: "#fff",
        backgroundColor: color,
        fontSize: "12px",
        fontWeight: "600",
        fontFamily: "inherit",
        width: "24px",
        height: "24px",
        lineHeight: "24px",
        textAlign: "center",
        borderRadius: "12px",
        border: "2px solid #fff",
        boxShadow: "0 2px 6px rgba(15, 23, 42, 0.35)",
        padding: "0",
        opacity: String(opacity),
      };
    },
    refreshMapDay() {
      this.redrawRoute();
      this.refreshMarkerStyles();
    },
    refreshMarkerStyles() {
      if (!this.map || !this.BMapGL) return;
      for (const s of this.spots) {
        const m = this.markerMap[this.keyOf(s)];
        if (!m) continue;
        const active = s.day === this.activeDay;
        m.label.setStyle(this.markerStyle(active ? this.routeColor : "#94a3b8", active ? 1 : 0.45));
      }
    },
    // ── 百度地理编码修正（真实坐标）──
    resolveGeo() {
      if (this.geoLoading) return;
      // 仅国内目的地请求百度修正：海外城市同名地点会被错误解析到国内
      if (!CN_CITIES.includes(this.city)) return;
      const missing = [];
      for (const s of this.spots) {
        if (this.resolved[s.name]) continue;
        // 内置地标坐标已精确，仅对哈希近似坐标请求百度修正
        if (!getSpotCoordInfo(s.name, this.city, s.num).exact) missing.push(s.name);
      }
      if (!missing.length) return;
      this.geoLoading = true;
      fetch(`${this.apiBase}/api/baidu/geocode-batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ city: this.city, names: missing }),
      })
        .then((r) => r.json())
        .then((data) => {
          const resolved = { ...this.resolved };
          for (const item of data.items || []) resolved[item.name] = item;
          this.resolved = resolved;
          this.refreshPositions();
        })
        .catch(() => {})
        .finally(() => {
          this.geoLoading = false;
        });
    },
    refreshPositions() {
      const BMapGL = this.BMapGL;
      if (!this.map || !BMapGL) return;
      let moved = false;
      for (const s of this.spots) {
        const key = this.keyOf(s);
        const m = this.markerMap[key];
        const c = this.spotCoords[key];
        if (!m || !c) continue;
        if (m.pt.lat === c.lat && m.pt.lng === c.lng) continue;
        const pt = new BMapGL.Point(c.lng, c.lat);
        m.pt = pt;
        m.label.setPosition(pt);
        moved = true;
      }
      if (moved) this.redrawRoute();
    },
    // ── 当日路线 ──
    redrawRoute() {
      const BMapGL = this.BMapGL;
      if (!this.map || !BMapGL) return;
      if (this.routeLine) {
        this.map.removeOverlay(this.routeLine);
        this.routeLine = null;
      }
      const daySpots = this.spots
        .filter((s) => s.day === this.activeDay)
        .sort((a, b) => a.num - b.num);
      if (daySpots.length < 2) return;
      const pts = [];
      for (const s of daySpots) {
        const c = this.spotCoords[this.keyOf(s)];
        if (c) pts.push(new BMapGL.Point(c.lng, c.lat));
      }
      if (pts.length < 2) return;
      this.routeLine = new BMapGL.Polyline(pts, {
        strokeColor: this.routeColor,
        strokeWeight: 3,
        strokeOpacity: 0.85,
        strokeStyle: "dashed",
      });
      this.map.addOverlay(this.routeLine);
    },
    // ── 信息窗 ──
    openInfoWindow(s, pt) {
      const BMapGL = this.BMapGL;
      if (!this.map || !BMapGL) return;
      this.closeInfoWindow();
      // 点击标记平滑聚焦放大：街区级视野（16 级）查看景点细节
      if (this.map.getZoom() < 16) this.map.centerAndZoom(pt, 16);
      else this.map.panTo(pt);
      this.infoWindow = new BMapGL.InfoWindow(
        `<div class="bd-iw"><strong>${this.escapeHtml(s.name)}</strong>` +
          `<span>Day ${s.day} · 第 ${s.num} 站</span></div>`,
        { width: 220, offset: new BMapGL.Size(0, -32) }
      );
      this.map.openInfoWindow(this.infoWindow, pt);
    },
    closeInfoWindow() {
      if (this.infoWindow && this.map) {
        this.map.closeInfoWindow();
        this.infoWindow = null;
      }
    },
    // ── 增强交互：全屏查看 ──
    toggleFullscreen() {
      const canvas = this.$el.querySelector(".map-canvas");
      if (!canvas) return;
      if (!document.fullscreenElement) {
        if (canvas.requestFullscreen) canvas.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen();
      }
    },
    onFullscreenChange() {
      this.isFullscreen = !!document.fullscreenElement;
      // 全屏切换后容器尺寸变化，等待布局完成后重算地图尺寸
      if (this.map) {
        setTimeout(() => {
          if (this.map) this.map.checkResize();
        }, 150);
      }
    },
    // ── 增强交互：卫星/街道图层切换 ──
    toggleSatellite() {
      if (!this.map || !this.BMapGL) return;
      this.isSatellite = !this.isSatellite;
      this.map.setMapType(
        this.isSatellite ? window.BMAP_EARTH_MAP : window.BMAP_NORMAL_MAP
      );
    },
    // ── 缩放交互（真实地图与 SVG 兑底共用同一控件）──
    zoomIn() {
      if (this.sdkStatus === "ready" && this.map) {
        this.map.zoomIn();
        return;
      }
      this.scale = Math.min(1.6, this.scale + 0.2);
      this.applyZoom();
    },
    zoomOut() {
      if (this.sdkStatus === "ready" && this.map) {
        this.map.zoomOut();
        return;
      }
      this.scale = Math.max(0.8, this.scale - 0.2);
      this.applyZoom();
    },
    resetZoom() {
      if (this.sdkStatus === "ready" && this.map && this.BMapGL) {
        this.fitViewport();
        return;
      }
      this.scale = 1;
      this.applyZoom();
    },
    // 全景复位：视野包含全部景点标记（含边距）
    fitViewport() {
      if (!this.map || !this.BMapGL) return;
      const points = Object.values(this.markerMap).map((m) => m.pt);
      if (points.length) {
        this.map.setViewport(points, { margins: [80, 80, 80, 80] });
      } else {
        const c = CITY_CENTERS[this.city];
        if (c) this.map.centerAndZoom(new this.BMapGL.Point(c[1], c[0]), 12);
        else this.map.centerAndZoom(new this.BMapGL.Point(108.5, 35.5), 4);
      }
    },
    // ── SVG 兑底交互 ──
    selectSpot(p) {
      this.selectedSpot = p.selected ? null : p;
    },
    clearSelection() {
      this.selectedSpot = null;
      this.closeInfoWindow();
    },
    applyZoom() {
      const canvas = this.$el.querySelector(".map-canvas");
      if (canvas) canvas.style.setProperty("--map-scale", this.scale);
    },
  },
};
</script>

<style scoped>
.map-shell {
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
}
.map-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line-soft);
  flex-wrap: wrap;
}
.map-title {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}
.map-title-icon {
  display: inline-flex;
  color: var(--brand);
}
.map-day-tabs {
  display: flex;
  gap: 4px;
  background: var(--bg-gray);
  border-radius: var(--radius-sm);
  padding: 3px;
}
.map-day-tab {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--muted);
  transition: all 0.2s ease;
}
.map-day-tab:hover {
  color: var(--ink);
}
.map-day-tab.active {
  background: var(--bg);
  color: var(--brand);
  box-shadow: var(--shadow-sm);
}
/* 真实地图增强控件（卫星视图 / 全屏） */
.map-ctrl {
  position: absolute;
  right: 12px;
  top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 12;
}
.map-ctrl button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--bg);
  border-radius: var(--radius-sm);
  color: var(--ink-2);
  box-shadow: var(--shadow-md);
  transition: all 0.2s ease;
}
.map-ctrl button:hover {
  color: var(--brand);
}
.map-ctrl button.active {
  color: var(--brand);
  background: var(--brand-soft);
}
/* 全屏模式：地图铺满视口 */
.map-canvas:fullscreen {
  background: #fff;
}
.map-canvas:fullscreen .bd-map {
  height: 100%;
}

.map-canvas {
  position: relative;
  cursor: crosshair;
  overflow: hidden;
}
/* 百度地图容器 */
.bd-map {
  width: 100%;
  height: 460px;
  cursor: grab;
}
.bd-map:active {
  cursor: grabbing;
}
.map-fallback-tip {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.72);
  color: #fff;
  font-size: 12px;
  z-index: 3;
  pointer-events: none;
  white-space: nowrap;
}
.map-canvas svg {
  display: block;
  width: 100%;
  height: auto;
  max-height: 460px;
  transform: scale(var(--map-scale, 1));
  transition: transform 0.25s ease;
}
.spot-group {
  cursor: pointer;
}
.spot-group.dimmed {
  opacity: 0.38;
  transition: opacity 0.2s ease;
}
.spot-group:hover {
  opacity: 1 !important;
}
.spot-group text {
  pointer-events: none;
  user-select: none;
}

.map-tooltip {
  position: absolute;
  transform: translate(-50%, -100%);
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: var(--ink);
  color: #fff;
  font-size: 12px;
  box-shadow: var(--shadow-md);
  pointer-events: none;
  white-space: nowrap;
  z-index: 2;
}
.map-tooltip strong {
  font-weight: 600;
  font-size: 12.5px;
}
.map-tooltip span {
  color: rgba(255, 255, 255, 0.7);
  font-size: 11px;
}

.map-zoom {
  position: absolute;
  right: 12px;
  bottom: 34px;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-sm);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  z-index: 12;
}
.map-zoom button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--bg);
  color: var(--ink-2);
  border-bottom: 1px solid var(--line-soft);
  transition: background 0.2s ease;
}
.map-zoom button:last-child {
  border-bottom: none;
}
.map-zoom button:hover {
  background: var(--bg-gray);
}
.map-scale {
  position: absolute;
  left: 12px;
  bottom: 10px;
  font-size: 11px;
  color: var(--muted);
  background: rgba(255, 255, 255, 0.85);
  padding: 2px 8px;
  border-radius: 4px;
  z-index: 2;
}
.map-scale::before {
  content: "";
  display: inline-block;
  width: 26px;
  height: 4px;
  border-left: 1.5px solid var(--muted);
  border-right: 1.5px solid var(--muted);
  border-top: 1.5px solid var(--muted);
  margin-right: 6px;
  vertical-align: middle;
}

.map-legend {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  border-top: 1px solid var(--line-soft);
  font-size: 12px;
  color: var(--muted);
  flex-wrap: wrap;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.legend-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px var(--line);
}
.legend-dot.current {
  background: var(--brand);
}
.legend-dot.spot {
  background: #94a3b8;
}
.legend-hint {
  color: var(--faint);
}
</style>

<!-- 百度 InfoWindow 内容为运行时注入的 HTML 字符串，Vue scoped 样式不生效，需全局样式 -->
<style>
.bd-iw {
  font-family: inherit;
  padding: 4px 2px;
}
.bd-iw strong {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 2px;
}
.bd-iw span {
  display: block;
  font-size: 11px;
  color: #64748b;
}
/* 百度地图遮罩层（BMap_mask）是拖拽事件链的关键，不能禁用其事件接收。
   景点标记渲染在 .bd-map 首个子 div（Label 容器，GL 默认 z-index 5），
   需提到遮罩（z-index 9）之上，才能保证：标记可点击、空白处可拖拽。 */
.bd-map > div:first-child {
  z-index: 12 !important;
}
</style>
