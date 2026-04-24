<script>
  import { onMount, onDestroy } from 'svelte';
  import Dashboard from './lib/Dashboard.svelte';
  import Trades from './lib/Trades.svelte';
  import Settings from './lib/Settings.svelte';

  let currentTab = 'dashboard';
  let status = { status: 'unknown', trading: false };
  let statusInterval;

  async function fetchStatus() {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        status = await res.json();
      } else {
        status = { status: 'error', trading: false };
      }
    } catch (e) {
      status = { status: 'offline', trading: false };
    }
  }

  onMount(() => {
    fetchStatus();
    statusInterval = setInterval(fetchStatus, 5000);
  });

  onDestroy(() => {
    if (statusInterval) clearInterval(statusInterval);
  });

  function getStatusColor(s) {
    if (s === 'ok' || s === 'running') return 'bg-cyber-primary shadow-[0_0_8px_rgba(0,255,157,0.8)]';
    if (s === 'error' || s === 'offline') return 'bg-cyber-secondary shadow-[0_0_8px_rgba(255,0,85,0.8)]';
    return 'bg-cyber-muted';
  }

  function getTradingColor(trading) {
    return trading ? 'text-cyber-primary' : 'text-cyber-secondary';
  }
</script>

<main class="h-screen bg-cyber-black text-cyber-text font-sans flex flex-col">
  <!-- Header -->
  <header class="border-b border-cyber-border bg-cyber-gray/30 backdrop-blur-md sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <div class="w-8 h-8 bg-cyber-primary/20 rounded flex items-center justify-center border border-cyber-primary/50">
          <span class="text-cyber-primary font-mono font-bold text-lg">L</span>
        </div>
        <h1 class="text-xl font-bold tracking-wider uppercase font-mono">
          L-Shape<span class="text-cyber-primary">Trader</span>
        </h1>
      </div>

      <div class="flex items-center space-x-6">
        <div class="flex items-center space-x-4">
          <div class="flex items-center space-x-2 px-3 py-1 rounded-full bg-cyber-black/50 border border-cyber-border">
            <span class="status-dot {getStatusColor(status.status)} animate-pulse-fast"></span>
            <span class="text-xs font-mono uppercase tracking-wider text-cyber-muted">
              {status.status}
            </span>
          </div>
          <div class="flex items-center space-x-2 px-3 py-1 rounded-full bg-cyber-black/50 border border-cyber-border">
            <span class="text-xs font-mono uppercase tracking-wider {getTradingColor(status.trading)}">
              Trading: {status.trading ? 'ON' : 'OFF'}
            </span>
          </div>
        </div>
      </div>
    </div>
  </header>

  <!-- Navigation -->
  <nav class="border-b border-cyber-border bg-cyber-black/50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex space-x-8">
        <button 
          class="tab-btn {currentTab === 'dashboard' ? 'active' : ''}"
          onclick={() => currentTab = 'dashboard'}
        >
          Dashboard
        </button>
        <button 
          class="tab-btn {currentTab === 'trades' ? 'active' : ''}"
          onclick={() => currentTab = 'trades'}
        >
          Trades
        </button>
        <button 
          class="tab-btn {currentTab === 'settings' ? 'active' : ''}"
          onclick={() => currentTab = 'settings'}
        >
          Settings
        </button>
      </div>
    </div>
  </nav>

  <!-- Content -->
  <div class="flex-1 overflow-hidden p-6 flex flex-col">
    <div class="max-w-7xl w-full mx-auto glass-panel flex-1 rounded-lg overflow-hidden relative flex flex-col">
      <div class="absolute inset-0 pointer-events-none opacity-5" 
           style="background-image: linear-gradient(#333 1px, transparent 1px), linear-gradient(90deg, #333 1px, transparent 1px); background-size: 20px 20px;">
      </div>

      <div class="relative z-10 flex-1 overflow-hidden flex flex-col">
        {#if currentTab === 'dashboard'}
          <Dashboard />
        {:else if currentTab === 'trades'}
          <Trades />
        {:else if currentTab === 'settings'}
          <Settings />
        {/if}
      </div>
    </div>
  </div>
</main>
