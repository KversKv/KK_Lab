// 逻辑冒烟：从生成的 report.html 提取 REPORT_DATA 与 evalRules，验证异常检测
const fs = require("fs");
const s = fs.readFileSync(__dirname + "/report.html", "utf-8");

const dj = s.match(/const REPORT_DATA = (\{"meta"[\s\S]*?\});\r?\n/);
if (!dj) { console.error("REPORT_DATA not found"); process.exit(1); }
const REPORT_DATA = JSON.parse(dj[1]);

const fn = s.match(/function evalRules\(table\) \{[\s\S]*?\n\}/);
if (!fn) { console.error("evalRules not found"); process.exit(1); }
eval(fn[0]);

let bad = 0;
const expect = {
  dcdc_vout_scan: 3,        // 2 处 Diff 跳变 + 首行 diff=0（相对中位步进同为离群）
  dcdc_efficiency: 1,       // 1 个 >100%
  dcdc_switching_freq: 1,   // 0.05kHz 突变
  dcdc_current_limit: 0,    // constant → banner 不计入行异常
};
for (const it of REPORT_DATA.items) {
  const r = it.table ? evalRules(it.table) : {count: 0, banners: []};
  const exp = expect[it.item_key];
  const tag = exp === undefined ? "-" : (r.count === exp ? "OK" : "MISMATCH");
  if (tag === "MISMATCH") bad++;
  console.log(
    (it.item_key + "                    ").slice(0, 32),
    "anom=" + r.count,
    "banners=" + r.banners.length,
    exp === undefined ? "" : "expect=" + exp, tag);
}
// constant 规则应产生 banner
const cl = REPORT_DATA.items.find(i => i.item_key === "dcdc_current_limit");
if (!evalRules(cl.table).banners.length) { console.error("constant banner MISSING"); bad++; }
// 缺字段降级
const meta = REPORT_DATA.meta;
console.log("meta.chip =", meta.chip, "| instruments:", JSON.stringify(meta.instruments));
console.log(bad ? "FAIL " + bad : "ALL_LOGIC_OK");
process.exit(bad ? 1 : 0);
