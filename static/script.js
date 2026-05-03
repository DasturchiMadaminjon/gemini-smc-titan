async function updateDashboard() {
    try {
        const response = await fetch('/api/symbols_data');
        const data = await response.json();

        if (data.err === 'unauth') {
            window.location.href = '/login';
            return;
        }

        // Simvollarni yangilash
        const grid = document.getElementById('symbols-grid');
        grid.innerHTML = '';
        
        for (const [sym, info] of Object.entries(data.symbols)) {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <h3>${sym}</h3>
                <p class="price-up" style="font-size: 1.5em; font-weight: bold;">$${info.price}</p>
                <p style="font-size: 0.8em; color: #a0a0a0;">O'zgarish: ${info.change}%</p>
            `;
            grid.appendChild(card);
        }

    } catch (e) {
        console.error("Dashboard update error:", e);
    }
}

// Har 5 soniyada yangilab turish
setInterval(updateDashboard, 5000);
updateDashboard();
