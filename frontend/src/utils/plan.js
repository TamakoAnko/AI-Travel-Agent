// ─────────────────────────────────────────────────────────────
// 行程解析：将后端生成的 Markdown 旅行计划解析为结构化数据
// 解析宽松容错：任何一步失败都不抛错，PlanView 有 Markdown 兜底
// ─────────────────────────────────────────────────────────────

const CITY_LIST = [
  "巴黎","东京","罗马","佛罗伦萨","威尼斯","米兰","巴厘岛","伦敦","纽约",
  "京都","大阪","首尔","曼谷","新加坡","北京","上海","杭州","成都","三亚",
  "云南","大理","丽江","青岛","厦门","西安","重庆","广州","深圳","香港","澳门",
  "台北","柏林","慕尼黑","瑞士","意大利","西班牙","巴塞罗那","马德里","葡萄牙",
  "阿姆斯特丹","布拉格","维也纳","冰岛","土耳其","伊斯坦布尔","迪拜","马尔代夫",
  "夏威夷","悉尼","墨尔本","新西兰","温哥华","多伦多","旧金山","洛杉矶","西雅图",
  "波士顿","华盛顿","希腊","雅典","埃及","开罗","摩洛哥","北欧","芬兰","挪威","丹麦",
];

// 国内目的地集合：仅这些城市可请求百度地理编码修正坐标；
// 海外城市百度地理编码会把同名地点解析到国内（如「清水寺」→ 成都清水寺），
// 故海外城市一律使用内置地标/近似坐标，避免错误定位。
export const CN_CITIES = [
  "北京","上海","杭州","成都","三亚","云南","大理","丽江","青岛","厦门",
  "西安","重庆","广州","深圳","香港","澳门","台北",
];

// 城市中心坐标（近似经纬度，用于示意地图投影）
export const CITY_CENTERS = {
  "巴黎": [48.8566, 2.3522], "东京": [35.6762, 139.6503], "罗马": [41.9028, 12.4964],
  "佛罗伦萨": [43.7696, 11.2558], "威尼斯": [45.4408, 12.3155], "米兰": [45.4642, 9.19],
  "巴厘岛": [-8.4095, 115.1889], "伦敦": [51.5074, -0.1278], "纽约": [40.7128, -74.006],
  "京都": [35.0116, 135.7681], "大阪": [34.6937, 135.5023], "首尔": [37.5665, 126.978],
  "曼谷": [13.7563, 100.5018], "新加坡": [1.3521, 103.8198], "北京": [39.9042, 116.4074],
  "上海": [31.2304, 121.4737], "杭州": [30.2741, 120.1551], "成都": [30.5728, 104.0668],
  "三亚": [18.2528, 109.5119], "云南": [25.0453, 102.7097], "大理": [25.6065, 100.2676],
  "丽江": [26.8721, 100.2299], "青岛": [36.0671, 120.3826], "厦门": [24.4798, 118.0894],
  "西安": [34.3416, 108.9398], "重庆": [29.563, 106.5516], "广州": [23.1291, 113.2644],
  "深圳": [22.5431, 114.0579], "香港": [22.3193, 114.1694], "澳门": [22.1987, 113.5439],
  "台北": [25.033, 121.5654], "柏林": [52.52, 13.405], "慕尼黑": [48.1351, 11.582],
  "瑞士": [46.8182, 8.2275], "意大利": [41.8719, 12.5674], "西班牙": [40.4637, -3.7492],
  "巴塞罗那": [41.3874, 2.1686], "马德里": [40.4168, -3.7038], "葡萄牙": [38.7223, -9.1393],
  "阿姆斯特丹": [52.3676, 4.9041], "布拉格": [50.0755, 14.4378], "维也纳": [48.2082, 16.3738],
  "冰岛": [64.9631, -19.0208], "土耳其": [38.9637, 35.2433], "伊斯坦布尔": [41.0082, 28.9784],
  "迪拜": [25.2048, 55.2708], "马尔代夫": [4.1755, 73.5093], "夏威夷": [21.3069, -157.8583],
  "悉尼": [-33.8688, 151.2093], "墨尔本": [-37.8136, 144.9631], "新西兰": [-40.9006, 174.886],
  "温哥华": [49.2827, -123.1207], "多伦多": [43.6532, -79.3832], "旧金山": [37.7749, -122.4194],
  "洛杉矶": [34.0522, -118.2437], "西雅图": [47.6062, -122.3321], "波士顿": [42.3601, -71.0589],
  "华盛顿": [38.9072, -77.0369], "希腊": [37.9838, 23.7275], "雅典": [37.9838, 23.7275],
  "埃及": [26.8206, 30.8025], "开罗": [30.0444, 31.2357], "摩洛哥": [31.7917, -7.0926],
  "北欧": [59.9139, 10.7522], "芬兰": [61.9241, 25.7482], "挪威": [60.472, 8.4689], "丹麦": [56.2639, 9.5018],
};

// 城市中心：先精确匹配，再容错「大阪市 / 京都府」这类后缀；都没有则返回 null
export function cityCenter(city) {
  if (!city) return null;
  if (CITY_CENTERS[city]) return CITY_CENTERS[city];
  const key = Object.keys(CITY_CENTERS).find((k) => city.includes(k));
  return key ? CITY_CENTERS[key] : null;
}

// 知名地标坐标（用于地图精确定位，按名称子串匹配）
const LANDMARKS = {
  "巴黎": {
    "卢浮宫": [48.8606, 2.3376], "埃菲尔铁塔": [48.8584, 2.2945], "奥赛博物馆": [48.86, 2.3266],
    "圣母院": [48.853, 2.3499], "圣心大教堂": [48.8867, 2.3431], "杜乐丽花园": [48.8635, 2.3274],
    "香榭丽舍": [48.8698, 2.3078], "凯旋门": [48.8738, 2.295], "蒙马特": [48.8867, 2.3431],
    "塞纳河": [48.855, 2.32], "圣日耳曼": [48.8539, 2.3333], "拉丁区": [48.8502, 2.3433],
    "卢森堡花园": [48.8462, 2.3372], "蓬皮杜": [48.8606, 2.3522], "歌剧院": [48.872, 2.3318],
  },
  "东京": {
    "浅草寺": [35.7148, 139.7967], "晴空塔": [35.7101, 139.8107], "东京塔": [35.6586, 139.7454],
    "明治神宫": [35.6764, 139.6993], "涩谷": [35.6595, 139.7005], "新宿": [35.6938, 139.7034],
    "银座": [35.6717, 139.765], "秋叶原": [35.7023, 139.7745], "上野公园": [35.7154, 139.7741],
    "台场": [35.6302, 139.7753], "筑地市场": [35.6654, 139.7707], "皇居": [35.6852, 139.7528],
  },
  "罗马": {
    "斗兽场": [41.8902, 12.4922], "万神殿": [41.8986, 12.4769], "许愿池": [41.9009, 12.4833],
    "西班牙广场": [41.906, 12.4827], "梵蒂冈": [41.9029, 12.4534], "圣彼得大教堂": [41.9022, 12.4539],
    "古罗马广场": [41.8925, 12.4853], "纳沃纳广场": [41.8992, 12.4731], "真理之口": [41.8881, 12.4817],
  },
  "伦敦": {
    "大英博物馆": [51.5194, -0.127], "伦敦塔桥": [51.5055, -0.0754], "大本钟": [51.5007, -0.1246],
    "白金汉宫": [51.5014, -0.1419], "威斯敏斯特": [51.4994, -0.1273], "伦敦眼": [51.5033, -0.1195],
    "海德公园": [51.5073, -0.1657], "塔桥": [51.5055, -0.0754], "圣保罗大教堂": [51.5138, -0.0984],
  },
  "纽约": {
    "自由女神像": [40.6892, -74.0445], "时代广场": [40.758, -73.9855], "中央公园": [40.7829, -73.9654],
    "大都会艺术博物馆": [40.7794, -73.9632], "帝国大厦": [40.7484, -73.9857], "华尔街": [40.7075, -74.0113],
    "第五大道": [40.7649, -73.9729], "布鲁克林大桥": [40.7061, -73.9969],
  },
  "北京": {
    "故宫": [39.9163, 116.3972], "天安门": [39.9087, 116.3975], "长城": [40.4319, 116.5704],
    "颐和园": [39.9999, 116.2755], "天坛": [39.8822, 116.4066], "王府井": [39.915, 116.4113],
    "南锣鼓巷": [39.9372, 116.4032], "什刹海": [39.9417, 116.3825], "鸟巢": [39.9928, 116.3975],
  },
  "上海": {
    "外滩": [31.2397, 121.4903], "东方明珠": [31.2397, 121.4998], "豫园": [31.2272, 121.4922],
    "南京路": [31.235, 121.4769], "田子坊": [31.2068, 121.4691], "武康路": [31.2103, 121.439],
    "迪士尼": [31.1443, 121.657], "新天地": [31.2191, 121.4747],
  },
  "杭州": {
    "西湖": [30.2437, 120.1512], "灵隐寺": [30.242, 120.099], "雷峰塔": [30.2309, 120.1484],
    "河坊街": [30.2412, 120.1719], "西溪湿地": [30.2693, 120.0633], "断桥": [30.2608, 120.1468],
  },
  "京都": {
    "清水寺": [34.9949, 135.785], "伏见稻荷": [34.9671, 135.7727], "金阁寺": [35.0394, 135.7292],
    "岚山": [35.0094, 135.6773], "祇园": [35.0036, 135.7767], "二条城": [35.0142, 135.7482],
  },
};

// 城市视觉配置（品牌色基调 + 图源；图片加载失败自动回退渐变）
const CITY_VISUALS = {
  "巴黎": { en: "Paris", tone: ["#1B2A4A", "#46618C"], img: "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=1600&q=80" },
  "东京": { en: "Tokyo", tone: ["#232338", "#7A5B8C"], img: "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=1600&q=80" },
  "罗马": { en: "Rome", tone: ["#3A2A1D", "#9C7B52"], img: "https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=1600&q=80" },
  "佛罗伦萨": { en: "Florence", tone: ["#3A2A1D", "#9C7B52"], img: "https://images.unsplash.com/photo-1543429257-3b32149be4e4?w=1600&q=80" },
  "威尼斯": { en: "Venice", tone: ["#14304A", "#4E7C9E"], img: "https://images.unsplash.com/photo-1514890547357-a9ee288728e0?w=1600&q=80" },
  "米兰": { en: "Milan", tone: ["#2B2B33", "#7D7D8C"], img: "https://images.unsplash.com/photo-1520170637580-4c1b5a3f8e9c?w=1600&q=80" },
  "巴厘岛": { en: "Bali", tone: ["#143A2E", "#4E8C6E"], img: "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=1600&q=80" },
  "伦敦": { en: "London", tone: ["#1E2A3A", "#5B6E8C"], img: "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=1600&q=80" },
  "纽约": { en: "New York", tone: ["#1F2937", "#64748B"], img: "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=1600&q=80" },
  "京都": { en: "Kyoto", tone: ["#3A2A2A", "#9C6B6B"], img: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=1600&q=80" },
  "大阪": { en: "Osaka", tone: ["#2A2438", "#7B5C9C"], img: "https://images.unsplash.com/photo-1590559899731-a382839e5549?w=1600&q=80" },
  "首尔": { en: "Seoul", tone: ["#1E2E3A", "#4E6E8C"], img: "https://images.unsplash.com/photo-1538485399081-7191377e8241?w=1600&q=80" },
  "曼谷": { en: "Bangkok", tone: ["#3A2A1A", "#9C7B4E"], img: "https://images.unsplash.com/photo-1508009603885-50cf7c579365?w=1600&q=80" },
  "新加坡": { en: "Singapore", tone: ["#0E2E2A", "#3E8C7B"], img: "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?w=1600&q=80" },
  "北京": { en: "Beijing", tone: ["#3A1E1E", "#9C4E4E"], img: "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?w=1600&q=80" },
  "上海": { en: "Shanghai", tone: ["#1E2E3E", "#4E6E9C"], img: "https://images.unsplash.com/photo-1545893835-abaa50cbe628?w=1600&q=80" },
  "杭州": { en: "Hangzhou", tone: ["#1E3A2E", "#4E8C6E"], img: "https://images.unsplash.com/photo-1599571234909-29ed5d1321d6?w=1600&q=80" },
  "成都": { en: "Chengdu", tone: ["#2E1E1E", "#8C4E4E"], img: "https://images.unsplash.com/photo-1612437118782-84bb46a5c95a?w=1600&q=80" },
  "三亚": { en: "Sanya", tone: ["#0E3A4E", "#3E9CBF"], img: "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=1600&q=80" },
  "云南": { en: "Yunnan", tone: ["#1E3A2E", "#4E8C6E"], img: "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1600&q=80" },
  "大理": { en: "Dali", tone: ["#1E3A4E", "#4E8CBF"], img: "https://images.unsplash.com/photo-1528164344705-47542687000d?w=1600&q=80" },
  "丽江": { en: "Lijiang", tone: ["#2E1E2E", "#8C4E8C"], img: "https://images.unsplash.com/photo-1558271736-cd043ef2e855?w=1600&q=80" },
  "青岛": { en: "Qingdao", tone: ["#0E3A4E", "#3E8C9C"], img: "https://images.unsplash.com/photo-1584646098378-0874589d76b1?w=1600&q=80" },
  "厦门": { en: "Xiamen", tone: ["#0E3A4E", "#3E8C9C"], img: "https://images.unsplash.com/photo-1548919973-5cef591cdbc9?w=1600&q=80" },
  "西安": { en: "Xi'an", tone: ["#3A2A1E", "#9C6B4E"], img: "https://images.unsplash.com/photo-1547981609-4b6bfe67ca0b?w=1600&q=80" },
  "重庆": { en: "Chongqing", tone: ["#1E2A3A", "#4E6B8C"], img: "https://images.unsplash.com/photo-1571519511807-95f5e2a0a8e9?w=1600&q=80" },
  "广州": { en: "Guangzhou", tone: ["#1E3A2E", "#4E8C6E"], img: "https://images.unsplash.com/photo-1537531383496-f4749b8032cf?w=1600&q=80" },
  "香港": { en: "Hong Kong", tone: ["#1E2E3A", "#4E6E8C"], img: "https://images.unsplash.com/photo-1506970845244-82f6d9a35a2a?w=1600&q=80" },
  "澳门": { en: "Macau", tone: ["#3A1E2E", "#9C4E8C"], img: "https://images.unsplash.com/photo-1569311504274-5540e984a58d?w=1600&q=80" },
  "台北": { en: "Taipei", tone: ["#1E2E3A", "#4E6E8C"], img: "https://images.unsplash.com/photo-1470004914212-05527e49370b?w=1600&q=80" },
  "柏林": { en: "Berlin", tone: ["#2A2A33", "#7B7B8C"], img: "https://images.unsplash.com/photo-1560969184-10fe8719e047?w=1600&q=80" },
  "慕尼黑": { en: "Munich", tone: ["#1E2E3A", "#4E6E8C"], img: "https://images.unsplash.com/photo-1595867818082-083862f3d630?w=1600&q=80" },
  "瑞士": { en: "Switzerland", tone: ["#1E3A2E", "#4E8C6E"], img: "https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?w=1600&q=80" },
  "巴塞罗那": { en: "Barcelona", tone: ["#3A2A1E", "#9C6B4E"], img: "https://images.unsplash.com/photo-1583422409516-2895a77efded?w=1600&q=80" },
  "马德里": { en: "Madrid", tone: ["#3A2A1E", "#9C6B4E"], img: "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?w=1600&q=80" },
  "阿姆斯特丹": { en: "Amsterdam", tone: ["#1E3A2E", "#4E8C6E"], img: "https://images.unsplash.com/photo-1534351590666-13e3e96b5017?w=1600&q=80" },
  "布拉格": { en: "Prague", tone: ["#3A2A1E", "#9C6B4E"], img: "https://images.unsplash.com/photo-1519677100203-a0e668c92439?w=1600&q=80" },
  "维也纳": { en: "Vienna", tone: ["#2E2E3A", "#7B7B9C"], img: "https://images.unsplash.com/photo-1516550893923-42d28e5677af?w=1600&q=80" },
  "冰岛": { en: "Iceland", tone: ["#1E2E3A", "#4E6E8C"], img: "https://images.unsplash.com/photo-1504893524553-b855bce32c67?w=1600&q=80" },
  "迪拜": { en: "Dubai", tone: ["#3A2A1A", "#9C7B4E"], img: "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1600&q=80" },
  "马尔代夫": { en: "Maldives", tone: ["#0E3A4E", "#3E9CBF"], img: "https://images.unsplash.com/photo-1514282401047-d79a71a590e8?w=1600&q=80" },
  "悉尼": { en: "Sydney", tone: ["#0E3A4E", "#3E9CBF"], img: "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?w=1600&q=80" },
  "旧金山": { en: "San Francisco", tone: ["#2E1E3A", "#7B4E9C"], img: "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=1600&q=80" },
  "洛杉矶": { en: "Los Angeles", tone: ["#3A2A1E", "#9C7B4E"], img: "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=1600&q=80" },
  "夏威夷": { en: "Hawaii", tone: ["#0E3A4E", "#3E9CBF"], img: "https://images.unsplash.com/photo-1505852679233-d9fd70aff56d?w=1600&q=80" },
};

const CN_NUM = { "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15 };

function findCity(md) {
  // 1) 标题/首段箭头模式：XX → YY，取终点城市（出发地 → 目的地）
  const head = md.split("\n").slice(0, 6).join("\n");
  const arrowLine = head.match(/[^\n]*(?:→|\u2192)[^\n]*/);
  if (arrowLine) {
    const dest = arrowLine[0].split(/[→\u2192]/).pop().trim();
    const c = CITY_LIST.find((x) => dest.includes(x) || x.includes(dest));
    if (c) return c;
  }
  // 2) 统计全篇出现次数，目的地城市会被反复提及（DAY 标题、景点描述）
  let best = "";
  let bestN = 0;
  for (const c of CITY_LIST) {
    const n = md.split(c).length - 1;
    if (n === 0) continue;
    // 平局时优先标题区域出现过的城市
    if (n > bestN || (n === bestN && !head.includes(best) && head.includes(c))) {
      best = c;
      bestN = n;
    }
  }
  return best;
}

function findDuration(md) {
  // "5天" / "五天" / "DAY 1" 最大天数 / "3日游"
  let m = md.match(/(\d{1,2})\s*天/);
  if (m) return parseInt(m[1], 10);
  m = md.match(/([一二三四五六七八九十]{1,3})\s*天/);
  if (m && CN_NUM[m[1]]) return CN_NUM[m[1]];
  m = md.match(/(\d{1,2})\s*日游/);
  if (m) return parseInt(m[1], 10);
  // Day 标题最大编号
  let maxDay = 0;
  const re = /DAY\s*(\d{1,2})/gi;
  let mm;
  while ((mm = re.exec(md))) maxDay = Math.max(maxDay, parseInt(mm[1], 10));
  if (maxDay > 0) return maxDay;
  return "";
}

function pad2(n) {
  return String(n).padStart(2, "0");
}

// 从计划正文里找具体出发日期：2026-11-25 / 2026年11月25日 / 11月25日
function findStartDate(md) {
  const full = md.match(/(20\d{2})\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})/);
  if (full) return `${full[1]}-${pad2(full[2])}-${pad2(full[3])}`;
  const short = md.match(/(\d{1,2})\s*月\s*(\d{1,2})\s*日/);
  if (short) return `${new Date().getFullYear()}-${pad2(short[1])}-${pad2(short[2])}`;
  return "";
}

// 第 n 天的日期（用于每日行程展示）；没有出发日期时返回空串
export function formatDayDate(startDate, dayNum) {
  if (!startDate) return "";
  const d = new Date(`${startDate}T00:00:00`);
  if (Number.isNaN(d.getTime())) return "";
  d.setDate(d.getDate() + (dayNum - 1));
  return `${d.getMonth() + 1}.${pad2(d.getDate())}`;
}

export function formatStartDate(startDate, month) {
  if (startDate) {
    const d = new Date(`${startDate}T00:00:00`);
    if (!Number.isNaN(d.getTime())) {
      return `${d.getMonth() + 1}月${d.getDate()}日`;
    }
  }
  return month || "";
}

function findMonth(md) {
  const m = md.match(/(\d{1,2})\s*月/);
  if (m) return `${parseInt(m[1], 10)}月`;
  const seasons = { "春": "春季", "夏": "夏季", "秋": "秋季", "冬": "冬季" };
  for (const [k, v] of Object.entries(seasons)) {
    if (md.includes(k + "季") || md.includes(k + "天")) return v;
  }
  return "";
}

function findBudget(md) {
  // 预算字段只出现在文档头部的「预算：」字段行（提取摘要/计划头部），
  // 只扫描前 15 行且要求“预算：”冒号格式 ——
  // 避免把预算汇总表/分项预算（住宿预算/弹性预算/总计）误当用户给出的预算
  const lines = md.split("\n").slice(0, 15);
  for (const line of lines) {
    if (/预算/.test(line)) {
      // 优先取“预算：”之后紧跟的数字，避免误匹配“6月出发”中的月份；
      // 支持“1.5万”“2万”等带“万”的表述（万单位 ×10000）
      const m = line.match(/预算[:：][^\d]{0,8}(\d[\d,，.]*)\s*(万)?\s*(?:元|¥|￥|块)?/);
      if (m) {
        const num = parseFloat(m[1].replace(/[,，]/g, ""));
        if (!isNaN(num)) {
          const amount = m[2] ? Math.round(num * 10000) : num;
          // 防御 LLM 幻觉金额（如用户没给预算却被编造成"2元"）：
          // 明显不合理的金额（<100元）视为无效，不采用
          return amount >= 100 ? amount : null;
        }
      }
    }
  }
  return null;
}

function findStyles(md) {
  const dict = ["艺术","美食","历史","博物馆","自然","海滩","海岛","购物","文化","亲子","蜜月",
    "摄影","户外","徒步","滑雪","温泉","夜生活","美食探店","建筑","音乐","动漫","街头","宗教","古城"];
  const styles = [];
  for (const s of dict) {
    if (md.includes(s)) styles.push(s);
  }
  return styles.slice(0, 4);
}

// 将行程 Markdown 切分为 Day 块
function splitDays(md) {
  // 注意：中文分支不能用 \b（CJK 字符非单词字符，\b 永远匹配失败），
  // 仅保留在 DAY 数字分支上；用 (?!天) 防止“第10天”被“第1天”误切。
  const re = /^#{1,4}\s*(?:DAY\s*(\d{1,2})\b|第\s*([一二三四五六七八九十\d]{1,3})\s*天(?![一二三四五六七八九十\d]))[：:.\s]*(.*)$/gim;
  const blocks = [];
  let lastIdx = -1;
  let lastRest = "";
  let m;
  while ((m = re.exec(md))) {
    if (lastIdx >= 0) {
      blocks.push({ num: blocks.length ? blocks[blocks.length - 1].num + 1 : 1, title: lastRest, body: md.slice(lastIdx, m.index) });
    }
    const num = m[1] ? parseInt(m[1], 10) : (CN_NUM[m[2]] || blocks.length + 1);
    lastIdx = m.index + m[0].length;
    lastRest = (m[3] || "").trim();
    // 记住标题里的编号（下一段 push 时用）
    blocks._nextNum = num;
    blocks._nextTitle = lastRest;
    blocks._nextStart = m.index + m[0].length;
  }
  if (blocks.length === 0) return [];
  // 最后一块
  blocks.push({ num: blocks._nextNum ?? 1, title: blocks._nextTitle, body: md.slice(blocks._nextStart) });
  delete blocks._nextNum;
  delete blocks._nextTitle;
  delete blocks._nextStart;
  return blocks.map((b, i) => ({ num: b.num || i + 1, title: b.title, body: b.body }));
}

// 从 Day 块中提取景点与时刻
const SCHEDULE_STOP_WORDS = /^(早餐|午餐|晚餐|早午餐|下午茶|夜宵|入住|休息|自由活动|酒店早餐|办理入住|退房|前往|出发|抵达|返程|集合|自由时间|购物时间|休息时间)/;

function parseDayBlock(block) {
  const points = [];
  const schedule = [];
  const lines = block.body.split("\n");

  // 子串去重：已有 POI 与新 POI 互为包含时，保留较长的名称（如“塞纳河散步”优于“塞纳河”）
  function pushPoint(p) {
    for (let i = 0; i < points.length; i++) {
      if (points[i].includes(p)) return;
      if (p.includes(points[i])) {
        points[i] = p;
        return;
      }
    }
    points.push(p);
  }

  // 标题括号内的景点列表：｜东山经典赏枫线（清水寺·永观堂·高台寺）
  const tm = (block.title || "").match(/[（(]([^）)]{1,60})[）)]/);
  if (tm) {
    for (const p of tm[1].split(/[·、,，/]+/).map((s) => s.trim()).filter((s) => s.length >= 2 && s.length <= 12)) {
      pushPoint(p);
    }
  }

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    // 遇到下一个章节标题 → 结束当前 Day 块（块体可能延伸到酒店/餐厅等章节）
    if (/^#{1,4}\s/.test(line)) break;
    // 跳过表格行
    if (line.startsWith("|")) continue;

    // 时刻表：09:30 - 卢浮宫 / 09:30 卢浮宫 / 09:30~11:00 卢浮宫
    const t = line.match(/^(\d{1,2})[:：](\d{2})\s*(?:[-–—~至到]\s*(\d{1,2})[:：](\d{2})\s*)?[·.\s─—–-]*(.+)$/);
    if (t) {
      const item = t[5].replace(/^[-–—─→\s]+/, "").trim();
      if (item) {
        schedule.push({ time: `${t[1]}:${t[2]}`, item });
        // 时刻中的地点也作为 POI（过滤明显的非地点条目）
        if (item.length <= 30 && !SCHEDULE_STOP_WORDS.test(item)) {
          pushPoint(item);
        }
      }
      continue;
    }

    // 行程 Agent 时段条目：- **上午（9:00-12:00）**：[景点名] —— [描述] | 门票约￥X
    // 或 - **午餐（12:00-13:30）**：[餐厅名] | 菜系：法餐 | 人均约￥X
    const seg = line.match(/^[-•*]+\s*\**(上午|中午|下午|晚上|晚间|清晨|傍晚|夜间|午餐|晚餐|早餐|早|午|晚|全天)[^：:\n]{0,6}[（(](\d{1,2})[:：](\d{2})(?:\s*[-–—~至]\s*\d{1,2}[:：]\d{2})?[)）]\**\s*[：:]\s*([\s\S]*)$/);
    if (seg) {
      const time = `${seg[2]}:${seg[3]}`;
      // 提取行首方括号中的地点/餐厅名（[卢浮宫] → 卢浮宫）
      const nm = (seg[4] || "").match(/^[\[【]([^\]】]{1,30})[\]】]/);
      let name = nm ? nm[1].replace(/\*\*/g, "").trim() : "";
      let item = (seg[4] || "").replace(/^[\[【]([^\]】]{1,30})[\]】]/, "$1").trim();
      if (!name && item) {
        const head = item.split(/[——–—|｜]/)[0].trim();
        if (head && head.length <= 24 && !SCHEDULE_STOP_WORDS.test(head)) name = head;
      }
      if (item) schedule.push({ time, item: item.length > 80 ? item.slice(0, 80) : item });
      if (name && !SCHEDULE_STOP_WORDS.test(name)) pushPoint(name);
      // 条目内带箭头路线时，箭头各段也作为 POI
      if (item.includes("→")) {
        for (const pp of item.split(/[→\u2192]+/).map((s) => s.trim()).filter(Boolean)) {
          const head2 = pp.split(/[——–—|｜]/)[0].trim();
          if (head2 && head2.length <= 24 && !SCHEDULE_STOP_WORDS.test(head2)) pushPoint(head2);
        }
      }
      continue;
    }

    // 箭头路线：卢浮宫 → 杜乐丽花园 → 塞纳河
    if (line.includes("→")) {
      const parts = line.split(/[→\u2192]+/).map((s) => s.trim()).filter(Boolean);
      if (parts.length > 1) {
        for (const p of parts) {
          pushPoint(p);
        }
        continue;
      }
    }

    // 列表项 / 短条目（剥离行首标记，过滤叙述句）
    const stripped = line
      .replace(/^[-•*\d]+[.、)）]\s*/, "")
      .replace(/^[-•*]\s+/, "")
      .trim();
    // 优先取粗体短语作为候选地点名（**岚山竹林**（描述）→ 岚山竹林）
    const bold = stripped.match(/^\*\*([^*]{1,30})\*\*/);
    let candidate = bold ? bold[1].trim() : stripped;
    // 时段词开头的行取第二个粗体（- **上午**：**岚山竹林**（…））
    if (/^(上午|中午|下午|晚上|晚间|清晨|傍晚|夜间|午餐|晚餐|早餐|早|午|晚|全天)$/.test(candidate)) {
      const b2 = stripped.match(/^\*\*[^*]{1,30}\*\*\s*[：:]\s*\*+([^*\n]{1,30})\*+/);
      candidate = b2 ? b2[1].trim() : "";
    }
    // 截断管道后缀（东福寺站 | 约¥30 → 东福寺站）
    candidate = candidate.split(/[|｜]/)[0].trim();
    // 非地点元信息行过滤（当日预估/费用/交通等）
    if (/^(当日|本日|每日|总)?(预估|预算|费用|花费|消费|小计|合计|总计|备注|提示|注意|贴士|交通|门票|住宿|餐饮)([:：]|$)/.test(candidate)) continue;
    if (
      candidate.length > 2 &&
      candidate.length <= 24 &&
      !/[。，；！？,;!?]/.test(candidate) &&
      !/^[#>\u2192]/.test(candidate)
    ) {
      pushPoint(candidate);
    }
  }
  return { points: points.slice(0, 10), schedule: schedule.slice(0, 14) };
}

function parseBudgetItems(md) {
  const items = [];
  const labels = ["交通","机票","航班","市内交通","接送机","住宿","酒店","餐饮","美食","门票","购物","娱乐","签证","保险","其他"];
  const lines = md.split("\n");
  let inBudgetSection = false;
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    // 章节切换：只在「预算汇总/费用」类章节内提取，
    // 避免误收天气表、航班表、每日行程「当日预估」「住宿预算建议」等正文数字
    if (/^#{1,4}\s/.test(line)) {
      inBudgetSection = /预算汇总|预算概览|预算表|预算明细|费用|开销|花费|总预算/.test(line);
      continue;
    }
    if (!inBudgetSection) continue;
    // 仅接受表格行（| 交通 | 地铁 | ￥300 |）或列表行（- **交通**：约￥300）
    const isTable = line.startsWith("|");
    const isList = /^[-•*]\s/.test(line) || /^\d+[.、)]\s/.test(line);
    if (!isTable && !isList) continue;
    // 剥离列表标记与粗体
    let body = line;
    if (isList) body = body.replace(/^[-•*\d]+[.、)）]\s*/, "").replace(/^[-•*]\s+/, "");
    body = body.replace(/\*\*/g, "").trim();
    if (/^[-:\s|]+$/.test(body)) continue; // 表头分隔行
    const cells = body.split("|").map((c) => c.trim()).filter(Boolean);
    const labelCell = cells[0] || body;
    let label = labels.find((l) => labelCell.includes(l));
    if (!label || /总计|合计|总预算/.test(labelCell)) continue;
    if (label === "酒店") label = "住宿"; // 同义类别合并，避免预算条重复
    const numSrc = cells.length >= 2 ? cells.slice(1).join(" ") : body;
    // 优先提取货币金额（¥2,200 / ￥600 / 800元），避免"75分钟"类干扰数字
    let m = numSrc.match(/[¥￥]\s*(\d[\d,，.]*)|(\d[\d,，]*)\s*元/);
    if (!m) m = numSrc.match(/(\d[\d,，.]*)/);
    if (!m) continue;
    const amount = parseInt((m[1] || m[2]).replace(/[,，.]/g, ""), 10);
    if (!isNaN(amount) && amount > 0) {
      items.push({ label, amount });
    }
  }
  // 去重（同 label 保留第一个）
  const seen = new Set();
  return items.filter((it) => {
    if (seen.has(it.label)) return false;
    seen.add(it.label);
    return true;
  });
}

function parseSection(md, keywords, max = 4) {
  const result = [];
  const pushItem = (name, detail, priceSrc) => {
    if (!name || result.some((r) => r.name === name)) return;
    const price = priceSrc && priceSrc.match(/[¥￥]\s*([\d,，.]+)/);
    result.push({ name, detail: detail || name, price: price ? price[1].replace(/[,，]/g, "") : null });
  };
  const lines = md.split("\n");
  let inSection = false;
  for (const raw of lines) {
    const line = raw.trim();
    if (/^#{1,4}\s/.test(line)) {
      if (/^#{1,2}\s/.test(line)) {
        // 一二级标题切换大章节
        inSection = keywords.some((k) => line.includes(k));
      }
      // ### 及以下子标题属于当前章节内部（如「推荐区域/经济型选择」），不结束章节
      continue;
    }
    if (!inSection || !line) continue;
    // 引用行（> 说明/免责声明）与分隔线不作为推荐条目
    if (line.startsWith(">") || /^-{3,}$/.test(line)) continue;
    // 预算建议类小节与冒号结尾的引导行不是推荐条目
    if (/预算建议|推荐首选|结合总预算|推荐方案|升级方案/.test(line)) continue;
    if (/[:：]$/.test(line)) continue;
    // 区域介绍类描述行（**大东海**：距市区最近…），非列表且无价格，不作为推荐条目
    if (!/^(?:[-•]\s|\d+[.、)）])/.test(line) && /^\*\*[^*]{2,12}\*\*[:：]/.test(line) && !/[¥￥]/.test(line)) continue;
    if (line.startsWith("|")) {
      // 表格行：首列为名称，价格从其余列提取（住宿/餐厅推荐常用表格）
      const cells = line.split("|").map((c) => c.replace(/\*/g, "").trim()).filter(Boolean);
      if (cells.length < 2) continue;
      if (cells.some((c) => /^[-:]+$/.test(c))) continue; // 表头分隔行
      const name = cells[0].replace(/[《》「」""]/g, "");
      if (!name || /酒店名|餐厅名|景点名|名称/.test(name)) continue; // 表头
      if (name.length > 3 && name.length < 40) pushItem(name, cells[cells.length - 1], cells.slice(1).join(" "));
      if (result.length >= max) break;
      continue;
    }
    // 剥离列表标记（- / • / 1. 等）+ Markdown 加粗/标题残留（如 **xxx** / ####）
    const stripped = line
      .replace(/^[-•*\d]+[.、)）]\s*/, "")
      .replace(/^[-•*]\s+/, "")
      .replace(/^#{1,6}\s*/, "")
      .replace(/\*{1,2}([^*]*)\*{1,2}/g, "$1")
      .replace(/\*+/g, "")
      .trim();
    if (!stripped) continue;
    const item = stripped.replace(/[《》「」""]/g, "");
    if (item.length > 3 && item.length < 80) {
      // 提取价格
      const price = item.match(/[¥￥]\s*([\d,，.]+)|\b(\d[\d,，]*)\s*元/);
      const name = item.split(/[¥￥·|｜,，—–-]/)[0].trim();
      // detail 去掉与 name 重复的前缀
      let detail = item;
      if (name && item.startsWith(name)) {
        detail = item.slice(name.length).replace(/^[·|｜,，:：\s]+/, "");
      }
      if (name) pushItem(name, detail || item, price ? (price[1] || price[2]) : null);
    }
    if (result.length >= max) break;
  }
  return result;
}

export function parsePlan(md) {
  if (!md || typeof md !== "string") return null;
  const city = findCity(md);
  const days = splitDays(md).map((b) => {
    const parsed = parseDayBlock(b);
    return { num: b.num, title: b.title, points: parsed.points, schedule: parsed.schedule };
  });
  const budgetItems = parseBudgetItems(md);
  const budgetTotal = budgetItems.reduce((s, it) => s + it.amount, 0);
  return {
    city,
    duration: findDuration(md),
    month: findMonth(md),
    startDate: findStartDate(md),
    budget: findBudget(md) || null,  // 用户给出的具体预算；未给出时为 null（不拿方案总计顶替）
    styles: findStyles(md),
    days,
    budgetItems,
    budgetTotal: budgetTotal || null,
    hotels: parseSection(md, ["住宿", "酒店推荐", "酒店"], 3),
    restaurants: parseSection(md, ["餐厅", "美食推荐", "餐饮推荐"], 4),
    attractions: parseSection(md, ["景点推荐", "必去景点", "推荐景点"], 6),
    hasDays: days.length > 0,
    raw: md,
  };
}

// 城市视觉信息（图片失败时前端回退到 tone 渐变）
export function getCityVisual(city) {
  return CITY_VISUALS[city] || { en: "", tone: ["#1E3A5F", "#5B7C99"], img: "" };
}

// 确定性哈希 → 稳定的示意坐标（用于无地标数据的 POI）
function hashPoint(name, city, seed) {
  let h = 0;
  const s = name + city;
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) % 100000;
  }
  const center = cityCenter(city) || [35, 105];
  const r = 0.012 + (h % 60) / 100000;
  const theta = ((h * 7 + seed * 131) % 360) * Math.PI / 180;
  return [center[0] + r * Math.cos(theta) * 0.55, center[1] + r * Math.sin(theta)];
}

// 返回景点坐标信息：{ lat, lng, exact }
// exact=true 表示内置知名地标精确坐标；false 为确定性哈希近似坐标（可再经百度地理编码修正）
export function getSpotCoordInfo(name, city, seed) {
  const lms = LANDMARKS[city] || {};
  for (const [key, coord] of Object.entries(lms)) {
    if (name.includes(key) || key.includes(name)) {
      return { lat: coord[0], lng: coord[1], exact: true };
    }
  }
  const c = hashPoint(name, city, seed);
  return { lat: c[0], lng: c[1], exact: false };
}

export function getSpotCoords(name, city, seed) {
  const info = getSpotCoordInfo(name, city, seed);
  return [info.lat, info.lng];
}

// ── 收藏行程（localStorage）──
const SAVED_KEY = "voyage_saved_trips";

export function getSavedTrips() {
  try {
    return JSON.parse(localStorage.getItem(SAVED_KEY) || "[]");
  } catch {
    return [];
  }
}

export function saveTrip(trip) {
  const list = getSavedTrips().filter((t) => t.raw !== trip.raw);
  list.unshift(trip);
  localStorage.setItem(SAVED_KEY, JSON.stringify(list.slice(0, 20)));
  return list;
}

export function removeSavedTrip(id) {
  const list = getSavedTrips().filter((t) => t.id !== id);
  localStorage.setItem(SAVED_KEY, JSON.stringify(list));
  return list;
}

export function isTripSaved(raw) {
  return getSavedTrips().some((t) => t.raw === raw);
}

// ── 账号行程（后端 SQLite，登录后跨设备可见）──
function authHeaders() {
  const token = localStorage.getItem("travel_token") || "";
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const SERVER_API_BASE = import.meta.env?.VITE_API_BASE || "";

// 后端存的是 plan 原文，这里转成卡片结构；请求失败返回空数组，降级到本地缓存
export async function fetchServerTrips() {
  if (!localStorage.getItem("travel_token")) return [];
  try {
    const res = await fetch(`${SERVER_API_BASE}/api/trips`, { headers: authHeaders() });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.items || []).map((t) => {
      const parsed = parsePlan(t.plan) || {};
      const city = parsed.city || (t.brief && t.brief.destination) || "";
      return {
        id: `srv-${t.id}`,
        serverId: t.id,
        threadId: t.thread_id,
        title: `${city || "行程"}${parsed.duration ? " · " + parsed.duration + "天" : ""}`,
        city,
        createdAt: Date.parse(t.created_at) || 0,
        raw: t.plan,
      };
    });
  } catch {
    return [];
  }
}

export async function deleteServerTrip(serverId) {
  try {
    const res = await fetch(`${SERVER_API_BASE}/api/trips/${serverId}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    return res.ok;
  } catch {
    return false;
  }
}
