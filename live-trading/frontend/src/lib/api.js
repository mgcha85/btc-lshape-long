import { API_BASE } from './config.js';

export async function fetchStatus() {
	const res = await fetch(`${API_BASE}/api/status`);
	return res.json();
}

export async function fetchConfig() {
	const res = await fetch(`${API_BASE}/api/config`);
	return res.json();
}

export async function fetchPosition() {
	const res = await fetch(`${API_BASE}/api/position`);
	return res.json();
}

export async function fetchTrades() {
	const res = await fetch(`${API_BASE}/api/trades`);
	return res.json();
}

export async function toggleTrading(enabled) {
	const res = await fetch(`${API_BASE}/api/toggle`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ enabled })
	});
	return res.json();
}

export async function fetchProfiles() {
	const res = await fetch(`${API_BASE}/api/profiles`);
	return res.json();
}

export async function updateConfig(config) {
	const res = await fetch(`${API_BASE}/api/config`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(config)
	});
	return res.json();
}

export async function toggleTelegram(enabled) {
	const res = await fetch(`${API_BASE}/api/telegram/toggle`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ enabled })
	});
	return res.json();
}
