<script>
  import { onMount } from 'svelte';

  let settings = {};
  let strategy = {
    BreakoutMA: 50,
    ConsolidationBars: 5,
    ConsolidationRangePct: 5.0,
    DropThresholdPct: 5.0,
    TakeProfitPct: 10.0,
    StopLossPct: 3.0,
    HalfCloseEnabled: true,
    HalfClosePct: 5.0
  };
  let loading = true;
  let error = null;
  let success = null;
  let activeSection = 'strategy';

  onMount(async () => {
    try {
      const [settingsRes, strategyRes] = await Promise.all([
        fetch('/api/settings'),
        fetch('/api/strategy')
      ]);
      
      if (settingsRes.ok) {
        settings = await settingsRes.json();
      }
      if (strategyRes.ok) {
        strategy = await strategyRes.json();
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  async function saveSettings() {
    loading = true;
    error = null;
    success = null;
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (res.ok) {
        success = 'Settings saved successfully';
        setTimeout(() => success = null, 3000);
      } else {
        error = 'Failed to save settings';
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  async function saveStrategy() {
    loading = true;
    error = null;
    success = null;
    try {
      const res = await fetch('/api/strategy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(strategy)
      });
      if (res.ok) {
        success = 'Strategy config saved successfully';
        setTimeout(() => success = null, 3000);
      } else {
        error = 'Failed to save strategy config';
      }
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }
</script>

<div class="w-full h-full flex flex-col">
  <div class="px-6 py-4 border-b border-cyber-border/50 shrink-0">
    <h2 class="text-2xl font-mono text-cyber-primary uppercase tracking-widest">
      Configuration
    </h2>
  </div>

  <div class="flex border-b border-cyber-border/50 px-6 shrink-0">
    <button
      class="px-4 py-2 text-sm font-mono uppercase border-b-2 transition-colors {activeSection === 'strategy' ? 'border-cyber-primary text-cyber-primary' : 'border-transparent text-cyber-muted hover:text-cyber-text'}"
      onclick={() => activeSection = 'strategy'}
    >
      Strategy
    </button>
    <button
      class="px-4 py-2 text-sm font-mono uppercase border-b-2 transition-colors {activeSection === 'api' ? 'border-cyber-primary text-cyber-primary' : 'border-transparent text-cyber-muted hover:text-cyber-text'}"
      onclick={() => activeSection = 'api'}
    >
      API Keys
    </button>
    <button
      class="px-4 py-2 text-sm font-mono uppercase border-b-2 transition-colors {activeSection === 'general' ? 'border-cyber-primary text-cyber-primary' : 'border-transparent text-cyber-muted hover:text-cyber-text'}"
      onclick={() => activeSection = 'general'}
    >
      General
    </button>
  </div>

  <div class="flex-1 overflow-y-auto custom-scrollbar p-6 min-h-0">
    <div class="max-w-2xl mx-auto">
      {#if error}
        <div class="p-4 border border-cyber-secondary/50 bg-cyber-secondary/10 text-cyber-secondary font-mono mb-4">
          ERROR: {error}
        </div>
      {/if}

      {#if success}
        <div class="p-4 border border-cyber-primary/50 bg-cyber-primary/10 text-cyber-primary font-mono mb-4">
          {success}
        </div>
      {/if}

      {#if loading && !strategy}
        <div class="text-cyber-muted animate-pulse font-mono">
          Loading configuration...
        </div>
      {:else if activeSection === 'strategy'}
        <div class="grid gap-6">
          <div class="border border-cyber-border p-4 bg-cyber-gray/30">
            <h3 class="text-sm font-mono text-cyber-accent uppercase mb-4">Entry Parameters</h3>
            <div class="grid gap-4">
              <div class="group">
                <label class="block text-xs font-mono text-cyber-muted uppercase mb-2">
                  MA Period (Breakout)
                </label>
                <input
                  type="number"
                  bind:value={strategy.BreakoutMA}
                  class="input-field"
                  min="1"
                  max="200"
                />
              </div>
              <div class="group">
                <label class="block text-xs font-mono text-cyber-muted uppercase mb-2">
                  Consolidation Bars
                </label>
                <input
                  type="number"
                  bind:value={strategy.ConsolidationBars}
                  class="input-field"
                  min="2"
                  max="50"
                />
              </div>
              <div class="group">
                <label class="block text-xs font-mono text-cyber-muted uppercase mb-2">
                  Consolidation Range (%)
                </label>
                <input
                  type="number"
                  bind:value={strategy.ConsolidationRangePct}
                  class="input-field"
                  step="0.1"
                  min="0.1"
                />
              </div>
              <div class="group">
                <label class="block text-xs font-mono text-cyber-muted uppercase mb-2">
                  Prior Drop Threshold (%)
                </label>
                <input
                  type="number"
                  bind:value={strategy.DropThresholdPct}
                  class="input-field"
                  step="0.1"
                  min="0.1"
                />
              </div>
            </div>
          </div>

          <div class="border border-cyber-border p-4 bg-cyber-gray/30">
            <h3 class="text-sm font-mono text-cyber-accent uppercase mb-4">Exit Parameters</h3>
            <div class="grid gap-4">
              <div class="group">
                <label class="block text-xs font-mono text-cyber-muted uppercase mb-2">
                  Take Profit (%)
                </label>
                <input
                  type="number"
                  bind:value={strategy.TakeProfitPct}
                  class="input-field"
                  step="0.1"
                  min="0.1"
                />
              </div>
              <div class="group">
                <label class="block text-xs font-mono text-cyber-muted uppercase mb-2">
                  Stop Loss (%)
                </label>
                <input
                  type="number"
                  bind:value={strategy.StopLossPct}
                  class="input-field"
                  step="0.1"
                  min="0.1"
                />
              </div>
              <div class="group">
                <label class="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    bind:checked={strategy.HalfCloseEnabled}
                    class="w-5 h-5 accent-cyber-primary"
                  />
                  <span class="text-xs font-mono text-cyber-muted uppercase">
                    Enable Half Close
                  </span>
                </label>
              </div>
              {#if strategy.HalfCloseEnabled}
                <div class="group">
                  <label class="block text-xs font-mono text-cyber-muted uppercase mb-2">
                    Half Close At (%)
                  </label>
                  <input
                    type="number"
                    bind:value={strategy.HalfClosePct}
                    class="input-field"
                    step="0.1"
                    min="0.1"
                  />
                </div>
              {/if}
            </div>
          </div>

          <div class="flex justify-end">
            <button onclick={saveStrategy} class="btn-primary" disabled={loading}>
              {loading ? 'Saving...' : 'Save Strategy Config'}
            </button>
          </div>
        </div>

      {:else if activeSection === 'api'}
        <div class="grid gap-6">
          <div class="border border-cyber-border p-4 bg-cyber-gray/30">
            <h3 class="text-sm font-mono text-cyber-accent uppercase mb-4">Binance API</h3>
            <div class="grid gap-4">
              <div class="group">
                <label class="block text-xs font-mono text-cyber-muted uppercase mb-2">
                  API Key
                </label>
                <input
                  type="password"
                  bind:value={settings.BINANCE_API_KEY}
                  class="input-field"
                  placeholder="Enter Binance API Key"
                />
              </div>
              <div class="group">
                <label class="block text-xs font-mono text-cyber-muted uppercase mb-2">
                  Secret Key
                </label>
                <input
                  type="password"
                  bind:value={settings.BINANCE_SECRET_KEY}
                  class="input-field"
                  placeholder="Enter Binance Secret Key"
                />
              </div>
            </div>
          </div>

          <div class="flex justify-end">
            <button onclick={saveSettings} class="btn-primary" disabled={loading}>
              {loading ? 'Saving...' : 'Save API Keys'}
            </button>
          </div>
        </div>

      {:else if activeSection === 'general'}
        <div class="grid gap-6">
          <div class="border border-cyber-border p-4 bg-cyber-gray/30">
            <h3 class="text-sm font-mono text-cyber-accent uppercase mb-4">Trading Settings</h3>
            <div class="grid gap-4">
              <div class="group">
                <label class="block text-xs font-mono text-cyber-muted uppercase mb-2">
                  Target Symbols (comma separated)
                </label>
                <input
                  type="text"
                  bind:value={settings.TARGET_SYMBOLS}
                  class="input-field"
                  placeholder="BTCUSDT,ETHUSDT"
                />
              </div>
              <div class="group">
                <label class="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.USE_FUTURES === 'true'}
                    onchange={(e) => settings.USE_FUTURES = e.target.checked ? 'true' : 'false'}
                    class="w-5 h-5 accent-cyber-primary"
                  />
                  <span class="text-xs font-mono text-cyber-muted uppercase">
                    Use Futures (vs Spot)
                  </span>
                </label>
              </div>
              <div class="group">
                <label class="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.USE_TESTNET === 'true'}
                    onchange={(e) => settings.USE_TESTNET = e.target.checked ? 'true' : 'false'}
                    class="w-5 h-5 accent-cyber-warning"
                  />
                  <span class="text-xs font-mono text-cyber-muted uppercase">
                    Use Testnet
                  </span>
                </label>
              </div>
            </div>
          </div>

          <div class="flex justify-end">
            <button onclick={saveSettings} class="btn-primary" disabled={loading}>
              {loading ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>
