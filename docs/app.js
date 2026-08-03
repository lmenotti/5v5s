const DATA_URL = 'data/players.json';
const LEAGUE_URL = 'data/league.json';

let playerStats = {};
let leagueData = null;
let activePlayer = null;
let activeView = 'profile';

async function loadJson(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Failed to load ${url} (${response.status})`);
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

function renderMetaBars(container, entries, valueKey = 'games') {
    container.innerHTML = '';
    if (!entries.length) {
        container.innerHTML = '<li><span class="bar-row"><span class="name">No data</span></span></li>';
        return;
    }
    const maxValue = entries[0][valueKey];
    entries.forEach((entry) => {
        const li = document.createElement('li');
        const pct = maxValue ? (entry[valueKey] / maxValue) * 100 : 0;
        li.innerHTML = `
            <div class="bar-row">
                <span class="name">${entry.champion}</span>
                <span class="count">${entry.games} · ${entry.winRate}%</span>
            </div>
            <div class="bar-track">
                <div class="bar-fill" style="width: ${pct}%"></div>
            </div>
        `;
        container.appendChild(li);
    });
}

function renderLeagueStrip(totals) {
    const strip = document.getElementById('leagueStrip');
    const items = [
        ['matches', totals.matches],
        ['players', totals.players],
        ['total kills', totals.totalKills.toLocaleString()],
        ['avg game', `${totals.avgGameMinutes}m`],
    ];
    strip.innerHTML = items
        .map(
            ([label, value]) => `
                <div class="strip-stat">
                    <span class="label">${label}</span>
                    <span class="value">${value}</span>
                </div>
            `
        )
        .join('');
    strip.hidden = false;
}

function setView(view) {
    activeView = view;
    document.querySelectorAll('.view-tab').forEach((tab) => {
        tab.classList.toggle('active', tab.dataset.view === view);
    });

    document.querySelectorAll('.view-panel').forEach((panel) => {
        panel.hidden = true;
    });
    document.querySelectorAll('.view-profile-only').forEach((el) => {
        el.hidden = view !== 'profile';
    });

    if (view === 'profile') {
        document.getElementById('dashboard').hidden = !activePlayer;
    } else if (view === 'rankings') {
        document.getElementById('rankingsPanel').hidden = false;
        renderRankings();
    } else if (view === 'meta') {
        document.getElementById('metaPanel').hidden = false;
        renderMeta();
    } else if (view === 'duos') {
        document.getElementById('duosPanel').hidden = false;
        renderDuos();
    }
}

function renderRankings() {
    if (!leagueData) return;
    const tbody = document.querySelector('#rankTable tbody');
    tbody.innerHTML = leagueData.leaderboard
        .map(
            (row) => `
                <tr data-player="${row.name}" class="${row.name === activePlayer ? 'is-active' : ''}">
                    <td class="rank-num">${String(row.rank).padStart(2, '0')}</td>
                    <td class="player-cell">${row.name}</td>
                    <td>${row.matches}</td>
                    <td>${row.wins}W · ${row.losses}L</td>
                    <td class="wr-cell">${row.winRate.toFixed(1)}%</td>
                    <td>${row.kda.toFixed(2)}</td>
                    <td>${Math.round(row.dpm).toLocaleString()}</td>
                </tr>
            `
        )
        .join('');

    tbody.querySelectorAll('tr').forEach((row) => {
        row.addEventListener('click', () => {
            const name = row.dataset.player;
            if (playerStats[name]) {
                renderPlayer(name);
                setView('profile');
            }
        });
    });
}

function renderMeta() {
    if (!leagueData) return;
    const totals = leagueData.totals;
    document.getElementById('metaTotals').innerHTML = [
        ['Registered players', totals.players],
        ['Matches tracked', totals.matches],
        ['Combined kills', totals.totalKills.toLocaleString()],
        ['Combined damage', totals.totalDamage.toLocaleString()],
        ['Average game length', `${totals.avgGameMinutes} min`],
    ]
        .map(
            ([label, value]) => `
                <div>
                    <dt>${label}</dt>
                    <dd>${value}</dd>
                </div>
            `
        )
        .join('');

    renderMetaBars(document.getElementById('metaChamps'), leagueData.championMeta.slice(0, 12));
}

function renderDuos() {
    const list = document.getElementById('duoList');
    if (!leagueData?.duos?.length) {
        list.innerHTML = '<li class="duo-card"><span class="duo-names">Not enough shared games for duo stats yet.</span></li>';
        return;
    }

    list.innerHTML = leagueData.duos
        .map(
            (duo) => `
                <li class="duo-card">
                    <div>
                        <div class="duo-names">${duo.playerA} + ${duo.playerB}</div>
                        <div class="duo-meta">
                            <span>${duo.games} games</span>
                        </div>
                    </div>
                    <div class="duo-wr">
                        ${duo.winRate.toFixed(1)}%
                        <small>win rate</small>
                    </div>
                    <div class="duo-meter">
                        <div class="duo-meter-fill" style="width: ${Math.min(duo.winRate, 100)}%"></div>
                    </div>
                </li>
            `
        )
        .join('');
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

    const teammateWr = avgTeammateWinRate(stats);
    document.getElementById('combatStats').innerHTML = [
        ['K / D / A', `${stats.kills} / ${stats.deaths} / ${stats.assists}`],
        ['Damage to champions', stats.damage.toLocaleString()],
        ['CS per minute', stats.total_cspm.toFixed(2)],
        ['Non-support CS/min', stats.cspm.toFixed(2)],
        ['Pentakills', stats.penta_kills],
        ['Avg teammate WR', `${teammateWr.toFixed(1)}%`],
        ['Time played', `${Math.round(stats.time_played / 60)} min`],
    ]
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

    renderBarList(document.getElementById('champList'), champions, champions[0]?.[1] ?? 0);
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
        button.addEventListener('click', () => {
            renderPlayer(name);
            if (activeView !== 'profile') setView('profile');
        });
        rail.appendChild(button);
    });
}

function setupViewNav() {
    const nav = document.getElementById('viewNav');
    nav.hidden = false;
    nav.querySelectorAll('.view-tab').forEach((tab) => {
        tab.addEventListener('click', () => setView(tab.dataset.view));
    });
}

async function initialize() {
    const loading = document.getElementById('loading');
    const emptyState = document.getElementById('emptyState');
    const meta = document.getElementById('meta');

    try {
        const [playersPayload, leaguePayload] = await Promise.all([
            loadJson(DATA_URL),
            loadJson(LEAGUE_URL),
        ]);

        playerStats = playersPayload.players;
        leagueData = leaguePayload;

        const generatedAt = new Date(playersPayload.generatedAt).toLocaleString(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short',
        });
        meta.textContent = `${playersPayload.matchCount} matches · ${generatedAt}`;

        renderLeagueStrip(leagueData.totals);
        setupViewNav();

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
