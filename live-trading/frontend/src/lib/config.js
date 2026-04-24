export const API_BASE = '';

export const BACKTEST_URL = 'https://mgcha85.github.io/btc-lshape-long/realistic-backtest';

export const PROFILES = [
	{
		id: '5m-aggressive',
		name: '5M Aggressive',
		description: 'High risk, high return',
		timeframe: '5m',
		positionSize: 0.30,
		leverage: 10,
		backtest: {
			return: 1012.0,
			cagr: 46.8,
			mdd: 46.3,
			calmar: 1.01,
			winRate: 45.5,
			trades: 334
		}
	},
	{
		id: '15m-aggressive',
		name: '15M Aggressive',
		description: 'Maximum returns',
		timeframe: '15m',
		positionSize: 0.30,
		leverage: 10,
		backtest: {
			return: 1862.4,
			cagr: 60.7,
			mdd: 69.9,
			calmar: 0.87,
			winRate: 42.4,
			trades: 255
		}
	},
	{
		id: '5m-balanced',
		name: '5M Balanced',
		description: 'Best risk-adjusted (Recommended)',
		timeframe: '5m',
		positionSize: 0.20,
		leverage: 10,
		backtest: {
			return: 510.9,
			cagr: 33.4,
			mdd: 32.0,
			calmar: 1.05,
			winRate: 45.5,
			trades: 334
		}
	}
];
