const DATA_URL = 'data/players.json';
const LEAGUE_URL = 'data/league.json';

let playerStats = {};
let leagueData = null;
let activePlayer = null;
let activeView = 'profile';
let sortedPlayerNames = [];

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

function h2hKey(nameA, nameB) {
    return [nameA, nameB].sort().join('|');
}

function getHeadToHead(nameA, nameB) {
    return leagueData?.headToHead?.[h2hKey(nameA, nameB)] || null;
}

function renderSparkline(form) {
    const block = document.getElementById('formBlock');
    const svg = document.getElementById('formSparkline');
    const summary = document.getElementById('formSummary');

    if (!form?.length) {
        block.hidden = true;
        return;
    }

    block.hidden = false;
    const wins = form.filter(Boolean).length;
    summary.textContent = `${wins}W · ${form.length - wins}L in last ${form.length}`;

    const barWidth = 200 / form.length;
    svg.innerHTML = form
        .map((win, index) => {
            const x = index * barWidth + 1;
            const width = Math.max(barWidth - 2, 2);
            const height = win ? 34 : 14;
            const y = 40 - height;
            const fill = win ? 'var(--win)' : 'var(--loss)';
            return `<rect class="spark-bar" x="${x}" y="${y}" width="${width}" height="${height}" fill="${fill}" rx="1" opacity="0.9"/>`;
        })
        .join('');
}

function renderMvpBanner() {
    const banner = document.getElementById('mvpBanner');
    const mvp = leagueData?.mvp;
    if (!mvp) {
        banner.hidden = true;
        return;
    }

    banner.hidden = false;
    banner.innerHTML = `
        <div class="mvp-badge">mvp</div>
        <div class="mvp-copy">
            <h2>${mvp.name}</h2>
            <p>League MVP · ${mvp.matches} games · best blend of win rate and impact</p>
        </div>
        <div class="mvp-stats">
            <div class="mvp-stat"><span class="label">wr</span><span class="value">${mvp.winRate.toFixed(1)}%</span></div>
            <div class="mvp-stat"><span class="label">kda</span><span class="value">${mvp.kda.toFixed(2)}</span></div>
            <div class="mvp-stat"><span class="label">dpm</span><span class="value">${Math.round(mvp.dpm).toLocaleString()}</span></div>
        </div>
    `;
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

function renderMetaBars(container, entries) {
    container.innerHTML = '';
    if (!entries.length) {
        container.innerHTML = '<li><span class="bar-row"><span class="name">No data</span></span></li>';
        return;
    }
    const maxValue = entries[0].games;
    entries.forEach((entry) => {
        const li = document.createElement('li');
        const pct = maxValue ? (entry.games / maxValue) * 100 : 0;
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
    } else if (view === 'compare') {
        document.getElementById('comparePanel').hidden = false;
        renderCompare();
    } else if (view === 'draft') {
        const panel = document.getElementById('draftPanel');
        panel.hidden = false;
        renderDraftSlots();
        updateDraftSimulateButton();
        panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (view === 'rankings') {
        document.getElementById('rankingsPanel').hidden = false;
        renderRankings();
    } else if (view === 'records') {
        document.getElementById('recordsPanel').hidden = false;
        renderRecords();
    } else if (view === 'meta') {
        document.getElementById('metaPanel').hidden = false;
        renderMeta();
    } else if (view === 'duos') {
        document.getElementById('duosPanel').hidden = false;
        renderDuos();
    }
}

function populateCompareSelects() {
    const selectA = document.getElementById('compareA');
    const selectB = document.getElementById('compareB');
    const options = sortedPlayerNames
        .map((name) => `<option value="${name}">${name}</option>`)
        .join('');

    selectA.innerHTML = options;
    selectB.innerHTML = options;
    selectA.value = sortedPlayerNames[0] || '';
    selectB.value = sortedPlayerNames[Math.min(1, sortedPlayerNames.length - 1)] || sortedPlayerNames[0] || '';

    const rerender = () => renderCompare();
    selectA.onchange = rerender;
    selectB.onchange = rerender;
}

function compareMetric(key, label, valueA, valueB, higherBetter = true) {
    let winner = 'tie';
    if (valueA !== valueB) {
        winner = higherBetter
            ? (valueA > valueB ? 'left' : 'right')
            : (valueA < valueB ? 'left' : 'right');
    }
    return { key, label, valueA, valueB, winner };
}

function formatCompareValue(key, value) {
    if (key === 'winRate') return `${Number(value).toFixed(1)}%`;
    if (key === 'kda') return Number(value).toFixed(2);
    if (key === 'dpm') return Math.round(value).toLocaleString();
    if (key === 'matches') return String(value);
    return String(value);
}

function renderCompare() {
    const nameA = document.getElementById('compareA').value;
    const nameB = document.getElementById('compareB').value;
    const statsA = playerStats[nameA];
    const statsB = playerStats[nameB];
    if (!statsA || !statsB) return;

    const h2h = getHeadToHead(nameA, nameB);
    const together = h2h?.together || statsA.teammates[nameB] || statsB.teammates[nameA] || 0;
    const togetherWr = together && h2h
        ? ((h2h.togetherWins / together) * 100).toFixed(1)
        : null;
    const versus = h2h?.versus || 0;
    const winsA = h2h?.wins?.[nameA] || 0;
    const winsB = h2h?.wins?.[nameB] || 0;

    document.getElementById('compareSummary').innerHTML = `
        <strong>${nameA}</strong> and <strong>${nameB}</strong> have queued together
        <strong>${together}</strong> times${togetherWr ? ` (${togetherWr}% WR)` : ''}.
        ${versus ? `They faced off in <strong>${versus}</strong> games — ${nameA} ${winsA}W, ${nameB} ${winsB}W.` : ''}
    `;

    const metrics = [
        compareMetric('winRate', 'win rate', statsA.WinRate, statsB.WinRate),
        compareMetric('kda', 'kda', statsA.kda, statsB.kda),
        compareMetric('dpm', 'dpm', statsA.dpm, statsB.dpm),
        compareMetric('matches', 'games', statsA.matches, statsB.matches),
        compareMetric('kills', 'kills', statsA.kills, statsB.kills),
        compareMetric('deaths', 'deaths', statsA.deaths, statsB.deaths, false),
        compareMetric('assists', 'assists', statsA.assists, statsB.assists),
    ];

    document.getElementById('compareGrid').innerHTML = metrics
        .map((metric) => {
            const leftClass = metric.winner === 'left' ? 'win' : '';
            const rightClass = metric.winner === 'right' ? 'win' : '';
            return `
                <div class="compare-row">
                    <div class="compare-value left ${leftClass}">${formatCompareValue(metric.key, metric.valueA)}</div>
                    <div class="compare-label">${metric.label}</div>
                    <div class="compare-value right ${rightClass}">${formatCompareValue(metric.key, metric.valueB)}</div>
                </div>
            `;
        })
        .join('');

    const shared = Object.keys(statsA.skins)
        .filter((champ) => statsB.skins[champ])
        .map((champ) => [champ, statsA.skins[champ], statsB.skins[champ]]);

    document.getElementById('compareShared').innerHTML = shared.length
        ? shared
            .sort((a, b) => (b[1] + b[2]) - (a[1] + a[2]))
            .map(
                ([champ, gamesA, gamesB]) =>
                    `<li>${champ}<span class="tag-meta">${gamesA} / ${gamesB}</span></li>`
            )
            .join('')
        : '<li>No shared champions</li>';
}

function animateRecordCards() {
    const cards = document.querySelectorAll('.record-card');
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('in-view');
                }
            });
        },
        { threshold: 0.35 }
    );
    cards.forEach((card) => observer.observe(card));
}

function leagueAvgWinRate() {
    if (!leagueData?.leaderboard?.length) return 50;
    const totalGames = leagueData.leaderboard.reduce((sum, row) => sum + row.matches, 0);
    const weighted = leagueData.leaderboard.reduce((sum, row) => sum + row.winRate * row.matches, 0);
    return totalGames ? weighted / totalGames : 50;
}

function pairSynergy(nameA, nameB, leagueAvg) {
    const h2h = getHeadToHead(nameA, nameB);
    if (!h2h || h2h.together < 2) {
        return { boost: 0, games: 0, wr: null };
    }
    const wr = (h2h.togetherWins / h2h.together) * 100;
    const confidence = Math.min(h2h.together / 12, 1);
    const boost = (wr - leagueAvg) * confidence * 0.35;
    return { boost, games: h2h.together, wr };
}

function analyzeTeam(players) {
    const filled = players.filter(Boolean);
    if (!filled.length) {
        return null;
    }

    const leagueAvg = leagueAvgWinRate();
    const weights = filled.map((name) => Math.sqrt(playerStats[name].matches));
    const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
    const baseWr = filled.reduce(
        (sum, name, index) => sum + playerStats[name].WinRate * weights[index],
        0
    ) / totalWeight;

    let synergyTotal = 0;
    const synergyPairs = [];
    for (let i = 0; i < filled.length; i += 1) {
        for (let j = i + 1; j < filled.length; j += 1) {
            const synergy = pairSynergy(filled[i], filled[j], leagueAvg);
            if (synergy.games >= 2) {
                synergyTotal += synergy.boost;
                synergyPairs.push({
                    a: filled[i],
                    b: filled[j],
                    ...synergy,
                });
            }
        }
    }

    synergyPairs.sort((a, b) => Math.abs(b.boost) - Math.abs(a.boost));

    const projectedWr = Math.max(5, Math.min(95, baseWr + synergyTotal));
    const impactScore = filled.reduce((sum, name) => {
        const stats = playerStats[name];
        const wrNorm = stats.WinRate / 100;
        const kdaNorm = Math.min(stats.kda / 5, 1);
        const dpmNorm = Math.min(stats.dpm / 1200, 1);
        return sum + wrNorm * 0.5 + kdaNorm * 0.25 + dpmNorm * 0.25;
    }, 0) / filled.length;

    return {
        players: filled,
        baseWr,
        synergyTotal,
        projectedWr,
        impactScore,
        synergyPairs: synergyPairs.slice(0, 4),
        leagueAvg,
    };
}

function winProbability(scoreA, scoreB) {
    const diff = scoreA - scoreB;
    return 1 / (1 + Math.exp(-diff / 8));
}

function projectPlayerStats(name, teamWinProb) {
    const stats = playerStats[name];
    const perfMult = 0.88 + teamWinProb * 0.24;
    return {
        kda: stats.kda * perfMult,
        dpm: stats.dpm * perfMult,
    };
}

const DRAFT_SIZE = 5;
let draftTeams = { a: Array(DRAFT_SIZE).fill(''), b: Array(DRAFT_SIZE).fill('') };

function draftSelectedPlayers(excludeTeam = null, excludeIndex = -1) {
    const selected = new Set();
    ['a', 'b'].forEach((teamKey) => {
        draftTeams[teamKey].forEach((name, index) => {
            if (!name) return;
            if (teamKey === excludeTeam && index === excludeIndex) return;
            selected.add(name);
        });
    });
    return selected;
}

function buildDraftOptions(teamKey, slotIndex) {
    const selected = draftSelectedPlayers(teamKey, slotIndex);
    const current = draftTeams[teamKey][slotIndex];
    const options = ['<option value="">— pick player —</option>'];
    sortedPlayerNames.forEach((name) => {
        if (selected.has(name) && name !== current) return;
        const stats = playerStats[name];
        const selectedAttr = name === current ? ' selected' : '';
        options.push(
            `<option value="${name}"${selectedAttr}>${name} · ${stats.WinRate.toFixed(1)}% · ${stats.matches}g</option>`
        );
    });
    return options.join('');
}

function renderDraftSlots() {
    if (!sortedPlayerNames.length) {
        return;
    }

    ['a', 'b'].forEach((teamKey) => {
        const container = document.getElementById(`draftSlots${teamKey.toUpperCase()}`);
        if (!container) {
            return;
        }

        container.innerHTML = draftTeams[teamKey]
            .map(
                (_, index) => `
                    <div class="draft-slot">
                        <span class="draft-slot-num">${String(index + 1).padStart(2, '0')}</span>
                        <select class="draft-select" data-team="${teamKey}" data-slot="${index}">
                            ${buildDraftOptions(teamKey, index)}
                        </select>
                    </div>
                `
            )
            .join('');
    });
}

function updateDraftSimulateButton() {
    const teamA = draftTeams.a.filter(Boolean);
    const teamB = draftTeams.b.filter(Boolean);
    document.getElementById('draftSimulate').disabled = teamA.length < 5 || teamB.length < 5;
}

function autofillDraftTeam(teamKey) {
    const otherKey = teamKey === 'a' ? 'b' : 'a';
    const taken = new Set(draftTeams[otherKey].filter(Boolean));
    const pool = leagueData.leaderboard
        .map((row) => row.name)
        .filter((name) => playerStats[name] && !taken.has(name));

    if (pool.length < DRAFT_SIZE) {
        sortedPlayerNames.forEach((name) => {
            if (pool.length >= DRAFT_SIZE) return;
            if (!taken.has(name) && !pool.includes(name)) {
                pool.push(name);
            }
        });
    }

    draftTeams[teamKey] = pool.slice(0, DRAFT_SIZE);
    while (draftTeams[teamKey].length < DRAFT_SIZE) {
        draftTeams[teamKey].push('');
    }
    renderDraftSlots();
    updateDraftSimulateButton();
    document.getElementById('draftResults').hidden = true;
}

function clearDraftTeam(teamKey) {
    draftTeams[teamKey] = Array(DRAFT_SIZE).fill('');
    renderDraftSlots();
    updateDraftSimulateButton();
    document.getElementById('draftResults').hidden = true;
}

function renderSynergyList(pairs) {
    if (!pairs.length) {
        return '<li>No duo history on this roster yet — estimate uses solo win rates only.</li>';
    }
    return pairs
        .map((pair) => {
            const sign = pair.boost >= 0 ? 'positive' : 'negative';
            const delta = pair.boost >= 0 ? `+${pair.boost.toFixed(1)}` : pair.boost.toFixed(1);
            return `<li class="${sign}">${pair.a} + ${pair.b} · ${pair.wr.toFixed(1)}% over ${pair.games}g (${delta}%)</li>`;
        })
        .join('');
}

function renderDraftProjections(teamLabel, teamKey, players, teamWinProb) {
    const className = teamKey === 'a' ? 'team-a' : 'team-b';
    const rows = players
        .map((name) => {
            const projected = projectPlayerStats(name, teamWinProb);
            return `
                <div class="draft-proj-row">
                    <span class="name">${name}</span>
                    <span class="stat">kda <strong>${projected.kda.toFixed(2)}</strong></span>
                    <span class="stat">dpm <strong>${Math.round(projected.dpm).toLocaleString()}</strong></span>
                </div>
            `;
        })
        .join('');

    return `
        <div class="draft-proj-team ${className}">
            <h5>${teamLabel}</h5>
            ${rows}
        </div>
    `;
}

function simulateDraft() {
    const teamA = analyzeTeam(draftTeams.a);
    const teamB = analyzeTeam(draftTeams.b);
    if (!teamA || !teamB) return;

    const probA = winProbability(teamA.projectedWr, teamB.projectedWr);
    const probB = 1 - probA;
    const pctA = probA * 100;
    const pctB = probB * 100;

    const results = document.getElementById('draftResults');
    results.hidden = false;
    results.innerHTML = `
        <section class="draft-matchup panel">
            <div class="draft-matchup-head">
                <h4>matchup forecast</h4>
                <span class="panel-note">Model blends weighted win rate + duo synergy from shared games.</span>
            </div>
            <div class="draft-prob-bar">
                <div class="draft-prob-fill-a" style="width: ${pctA}%"></div>
                <div class="draft-prob-fill-b" style="width: ${pctB}%"></div>
            </div>
            <div class="draft-prob-labels">
                <span class="team-a-label">blue ${pctA.toFixed(1)}%</span>
                <span class="team-b-label">red ${pctB.toFixed(1)}%</span>
            </div>
        </section>

        <div class="draft-breakdown">
            <div class="draft-stat-block">
                <span class="label">blue projected wr</span>
                <span class="value">${teamA.projectedWr.toFixed(1)}%</span>
                <div class="detail">Base ${teamA.baseWr.toFixed(1)}% · synergy ${teamA.synergyTotal >= 0 ? '+' : ''}${teamA.synergyTotal.toFixed(1)}%</div>
                <ul class="draft-synergy-list">${renderSynergyList(teamA.synergyPairs)}</ul>
            </div>
            <div class="draft-stat-block">
                <span class="label">red projected wr</span>
                <span class="value">${teamB.projectedWr.toFixed(1)}%</span>
                <div class="detail">Base ${teamB.baseWr.toFixed(1)}% · synergy ${teamB.synergyTotal >= 0 ? '+' : ''}${teamB.synergyTotal.toFixed(1)}%</div>
                <ul class="draft-synergy-list">${renderSynergyList(teamB.synergyPairs)}</ul>
            </div>
        </div>

        <section class="draft-projections panel">
            <div class="panel-head compact">
                <p class="panel-tag">projected box score</p>
                <h3>if this game happened</h3>
                <p class="panel-note">KDA and DPM scaled by expected team win chance — rough vibe check, not prophecy.</p>
            </div>
            <div class="draft-proj-grid">
                ${renderDraftProjections('blue side', 'a', teamA.players, probA)}
                ${renderDraftProjections('red side', 'b', teamB.players, probB)}
            </div>
        </section>
    `;
}

function setupDraftPanel() {
    const panel = document.getElementById('draftPanel');
    if (!panel) {
        return;
    }

    renderDraftSlots();
    updateDraftSimulateButton();

    panel.addEventListener('change', (event) => {
        const select = event.target.closest('.draft-select');
        if (!select) {
            return;
        }
        const team = select.dataset.team;
        const slot = Number(select.dataset.slot);
        draftTeams[team][slot] = select.value;
        renderDraftSlots();
        updateDraftSimulateButton();
        document.getElementById('draftResults').hidden = true;
    });

    panel.addEventListener('click', (event) => {
        const autofill = event.target.closest('[data-autofill]');
        if (autofill) {
            autofillDraftTeam(autofill.dataset.autofill);
            return;
        }

        const clear = event.target.closest('[data-clear]');
        if (clear) {
            clearDraftTeam(clear.dataset.clear);
            return;
        }

        if (event.target.id === 'draftSimulate') {
            simulateDraft();
        }
    });
}

function renderRecords() {
    const grid = document.getElementById('recordGrid');
    const highlights = leagueData?.records?.highlights || [];
    grid.innerHTML = highlights
        .map(
            (record) => `
                <article class="record-card" data-record-id="${record.id}">
                    <span class="label">${record.label}</span>
                    <span class="value">${record.value}</span>
                    <span class="player">${record.player}</span>
                    <span class="detail">${record.detail || ''}</span>
                </article>
            `
        )
        .join('');
    animateRecordCards();
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
                        <div class="duo-meta"><span>${duo.games} games</span></div>
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

    renderSparkline(stats.form || []);

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

function buildPlayerRail() {
    const rail = document.getElementById('playerRail');
    rail.innerHTML = '';

    sortedPlayerNames.forEach((name) => {
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
        renderMvpBanner();
        setupViewNav();

        sortedPlayerNames = Object.keys(playerStats).sort(
            (a, b) => playerStats[b].matches - playerStats[a].matches
        );

        if (!sortedPlayerNames.length) {
            emptyState.hidden = false;
            return;
        }

        buildPlayerRail();
        populateCompareSelects();
        setupDraftPanel();
        renderPlayer(sortedPlayerNames[0]);
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
