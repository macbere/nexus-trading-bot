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
    try {
        const [stats, trades, balance] = await Promise.all([
            fetch('/api/stats').then(r => r.json()),
            fetch('/api/trades/open').then(r => r.json()),
            fetch('/api/balance').then(r => r.json())
        ]);
        
        updateOverviewCards(stats, balance);
        updateLiveTrades(trades);
        updateActivityLog(stats.logs || []);
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
