<template>
  <span
    class="base-icon"
    :style="{ width: px, height: px }"
    :aria-hidden="true"
    v-html="svg"
  ></span>
</template>

<script>
import ICONS from "../icons.js";

export default {
  name: "BaseIcon",
  props: {
    name: { type: String, required: true },
    size: { type: [Number, String], default: 18 },
  },
  computed: {
    px() {
      return typeof this.size === "number" ? `${this.size}px` : this.size;
    },
    svg() {
      return ICONS[this.name] || "";
    },
  },
};
</script>

<style scoped>
.base-icon {
  display: inline-flex;
  flex-shrink: 0;
  line-height: 0;
}
.base-icon :deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
