function updateClock() {
    const now = new Date();
    const time = now.getHours().toString().padStart(2, '0') + ":" + 
                 now.getMinutes().toString().padStart(2, '0') + ":" + 
                 now.getSeconds().toString().padStart(2, '0');
    document.getElementById('clock').innerText = time;
}

async function updateDashboard() {
    try {
        const response = await fetch('/api/symbols_data');
        const data = await response.json();

        if (data.err === 'unauth') {
            window.location.href = '/login';
            return;
        }

        // 1. Simvollarni yangilash (Cards)
        const grid = document.getElementById('symbols-grid');
        grid.innerHTML = '';
        
        for (const [sym, info] of Object.entries(data.symbols)) {
            const isUp = parseFloat(info.change) >= 0;
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <h3>${sym}</h3>
                <div class="price-box ${isUp ? 'up' : 'down'}">$${info.price}</div>
                <div class="change-box ${isUp ? 'up' : 'down'}">
                    ${isUp ? '▲' : '▼'} ${Math.abs(info.change)}%
                </div>
                <div style="margin-top: 15px; font-size: 0.7rem; color: #555;">
                    SMC TREND: <span style="color: var(--accent-cyan)">ANALYZING...</span>
                </div>
            `;
            grid.appendChild(card);
        }

        // 2. Signallar logini yangilash
        const log = document.getElementById('signals-log');
        if (data.signals && data.signals.length > 0) {
            log.innerHTML = ''; // Tozalash
            data.signals.slice(-10).reverse().forEach(sig => {
                const row = document.createElement('div');
                row.className = 'signal-row';
                const typeColor = sig.direction === 'BUY' ? 'var(--accent-green)' : 'var(--accent-red)';
                row.innerHTML = `
                    <span style="font-weight: 800; color: var(--accent-cyan);">${sig.symbol}</span>
                    <span style="font-weight: 800; color: ${typeColor};">${sig.direction}</span>
                    <span style="color: var(--text-dim);">${sig.reason || 'SMC Setup'}</span>
                    <span style="color: var(--accent-purple); font-weight: 800;">${sig.quality || 75}%</span>
                `;
                log.appendChild(row);
            });
        }

        // 3. Genetik Engine vizualizatsiyasi (Mock update)
        document.getElementById('fitness-score').innerText = (0.95 + Math.random() * 0.04).toFixed(3);

    } catch (e) {
        console.error("Dashboard update error:", e);
    }
}

// Intervallar
setInterval(updateClock, 1000);
setInterval(updateDashboard, 5000);

// Start
updateClock();
updateDashboard();
