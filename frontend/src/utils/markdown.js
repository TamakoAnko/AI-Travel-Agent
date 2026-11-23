// ── JSON 兜底清洗 ──
// 后端/模型偶尔会直接输出 JSON（代码块或裸对象），用户可见页面一律不允许出现
// JSON 格式数据，这里统一转成中文可读的「键: 值」列表。

function jsonToReadable(data, depth = 0, maxDepth = 3, maxItems = 10) {
  const indent = "  ".repeat(depth);
  if (data === null || data === undefined) return "无";
  if (Array.isArray(data)) {
    if (depth >= maxDepth) return "…";
    if (!data.length) return "（空）";
    const items = data.slice(0, maxItems).map((item) => {
      const rendered = jsonToReadable(item, depth + 1, maxDepth, maxItems);
      return `${indent}- ${rendered}`;
    });
    if (data.length > maxItems) {
      items.push(`${indent}- …（共 ${data.length} 项，已省略）`);
    }
    return items.join("\n");
  }
  if (typeof data === "object") {
    if (depth >= maxDepth) return "…";
    const entries = Object.entries(data);
    if (!entries.length) return "（空）";
    return entries
      .slice(0, maxItems)
      .map(([k, v]) => {
        if (v !== null && typeof v === "object") {
          return `${indent}${k}:\n${jsonToReadable(v, depth + 1, maxDepth, maxItems)}`;
        }
        return `${indent}${k}: ${v}`;
      })
      .join("\n");
  }
  return String(data);
}

/**
 * 清洗用户可见文本中的 JSON：
 * 1. ```json 代码块 → 中文可读列表
 * 2. 整段裸 JSON 对象/数组 → 中文可读列表
 * 无法解析的内容原样返回。
 */
export function sanitizeJson(text) {
  if (!text || typeof text !== "string") return text || "";
  let out = text;
  // 1. JSON 代码块
  out = out.replace(/```(?:json|JSON)?\s*\n?([\s\S]*?)\n?```/g, (match, inner) => {
    try {
      const data = JSON.parse(inner.trim());
      return "\n\n" + jsonToReadable(data) + "\n\n";
    } catch {
      return match; // 非 JSON 代码块保留原样
    }
  });
  // 2. 整段裸 JSON
  const trimmed = out.trim();
  if (
    (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
    (trimmed.startsWith("[") && trimmed.endsWith("]"))
  ) {
    try {
      const data = JSON.parse(trimmed);
      return jsonToReadable(data);
    } catch {
      // 解析失败原样返回
    }
  }
  return out;
}

// 轻量 Markdown 渲染器（转义后按规则替换，输出安全 HTML）
export function renderMarkdown(text) {
  if (!text) return "";
  // 先清洗 JSON（用户可见页面不出现 JSON 数据）
  text = sanitizeJson(text);
  // 再转义 HTML
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // 搜索中心跳占位符 → 动画 blockquote
  html = html.replace(
    /\u23F3SEARCHING/g,
    '<blockquote class="gap-indicator"><span class="gap-dots"><i></i><i></i><i></i></span>搜索中</blockquote>'
  );

  // 代码块（```...```）—— 先处理避免被后续规则干扰
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  // 行内代码
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // 标题
  html = html.replace(/^#### (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/^### (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/^## (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^# (.+)$/gm, "<h2>$1</h2>");

  // 粗体 / 斜体
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // 水平线
  html = html.replace(/^---$/gm, "<hr>");

  // 引用
  html = html.replace(/^&gt; ?(.+)$/gm, "<blockquote>$1</blockquote>");

  // 表格
  html = html.replace(/^\|(.+)\|$/gm, (line) => {
    const cells = line.split("|").filter((c) => c.length > 0);
    if (/^[-:\s|]+$/.test(cells.join("|"))) return "<!-- sep -->";
    const isHeader = line.includes("---");
    const tag = isHeader ? "th" : "td";
    return `<tr>${cells.map((c) => `<${tag}>${c.trim()}</${tag}>`).join("")}</tr>`;
  });
  html = html.replace(
    /(?:<!-- sep -->\n?)?((?:<tr>.*<\/tr>\n?)+)/g,
    "<table>$1</table>"
  );
  html = html.replace(/<!-- sep -->/g, "");

  // 无序列表
  html = html.replace(/^[\-\*] (.+)$/gm, "<li>$1</li>");
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, "<ul>$1</ul>");

  // 按双换行分段
  const paragraphs = html.split(/\n\n+/);
  html = paragraphs
    .map((p) => {
      p = p.trim();
      if (!p) return "";
      // 已经是块级元素的跳过包装
      if (
        /^<(h[2-4]|hr|ul|ol|table|blockquote|pre)>/.test(p)
      ) {
        return p;
      }
      // 单换行转 <br>
      return "<p>" + p.replace(/\n/g, "<br>") + "</p>";
    })
    .join("\n");

  return html;
}
