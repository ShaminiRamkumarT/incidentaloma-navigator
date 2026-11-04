// Usage: python web/parity_export.py > py_out.json && node web/parity_check.js py_out.json
// Compares the browser engine with the Python reader and rules on every report, field by field.
const N = require("./engine.js");
const data = require(require("path").resolve(process.argv[2]));
let bad = 0, n = 0;
for (const r of data) {
  const js = N.extract(r.text).map((f) => { const g = N.classify(f), c = N.concordance(f, g);
    return { ...f, category: g.category, actions: g.actions, status: c.status, severity: c.severity, message: c.message, rationale: g.rationale, notes: g.notes }; });
  if (js.length !== r.py.length) { bad++; console.log(r.id, "count", js.length, r.py.length); continue; }
  r.py.forEach((p, i) => { n++;
    for (const k of Object.keys(p)) {
      if (JSON.stringify(p[k]) !== JSON.stringify(js[i][k])) { bad++; console.log(r.id, i, k, JSON.stringify(p[k]), JSON.stringify(js[i][k])); }
    } });
}
console.log(`${data.length} reports, ${n} findings compared, ${bad} mismatches`);
process.exit(bad ? 1 : 0);
