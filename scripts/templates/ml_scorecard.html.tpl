<title>Rapor Sinyal BUY</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">

<style>
:root{
  color-scheme: light;
  --ground:#f5f7f9; --surface:#ffffff; --surface-2:#eceff4; --surface-3:#e3e8ee;
  --ink:#0f151d; --ink-2:#4b5663; --ink-3:#7a8492;
  --line:#dfe4ea; --line-2:#c6ced8;
  --model:#2a78d6; --model-soft:#9ec5f4; --market:#eb6834;
  --bad:#c8322f; --good:#12855c; --warn:#a06b00;
  --bad-bg:#fbeceb; --good-bg:#e7f6ef; --warn-bg:#fbf3e2;
  --shadow:0 1px 2px rgba(15,21,29,.05), 0 1px 8px rgba(15,21,29,.04);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --ground:#0c1116; --surface:#141a21; --surface-2:#1b222b; --surface-3:#232b35;
    --ink:#edf1f6; --ink-2:#a3aeba; --ink-3:#6c7784;
    --line:#212932; --line-2:#2f3945;
    --model:#3987e5; --model-soft:#1c5cab; --market:#d95926;
    --bad:#e66767; --good:#199e70; --warn:#c98500;
    --bad-bg:#2a1718; --good-bg:#0f2620; --warn-bg:#2a2113;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 1px 8px rgba(0,0,0,.25);
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --ground:#0c1116; --surface:#141a21; --surface-2:#1b222b; --surface-3:#232b35;
  --ink:#edf1f6; --ink-2:#a3aeba; --ink-3:#6c7784;
  --line:#212932; --line-2:#2f3945;
  --model:#3987e5; --model-soft:#1c5cab; --market:#d95926;
  --bad:#e66767; --good:#199e70; --warn:#c98500;
  --bad-bg:#2a1718; --good-bg:#0f2620; --warn-bg:#2a2113;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 1px 8px rgba(0,0,0,.25);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:"Archivo",system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:15px; line-height:1.55; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1160px; margin:0 auto; padding:28px 20px 72px; display:flex; flex-direction:column; gap:26px}
.mono{font-family:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,monospace; font-variant-numeric:tabular-nums}
h1,h2,h3{margin:0; text-wrap:balance; font-weight:600; letter-spacing:-.01em}

/* ---------- header ---------- */
.masthead{display:flex; flex-wrap:wrap; align-items:flex-end; justify-content:space-between; gap:16px 24px;
  padding-bottom:18px; border-bottom:1px solid var(--line)}
.masthead h1{font-size:26px; line-height:1.2}
.eyebrow{font-family:"IBM Plex Mono",monospace; font-size:11px; letter-spacing:.13em;
  text-transform:uppercase; color:var(--ink-3); margin-bottom:7px}
.meta-list{display:flex; flex-wrap:wrap; gap:4px 22px; font-size:12.5px; color:var(--ink-2)}
.meta-list div{display:flex; gap:7px; align-items:baseline}
.meta-list dt{color:var(--ink-3); font-size:11px; letter-spacing:.06em; text-transform:uppercase}

/* ---------- verdict ---------- */
.verdict{background:var(--surface); border:1px solid var(--line); border-radius:12px; box-shadow:var(--shadow);
  padding:24px; display:grid; grid-template-columns:minmax(210px,290px) 1fr; gap:28px; align-items:center}
@media (max-width:760px){.verdict{grid-template-columns:1fr; gap:20px}}
.hero-fig{display:flex; flex-direction:column; gap:2px}
.hero-num{font-family:"IBM Plex Mono",monospace; font-size:66px; line-height:.95; font-weight:600;
  letter-spacing:-.035em; font-variant-numeric:tabular-nums}
.hero-cap{font-size:13px; color:var(--ink-2)}
.hero-sub{font-family:"IBM Plex Mono",monospace; font-size:11.5px; color:var(--ink-3); margin-top:6px}
.verdict-body h2{font-size:17px; margin-bottom:8px}
.verdict-body p{margin:0 0 9px; font-size:14px; color:var(--ink-2); max-width:62ch}
.verdict-body p:last-child{margin-bottom:0}
.verdict-body b{color:var(--ink); font-weight:600}

.chip{display:inline-flex; align-items:center; gap:6px; padding:3px 9px; border-radius:999px;
  font-family:"IBM Plex Mono",monospace; font-size:11.5px; font-weight:500; white-space:nowrap}
.chip.bad{background:var(--bad-bg); color:var(--bad)}
.chip.good{background:var(--good-bg); color:var(--good)}
.chip.warn{background:var(--warn-bg); color:var(--warn)}
.chip.flat{background:var(--surface-2); color:var(--ink-2)}
.chip .dot{width:6px; height:6px; border-radius:50%; background:currentColor; flex:none}

/* ---------- sections ---------- */
section{display:flex; flex-direction:column; gap:14px}
.sec-head{display:flex; flex-wrap:wrap; align-items:baseline; justify-content:space-between; gap:8px 18px}
.sec-head h2{font-size:15.5px}
.sec-head p{margin:0; font-size:12.5px; color:var(--ink-3); max-width:64ch}
.card{background:var(--surface); border:1px solid var(--line); border-radius:12px; box-shadow:var(--shadow); padding:20px}

/* ---------- kpi ---------- */
.kpis{display:grid; grid-template-columns:repeat(auto-fit,minmax(212px,1fr)); gap:12px}
.kpi{background:var(--surface); border:1px solid var(--line); border-radius:12px; box-shadow:var(--shadow);
  padding:16px 16px 14px; display:flex; flex-direction:column; gap:11px}
.kpi-top{display:flex; align-items:baseline; justify-content:space-between; gap:8px}
.kpi-hz{font-family:"IBM Plex Mono",monospace; font-size:13px; font-weight:600; letter-spacing:.02em}
.kpi-thr{font-family:"IBM Plex Mono",monospace; font-size:10.5px; color:var(--ink-3)}
.kpi-val{font-family:"IBM Plex Mono",monospace; font-size:32px; font-weight:600; line-height:1;
  letter-spacing:-.03em; font-variant-numeric:tabular-nums}
.kpi-ci{font-family:"IBM Plex Mono",monospace; font-size:11px; color:var(--ink-3); margin-left:5px; font-weight:400}
.pairbar{display:flex; flex-direction:column; gap:5px}
.pairbar-row{display:grid; grid-template-columns:52px 1fr 44px; align-items:center; gap:8px}
.pairbar-lab{font-family:"IBM Plex Mono",monospace; font-size:10px; color:var(--ink-3); letter-spacing:.03em}
.pairbar-track{height:7px; background:var(--surface-2); border-radius:4px; overflow:hidden}
.pairbar-fill{height:100%; border-radius:4px}
.pairbar-num{font-family:"IBM Plex Mono",monospace; font-size:11px; text-align:right; color:var(--ink-2)}
.kpi-foot{display:flex; flex-wrap:wrap; gap:6px; align-items:center; padding-top:3px;
  border-top:1px solid var(--line); font-family:"IBM Plex Mono",monospace; font-size:10.5px; color:var(--ink-3)}

/* ---------- charts ---------- */
.chart-wrap{overflow-x:auto}
svg{display:block; max-width:100%; height:auto}
svg text{font-family:"IBM Plex Mono",monospace; font-variant-numeric:tabular-nums}
.legend{display:flex; flex-wrap:wrap; gap:6px 18px; align-items:center;
  font-family:"IBM Plex Mono",monospace; font-size:11.5px; color:var(--ink-2)}
.legend span{display:inline-flex; align-items:center; gap:7px}
.swatch{width:11px; height:11px; border-radius:3px; flex:none}
.swatch.line{height:3px; border-radius:2px; width:15px}

.seg{display:inline-flex; background:var(--surface-2); border-radius:8px; padding:2px; gap:2px}
.seg button{font-family:"IBM Plex Mono",monospace; font-size:11.5px; font-weight:500; color:var(--ink-2);
  background:none; border:0; padding:5px 11px; border-radius:6px; cursor:pointer}
.seg button:hover{color:var(--ink)}
.seg button[aria-pressed="true"]{background:var(--surface); color:var(--ink); box-shadow:var(--shadow)}
.seg button:focus-visible{outline:2px solid var(--model); outline-offset:1px}

#tip{position:fixed; z-index:50; pointer-events:none; opacity:0; transition:opacity .1s;
  background:var(--surface); border:1px solid var(--line-2); border-radius:8px; padding:8px 10px;
  box-shadow:0 4px 16px rgba(0,0,0,.16); font-family:"IBM Plex Mono",monospace; font-size:11.5px;
  color:var(--ink); max-width:230px}
#tip.on{opacity:1}
#tip .tip-t{font-weight:600; margin-bottom:4px}
#tip .tip-r{display:flex; justify-content:space-between; gap:12px; color:var(--ink-2)}
#tip .tip-r b{color:var(--ink); font-weight:500}

/* ---------- tables ---------- */
.tbl-wrap{overflow-x:auto; border:1px solid var(--line); border-radius:12px; background:var(--surface);
  box-shadow:var(--shadow)}
table{border-collapse:collapse; width:100%; font-size:13px}
th,td{padding:9px 14px; text-align:left; border-bottom:1px solid var(--line); white-space:nowrap}
th{font-family:"IBM Plex Mono",monospace; font-size:10.5px; letter-spacing:.07em; text-transform:uppercase;
  color:var(--ink-3); font-weight:500; background:var(--surface-2); position:sticky; top:0}
tbody tr:last-child td{border-bottom:0}
td.num{font-family:"IBM Plex Mono",monospace; text-align:right; font-variant-numeric:tabular-nums}
.scroll-y{max-height:340px; overflow-y:auto}
.minibar{display:inline-block; height:6px; border-radius:3px; background:var(--model); vertical-align:middle}

/* ---------- integrity log ---------- */
.fixes{display:flex; flex-direction:column; gap:0}
.fix{display:grid; grid-template-columns:26px 1fr; gap:14px; padding:15px 0; border-bottom:1px solid var(--line)}
.fix:last-child{border-bottom:0}
.fix:first-child{padding-top:0}
.fix-n{font-family:"IBM Plex Mono",monospace; font-size:11px; color:var(--ink-3); padding-top:2px}
.fix h3{font-size:13.5px; margin-bottom:5px}
.fix p{margin:0 0 7px; font-size:13px; color:var(--ink-2); max-width:74ch}
.fix p:last-child{margin-bottom:0}
.fix code, .inline-code{font-family:"IBM Plex Mono",monospace; font-size:12px;
  background:var(--surface-2); padding:1px 5px; border-radius:4px; color:var(--ink)}
.fix-meta{display:flex; flex-wrap:wrap; gap:6px; margin-top:8px}

pre.cmd{margin:0; background:var(--surface-2); border:1px solid var(--line); border-radius:8px;
  padding:11px 13px; overflow-x:auto; font-family:"IBM Plex Mono",monospace; font-size:12px; color:var(--ink)}
footer{border-top:1px solid var(--line); padding-top:18px; display:flex; flex-direction:column; gap:11px}
footer p{margin:0; font-size:12.5px; color:var(--ink-3); max-width:76ch}
.caveat{border-left:2px solid var(--warn); padding-left:13px; font-size:13px; color:var(--ink-2)}
@media (prefers-reduced-motion:reduce){*{transition:none!important; animation:none!important}}
</style>

<div class="wrap">
  <header class="masthead">
    <div>
      <div class="eyebrow">Scorecard model ML · IDX</div>
      <h1>Rapor Sinyal BUY</h1>
    </div>
    <dl class="meta-list" id="meta"></dl>
  </header>

  <div class="verdict" id="verdict"></div>

  <section>
    <div class="sec-head">
      <h2>Per horizon</h2>
      <p>Win rate dihitung hanya dari sinyal yang benar-benar bilang BELI, dengan
         threshold yang sama seperti label training. Base rate = berapa persen seluruh
         saham yang naik di atas threshold itu pada periode yang sama.</p>
    </div>
    <div class="kpis" id="kpis"></div>
  </section>

  <section>
    <div class="sec-head">
      <h2>Edge harian: model vs pasar</h2>
      <p>Tiap titik satu hari bursa untuk satu horizon. Garis diagonal = win rate model
         persis sama dengan breadth pasar hari itu. Titik di atas garis berarti model
         menambah nilai; menempel di garis berarti tidak.</p>
    </div>
    <div class="card">
      <div class="chart-wrap"><svg id="scatter" viewBox="0 0 720 400" role="img"
        aria-label="Sebaran win rate sinyal BUY harian terhadap base rate pasar harian"></svg></div>
      <div class="legend" style="margin-top:12px">
        <span><i class="swatch" style="background:var(--model)"></i>hari bursa (ukuran titik = jumlah sinyal BUY)</span>
        <span><i class="swatch line" style="background:var(--ink-3)"></i>win rate = base rate</span>
      </div>
    </div>
  </section>

  <section>
    <div class="sec-head">
      <h2>Runtutan harian</h2>
      <div class="seg" id="hzseg" role="group" aria-label="Pilih horizon"></div>
    </div>
    <div class="card">
      <div class="chart-wrap"><svg id="lines" viewBox="0 0 720 320" role="img"
        aria-label="Win rate sinyal BUY dan base rate pasar per hari bursa"></svg></div>
      <div class="legend" style="margin-top:12px">
        <span><i class="swatch line" style="background:var(--model)"></i>win rate sinyal BUY</span>
        <span><i class="swatch line" style="background:var(--market)"></i>base rate pasar</span>
      </div>
    </div>
  </section>

  <section>
    <div class="sec-head">
      <h2>Holdout vs kenyataan</h2>
      <p>Edge yang dijanjikan test split saat training, dibanding edge yang benar-benar
         terjadi di log live. Kalau dua titiknya jauh, test split-nya bocor.</p>
    </div>
    <div class="card">
      <div class="chart-wrap"><svg id="dumbbell" viewBox="0 0 720 240" role="img"
        aria-label="Perbandingan edge holdout dan edge live per horizon"></svg></div>
      <div class="legend" style="margin-top:12px">
        <span><i class="swatch" style="background:var(--model-soft)"></i>edge holdout (saat training)</span>
        <span><i class="swatch" style="background:var(--model)"></i>edge live (log nyata)</span>
        <span><i class="swatch line" style="background:var(--ink-3)"></i>nol — tidak ada edge</span>
      </div>
    </div>
  </section>

  <section>
    <div class="sec-head">
      <h2>Cakupan model</h2>
      <p>Berapa banyak model per-ticker yang benar-benar punya sinyal. Model degenerate
         tetap ikut dipakai di prediksi harian, tapi tidak menyumbang informasi apa pun.</p>
    </div>
    <div class="card"><div id="coverage" style="display:flex; flex-direction:column; gap:13px"></div></div>
  </section>

  <section>
    <div class="sec-head">
      <h2>Per ticker</h2>
      <p>Minimal 5 sinyal BUY dalam periode. Sampel per ticker kecil — baca sebagai
         petunjuk arah, bukan bukti.</p>
    </div>
    <div class="tbl-wrap scroll-y">
      <table><thead><tr>
        <th>Ticker</th><th style="text-align:right">Sinyal BUY</th>
        <th style="text-align:right">Win rate</th><th style="width:44%">&nbsp;</th>
      </tr></thead><tbody id="tickers"></tbody></table>
    </div>
  </section>

  <section>
    <div class="sec-head">
      <h2>Perbaikan metrik</h2>
      <p>Empat cacat yang bikin angka lama tidak bisa dibandingkan dengan apa pun.
         Semua sudah diperbaiki, dan seluruh log divalidasi ulang.</p>
    </div>
    <div class="card"><div class="fixes">
      <article class="fix">
        <div class="fix-n mono">01</div>
        <div>
          <h3>Label validasi tidak sama dengan label training</h3>
          <p>Model dilatih memprediksi kenaikan di <b>atas threshold</b> — 1d +0,6%,
             3d +1,8%, 5d +2,5%, 7d +3,0% — tapi validator menilai benar/salah dengan
             <code>actual_return &gt; 0</code>. Sinyal 5d yang naik +0,3% dihitung menang,
             padahal bagi model itu label 0.</p>
          <p>Threshold sekarang dibaca dari <code>TARGET_THRESHOLDS</code>, satu konstanta
             yang dipakai bareng oleh pembuat label training dan validator.</p>
          <div class="fix-meta"><span class="chip flat"><i class="dot"></i>data/ml_features.py</span>
            <span class="chip flat"><i class="dot"></i>scripts/cron_ml_validate.py</span></div>
        </div>
      </article>
      <article class="fix">
        <div class="fix-n mono">02</div>
        <div>
          <h3>Horizon 3d/5d/7d diukur satu hari terlalu panjang</h3>
          <p>Validator memakai <code>index &gt; trade_date</code> lalu <code>iloc[days-1]</code>,
             sementara base close diambil dari hari <b>sebelum</b> trade_date. Akibatnya 3d
             sebenarnya diukur sepanjang 4 hari bursa, 5d jadi 6, 7d jadi 8. Dari 400 sampel
             yang diuji, 301 cocok dengan pola off-by-one ini.</p>
          <p>Semua horizon sekarang lewat satu helper <code>resolve_window()</code> yang
             hasilnya sudah diuji cocok persis dengan <code>Close.shift(-N)</code> di training.</p>
          <div class="fix-meta"><span class="chip flat"><i class="dot"></i>scripts/cron_ml_validate.py</span></div>
        </div>
      </article>
      <article class="fix">
        <div class="fix-n mono">03</div>
        <div>
          <h3>API menimpa verdict yang tersimpan</h3>
          <p>Endpoint akurasi memakai <code>is_correct is True or actual_return &gt; 0</code>.
             Cabang <code>or</code> itu membatalkan verdict yang sudah dihitung: baris dengan
             <code>is_correct=False</code> tapi return +0,3% tampil <b>BENAR</b> di UI.
             1.873 baris salah tampil.</p>
          <p><code>is_correct</code> sekarang jadi satu-satunya sumber kebenaran.</p>
          <div class="fix-meta"><span class="chip flat"><i class="dot"></i>web-backend/main.py</span></div>
        </div>
      </article>
      <article class="fix">
        <div class="fix-n mono">04</div>
        <div>
          <h3>Verdict historis berubah setiap kali model diretrain</h3>
          <p>Validator menurunkan ulang keputusan BUY dari <code>predictor.thresholds</code>
             yang dibaca fresh dari disk. Setelah retrain, threshold bergeser: 272 dari 1.950
             baris punya keputusan BUY yang berbeda dari yang tercatat. Untuk baris yang
             tercatat NAIK tapi threshold baru bilang bukan-BUY, aturan penilaian ikut
             <b>terbalik</b> — sinyal BUY yang rugi malah ditandai benar.</p>
          <p>Keputusan BUY sekarang dibaca dari kolom <code>predicted_direction</code> —
             apa yang benar-benar diputuskan saat itu — sehingga log kembali jadi audit trail.</p>
          <div class="fix-meta"><span class="chip flat"><i class="dot"></i>scripts/cron_ml_validate.py</span></div>
        </div>
      </article>
    </div></div>
  </section>

  <footer>
    <p class="caveat" id="caveat"></p>
    <p>Halaman ini di-generate dari <span class="inline-code">ml_prediction_log</span>. Untuk memperbaruinya:</p>
    <pre class="cmd">docker exec -w /app stock_app python scripts/cron_ml_validate.py
docker exec -w /app stock_app python scripts/ml_scorecard.py --days 14 --out scratch/ml_scorecard.html</pre>
    <p id="stamp"></p>
  </footer>
</div>

<div id="tip" role="status" aria-live="polite"></div>

<script>
const DATA = /*__SCORECARD_DATA__*/;

/* ---------- helpers ---------- */
const $ = s => document.querySelector(s);
const pct = (v, d = 1) => v == null ? "–" : v.toFixed(d) + "%";
const pp = (v, d = 1) => v == null ? "–" : (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(d) + "pp";
const num = v => v == null ? "–" : v.toLocaleString("id-ID");
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* Edge dianggap "tidak ada" kalau lebih kecil dari ketidakpastian sampelnya.
   Tanpa ambang ini, +2,8pp dari 93 sinyal (CI ±9,7) terbaca seperti temuan. */
function edgeVerdict(edge, ci) {
  if (edge == null) return { cls: "flat", txt: "data kurang" };
  if (ci != null && Math.abs(edge) < ci) return { cls: "flat", txt: "dalam derau" };
  return edge > 0 ? { cls: "good", txt: "ada edge" } : { cls: "bad", txt: "edge negatif" };
}

/* ---------- tooltip ---------- */
const tip = $("#tip");
function showTip(e, title, rows) {
  tip.innerHTML = `<div class="tip-t">${esc(title)}</div>` +
    rows.map(([k, v]) => `<div class="tip-r"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join("");
  tip.classList.add("on");
  moveTip(e);
}
function moveTip(e) {
  const r = tip.getBoundingClientRect();
  let x = e.clientX + 14, y = e.clientY + 14;
  if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 14;
  if (y + r.height > innerHeight - 8) y = e.clientY - r.height - 14;
  tip.style.left = Math.max(8, x) + "px";
  tip.style.top = Math.max(8, y) + "px";
}
const hideTip = () => tip.classList.remove("on");
function bindTip(el, title, rows) {
  el.addEventListener("pointerenter", e => showTip(e, title, rows));
  el.addEventListener("pointermove", moveTip);
  el.addEventListener("pointerleave", hideTip);
}

/* ---------- svg builder ---------- */
const NS = "http://www.w3.org/2000/svg";
// fill & stroke go through inline style, not attributes: SVG presentation
// attributes do not resolve var(), so a themed color set as an attribute would
// freeze at load and the chart would keep light colors after a theme switch.
const STYLE_PROPS = new Set(["fill", "stroke"]);
function mk(tag, attrs = {}, parent) {
  const el = document.createElementNS(NS, tag);
  for (const k in attrs) {
    if (attrs[k] == null) continue;
    if (STYLE_PROPS.has(k)) el.style.setProperty(k, attrs[k]);
    else el.setAttribute(k, attrs[k]);
  }
  if (parent) parent.appendChild(el);
  return el;
}

/* ---------- header + verdict ---------- */
const W = DATA.window, H = DATA.headline, F = DATA.freshness;
$("#meta").innerHTML = [
  ["Periode", `${W.start} → ${W.end}`],
  ["Hari bursa", W.trading_days],
  ["Sinyal BUY", num(H.buy_signals)],
  ["Divalidasi", (F.last_validated || "").slice(0, 16).replace("T", " ")],
].map(([k, v]) => `<div><dt>${esc(k)}</dt><dd class="mono" style="margin:0">${esc(v)}</dd></div>`).join("");

const headEdge = (H.buy_win_rate != null && H.base_rate != null) ? H.buy_win_rate - H.base_rate : null;
const hv = edgeVerdict(headEdge, H.ci);
$("#verdict").innerHTML = `
  <div class="hero-fig">
    <div class="hero-num" style="color:var(--model)">${H.buy_win_rate == null ? "–" : H.buy_win_rate.toFixed(1) + "%"}</div>
    <div class="hero-cap">win rate dari <b>${num(H.buy_signals)}</b> sinyal BUY</div>
    <div class="hero-sub">base rate pasar ${pct(H.base_rate)} · edge ${pp(headEdge)}</div>
  </div>
  <div class="verdict-body">
    <h2>Model belum terbukti punya edge</h2>
    <p>Dari seluruh sinyal BUY dalam periode ini, <b>${pct(H.buy_win_rate)}</b> kena target
       threshold-nya. Pasar secara umum naik di atas threshold yang sama sebanyak
       <b>${pct(H.base_rate)}</b>. Selisihnya <b>${pp(headEdge)}</b>.</p>
    <p>Win rate harian bergerak hampir searah dengan breadth pasar hari itu —
       korelasi <b>${H.pooled_corr == null ? "–" : (H.pooled_corr >= 0 ? "+" : "−") + Math.abs(H.pooled_corr).toFixed(2)}</b>
       dari ${H.corr_days} hari-horizon, rata-rata edge <b>${pp(H.pooled_edge)}</b>. Artinya
       hasil sinyal ditentukan oleh arah pasar, bukan oleh pilihan sahamnya.</p>
    <p>Selisih ${pp(headEdge)} itu lebih kecil dari ketidakpastian sampelnya sendiri
       (±${H.ci == null ? "–" : H.ci.toFixed(1)}pp pada ${num(H.buy_signals)} sinyal), jadi belum bisa
       dibedakan dari nol.</p>
    <div style="display:flex; flex-wrap:wrap; gap:7px; margin-top:12px">
      <span class="chip ${hv.cls}"><i class="dot"></i>${hv.txt}</span>
      <span class="chip flat"><i class="dot"></i>${num(H.matured)} prediksi matang</span>
      <span class="chip warn"><i class="dot"></i>${num(F.pending)} belum matang</span>
    </div>
  </div>`;

$("#caveat").textContent =
  `Sampel per horizon 54–152 sinyal BUY, jadi interval kepercayaan 95%-nya lebar (±8 sampai ±12 poin persen). ` +
  `Angka di halaman ini cukup untuk menyimpulkan "belum terbukti ada edge", tapi belum cukup untuk memberi ` +
  `peringkat antar horizon atau antar ticker. ${num(F.pending)} prediksi sejak ${F.pending_from} belum bisa dinilai ` +
  `karena horizonnya belum lewat — bukan data hilang.`;

$("#stamp").textContent =
  `Data terakhir divalidasi ${(F.last_validated || "").slice(0, 19).replace("T", " ")}. ` +
  `Prediksi terjauh ${F.max_trade_date}. Model dilatih ${(DATA.training.run_date || "").slice(0, 10)} ` +
  `(walk_forward: ${DATA.training.walk_forward}, test_size: ${DATA.training.test_size}).`;

/* ---------- kpi tiles ---------- */
$("#kpis").innerHTML = DATA.horizons.map(h => {
  const v = edgeVerdict(h.edge, h.ci);
  const scale = Math.max(h.buy_win || 0, h.base || 0, 1);
  const bar = (lab, val, color) => `
    <div class="pairbar-row">
      <span class="pairbar-lab">${lab}</span>
      <span class="pairbar-track"><span class="pairbar-fill" style="width:${(100 * (val || 0) / scale).toFixed(1)}%;background:${color}"></span></span>
      <span class="pairbar-num">${pct(val)}</span>
    </div>`;
  return `<article class="kpi">
    <div class="kpi-top">
      <span class="kpi-hz">${h.horizon}</span>
      <span class="kpi-thr">target &gt; +${h.threshold_pct.toFixed(1)}%</span>
    </div>
    <div>
      <span class="kpi-val" style="color:var(--model)">${h.buy_win == null ? "–" : h.buy_win.toFixed(1) + "%"}</span>
      <span class="kpi-ci">±${h.ci == null ? "–" : h.ci.toFixed(1)}</span>
    </div>
    <div class="pairbar">
      ${bar("model", h.buy_win, "var(--model)")}
      ${bar("pasar", h.base, "var(--market)")}
    </div>
    <div class="kpi-foot">
      <span class="chip ${v.cls}"><i class="dot"></i>${pp(h.edge)} · ${v.txt}</span>
      <span>${num(h.buy)} sinyal</span>
    </div>
  </article>`;
}).join("");

/* ---------- scatter: buy win vs base ---------- */
(function () {
  const svg = $("#scatter"), pts = DATA.daily.filter(d => d.base != null);
  const M = { t: 16, r: 18, b: 44, l: 48 }, w = 720, h = 400;
  const px = v => M.l + (v / 100) * (w - M.l - M.r);
  const py = v => h - M.b - (v / 100) * (h - M.t - M.b);

  for (let g = 0; g <= 100; g += 25) {
    mk("line", { x1: px(g), y1: py(0), x2: px(g), y2: py(100), stroke: "var(--line)", "stroke-width": 1 }, svg);
    mk("line", { x1: px(0), y1: py(g), x2: px(100), y2: py(g), stroke: "var(--line)", "stroke-width": 1 }, svg);
    const tx = mk("text", { x: px(g), y: h - M.b + 17, "text-anchor": "middle", "font-size": 10.5, fill: "var(--ink-3)" }, svg);
    tx.textContent = g + "%";
    const ty = mk("text", { x: M.l - 9, y: py(g) + 3.5, "text-anchor": "end", "font-size": 10.5, fill: "var(--ink-3)" }, svg);
    ty.textContent = g + "%";
  }
  // diagonal: win rate == base rate
  mk("line", {
    x1: px(0), y1: py(0), x2: px(100), y2: py(100),
    stroke: "var(--ink-3)", "stroke-width": 2, "stroke-dasharray": "5 4"
  }, svg);
  const dl = mk("text", { x: px(78) + 6, y: py(78) - 8, "font-size": 10.5, fill: "var(--ink-3)" }, svg);
  dl.textContent = "tanpa edge";

  const maxBuy = Math.max(...pts.map(p => p.buy), 1);
  pts.forEach(p => {
    const r = 4 + 6 * Math.sqrt(p.buy / maxBuy);
    // 2px ring in the surface color keeps overlapping marks readable
    mk("circle", { cx: px(p.base), cy: py(p.buy_win), r: r + 1.6, fill: "var(--surface)", opacity: .9 }, svg);
    const c = mk("circle", {
      cx: px(p.base), cy: py(p.buy_win), r,
      fill: "var(--model)", opacity: p.in_window ? .85 : .34,
      stroke: "var(--model)", "stroke-width": p.in_window ? 0 : 1.4
    }, svg);
    c.style.cursor = "crosshair";
    bindTip(c, `${p.date} · ${p.horizon}`, [
      ["win rate BUY", pct(p.buy_win)], ["base rate pasar", pct(p.base)],
      ["edge", pp(p.buy_win - p.base)], ["sinyal BUY", p.buy],
      ["dalam periode", p.in_window ? "ya" : "tidak"],
    ]);
  });

  const xl = mk("text", { x: (M.l + w - M.r) / 2, y: h - 6, "text-anchor": "middle", "font-size": 11, fill: "var(--ink-2)" }, svg);
  xl.textContent = "base rate pasar hari itu";
  const yl = mk("text", { x: 13, y: (M.t + h - M.b) / 2, "text-anchor": "middle", "font-size": 11, fill: "var(--ink-2)",
    transform: `rotate(-90 13 ${(M.t + h - M.b) / 2})` }, svg);
  yl.textContent = "win rate sinyal BUY";
})();

/* ---------- daily lines, per horizon ---------- */
(function () {
  const seg = $("#hzseg"), svg = $("#lines");
  let active = DATA.horizons[0].horizon;

  function draw() {
    svg.textContent = "";
    const pts = DATA.daily.filter(d => d.horizon === active && d.base != null);
    const M = { t: 16, r: 16, b: 52, l: 44 }, w = 720, h = 320;
    if (!pts.length) {
      const t = mk("text", { x: w / 2, y: h / 2, "text-anchor": "middle", "font-size": 12, fill: "var(--ink-3)" }, svg);
      t.textContent = "Belum ada hari dengan minimal 5 sinyal BUY untuk horizon ini.";
      return;
    }
    const lo = 0, hi = 100;
    const px = i => pts.length === 1 ? (M.l + w - M.r) / 2
      : M.l + (i / (pts.length - 1)) * (w - M.l - M.r);
    const py = v => h - M.b - ((v - lo) / (hi - lo)) * (h - M.t - M.b);

    for (let g = 0; g <= 100; g += 25) {
      mk("line", { x1: M.l, y1: py(g), x2: w - M.r, y2: py(g), stroke: "var(--line)", "stroke-width": 1 }, svg);
      const ty = mk("text", { x: M.l - 9, y: py(g) + 3.5, "text-anchor": "end", "font-size": 10.5, fill: "var(--ink-3)" }, svg);
      ty.textContent = g + "%";
    }
    const path = (key, color) => {
      const d = pts.map((p, i) => `${i ? "L" : "M"}${px(i).toFixed(1)} ${py(p[key]).toFixed(1)}`).join(" ");
      mk("path", { d, fill: "none", stroke: color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
      pts.forEach((p, i) => {
        mk("circle", { cx: px(i), cy: py(p[key]), r: 4.6, fill: "var(--surface)" }, svg);
        mk("circle", { cx: px(i), cy: py(p[key]), r: 3, fill: color }, svg);
      });
      // emphasise the endpoint
      const last = pts.length - 1;
      mk("circle", { cx: px(last), cy: py(pts[last][key]), r: 5, fill: color, stroke: "var(--surface)", "stroke-width": 2 }, svg);
    };
    path("base", "var(--market)");
    path("buy_win", "var(--model)");

    pts.forEach((p, i) => {
      const hit = mk("rect", {
        x: px(i) - (w - M.l - M.r) / Math.max(pts.length * 2, 2), y: M.t,
        width: Math.max((w - M.l - M.r) / pts.length, 12), height: h - M.t - M.b,
        fill: "transparent"
      }, svg);
      hit.style.cursor = "crosshair";
      bindTip(hit, `${p.date} · ${p.horizon}`, [
        ["win rate BUY", pct(p.buy_win)], ["base rate pasar", pct(p.base)],
        ["edge", pp(p.buy_win - p.base)], ["sinyal BUY", p.buy],
      ]);
      if (i % Math.ceil(pts.length / 8) === 0 || i === pts.length - 1) {
        const t = mk("text", {
          x: px(i), y: h - M.b + 16, "text-anchor": "end", "font-size": 10, fill: "var(--ink-3)",
          transform: `rotate(-42 ${px(i)} ${h - M.b + 16})`
        }, svg);
        t.textContent = p.date.slice(5);
      }
    });
  }

  seg.innerHTML = DATA.horizons.map(h =>
    `<button type="button" data-hz="${h.horizon}" aria-pressed="${h.horizon === active}">${h.horizon}</button>`).join("");
  seg.addEventListener("click", e => {
    const b = e.target.closest("button");
    if (!b) return;
    active = b.dataset.hz;
    seg.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", String(x.dataset.hz === active)));
    draw();
  });
  draw();
})();

/* ---------- dumbbell: holdout edge vs live edge ---------- */
(function () {
  const svg = $("#dumbbell"), rows = DATA.horizons;
  const M = { t: 22, r: 66, b: 40, l: 52 }, w = 720, h = 240;
  const vals = rows.flatMap(r => [r.edge, r.holdout && r.holdout.edge]).filter(v => v != null);
  const lo = Math.min(-2, ...vals) - 2, hi = Math.max(2, ...vals) + 2;
  const px = v => M.l + ((v - lo) / (hi - lo)) * (w - M.l - M.r);
  const band = (h - M.t - M.b) / rows.length;
  const py = i => M.t + band * (i + .5);

  mk("line", { x1: px(0), y1: M.t - 8, x2: px(0), y2: h - M.b + 4, stroke: "var(--ink-3)", "stroke-width": 2, "stroke-dasharray": "5 4" }, svg);
  const zl = mk("text", { x: px(0), y: M.t - 12, "text-anchor": "middle", "font-size": 10.5, fill: "var(--ink-3)" }, svg);
  zl.textContent = "nol";

  for (let g = Math.ceil(lo / 5) * 5; g <= hi; g += 5) {
    if (Math.abs(g) < .01) continue;
    mk("line", { x1: px(g), y1: M.t - 4, x2: px(g), y2: h - M.b, stroke: "var(--line)", "stroke-width": 1 }, svg);
    const t = mk("text", { x: px(g), y: h - M.b + 16, "text-anchor": "middle", "font-size": 10.5, fill: "var(--ink-3)" }, svg);
    t.textContent = (g > 0 ? "+" : "") + g;
  }

  rows.forEach((r, i) => {
    const y = py(i), ho = r.holdout || {};
    const lab = mk("text", { x: M.l - 12, y: y + 4, "text-anchor": "end", "font-size": 11.5, fill: "var(--ink)", "font-weight": 600 }, svg);
    lab.textContent = r.horizon;
    if (ho.edge != null && r.edge != null) {
      mk("line", { x1: px(ho.edge), y1: y, x2: px(r.edge), y2: y, stroke: "var(--line-2)", "stroke-width": 2 }, svg);
    }
    const dot = (v, color, title) => {
      if (v == null) return;
      mk("circle", { cx: px(v), cy: y, r: 7.5, fill: "var(--surface)" }, svg);
      const c = mk("circle", { cx: px(v), cy: y, r: 5.5, fill: color }, svg);
      c.style.cursor = "pointer";
      bindTip(c, `${r.horizon} · ${title}`, [
        ["edge", pp(v)],
        ["win rate / precision", pct(title === "live" ? r.buy_win : ho.buy_precision)],
        ["base rate", pct(title === "live" ? r.base : ho.base_rate)],
      ]);
    };
    dot(ho.edge, "var(--model-soft)", "holdout");
    dot(r.edge, "var(--model)", "live");
    if (r.edge != null) {
      const v = edgeVerdict(r.edge, r.ci);
      const t = mk("text", {
        x: w - M.r + 10, y: y + 4, "font-size": 11, fill:
          v.cls === "good" ? "var(--good)" : v.cls === "bad" ? "var(--bad)" : "var(--ink-3)"
      }, svg);
      t.textContent = pp(r.edge);
    }
  });

  const xl = mk("text", { x: (M.l + w - M.r) / 2, y: h - 6, "text-anchor": "middle", "font-size": 11, fill: "var(--ink-2)" }, svg);
  xl.textContent = "edge dalam poin persen (win rate − base rate)";
})();

/* ---------- coverage meters ---------- */
$("#coverage").innerHTML = DATA.horizons.map(h => {
  const ho = h.holdout || {};
  const tot = (ho.n_usable || 0) + (ho.n_degenerate || 0);
  const share = tot ? 100 * ho.n_usable / tot : 0;
  const cls = share >= 70 ? "good" : share >= 50 ? "warn" : "bad";
  return `<div style="display:grid; grid-template-columns:34px 1fr 168px; gap:12px; align-items:center">
    <span class="mono" style="font-size:12px; font-weight:600">${h.horizon}</span>
    <span style="height:9px; background:var(--surface-2); border-radius:5px; overflow:hidden; display:block">
      <span style="display:block; height:100%; width:${share.toFixed(1)}%; border-radius:5px; background:var(--${cls})"></span>
    </span>
    <span class="mono" style="font-size:11.5px; color:var(--ink-2); text-align:right">
      ${ho.n_usable == null ? "–" : ho.n_usable} / ${tot} model berguna
      <span style="color:var(--${cls})">· ${share.toFixed(0)}%</span>
    </span>
  </div>`;
}).join("");

/* ---------- ticker table ---------- */
const maxWin = Math.max(...DATA.tickers.map(t => t.win), 1);
$("#tickers").innerHTML = DATA.tickers.map(t => `<tr>
  <td class="mono" style="font-weight:600">${esc(t.ticker)}</td>
  <td class="num">${t.buy}</td>
  <td class="num" style="color:${t.win >= 50 ? "var(--good)" : t.win >= 30 ? "var(--ink)" : "var(--bad)"}">${t.win.toFixed(1)}%</td>
  <td><span class="minibar" style="width:${(100 * t.win / maxWin).toFixed(1)}%; min-width:2px"></span></td>
</tr>`).join("") || `<tr><td colspan="4" style="color:var(--ink-3)">Belum ada ticker dengan minimal 5 sinyal BUY.</td></tr>`;
</script>
