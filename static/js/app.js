/* ========================================================================= */
/* Global Portfolio One – Dashboard Application                              */
/* ========================================================================= */

const API = {
    dashboard:  '/api/dashboard',
    allocate:   '/api/allocate',
    simulate:   '/api/simulate',
    reference:  '/api/reference',
};

let state = {
    market: null,
    regime: null,
    recovery: null,
    allocation: null,
};

let drawdownChart = null;
let priceChart    = null;

/* ---- Tabs --------------------------------------------------------------- */

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
    });
});

/* ---- Helpers ------------------------------------------------------------ */

function fmt(n, decimals = 2) {
    if (n == null) return '—';
    return Number(n).toLocaleString('de-DE', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

function fmtEur(n) {
    if (n == null) return '—';
    return '€' + Number(n).toLocaleString('de-DE', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
}

function fmtPct(n) {
    if (n == null) return '—';
    return fmt(n, 2) + '%';
}

function el(id) { return document.getElementById(id); }

function setLoading(containerId, loading) {
    const container = el(containerId);
    if (!container) return;
    if (loading) {
        container.innerHTML = `<div class="loading-overlay"><span class="spinner"></span> Loading market data…</div>`;
    }
}

function regimeClass(r) {
    return 'regime-' + (r || 'a').toLowerCase();
}

/* ---- Dashboard Tab ------------------------------------------------------ */

async function loadDashboard() {
    setLoading('dashboard-content', true);

    try {
        const resp = await fetch(API.dashboard);
        const data = await resp.json();

        if (data.error) throw new Error(data.error);

        state.market   = data.market;
        state.regime   = data.regime;
        state.recovery = data.recovery;

        renderDashboard();
    } catch (err) {
        el('dashboard-content').innerHTML = `
            <div class="card">
                <p style="color:var(--accent-red)">Failed to load market data: ${err.message}</p>
                <p style="color:var(--text-secondary);margin-top:8px">
                    Ensure the server is running and try refreshing.
                </p>
            </div>`;
    }
}

function renderDashboard() {
    const m   = state.market;
    const r   = state.regime;
    const rec = state.recovery;
    const dd  = m.drawdown;

    const rc = regimeClass(r.regime);

    let triggersHtml = '';
    (r.triggers_met || []).forEach(t => {
        const cls = t.includes('extreme') || t.includes('Drawdown') && r.regime === 'C' ? 'danger' :
                    t.includes('elevated') || t.includes('VIX') ? 'warning' : 'ok';
        triggersHtml += `<li class="${cls}">${t}</li>`;
    });

    let recoveryHtml = '';
    if (rec && rec.trough_price) {
        recoveryHtml = `
        <div class="card">
            <div class="card-header"><h3>Recovery Protocol</h3></div>
            <div class="grid-3">
                <div class="stat-box">
                    <div class="label">Trough Price</div>
                    <div class="value">${fmt(rec.trough_price)}</div>
                </div>
                <div class="stat-box">
                    <div class="label">C→B Target (+50%)</div>
                    <div class="value">${fmt(rec.regime_c_to_b_price)}</div>
                    ${rec.progress_to_b != null ? `
                    <div class="progress-track" style="margin-top:8px">
                        <div class="progress-fill amber" style="width:${rec.progress_to_b}%"></div>
                    </div>
                    <div class="sub">${fmtPct(rec.progress_to_b)} progress</div>` : ''}
                </div>
                <div class="stat-box">
                    <div class="label">B→A Target (+87.5%)</div>
                    <div class="value">${fmt(rec.regime_b_to_a_price)}</div>
                    ${rec.progress_to_a != null ? `
                    <div class="progress-track" style="margin-top:8px">
                        <div class="progress-fill green" style="width:${rec.progress_to_a}%"></div>
                    </div>
                    <div class="sub">${fmtPct(rec.progress_to_a)} progress</div>` : ''}
                </div>
            </div>
        </div>`;
    }

    el('dashboard-content').innerHTML = `
        <!-- Regime Banner -->
        <div class="card" style="text-align:center; padding:32px;">
            <div class="regime-badge ${rc}" style="margin:0 auto 16px;">
                <span class="regime-dot"></span>
                Regime ${r.regime}: ${r.label}
            </div>
            <p class="description-block" style="text-align:left">${r.description}</p>
        </div>

        <!-- Key Metrics -->
        <div class="grid-4">
            <div class="stat-box">
                <div class="label">MSCI World Proxy</div>
                <div class="value">${fmt(dd.current_price)}</div>
                <div class="sub">ATH: ${fmt(dd.ath)} (${dd.ath_date || '—'})</div>
            </div>
            <div class="stat-box">
                <div class="label">Drawdown from ATH</div>
                <div class="value" style="color:${dd.drawdown_pct < -20 ? 'var(--accent-red)' : dd.drawdown_pct < -10 ? 'var(--accent-amber)' : 'var(--accent-green)'}">${fmtPct(dd.drawdown_pct)}</div>
                <div class="sub">Trigger B: ≤ -20% / C: ≤ -40%</div>
            </div>
            <div class="stat-box">
                <div class="label">VIX (Fear Index)</div>
                <div class="value" style="color:${m.vix >= 30 ? 'var(--accent-red)' : m.vix >= 20 ? 'var(--accent-amber)' : 'var(--accent-green)'}">${fmt(m.vix, 1)}</div>
                <div class="sub">Stress threshold: ≥ 30</div>
            </div>
            <div class="stat-box">
                <div class="label">Credit Spread (BBB OAS)</div>
                <div class="value" style="color:${m.credit_spread >= 4.5 ? 'var(--accent-red)' : m.credit_spread >= 2.5 ? 'var(--accent-amber)' : 'var(--accent-green)'}">${fmtPct(m.credit_spread)}</div>
                <div class="sub">Elevated: ≥ 2.5% / Extreme: ≥ 4.5%</div>
            </div>
        </div>

        <!-- Allocation Bar -->
        <div class="card">
            <div class="card-header"><h3>Target Asset Allocation</h3></div>
            <div class="alloc-bar-container">
                <div class="alloc-bar">
                    <div class="segment equity" style="width:${r.equity_pct * 100}%">${(r.equity_pct*100).toFixed(0)}% Equity</div>
                    ${r.reserve_pct > 0 ? `<div class="segment reserve" style="width:${r.reserve_pct * 100}%">${(r.reserve_pct*100).toFixed(0)}% Reserve</div>` : ''}
                </div>
                <div class="alloc-legend">
                    <span><span class="dot eq"></span> Welt AG (Equity)</span>
                    <span><span class="dot res"></span> Investment Reserve</span>
                </div>
            </div>
        </div>

        <!-- Triggers -->
        <div class="card">
            <div class="card-header"><h3>Active Signals</h3></div>
            <ul class="trigger-list">${triggersHtml}</ul>
        </div>

        ${recoveryHtml}

        <!-- Charts -->
        <div class="grid-2">
            <div class="card">
                <div class="card-header"><h3>Price History (MSCI World Proxy)</h3></div>
                <div class="chart-container"><canvas id="priceCanvas"></canvas></div>
            </div>
            <div class="card">
                <div class="card-header"><h3>Drawdown from ATH</h3></div>
                <div class="chart-container"><canvas id="drawdownCanvas"></canvas></div>
            </div>
        </div>

        <p style="text-align:center;color:var(--text-muted);font-size:.78rem;margin-top:8px;">
            Last updated: ${m.last_updated}
        </p>
    `;

    renderCharts(m.price_chart, m.drawdown_chart);
}


/* ---- Chart Rendering (lightweight Canvas) ------------------------------- */

function renderCharts(priceData, ddData) {
    if (priceData && priceData.length > 0) {
        drawCanvasChart('priceCanvas', priceData.map(d => d.date), priceData.map(d => d.price), {
            lineColor: '#4a8eff',
            fillColor: 'rgba(74,142,255,.08)',
            yPrefix: '',
            ySuffix: '',
        });
    }
    if (ddData && ddData.length > 0) {
        drawCanvasChart('drawdownCanvas', ddData.map(d => d.date), ddData.map(d => d.drawdown), {
            lineColor: '#ef4444',
            fillColor: 'rgba(239,68,68,.08)',
            yPrefix: '',
            ySuffix: '%',
            thresholds: [
                { value: -20, color: '#f59e0b', label: '-20% (B)' },
                { value: -40, color: '#ef4444', label: '-40% (C)' },
            ],
        });
    }
}

function drawCanvasChart(canvasId, labels, values, opts = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width  = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width  = rect.width + 'px';
    canvas.style.height = rect.height + 'px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const W = rect.width;
    const H = rect.height;
    const pad = { top: 20, right: 16, bottom: 36, left: 60 };
    const cw = W - pad.left - pad.right;
    const ch = H - pad.top - pad.bottom;

    const yMin = Math.min(...values);
    const yMax = Math.max(...values);
    const yRange = yMax - yMin || 1;
    const yPad = yRange * 0.1;

    function toX(i) { return pad.left + (i / (values.length - 1)) * cw; }
    function toY(v) { return pad.top + ch - ((v - (yMin - yPad)) / (yRange + 2 * yPad)) * ch; }

    // Grid lines
    ctx.strokeStyle = '#2d3348';
    ctx.lineWidth = 1;
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
        const y = pad.top + (i / gridLines) * ch;
        ctx.beginPath();
        ctx.moveTo(pad.left, y);
        ctx.lineTo(W - pad.right, y);
        ctx.stroke();

        const val = yMax + yPad - (i / gridLines) * (yRange + 2 * yPad);
        ctx.fillStyle = '#5d6178';
        ctx.font = '11px Inter, sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText((opts.yPrefix || '') + val.toFixed(1) + (opts.ySuffix || ''), pad.left - 8, y + 4);
    }

    // Thresholds
    if (opts.thresholds) {
        opts.thresholds.forEach(t => {
            const y = toY(t.value);
            if (y >= pad.top && y <= pad.top + ch) {
                ctx.setLineDash([6, 4]);
                ctx.strokeStyle = t.color;
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.moveTo(pad.left, y);
                ctx.lineTo(W - pad.right, y);
                ctx.stroke();
                ctx.setLineDash([]);

                ctx.fillStyle = t.color;
                ctx.font = '10px Inter, sans-serif';
                ctx.textAlign = 'left';
                ctx.fillText(t.label, W - pad.right + 4, y + 4);
            }
        });
    }

    // Fill
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(values[0]));
    for (let i = 1; i < values.length; i++) ctx.lineTo(toX(i), toY(values[i]));
    ctx.lineTo(toX(values.length - 1), pad.top + ch);
    ctx.lineTo(toX(0), pad.top + ch);
    ctx.closePath();
    ctx.fillStyle = opts.fillColor || 'rgba(74,142,255,.06)';
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.moveTo(toX(0), toY(values[0]));
    for (let i = 1; i < values.length; i++) ctx.lineTo(toX(i), toY(values[i]));
    ctx.strokeStyle = opts.lineColor || '#4a8eff';
    ctx.lineWidth = 2;
    ctx.stroke();

    // X-axis labels (sparse)
    ctx.fillStyle = '#5d6178';
    ctx.font = '10px Inter, sans-serif';
    ctx.textAlign = 'center';
    const step = Math.max(1, Math.floor(labels.length / 6));
    for (let i = 0; i < labels.length; i += step) {
        const lbl = labels[i].substring(0, 7);
        ctx.fillText(lbl, toX(i), H - 8);
    }
}


/* ---- Allocator Tab ------------------------------------------------------ */

async function loadAllocation() {
    const pvInput = el('portfolio-value');
    const pv = parseFloat(pvInput.value) || 100000;

    el('alloc-results').innerHTML = `<div class="loading-overlay"><span class="spinner"></span> Computing allocation…</div>`;

    try {
        const resp = await fetch(API.allocate, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ portfolio_value: pv }),
        });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);

        state.allocation = data.allocation;
        renderAllocation();
    } catch (err) {
        el('alloc-results').innerHTML = `<div class="card"><p style="color:var(--accent-red)">Error: ${err.message}</p></div>`;
    }
}

function renderAllocation() {
    const a = state.allocation;
    if (!a) return;

    const equityPositions = a.positions.filter(p =>
        !['inflation_linked','money_market','gold','cash'].includes(p.region)
    );
    const reservePositions = a.positions.filter(p =>
        ['inflation_linked','money_market','gold','cash'].includes(p.region)
    );

    function posRow(p) {
        const region = p.region.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        return `<tr>
            <td>${region}</td>
            <td>${p.etf_name}</td>
            <td class="mono">${p.isin}</td>
            <td class="number">${fmtPct(p.target_weight * 100)}</td>
            <td class="number" style="font-weight:600">${fmtEur(p.target_value)}</td>
        </tr>`;
    }

    function simpleRow(p) {
        const region = p.region.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        return `<tr>
            <td>${region}</td>
            <td>${p.etf_name}</td>
            <td class="number">${fmtPct(p.target_weight * 100)}</td>
            <td class="number" style="font-weight:600">${fmtEur(p.target_value)}</td>
        </tr>`;
    }

    el('alloc-results').innerHTML = `
        <div class="grid-3" style="margin-bottom:20px">
            <div class="stat-box">
                <div class="label">Portfolio Value</div>
                <div class="value" style="color:var(--accent-blue)">${fmtEur(a.portfolio_value)}</div>
            </div>
            <div class="stat-box">
                <div class="label">Equity / Reserve</div>
                <div class="value">${fmtEur(a.equity_value)} / ${fmtEur(a.reserve_value)}</div>
                <div class="sub">Regime ${a.regime}: ${(a.equity_pct*100).toFixed(0)}/${(a.reserve_pct*100).toFixed(0)}</div>
            </div>
            <div class="stat-box">
                <div class="label">Weighted TER</div>
                <div class="value">${a.weighted_ter}%</div>
                <div class="sub">Blended annual cost</div>
            </div>
        </div>

        <!-- Full Model -->
        <div class="card">
            <div class="card-header"><h3>Scientific Model – 6 ETF Welt AG + Reserve</h3></div>

            <h4 style="margin: 10px 0 8px; color:var(--accent-blue);">Equity Sleeve (Welt AG)</h4>
            <table class="data-table">
                <thead><tr><th>Region</th><th>ETF</th><th>ISIN</th><th>Weight</th><th>Target Value</th></tr></thead>
                <tbody>${equityPositions.map(posRow).join('')}</tbody>
            </table>

            <h4 style="margin: 20px 0 8px; color:var(--accent-amber);">Investment Reserve</h4>
            <table class="data-table">
                <thead><tr><th>Component</th><th>ETF</th><th>ISIN</th><th>Weight</th><th>Target Value</th></tr></thead>
                <tbody>${reservePositions.map(posRow).join('')}</tbody>
            </table>
        </div>

        <!-- Simple Model -->
        <div class="card">
            <div class="card-header"><h3>Simplified 3-ETF Model</h3></div>
            <table class="data-table">
                <thead><tr><th>Component</th><th>ETF / Instrument</th><th>Weight</th><th>Target Value</th></tr></thead>
                <tbody>${a.simple_positions.map(simpleRow).join('')}</tbody>
            </table>
        </div>
    `;
}


/* ---- Simulator Tab ------------------------------------------------------ */

async function runSimulation() {
    const dd     = parseFloat(el('sim-drawdown').value) || 0;
    const spread = el('sim-spread').value ? parseFloat(el('sim-spread').value) : null;
    const vix    = el('sim-vix').value ? parseFloat(el('sim-vix').value) : null;
    const pv     = parseFloat(el('sim-pv').value) || 100000;

    el('sim-results').innerHTML = `<div class="loading-overlay"><span class="spinner"></span> Running simulation…</div>`;

    try {
        const resp = await fetch(API.simulate, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                drawdown_pct: dd,
                credit_spread: spread,
                vix: vix,
                portfolio_value: pv,
            }),
        });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);

        renderSimulation(data);
    } catch (err) {
        el('sim-results').innerHTML = `<div class="card"><p style="color:var(--accent-red)">Error: ${err.message}</p></div>`;
    }
}

function renderSimulation(data) {
    const r = data.regime;
    const a = data.allocation;
    const rc = regimeClass(r.regime);

    let triggersHtml = (r.triggers_met || []).map(t => `<li class="warning">${t}</li>`).join('');

    const positions = a.positions || [];
    function posRow(p) {
        const region = p.region.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        return `<tr>
            <td>${region}</td>
            <td>${p.etf_name}</td>
            <td class="number">${fmtPct(p.target_weight * 100)}</td>
            <td class="number" style="font-weight:600">${fmtEur(p.target_value)}</td>
        </tr>`;
    }

    el('sim-results').innerHTML = `
        <div class="card" style="text-align:center; padding:28px;">
            <div class="regime-badge ${rc}" style="margin:0 auto 14px;">
                <span class="regime-dot"></span>
                Regime ${r.regime}: ${r.label}
            </div>
            <p class="description-block" style="text-align:left">${r.description}</p>

            <div class="alloc-bar-container" style="margin-top:18px">
                <div class="alloc-bar">
                    <div class="segment equity" style="width:${r.equity_pct * 100}%">${(r.equity_pct*100).toFixed(0)}% Equity</div>
                    ${r.reserve_pct > 0 ? `<div class="segment reserve" style="width:${r.reserve_pct * 100}%">${(r.reserve_pct*100).toFixed(0)}% Reserve</div>` : ''}
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header"><h3>Active Signals</h3></div>
            <ul class="trigger-list">${triggersHtml}</ul>
        </div>

        <div class="card">
            <div class="card-header"><h3>Simulated Allocation – ${fmtEur(a.portfolio_value)}</h3></div>
            <table class="data-table">
                <thead><tr><th>Component</th><th>ETF</th><th>Weight</th><th>Target Value</th></tr></thead>
                <tbody>${positions.map(posRow).join('')}</tbody>
            </table>
        </div>
    `;
}


/* ---- Reference Tab (loaded once) ---------------------------------------- */

async function loadReference() {
    try {
        const resp = await fetch(API.reference);
        const data = await resp.json();
        renderReference(data);
    } catch (err) {
        el('reference-content').innerHTML = `<p style="color:var(--accent-red)">Failed to load: ${err.message}</p>`;
    }
}

function renderReference(data) {
    function etfRow(key, etf) {
        return `<tr>
            <td>${key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</td>
            <td>${etf.name}</td>
            <td class="mono">${etf.isin}</td>
            <td>${etf.index}</td>
            <td class="number">${(etf.ter * 100).toFixed(2)}%</td>
        </tr>`;
    }

    const eqWeights = data.equity_weights;
    const eqTotal = Object.values(eqWeights).reduce((s, v) => s + v, 0);

    let eqRows = '';
    for (const [k, v] of Object.entries(eqWeights)) {
        const label = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        eqRows += `<tr>
            <td>${label}</td>
            <td class="number">${(v * 100).toFixed(2)}%</td>
            <td class="number">${((v / eqTotal) * 100).toFixed(2)}%</td>
        </tr>`;
    }

    let etfRows = '';
    for (const [k, etf] of Object.entries(data.etfs)) {
        etfRows += etfRow(k, etf);
    }

    el('reference-content').innerHTML = `
        <div class="card">
            <div class="card-header"><h3>Equal-Value-Index Regional Weights</h3></div>
            <table class="data-table">
                <thead><tr><th>Region</th><th>GPO Weight</th><th>Normalized (Equity Only)</th></tr></thead>
                <tbody>${eqRows}</tbody>
            </table>
        </div>

        <div class="card">
            <div class="card-header"><h3>ETF Universe</h3></div>
            <table class="data-table">
                <thead><tr><th>Component</th><th>ETF Name</th><th>ISIN</th><th>Index</th><th>TER</th></tr></thead>
                <tbody>${etfRows}</tbody>
            </table>
        </div>

        <div class="card">
            <div class="card-header"><h3>Regime Dashboard Summary</h3></div>
            <table class="data-table">
                <thead>
                    <tr><th>Metric</th><th>Regime A (Normal)</th><th>Regime B (Scarcity)</th><th>Regime C (Escalation)</th></tr>
                </thead>
                <tbody>
                    <tr><td>Drawdown</td><td>0% to -19%</td><td>-20% to -39%</td><td>≥ -40%</td></tr>
                    <tr><td>Credit Spreads</td><td>Normal</td><td>Elevated (≥2.5%)</td><td>Extreme (≥4.5%)</td></tr>
                    <tr><td>Equity Allocation</td><td style="color:var(--accent-green)">80%</td><td style="color:var(--accent-amber)">90%</td><td style="color:var(--accent-red)">100%</td></tr>
                    <tr><td>Reserve Allocation</td><td>20%</td><td>10%</td><td>0%</td></tr>
                    <tr><td>Action</td><td>Rebalance quarterly</td><td>Deploy 50% reserve</td><td>Deploy all reserve</td></tr>
                </tbody>
            </table>
        </div>

        <div class="card">
            <div class="card-header"><h3>Recovery Protocol</h3></div>
            <table class="data-table">
                <thead><tr><th>Transition</th><th>Trigger</th><th>Action</th></tr></thead>
                <tbody>
                    <tr><td>C → B</td><td>+50% from trough + spreads normalising</td><td>Rebuild reserve to 10%</td></tr>
                    <tr><td>B → A</td><td>+25% beyond C→B target</td><td>Rebuild reserve to 20%</td></tr>
                </tbody>
            </table>
        </div>
    `;
}


/* ---- Init --------------------------------------------------------------- */

document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    loadReference();

    el('btn-allocate').addEventListener('click', loadAllocation);
    el('btn-simulate').addEventListener('click', runSimulation);
    el('btn-refresh').addEventListener('click', loadDashboard);

    // Enter key in portfolio value
    el('portfolio-value').addEventListener('keydown', e => {
        if (e.key === 'Enter') loadAllocation();
    });
});
