/**
 * VoyageIntel AI — Chart Engine
 * ================================
 * Chart.js-powered visualisations for the Travel Logistics Dashboard.
 * Exposes window.VI_Charts.renderAll(trip) for the main app to call.
 */

'use strict';

(function () {
  // Colour palette
  const RED    = '#c0392b';
  const REDL   = '#e74c3c';
  const GREEN  = '#27ae60';
  const BLUE   = '#2980b9';
  const AMBER  = '#d4a017';
  const PURPLE = '#8e44ad';
  const MUTED  = '#555555';
  const GRID   = '#2a2a2a';
  const TEXT   = '#888888';

  const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: {
          color: TEXT,
          font: { size: 12, family: '-apple-system, "Segoe UI", system-ui, sans-serif' },
          boxWidth: 12,
          padding: 16,
        },
      },
      tooltip: {
        backgroundColor: '#1e1e1e',
        titleColor: '#e8e8e8',
        bodyColor: '#aaaaaa',
        borderColor: '#333333',
        borderWidth: 1,
        cornerRadius: 8,
        padding: 10,
      },
    },
    scales: {
      x: {
        ticks:  { color: TEXT, font: { size: 11 } },
        grid:   { color: GRID },
        border: { color: GRID },
      },
      y: {
        ticks:  { color: TEXT, font: { size: 11 } },
        grid:   { color: GRID },
        border: { color: GRID },
      },
    },
  };

  /* ── Chart instances (destroyed on re-render) ───────────────────── */
  let budgetChart   = null;
  let comfortChart  = null;
  let transitChart  = null;

  function destroyAll() {
    [budgetChart, comfortChart, transitChart].forEach(c => c?.destroy());
    budgetChart = comfortChart = transitChart = null;
  }

  /* ── Budget Distribution Doughnut ───────────────────────────────── */
  function renderBudgetChart(params) {
    const ctx = document.getElementById('budgetChart');
    if (!ctx) return;

    const total = parseFloat(params.budget_total) || 10000;
    const pools = {
      'Transit':    Math.round(total * 0.30),
      'Stay':       Math.round(total * 0.35),
      'Food':       Math.round(total * 0.20),
      'Activities': Math.round(total * 0.10),
      'Contingency':Math.round(total * 0.05),
    };

    budgetChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(pools),
        datasets: [{
          data: Object.values(pools),
          backgroundColor: [RED, BLUE, GREEN, AMBER, PURPLE],
          borderColor: '#161616',
          borderWidth: 3,
          hoverBorderWidth: 4,
        }],
      },
      options: {
        ...CHART_DEFAULTS,
        cutout: '65%',
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { ...CHART_DEFAULTS.plugins.legend, position: 'bottom' },
          tooltip: {
            ...CHART_DEFAULTS.plugins.tooltip,
            callbacks: {
              label: ctx => {
                const sym = params.budget_currency || '₹';
                return `  ${ctx.label}: ${sym}${ctx.raw.toLocaleString()}`;
              },
            },
          },
        },
      },
    });
  }

  /* ── Daily Comfort Weight Bar Chart ─────────────────────────────── */
  function renderComfortChart(params) {
    const ctx = document.getElementById('comfortChart');
    if (!ctx) return;

    const days = parseInt(params.duration_days) || 3;
    const labels = Array.from({ length: days }, (_, i) => `Day ${i + 1}`);

    // Generate plausible comfort weights 60–95
    const seed = (params.destination || '').length + days;
    const data = labels.map((_, i) => {
      const base = 68 + Math.sin(seed + i * 1.3) * 14;
      return Math.round(Math.max(55, Math.min(95, base)));
    });

    comfortChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Comfort Weight (%)',
          data,
          backgroundColor: data.map(v =>
            v >= 80 ? `${GREEN}cc` : v >= 65 ? `${AMBER}cc` : `${RED}cc`
          ),
          borderRadius: 6,
          borderWidth: 0,
        }],
      },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          x: CHART_DEFAULTS.scales.x,
          y: {
            ...CHART_DEFAULTS.scales.y,
            min: 0, max: 100,
            ticks: { ...CHART_DEFAULTS.scales.y.ticks, callback: v => v + '%' },
          },
        },
        plugins: {
          ...CHART_DEFAULTS.plugins,
          tooltip: {
            ...CHART_DEFAULTS.plugins.tooltip,
            callbacks: { label: ctx => `  Comfort: ${ctx.raw}%` },
          },
        },
      },
    });
  }

  /* ── Transit Cost vs. Time Line/Scatter Chart ───────────────────── */
  function renderTransitChart(params) {
    const ctx = document.getElementById('transitChart');
    if (!ctx) return;

    const persona = params.persona || 'balanced';
    const modes = [
      { mode: 'Auto/Cab',    time: 0.5,  cost: 80  },
      { mode: 'Local Bus',   time: 1.5,  cost: 25  },
      { mode: 'Train (Exp)', time: 3.5,  cost: 200 },
      { mode: 'Train (Sl)',  time: 5.0,  cost: 90  },
      { mode: 'Flight',      time: 2.5,  cost: 2800 },
      { mode: 'Rented Bike', time: 2.0,  cost: 150 },
      { mode: 'Bus (AC)',    time: 4.0,  cost: 350 },
    ];

    // Highlight cheapest vs fastest
    const cheapest = modes.reduce((a, b) => a.cost < b.cost ? a : b).mode;
    const fastest  = modes.reduce((a, b) => a.time < b.time ? a : b).mode;

    transitChart = new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Transit Options',
          data: modes.map(m => ({ x: m.time, y: m.cost, label: m.mode })),
          backgroundColor: modes.map(m =>
            m.mode === cheapest ? `${GREEN}dd` :
            m.mode === fastest  ? `${AMBER}dd` :
            `${RED}99`
          ),
          pointRadius: 9,
          pointHoverRadius: 12,
          borderWidth: 1,
          borderColor: modes.map(m =>
            m.mode === cheapest ? GREEN :
            m.mode === fastest  ? AMBER : RED
          ),
        }],
      },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          x: {
            ...CHART_DEFAULTS.scales.x,
            title: {
              display: true,
              text: 'Estimated Transit Time (hrs)',
              color: TEXT,
              font: { size: 11 },
            },
          },
          y: {
            ...CHART_DEFAULTS.scales.y,
            title: {
              display: true,
              text: `Cost (${params.budget_currency || '₹'})`,
              color: TEXT,
              font: { size: 11 },
            },
          },
        },
        plugins: {
          ...CHART_DEFAULTS.plugins,
          tooltip: {
            ...CHART_DEFAULTS.plugins.tooltip,
            callbacks: {
              label: ctx => {
                const pt = ctx.raw;
                const sym = params.budget_currency || '₹';
                return `  ${pt.label}: ${pt.x}h · ${sym}${pt.y}`;
              },
            },
          },
        },
      },
    });

    // Add mode labels as annotations (manual text below chart)
    _addTransitLegend(ctx.parentElement, modes, params.budget_currency || '₹');
  }

  function _addTransitLegend(container, modes, sym) {
    let legend = container.querySelector('.vi-transit-legend');
    if (legend) legend.remove();
    legend = document.createElement('div');
    legend.className = 'vi-transit-legend d-flex flex-wrap gap-2 mt-2 px-1';
    modes.forEach(m => {
      const span = document.createElement('span');
      span.className = 'vi-muted-sm';
      span.textContent = `${m.mode}: ${m.time}h · ${sym}${m.cost}`;
      legend.appendChild(span);
    });
    container.appendChild(legend);
  }

  /* ── Public API ─────────────────────────────────────────────────── */
  window.VI_Charts = {
    renderAll(trip) {
      destroyAll();
      const p = trip?.params || {};
      renderBudgetChart(p);
      renderComfortChart(p);
      renderTransitChart(p);
    },
  };

})();
