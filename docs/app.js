const DATA_URL = 'data/players.json';

let playerStats = {};
let activePlayer = null;

async function loadPlayerData() {
    const response = await fetch(DATA_URL);
    if (!response.ok) {
        throw new Error(`Failed to load player data (${response.status})`);
    }
    return response.json();
}

function avgTeammateWinRate(stats) {
    if (!stats.teammateWinRates.length) return 0;
    return (
        stats.teammateWinRates.reduce((sum, rate) => sum + rate, 0) /
        stats.teammateWinRates.length *
        100
    );
}

function renderBarList(container, entries, maxValue, className = '') {
    container.innerHTML = '';
    container.className = `bar-list ${className}`.trim();

    if (!entries.length) {
        container.innerHTML = '<li><span class="bar-row"><span class="name">No data</span></span></li>';
        return;
    }

    entries.forEach(([name, count]) => {
        const li = document.createElement('li');
        const pct = maxValue ? (count / maxValue) * 100 : 0;
        li.innerHTML = `
            <div class="bar-row">
                <span class="name">${name}</span>
                <span class="count">${count}</span>
            </div>
            <div class="bar-track">
                <div class="bar-fill" style="width: ${pct}%"></div>
            </div>
        `;
        container.appendChild(li);
    });
}

function renderPlayer(playerName) {
    const stats = playerStats[playerName];
    if (!stats) return;

    activePlayer = playerName;
    document.querySelectorAll('.player-chip').forEach((chip) => {
        chip.classList.toggle('active', chip.dataset.player === playerName);
        chip.setAttribute('aria-selected', chip.dataset.player === playerName ? 'true' : 'false');
    });

    const dashboard = document.getElementById('dashboard');
    dashboard.hidden = false;
    dashboard.classList.remove('is-switching');
    void dashboard.offsetWidth;
    dashboard.classList.add('is-switching');

    document.getElementById('playerTitle').textContent = playerName;

    const recordBadge = document.getElementById('recordBadge');
    recordBadge.textContent = `${stats.wins}W · ${stats.losses}L`;
    recordBadge.classList.remove('win-heavy', 'loss-heavy');
    if (stats.WinRate >= 55) recordBadge.classList.add('win-heavy');
    if (stats.WinRate <= 45) recordBadge.classList.add('loss-heavy');

    document.getElementById('statWinRate').textContent = `${stats.WinRate.toFixed(1)}%`;
    document.getElementById('statGames').textContent = stats.matches;
    document.getElementById('statKda').textContent = stats.kda.toFixed(2);
    document.getElementById('statDpm').textContent = Math.round(stats.dpm).toLocaleString();
    document.getElementById('winRateMeter').style.width = `${Math.min(stats.WinRate, 100)}%`;

    const combatStats = document.getElementById('combatStats');
    const teammateWr = avgTeammateWinRate(stats);
    const rows = [
        ['K / D / A', `${stats.kills} / ${stats.deaths} / ${stats.assists}`],
        ['Damage to champions', stats.damage.toLocaleString()],
        ['CS per minute', stats.total_cspm.toFixed(2)],
        ['Non-support CS/min', stats.cspm.toFixed(2)],
        ['Pentakills', stats.penta_kills],
        ['Avg teammate WR', `${teammateWr.toFixed(1)}%`],
        ['Time played', `${Math.round(stats.time_played / 60)} min`],
    ];

    combatStats.innerHTML = rows
        .map(
            ([label, value]) => `
                <div>
                    <dt>${label}</dt>
                    <dd>${value}</dd>
                </div>
            `
        )
        .join('');

    const champions = Object.entries(stats.skins).sort((a, b) => b[1] - a[1]);
    const teammates = Object.entries(stats.teammates).sort((a, b) => b[1] - a[1]);

    renderBarList(
        document.getElementById('champList'),
        champions,
        champions[0]?.[1] ?? 0
    );
    renderBarList(
        document.getElementById('teammateList'),
        teammates,
        teammates[0]?.[1] ?? 0,
        'teammates'
    );
}

function buildPlayerRail(sortedNames) {
    const rail = document.getElementById('playerRail');
    rail.innerHTML = '';

    sortedNames.forEach((name) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'player-chip';
        button.dataset.player = name;
        button.setAttribute('role', 'tab');
        button.innerHTML = `
            ${name}
            <span class="chip-count">${playerStats[name].matches} games</span>
        `;
        button.addEventListener('click', () => renderPlayer(name));
        rail.appendChild(button);
    });
}

async function initialize() {
    const loading = document.getElementById('loading');
    const emptyState = document.getElementById('emptyState');
    const meta = document.getElementById('meta');

    try {
        const payload = await loadPlayerData();
        playerStats = payload.players;

        const generatedAt = new Date(payload.generatedAt).toLocaleString(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short',
        });
        meta.textContent = `${payload.matchCount} matches · ${generatedAt}`;

        const sortedNames = Object.keys(playerStats).sort(
            (a, b) => playerStats[b].matches - playerStats[a].matches
        );

        if (!sortedNames.length) {
            emptyState.hidden = false;
            return;
        }

        buildPlayerRail(sortedNames);
        renderPlayer(sortedNames[0]);
    } catch (error) {
        console.error(error);
        meta.textContent = 'offline';
        emptyState.textContent = 'Could not load stats.';
        emptyState.hidden = false;
    } finally {
        loading.style.display = 'none';
    }
}

initialize();
