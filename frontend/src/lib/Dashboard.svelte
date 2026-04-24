<script>
  import { onMount, onDestroy } from 'svelte';

  let dashboard = {
    stats: {
      total_trades: 0,
      winning_trades: 0,
      win_rate: 0,
      total_profit: 0,
      profit_factor: 0,
      max_drawdown: 0
    },
    positions: [],
    trading_enabled: false,
    open_trades: 0
  };
  let loading = true;
  let error = null;
  let refreshInterval;

  async function fetchDashboard() {
    try {
      const res = await fetch('/api/dashboard');
      if (res.ok) {
        dashboard = await res.json();
      } else {
        error = 'Failed to fetch dashboard';
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function toggleTrading() {
    try {
      const res = await fetch('/api/trading/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !dashboard.trading_enabled })
      });
      if (res.ok) {
        const result = await res.json();
        dashboard.trading_enabled = result.trading_enabled;
      }
    } catch (e) {
      error = e.message;
    }
  }

  onMount(() => {
    fetchDashboard();
    refreshInterval = setInterval(fetchDashboard, 10000);
  });

  onDestroy(() => {
    if (refreshInterval) clearInterval(refreshInterval);
  });

  function formatPct(val) {
    if (val === null || val === undefined) return '-';
    return (val >= 0 ? '+' : '') + val.toFixed(2) + '%';
  }

  function formatPrice(val) {
    if (!val) return '-';
    return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function formatTime(timestamp) {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleString();
  }
</script>

<div class="w-full h-full flex flex-col">
  <div class="flex justify-between items-center px-6 py-4 border-b border-cyber-border/50 shrink-0">
    <h2 class="text-2xl font-mono text-cyber-primary uppercase tracking-widest">
      Dashboard
    </h2>
    <div class="flex items-center space-x-4">
      <button 
        onclick={toggleTrading} 
        class="{dashboard.trading_enabled ? 'btn-secondary' : 'btn-primary'}"
      >
        {dashboard.trading_enabled ? 'Stop Trading' : 'Start Trading'}
      </button>
      <button onclick={fetchDashboard} class="btn-warning text-xs">
        Refresh
      </button>
    </div>
  </div>

  {#if loading}
    <div class="flex-1 flex items-center justify-center text-cyber-muted animate-pulse font-mono">
      Loading dashboard...
    </div>
  {:else if error}
    <div class="m-6 p-4 border border-cyber-secondary/50 bg-cyber-secondary/10 text-cyber-secondary font-mono">
      ERROR: {error}
    </div>
  {:else}
    <div class="flex-1 overflow-y-auto custom-scrollbar p-6 min-h-0">
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <div class="stat-card">
          <span class="stat-label">Total Trades</span>
          <span class="stat-value text-cyber-text">{dashboard.stats.total_trades}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Win Rate</span>
          <span class="stat-value text-cyber-primary">{dashboard.stats.win_rate.toFixed(1)}%</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Total PnL</span>
          <span class="stat-value {dashboard.stats.total_profit >= 0 ? 'text-cyber-primary' : 'text-cyber-secondary'}">
            {formatPct(dashboard.stats.total_profit)}
          </span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Profit Factor</span>
          <span class="stat-value text-cyber-accent">{dashboard.stats.profit_factor.toFixed(2)}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Max DD</span>
          <span class="stat-value text-cyber-secondary">{dashboard.stats.max_drawdown.toFixed(2)}%</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Open Positions</span>
          <span class="stat-value text-cyber-warning">{dashboard.open_trades}</span>
        </div>
      </div>

      <div class="mb-4">
        <h3 class="text-lg font-mono text-cyber-muted uppercase tracking-wider mb-4">
          Open Positions
        </h3>
        
        {#if dashboard.positions.length === 0}
          <div class="text-center py-8 text-cyber-muted font-mono border border-cyber-border/30 bg-cyber-black/30">
            No open positions
          </div>
        {:else}
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-cyber-border text-left">
              <thead class="bg-cyber-gray/50">
                <tr>
                  <th class="table-header">Symbol</th>
                  <th class="table-header">Side</th>
                  <th class="table-header">Entry Price</th>
                  <th class="table-header">Entry Time</th>
                  <th class="table-header">Quantity</th>
                  <th class="table-header">Stop Loss</th>
                  <th class="table-header">Take Profit</th>
                  <th class="table-header">Half Closed</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-cyber-border/30 bg-cyber-black/50">
                {#each dashboard.positions as pos}
                  <tr class="hover:bg-cyber-gray/30 transition-colors">
                    <td class="table-cell font-bold text-cyber-accent">{pos.symbol}</td>
                    <td class="table-cell">
                      <span class="px-2 py-1 rounded text-xs font-bold uppercase bg-cyber-primary/20 text-cyber-primary">
                        {pos.side}
                      </span>
                    </td>
                    <td class="table-cell">{formatPrice(pos.entry_price)}</td>
                    <td class="table-cell text-cyber-muted text-xs">{formatTime(pos.entry_time)}</td>
                    <td class="table-cell">{pos.remaining_qty.toFixed(6)}</td>
                    <td class="table-cell text-cyber-secondary">{formatPrice(pos.stop_loss)}</td>
                    <td class="table-cell text-cyber-primary">{formatPrice(pos.take_profit)}</td>
                    <td class="table-cell">
                      {#if pos.half_closed}
                        <span class="text-cyber-warning">Yes</span>
                      {:else}
                        <span class="text-cyber-muted">No</span>
                      {/if}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>
