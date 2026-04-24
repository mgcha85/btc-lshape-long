<script>
	import { onMount } from 'svelte';
	import { fetchStatus, fetchTrades, toggleTrading } from '$lib/api.js';
	import { PROFILES, BACKTEST_URL } from '$lib/config.js';
	
	let activeTab = 'dashboard';
	let status = null;
	let trades = [];
	let loading = true;
	let error = null;
	
	let settings = {
		apiKey: '',
		secretKey: '',
		profile: '5m-balanced',
		tradingEnabled: false
	};
	
	onMount(async () => {
		await loadData();
		const interval = setInterval(loadData, 5000);
		return () => clearInterval(interval);
	});
	
	async function loadData() {
		try {
			status = await fetchStatus();
			trades = await fetchTrades();
			settings.tradingEnabled = status?.trading_enabled || false;
			loading = false;
		} catch (e) {
			error = 'Failed to connect to engine';
			loading = false;
		}
	}
	
	async function handleToggle() {
		try {
			const result = await toggleTrading(!settings.tradingEnabled);
			settings.tradingEnabled = result.enabled;
		} catch (e) {
			error = 'Failed to toggle trading';
		}
	}
	
	function getSelectedProfile() {
		return PROFILES.find(p => p.id === settings.profile) || PROFILES[2];
	}
	
	function formatPnL(pnl) {
		if (pnl === null || pnl === undefined) return '-';
		const color = pnl >= 0 ? '#22c55e' : '#ef4444';
		return `<span style="color: ${color}">${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}%</span>`;
	}
</script>

<div class="container">
	<header>
		<h1>L-Shape Trading</h1>
		<div class="status-badge" class:online={!loading && !error} class:offline={error}>
			{error ? 'Offline' : loading ? 'Loading...' : 'Online'}
		</div>
	</header>
	
	<nav>
		<button class:active={activeTab === 'dashboard'} on:click={() => activeTab = 'dashboard'}>
			Dashboard
		</button>
		<button class:active={activeTab === 'history'} on:click={() => activeTab = 'history'}>
			History
		</button>
		<button class:active={activeTab === 'settings'} on:click={() => activeTab = 'settings'}>
			Settings
		</button>
	</nav>
	
	<main>
		{#if activeTab === 'dashboard'}
			<section class="dashboard">
				<div class="card">
					<h3>Status</h3>
					<div class="stat-grid">
						<div class="stat">
							<span class="label">Trading</span>
							<span class="value" class:on={settings.tradingEnabled} class:off={!settings.tradingEnabled}>
								{settings.tradingEnabled ? 'ON' : 'OFF'}
							</span>
						</div>
						<div class="stat">
							<span class="label">Profile</span>
							<span class="value">{status?.profile || '-'}</span>
						</div>
						<div class="stat">
							<span class="label">Symbol</span>
							<span class="value">{status?.symbol || '-'}</span>
						</div>
						<div class="stat">
							<span class="label">Trades</span>
							<span class="value">{status?.trade_count || 0}</span>
						</div>
					</div>
				</div>
				
				<div class="card">
					<h3>Current Position</h3>
					{#if status?.position}
						<div class="position">
							<div class="position-info">
								<span class="side long">LONG</span>
								<span class="entry">Entry: ${status.position.EntryPrice?.toFixed(2)}</span>
								<span class="qty">Qty: {status.position.Quantity?.toFixed(4)}</span>
							</div>
						</div>
					{:else}
						<p class="no-position">No active position</p>
					{/if}
				</div>
				
				<div class="card">
					<h3>Selected Profile</h3>
					{#if true}
						{@const profile = getSelectedProfile()}
						<div class="profile-info">
							<h4>{profile.name}</h4>
							<p>{profile.description}</p>
							<div class="backtest-stats">
								<span>Return: {profile.backtest.return}%</span>
								<span>CAGR: {profile.backtest.cagr}%</span>
								<span>MDD: {profile.backtest.mdd}%</span>
								<span>Calmar: {profile.backtest.calmar}</span>
							</div>
						</div>
					{/if}
				</div>
			</section>
			
		{:else if activeTab === 'history'}
			<section class="history">
				<div class="card">
					<h3>Trade History</h3>
					{#if trades.length > 0}
						<table>
							<thead>
								<tr>
									<th>Time</th>
									<th>Side</th>
									<th>Entry</th>
									<th>Exit</th>
									<th>Result</th>
									<th>PnL</th>
								</tr>
							</thead>
							<tbody>
								{#each trades as trade}
									<tr>
										<td>{new Date(trade.EntryTime).toLocaleString()}</td>
										<td class="side">{trade.Side}</td>
										<td>${trade.EntryPrice?.toFixed(2)}</td>
										<td>${trade.ExitPrice?.toFixed(2)}</td>
										<td class="result {trade.Result?.toLowerCase()}">{trade.Result}</td>
										<td>{@html formatPnL(trade.PnLPct)}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{:else}
						<p class="empty">No trades yet</p>
					{/if}
				</div>
			</section>
			
		{:else if activeTab === 'settings'}
			<section class="settings">
				<div class="card">
					<h3>Exchange API</h3>
					<div class="form-group">
						<label>API Key</label>
						<input type="password" bind:value={settings.apiKey} placeholder="Enter API Key" />
					</div>
					<div class="form-group">
						<label>Secret Key</label>
						<input type="password" bind:value={settings.secretKey} placeholder="Enter Secret Key" />
					</div>
				</div>
				
				<div class="card">
					<h3>Strategy Profile</h3>
					<div class="profiles">
						{#each PROFILES as profile}
							<label class="profile-option" class:selected={settings.profile === profile.id}>
								<input type="radio" bind:group={settings.profile} value={profile.id} />
								<div class="profile-content">
									<strong>{profile.name}</strong>
									<span class="desc">{profile.description}</span>
									<div class="mini-stats">
										<span>CAGR: {profile.backtest.cagr}%</span>
										<span>MDD: {profile.backtest.mdd}%</span>
										<span>Calmar: {profile.backtest.calmar}</span>
									</div>
								</div>
							</label>
						{/each}
					</div>
				</div>
				
				<div class="card">
					<h3>Trading Control</h3>
					<div class="toggle-section">
						<span>Enable Trading</span>
						<button 
							class="toggle-btn" 
							class:on={settings.tradingEnabled}
							on:click={handleToggle}
						>
							{settings.tradingEnabled ? 'ON' : 'OFF'}
						</button>
					</div>
					<p class="warning">⚠️ Enabling will start live trading with real funds</p>
				</div>
			</section>
		{/if}
	</main>
	
	<footer>
		<p>
			<a href={BACKTEST_URL} target="_blank" rel="noopener">
				📊 View Backtest Results
			</a>
			<span class="divider">|</span>
			<span>L-Shape Strategy v1.0</span>
		</p>
	</footer>
</div>

<style>
	:global(body) {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		background: #0f172a;
		color: #e2e8f0;
	}
	
	.container {
		max-width: 1200px;
		margin: 0 auto;
		padding: 20px;
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}
	
	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 20px;
	}
	
	h1 {
		margin: 0;
		font-size: 1.5rem;
	}
	
	.status-badge {
		padding: 6px 12px;
		border-radius: 20px;
		font-size: 0.8rem;
		font-weight: 600;
	}
	
	.status-badge.online {
		background: #22c55e20;
		color: #22c55e;
	}
	
	.status-badge.offline {
		background: #ef444420;
		color: #ef4444;
	}
	
	nav {
		display: flex;
		gap: 8px;
		margin-bottom: 20px;
	}
	
	nav button {
		padding: 10px 20px;
		border: none;
		background: #1e293b;
		color: #94a3b8;
		border-radius: 8px;
		cursor: pointer;
		font-size: 0.9rem;
		transition: all 0.2s;
	}
	
	nav button:hover {
		background: #334155;
	}
	
	nav button.active {
		background: #3b82f6;
		color: white;
	}
	
	main {
		flex: 1;
	}
	
	.card {
		background: #1e293b;
		border-radius: 12px;
		padding: 20px;
		margin-bottom: 16px;
	}
	
	.card h3 {
		margin: 0 0 16px 0;
		font-size: 1rem;
		color: #94a3b8;
	}
	
	.stat-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
		gap: 16px;
	}
	
	.stat {
		text-align: center;
	}
	
	.stat .label {
		display: block;
		font-size: 0.8rem;
		color: #64748b;
		margin-bottom: 4px;
	}
	
	.stat .value {
		font-size: 1.2rem;
		font-weight: 600;
	}
	
	.stat .value.on { color: #22c55e; }
	.stat .value.off { color: #ef4444; }
	
	.no-position, .empty {
		color: #64748b;
		text-align: center;
		padding: 20px;
	}
	
	.position-info {
		display: flex;
		gap: 16px;
		align-items: center;
	}
	
	.side.long {
		background: #22c55e20;
		color: #22c55e;
		padding: 4px 12px;
		border-radius: 4px;
		font-weight: 600;
	}
	
	.profile-info h4 {
		margin: 0 0 4px 0;
	}
	
	.profile-info p {
		color: #64748b;
		margin: 0 0 12px 0;
	}
	
	.backtest-stats {
		display: flex;
		gap: 16px;
		flex-wrap: wrap;
		font-size: 0.85rem;
		color: #94a3b8;
	}
	
	table {
		width: 100%;
		border-collapse: collapse;
	}
	
	th, td {
		padding: 12px;
		text-align: left;
		border-bottom: 1px solid #334155;
	}
	
	th {
		color: #64748b;
		font-weight: 500;
		font-size: 0.85rem;
	}
	
	.result.take_profit { color: #22c55e; }
	.result.stop_loss { color: #ef4444; }
	
	.form-group {
		margin-bottom: 16px;
	}
	
	.form-group label {
		display: block;
		margin-bottom: 6px;
		font-size: 0.85rem;
		color: #94a3b8;
	}
	
	.form-group input {
		width: 100%;
		padding: 10px 12px;
		border: 1px solid #334155;
		border-radius: 8px;
		background: #0f172a;
		color: #e2e8f0;
		font-size: 0.9rem;
		box-sizing: border-box;
	}
	
	.profiles {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	
	.profile-option {
		display: flex;
		align-items: flex-start;
		gap: 12px;
		padding: 16px;
		border: 2px solid #334155;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.2s;
	}
	
	.profile-option:hover {
		border-color: #3b82f6;
	}
	
	.profile-option.selected {
		border-color: #3b82f6;
		background: #3b82f610;
	}
	
	.profile-option input {
		margin-top: 4px;
	}
	
	.profile-content {
		flex: 1;
	}
	
	.profile-content strong {
		display: block;
		margin-bottom: 4px;
	}
	
	.profile-content .desc {
		font-size: 0.85rem;
		color: #64748b;
	}
	
	.mini-stats {
		margin-top: 8px;
		display: flex;
		gap: 12px;
		font-size: 0.8rem;
		color: #94a3b8;
	}
	
	.toggle-section {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	
	.toggle-btn {
		padding: 8px 24px;
		border: none;
		border-radius: 20px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s;
		background: #334155;
		color: #94a3b8;
	}
	
	.toggle-btn.on {
		background: #22c55e;
		color: white;
	}
	
	.warning {
		margin-top: 12px;
		padding: 12px;
		background: #ef444420;
		border-radius: 8px;
		color: #fca5a5;
		font-size: 0.85rem;
	}
	
	footer {
		margin-top: 20px;
		padding: 20px;
		text-align: center;
		border-top: 1px solid #334155;
	}
	
	footer a {
		color: #3b82f6;
		text-decoration: none;
	}
	
	footer a:hover {
		text-decoration: underline;
	}
	
	footer .divider {
		margin: 0 12px;
		color: #334155;
	}
</style>
