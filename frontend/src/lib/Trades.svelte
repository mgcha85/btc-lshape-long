<script>
  import { onMount } from 'svelte';

  let trades = [];
  let stats = { total_trades: 0, win_rate: 0, total_profit: 0, profit_factor: 0, max_drawdown: 0 };
  let loading = true;
  let error = null;
  let filterResult = 'all';

  $: filteredTrades = filterResult === 'all' 
    ? trades 
    : trades.filter(t => {
        if (filterResult === 'win') return t.profit_pct && t.profit_pct > 0;
        if (filterResult === 'loss') return t.profit_pct && t.profit_pct < 0;
        if (filterResult === 'open') return !t.close_time;
        return true;
      });

  async function fetchTrades() {
    loading = true;
    try {
      const [tradesRes, statsRes] = await Promise.all([
        fetch('/api/trades'),
        fetch('/api/stats')
      ]);

      if (tradesRes.ok && statsRes.ok) {
        trades = await tradesRes.json();
        stats = await statsRes.json();
      } else {
        error = 'Failed to load data';
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(fetchTrades);

  function formatTime(timestamp) {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleString();
  }

  function formatPct(val) {
    if (val === null || val === undefined) return '-';
    return (val >= 0 ? '+' : '') + val.toFixed(2) + '%';
  }

  function formatPrice(val) {
    if (!val) return '-';
    return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function getResultBadge(result, profitPct) {
    if (!result || result === '') {
      return { class: 'bg-cyber-warning/20 text-cyber-warning', text: 'OPEN' };
    }
    if (result === 'TP') {
      return { class: 'bg-cyber-primary/20 text-cyber-primary', text: 'TP' };
    }
    if (result === 'SL') {
      return { class: 'bg-cyber-secondary/20 text-cyber-secondary', text: 'SL' };
    }
    return { class: 'bg-cyber-muted/20 text-cyber-muted', text: result };
  }
</script>

<div class="w-full h-full flex flex-col">
  <div class="flex justify-between items-center px-6 py-4 border-b border-cyber-border/50 shrink-0">
    <h2 class="text-2xl font-mono text-cyber-primary uppercase tracking-widest">
      Trade History
    </h2>
    <div class="flex space-x-2">
      <button
        class="px-3 py-1 text-xs font-mono uppercase border border-cyber-border transition-colors {filterResult === 'all' ? 'bg-cyber-primary text-cyber-black' : 'text-cyber-muted hover:text-cyber-text'}"
        onclick={() => filterResult = 'all'}
      >
        All
      </button>
      <button
        class="px-3 py-1 text-xs font-mono uppercase border border-cyber-border transition-colors {filterResult === 'open' ? 'bg-cyber-warning text-cyber-black' : 'text-cyber-muted hover:text-cyber-text'}"
        onclick={() => filterResult = 'open'}
      >
        Open
      </button>
      <button
        class="px-3 py-1 text-xs font-mono uppercase border border-cyber-border transition-colors {filterResult === 'win' ? 'bg-cyber-primary text-cyber-black' : 'text-cyber-muted hover:text-cyber-text'}"
        onclick={() => filterResult = 'win'}
      >
        Wins
      </button>
      <button
        class="px-3 py-1 text-xs font-mono uppercase border border-cyber-border transition-colors {filterResult === 'loss' ? 'bg-cyber-secondary text-cyber-black' : 'text-cyber-muted hover:text-cyber-text'}"
        onclick={() => filterResult = 'loss'}
      >
        Losses
      </button>
      <div class="w-px h-6 bg-cyber-border mx-2"></div>
      <button onclick={fetchTrades} class="btn-secondary text-xs">
        Refresh
      </button>
    </div>
  </div>

  <div class="grid grid-cols-4 gap-4 px-6 py-4 shrink-0">
    <div class="stat-card">
      <span class="stat-label">Total Trades</span>
      <span class="stat-value text-cyber-text">{stats.total_trades}</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Win Rate</span>
      <span class="stat-value text-cyber-primary">{stats.win_rate.toFixed(1)}%</span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Total PnL</span>
      <span class="stat-value {stats.total_profit >= 0 ? 'text-cyber-primary' : 'text-cyber-secondary'}">
        {formatPct(stats.total_profit)}
      </span>
    </div>
    <div class="stat-card">
      <span class="stat-label">Profit Factor</span>
      <span class="stat-value text-cyber-accent">{stats.profit_factor.toFixed(2)}</span>
    </div>
  </div>

  <div class="flex-1 overflow-hidden relative min-h-0">
    {#if loading && trades.length === 0}
      <div class="absolute inset-0 flex items-center justify-center text-cyber-muted animate-pulse font-mono">
        Loading trades...
      </div>
    {:else if error}
      <div class="m-6 p-4 border border-cyber-secondary/50 bg-cyber-secondary/10 text-cyber-secondary font-mono">
        ERROR: {error}
      </div>
    {:else}
      <div class="absolute inset-0 overflow-auto custom-scrollbar">
        <table class="min-w-full divide-y divide-cyber-border text-left">
          <thead class="bg-cyber-gray/50 sticky top-0 z-10 backdrop-blur-sm">
            <tr>
              <th class="table-header">Open Time</th>
              <th class="table-header">Symbol</th>
              <th class="table-header">Side</th>
              <th class="table-header">Entry</th>
              <th class="table-header">Exit</th>
              <th class="table-header">Qty</th>
              <th class="table-header">PnL</th>
              <th class="table-header">Result</th>
              <th class="table-header">Half Close</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-cyber-border/30 bg-cyber-black/50">
            {#each filteredTrades as trade}
              {@const badge = getResultBadge(trade.result, trade.profit_pct)}
              <tr class="hover:bg-cyber-gray/30 transition-colors">
                <td class="table-cell text-cyber-muted text-xs">{formatTime(trade.open_time)}</td>
                <td class="table-cell font-bold text-cyber-accent">{trade.symbol}</td>
                <td class="table-cell">
                  <span class="px-2 py-1 rounded text-xs font-bold uppercase bg-cyber-primary/20 text-cyber-primary">
                    {trade.side}
                  </span>
                </td>
                <td class="table-cell">{formatPrice(trade.open_price)}</td>
                <td class="table-cell">{formatPrice(trade.close_price)}</td>
                <td class="table-cell">{trade.quantity.toFixed(6)}</td>
                <td class="table-cell {trade.profit_pct && trade.profit_pct >= 0 ? 'text-cyber-primary' : 'text-cyber-secondary'}">
                  {formatPct(trade.profit_pct)}
                </td>
                <td class="table-cell">
                  <span class="px-2 py-1 rounded text-xs font-bold uppercase {badge.class}">
                    {badge.text}
                  </span>
                </td>
                <td class="table-cell">
                  {#if trade.half_closed}
                    <span class="text-cyber-warning text-xs">
                      {formatPct(trade.half_close_pct)} @ {formatPrice(trade.half_close_price)}
                    </span>
                  {:else}
                    <span class="text-cyber-muted">-</span>
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
