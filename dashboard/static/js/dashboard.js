
// Chart instances
let pnlChart, winRateChart, equityChart;

// Initialize charts after DOM loads
function initializeCharts() {
    // P&L Chart
    const pnlCtx = document.getElementById('pnlChart').getContext('2d');
    pnlChart = new Chart(pnlCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'P&L ($)',
                data: [],
                borderColor: '#00d9a5',
                backgroundColor: 'rgba(0, 217, 165, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#b8b8d1' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#b8b8d1' }
                }
            }
        }
    });
    
    // Win Rate Chart
    const winCtx = document.getElementById('winRateChart').getContext('2d');
    winRateChart = new Chart(winCtx, {
        type: 'doughnut',        data: {
            labels: ['Wins', 'Losses'],
            datasets: [{
                data: [0, 0],
                backgroundColor: ['#00d9a5', '#dc3545'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#b8b8d1' } }
            }
        }
    });
    
    // Equity Chart
    const equityCtx = document.getElementById('equityChart').getContext('2d');
    equityChart = new Chart(equityCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Equity ($)',
                data: [],
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#b8b8d1' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#b8b8d1' }
                }
            }
        }
    });}

// Update charts with new data
function updateCharts(analyticsData) {
    // Update P&L Chart
    if (pnlChart && analyticsData.pnl_history) {
        pnlChart.data.labels = analyticsData.pnl_history.map(p => p.time);
        pnlChart.data.datasets[0].data = analyticsData.pnl_history.map(p => p.value);
        pnlChart.update();
    }
    
    // Update Win Rate Chart
    if (winRateChart) {
        const wins = analyticsData.wins || 0;
        const losses = analyticsData.losses || 0;
        winRateChart.data.datasets[0].data = [wins, losses];
        winRateChart.update();
    }
    
    // Update Equity Chart
    if (equityChart && analyticsData.equity_history) {
        equityChart.data.labels = analyticsData.equity_history.map(e => e.time);
        equityChart.data.datasets[0].data = analyticsData.equity_history.map(e => e.value);
        equityChart.update();
    }
}

// Update performance statistics
function updatePerformanceStats(stats) {
    document.getElementById('totalProfit').textContent = `+$${(stats.total_profit || 0).toFixed(2)}`;
    document.getElementById('bestTrade').textContent = `+$${(stats.best_trade || 0).toFixed(2)}`;
    document.getElementById('worstTrade').textContent = `-$${Math.abs(stats.worst_trade || 0).toFixed(2)}`;
    document.getElementById('avgWinLoss').textContent = `$${(stats.avg_win || 0).toFixed(2)}/$${(stats.avg_loss || 0).toFixed(2)}`;
    document.getElementById('profitFactor').textContent = (stats.profit_factor || 0).toFixed(2);
    document.getElementById('sharpeRatio').textContent = (stats.sharpe_ratio || 0).toFixed(2);
    document.getElementById('maxDrawdown').textContent = `${(stats.max_drawdown || 0).toFixed(2)}%`;
    document.getElementById('totalTrades').textContent = stats.total_trades || 0;
}

// Update trade history table
function updateTradeHistory(trades) {
    const tbody = document.getElementById('tradeHistoryBody');
    
    if (!trades || trades.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="12" class="text-center text-muted py-4">
                    <i class="bi bi-hourglass-split me-2"></i>No trade history yet...
                </td>
            </tr>        `;
        return;
    }
    
    tbody.innerHTML = trades.map(trade => `
        <tr>
            <td><small>${trade.timestamp || 'N/A'}</small></td>
            <td><strong>${trade.pair}</strong></td>
            <td><span class="badge ${trade.direction === 'LONG' ? 'badge-long' : 'badge-short'}">${trade.direction}</span></td>
            <td>$${(trade.entry_price || 0).toFixed(2)}</td>
            <td>$${(trade.exit_price || 0).toFixed(2)}</td>
            <td>$${(trade.size || 0).toFixed(2)}</td>
            <td class="${trade.pnl >= 0 ? 'profit' : 'loss'}">
                ${trade.pnl >= 0 ? '+' : ''}$${Math.abs(trade.pnl || 0).toFixed(2)}
            </td>
            <td class="${trade.pnl_percent >= 0 ? 'profit' : 'loss'}">
                ${(trade.pnl_percent || 0).toFixed(2)}%
            </td>
            <td><small>${formatDuration(trade.duration || 0)}</small></td>
            <td>${trade.ml_score || 0}%</td>
            <td><small>${trade.pattern || 'N/A'}</small></td>
            <td><span class="badge ${trade.pnl >= 0 ? 'bg-success' : 'bg-danger'}">${trade.pnl >= 0 ? 'WIN' : 'LOSS'}</span></td>
        </tr>
    `).join('');
}

// Export trades to CSV
function exportTrades() {
    fetch('/api/trades/history')
        .then(r => r.json())
        .then(trades => {
            const csv = [
                ['Date/Time', 'Pair', 'Direction', 'Entry', 'Exit', 'Size', 'P&L', 'P&L %', 'Duration', 'ML Score', 'Pattern', 'Status'].join(','),
                ...trades.map(t => [
                    t.timestamp, t.pair, t.direction, t.entry_price, t.exit_price,
                    t.size, t.pnl, t.pnl_percent, t.duration, t.ml_score, t.pattern,
                    t.pnl >= 0 ? 'WIN' : 'LOSS'
                ].join(','))
            ].join('\n');
            
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `trades_${new Date().toISOString().split('T')[0]}.csv`;
            a.click();
        });
}


// Dashboard JavaScript - Real-time Updates

let autoRefreshInterval;
let theme = localStorage.getItem('theme') || 'dark';

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
    applyTheme(theme);
    loadDashboardData();
    startAutoRefresh();
    setupEventListeners();
});

// Apply theme
function applyTheme(selectedTheme) {
    document.documentElement.setAttribute('data-theme', selectedTheme);
    document.getElementById('themeIcon').className = 
        selectedTheme === 'dark' ? 'bi bi-moon-stars-fill' : 'bi bi-sun-fill';
    localStorage.setItem('theme', selectedTheme);
}

// Toggle theme
function toggleTheme() {
    theme = theme === 'dark' ? 'light' : 'dark';
    applyTheme(theme);
}

// Setup event listeners
function setupEventListeners() {
    // Auto-save settings on change (debounced)
    const settingsInputs = document.querySelectorAll('#settingsForm input');
    settingsInputs.forEach(input => {
        input.addEventListener('change', debounce(saveSettings, 1000));
    });
}

// Debounce utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
// Start auto-refresh
function startAutoRefresh() {
    autoRefreshInterval = setInterval(loadDashboardData, 5000);
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
}

// Load all dashboard data
async function loadDashboardData() {
    // Initialize charts if not already done
    if (!pnlChart) initializeCharts();
    
    try {
        const [stats, analytics, tradeHistory, trades, balance] = await Promise.all([
            fetch('/api/stats').then(r => r.json()),
            fetch('/api/analytics').then(r => r.json()),
            fetch('/api/trades/history').then(r => r.json()),
            fetch('/api/trades/open').then(r => r.json()),
            fetch('/api/balance').then(r => r.json())
        ]);
        
        updateOverviewCards(stats, balance);
        updateLiveTrades(trades);
        updateActivityLog(stats.logs || []);
        updateCharts(analytics);
        updateTradeHistory(tradeHistory);
        updatePerformanceStats(stats);
        updateTimestamp();
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        updateConnectionStatus(false);
    }
}

// Update overview cards
function updateOverviewCards(stats, balance) {
    // Balance
    document.getElementById('totalBalance').textContent = 
        `$${(balance.total || 0).toFixed(2)}`;
    
    // Daily P&L
    const pnl = stats.daily_pnl || 0;
    const pnlElement = document.getElementById('dailyPnl');
    const pnlPercent = document.getElementById('pnlPercent');
    const pnlCard = document.getElementById('pnlCard');
    
    pnlElement.textContent = `${pnl >= 0 ? '+' : ''}$${Math.abs(pnl).toFixed(2)}`;
    pnlElement.className = `card-title mb-0 ${pnl >= 0 ? 'profit' : 'loss'}`;
    
    const pnlPct = stats.daily_pnl_percent || 0;
    pnlPercent.textContent = `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%`;    
    // Win Rate
    const winRate = stats.win_rate || 0;
    document.getElementById('winRate').textContent = `${winRate.toFixed(1)}%`;
    document.getElementById('winLoss').textContent = 
        `${stats.wins || 0}W / ${stats.losses || 0}L`;
    
    // Active Positions
    const active = stats.active_positions || 0;
    const maxPositions = stats.max_positions || 5;
    document.getElementById('activePositions').textContent = `${active}/${maxPositions}`;
    document.getElementById('tradesToday').textContent = 
        `${stats.trades_today || 0} trades today`;
}

// Update live trades table
function updateLiveTrades(trades) {
    const tbody = document.getElementById('liveTradesBody');
    const countBadge = document.getElementById('openTradesCount');
    
    countBadge.textContent = `${trades.length} Open`;
    
    if (trades.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-muted py-4">
                    <i class="bi bi-hourglass-split me-2"></i>No active trades - Waiting for opportunities...
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = trades.map(trade => `
        <tr>
            <td><strong>${trade.pair}</strong></td>
            <td><span class="badge ${trade.direction === 'LONG' ? 'badge-long' : 'badge-short'}">
                ${trade.direction}
            </span></td>
            <td>$${trade.entry_price?.toFixed(2) || '0.00'}</td>
            <td>$${trade.current_price?.toFixed(2) || '0.00'}</td>
            <td class="${trade.pnl >= 0 ? 'profit' : 'loss'}">
                ${trade.pnl >= 0 ? '+' : ''}$${Math.abs(trade.pnl || 0).toFixed(2)}
                <br><small>${trade.pnl_percent?.toFixed(2) || 0}%</small>
            </td>
            <td>
                <small>TP: $${trade.tp?.toFixed(2)}</small><br>
                <small>SL: $${trade.sl?.toFixed(2)}</small>
            </td>
            <td><small>${formatDuration(trade.duration || 0)}</small></td>            <td>
                <div class="progress" style="height: 6px; width: 60px;">
                    <div class="progress-bar bg-success" role="progressbar" 
                         style="width: ${trade.ml_score || 0}%"></div>
                </div>
                <small>${trade.ml_score || 0}%</small>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-danger" 
                        onclick="closePosition('${trade.id || trade.pair}')">
                    <i class="bi bi-x-circle"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// Format duration in human readable format
function formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
    return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
}

// Update activity log
function updateActivityLog(logs) {
    const logList = document.getElementById('activityLog');
    
    if (!logs || logs.length === 0) {
        logList.innerHTML = `
            <li class="text-muted text-center py-3">
                <i class="bi bi-info-circle me-2"></i>Bot activity will appear here...
            </li>
        `;
        return;
    }
    
    logList.innerHTML = logs.slice(0, 10).map(log => `
        <li>
            <small class="text-muted">${log.time || 'Just now'}</small>
            <span class="${log.type === 'error' ? 'text-danger' : log.type === 'success' ? 'text-success' : ''}">
                ${log.message}
            </span>
        </li>
    `).join('');
}

// Update timestamp
function updateTimestamp() {    const now = new Date();
    document.getElementById('lastUpdate').textContent = 
        `Last update: ${now.toLocaleTimeString()}`;
}

// Update connection status
function updateConnectionStatus(connected) {
    const status = document.getElementById('connectionStatus');
    if (connected) {
        status.className = 'badge bg-success';
        status.innerHTML = '<i class="bi bi-circle-fill"></i> Connected';
    } else {
        status.className = 'badge bg-danger pulse';
        status.innerHTML = '<i class="bi bi-circle-fill"></i> Disconnected';
    }
}

// Manual refresh
function refreshData() {
    const refreshBtn = event.target.closest('button');
    const icon = refreshBtn.querySelector('i');
    icon.classList.add('bi-spin');
    
    loadDashboardData().finally(() => {
        setTimeout(() => icon.classList.remove('bi-spin'), 500);
    });
}

// Save settings
async function saveSettings() {
    const settings = {
        max_positions: parseInt(document.getElementById('maxPositions').value),
        min_trade_score: parseInt(document.getElementById('minTradeScore').value),
        position_size: parseFloat(document.getElementById('positionSize').value),
        daily_loss_limit: parseFloat(document.getElementById('dailyLossLimit').value)
    };
    
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(settings)
        });
        
        const result = await response.json();
        if (result.success) {
            addLogEntry('Settings saved successfully', 'success');
        } else {
            addLogEntry('Failed to save settings: ' + result.error, 'error');
        }    } catch (error) {
        addLogEntry('Error saving settings: ' + error.message, 'error');
    }
}

// Emergency stop
async function emergencyStop() {
    if (!confirm('⚠️ EMERGENCY STOP: Close all positions and pause trading?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/emergency-stop', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const result = await response.json();
        addLogEntry(result.message || 'Emergency stop initiated', 
                   result.success ? 'success' : 'error');
        
        // Refresh data after stop
        setTimeout(loadDashboardData, 2000);
        
    } catch (error) {
        addLogEntry('Emergency stop error: ' + error.message, 'error');
    }
}

// Close individual position
async function closePosition(tradeId) {
    if (!confirm(`Close position ${tradeId}?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/trades/close', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ trade_id: tradeId })
        });
        
        const result = await response.json();
        addLogEntry(result.message || 'Position closed', 
                   result.success ? 'success' : 'error');
        
        // Refresh trades
        setTimeout(() => {
            fetch('/api/trades/open')
                .then(r => r.json())                .then(trades => updateLiveTrades(trades));
        }, 1000);
        
    } catch (error) {
        addLogEntry('Error closing position: ' + error.message, 'error');
    }
}

// Add log entry
function addLogEntry(message, type = 'info') {
    const logList = document.getElementById('activityLog');
    const now = new Date().toLocaleTimeString();
    
    const entry = document.createElement('li');
    entry.innerHTML = `
        <small class="text-muted">${now}</small>
        <span class="${type === 'error' ? 'text-danger' : type === 'success' ? 'text-success' : ''}">
            ${message}
        </span>
    `;
    
    logList.insertBefore(entry, logList.firstChild);
    
    // Keep only last 20 entries
    while (logList.children.length > 20) {
        logList.removeChild(logList.lastChild);
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});
