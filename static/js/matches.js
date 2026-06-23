let groupStandingsData = {};
let expandedOldMatches = new Set();
let showAllOldMatches = false;


function getDateKey(utcDateText) {
    const date = new Date(utcDateText);
    return date.toISOString().split("T")[0];
}


function isPreviousDayMatch(match) {
    const matchDateKey = getDateKey(match.utc_date);
    const todayKey = new Date().toISOString().split("T")[0];

    return matchDateKey < todayKey;
}


function toggleOldMatch(matchApiId) {
    if (expandedOldMatches.has(matchApiId)) {
        expandedOldMatches.delete(matchApiId);
    } else {
        expandedOldMatches.add(matchApiId);
    }

    renderMatches();
}


function getCountdownText(utcDateText) {
    if (!utcDateText) {
        return "No match time";
    }

    const matchTime = new Date(utcDateText);
    const now = new Date();

    const diff = matchTime - now;

    if (diff <= 0) {
        return "Prediction closed";
    }

    const totalSeconds = Math.floor(diff / 1000);

    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    if (days > 0) {
        return `Prediction closes in: ${days}d ${hours}h ${minutes}m`;
    }

    if (hours > 0) {
        return `Prediction closes in: ${hours}h ${minutes}m ${seconds}s`;
    }

    if (minutes > 0) {
        return `Prediction closes in: ${minutes}m ${seconds}s`;
    }

    return `Prediction closes in: ${seconds}s`;
}


function getCountdownClass(match) {
    if (!isPredictionOpen(match)) {
        return "countdown-closed";
    }

    const matchTime = new Date(match.utc_date);
    const now = new Date();
    const diffMinutes = (matchTime - now) / 1000 / 60;

    if (diffMinutes <= 30) {
        return "countdown-danger";
    }

    if (diffMinutes <= 120) {
        return "countdown-warning";
    }

    return "countdown-normal";
}


async function loadGroupStandingsData() {
    const response = await fetch("/api/group-standings");
    groupStandingsData = await response.json();
}


async function loadMatches() {
    let url = "/api/matches";

    if (userId) {
        url = "/api/matches?user_id=" + userId;
    }

    await loadGroupStandingsData();

    const response = await fetch(url);
    allMatches = await response.json();

    updateStats();
    renderMatches();
}


function updateStats() {
    document.getElementById("statTotal").innerText = allMatches.length;
    document.getElementById("statUpcoming").innerText = allMatches.filter(isPredictionOpen).length;
    document.getElementById("statFinished").innerText = allMatches.filter(isFinished).length;
    document.getElementById("statLive").innerText = allMatches.filter(isLive).length;
}


function renderSideRanking(groupName) {
    const teams = groupStandingsData[groupName];

    if (!teams || teams.length === 0) {
        return `
            <div class="side-ranking-empty">
                No ranking yet
            </div>
        `;
    }

    let html = `
        <div class="side-ranking-title">
            ${formatGroup(groupName)} Ranking
        </div>

        <div class="side-ranking-list">
    `;

    teams.forEach(team => {
        let rowClass = "";

        if (team.rank === 1 || team.rank === 2) {
            rowClass = "side-rank-qualified";
        }

        html += `
            <div class="side-rank-row ${rowClass}">
                <div class="side-rank-position">${team.rank}</div>

                <div class="side-rank-team">
                    <div class="side-rank-name">${team.team}</div>
                    <div class="side-rank-small">
                        P${team.played} W${team.won} D${team.drawn} L${team.lost} GD ${team.goal_difference}
                    </div>
                </div>

                <div class="side-rank-points">
                    ${team.points}
                </div>
            </div>
        `;
    });

    html += `
        </div>
    `;

    return html;
}


function renderCompactOldMatch(match) {
    return `
        <div class="match old-match-card">
            <div class="old-match-header">
                <div class="old-match-summary">
                    ${formatDate(match.utc_date)} • ${formatGroup(match.group_name)} •
                    ${match.home_team} ${match.home_score ?? "-"} - ${match.away_score ?? "-"} ${match.away_team}
                </div>

                <button class="old-match-toggle"
                        onclick="toggleOldMatch(${match.match_api_id})">
                    Show
                </button>
            </div>
        </div>
    `;
}


function renderFullMatch(match, oldMatch) {
    const predictionOpen = isPredictionOpen(match);

    const hasPrediction =
        match.home_pred !== null &&
        match.home_pred !== undefined &&
        match.away_pred !== null &&
        match.away_pred !== undefined;

    const hasFinalScore =
        match.home_score !== null &&
        match.home_score !== undefined &&
        match.away_score !== null &&
        match.away_score !== undefined;

    let predictionText = "";

    if (isFinished(match)) {
        if (hasPrediction) {
            const points = match.points ?? 0;

            let pointsClass = "points-zero";

            if (points === 3) {
                pointsClass = "points-good";
            } else if (points === 1) {
                pointsClass = "points-mid";
            }

            predictionText = `
                <div class="prediction-summary">
                    <div class="prediction-chip">Your prediction: ${match.home_pred} - ${match.away_pred}</div>
                    <div class="prediction-chip">Final result: ${hasFinalScore ? match.home_score + " - " + match.away_score : "Pending"}</div>
                    <div class="prediction-chip ${pointsClass}">Points earned: ${hasFinalScore ? points : "Pending"}</div>
                </div>
            `;
        } else {
            predictionText = `
                <p class="no-prediction-text">No prediction was made for this match.</p>
            `;
        }
    } else {
        if (hasPrediction) {
            const livePoints = match.points ?? 0;

            let livePointsClass = "points-zero";

            if (livePoints === 3) {
                livePointsClass = "points-good";
            } else if (livePoints === 1) {
                livePointsClass = "points-mid";
            }

            predictionText = `
                <div class="prediction-summary">
                    <div class="prediction-chip">Your prediction: ${match.home_pred} - ${match.away_pred}</div>
                    <div class="prediction-chip">Current score: ${hasFinalScore ? match.home_score + " - " + match.away_score : "Pending"}</div>
                    <div class="prediction-chip ${livePointsClass}">Current points: ${hasFinalScore ? livePoints : "Pending"}</div>
                </div>
            `;
        } else {
            predictionText = `
                <p class="no-prediction-text">No prediction was made for this match.</p>
            `;
        }
    }

    let predictionInputs = "";

    if (predictionOpen) {
        const existingHome = hasPrediction ? match.home_pred : "";
        const existingAway = hasPrediction ? match.away_pred : "";

        predictionInputs = `
            <div class="prediction-form">
                <div class="prediction-field">
                    <label>${match.home_team}</label>
                    <input type="number" id="home-${match.match_api_id}" value="${existingHome}" placeholder="0" min="0">
                </div>

                <div class="prediction-vs">-</div>

                <div class="prediction-field">
                    <label>${match.away_team}</label>
                    <input type="number" id="away-${match.match_api_id}" value="${existingAway}" placeholder="0" min="0">
                </div>

                <button onclick="savePrediction(${match.match_api_id})">
                    ${hasPrediction ? "Update" : "Save"}
                </button>
            </div>
        `;
    } else if (isFinished(match)) {
        predictionInputs = "";
    } else if (isLive(match)) {
        predictionInputs = `
            <p class="locked-text">Prediction closed. Match is in progress.</p>
        `;
    } else {
        predictionInputs = `
            <p class="locked-text">Prediction closed.</p>
        `;
    }

    return `
        <div class="match match-with-ranking ${oldMatch ? "old-match-card" : ""}">

            <div class="match-left">

                ${oldMatch ? `
                    <div class="old-match-header">
                        <div class="old-match-summary">
                            ${formatDate(match.utc_date)} • ${formatGroup(match.group_name)} •
                            ${match.home_team} ${match.home_score ?? "-"} - ${match.away_score ?? "-"} ${match.away_team}
                        </div>

                        <button class="old-match-toggle"
                                onclick="toggleOldMatch(${match.match_api_id})">
                            Hide
                        </button>
                    </div>
                ` : ""}

                <div class="match-top">
                    <div class="match-competition">
                        ${formatGroup(match.group_name)} • ${formatStage(match.stage)}
                    </div>

                    <div class="match-date">
                        ${formatDate(match.utc_date)}
                    </div>
                </div>

                <div class="match-main">
                    <div class="team-block">
                        <div class="team-label">Home</div>

                        <div class="team-row">
                            ${getCrestHtml(match.home_crest, match.home_team)}
                            <div class="team-name">${match.home_team}</div>
                        </div>

                        <div class="squad-actions">
                            <button class="squad-btn" onclick="showSquad(${match.home_team_id})">
                                View Squad
                            </button>
                        </div>
                    </div>

                    <div class="score-box">
                        ${getScoreText(match) === "-" ? "<span class='vs-box'>VS</span>" : getScoreText(match)}
                    </div>

                    <div class="team-block away-team">
                        <div class="team-label">Away</div>

                        <div class="team-row">
                            ${getCrestHtml(match.away_crest, match.away_team)}
                            <div class="team-name">${match.away_team}</div>
                        </div>

                        <div class="squad-actions">
                            <button class="squad-btn" onclick="showSquad(${match.away_team_id})">
                                View Squad
                            </button>
                        </div>
                    </div>
                </div>

                <div class="match-bottom">
                    <div class="status-line">
                        ${getStatusBadge(match)}

                        <span class="countdown-badge ${getCountdownClass(match)}" data-countdown="${match.utc_date}">
                            ${getCountdownText(match.utc_date)}
                        </span>
                    </div>

                    <div class="prediction-area">
                        ${predictionText}
                        ${predictionInputs}
                    </div>
                </div>
            </div>

            <div class="match-ranking-panel">
                ${renderSideRanking(match.group_name)}
            </div>

        </div>
    `;
}
function renderOldMatchesTable(oldMatches) {
    if (oldMatches.length === 0) {
        return "";
    }

    const sortedOldMatches = [...oldMatches].sort((a, b) => {
        return new Date(b.utc_date) - new Date(a.utc_date);
    });

    let visibleOldMatches = showAllOldMatches
        ? sortedOldMatches
        : sortedOldMatches.slice(0, 3);

    if (!showAllOldMatches) {
        visibleOldMatches = visibleOldMatches.sort((a, b) => {
            return new Date(a.utc_date) - new Date(b.utc_date);
        });
    }

    let html = `
        <div class="old-matches-table-box">
            <div class="old-matches-title-row">
                <div class="old-matches-title">Previous Matches</div>

                <button class="old-matches-show-btn" onclick="toggleOldMatchesTable()">
                    ${showAllOldMatches ? "Show last 3 only" : "Show all previous matches"}
                </button>
            </div>

            <table class="old-matches-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Group</th>
                        <th>Team A</th>
                        <th>Score</th>
                        <th>Team B</th>
                        <th>Your Prediction</th>
                        <th>Points</th>
                    </tr>
                </thead>
                <tbody>
    `;

    visibleOldMatches.forEach(match => {
        const hasPrediction =
            match.home_pred !== null &&
            match.home_pred !== undefined &&
            match.away_pred !== null &&
            match.away_pred !== undefined;

        const predictionText = hasPrediction
            ? `${match.home_pred} - ${match.away_pred}`
            : "-";

        const pointsText = hasPrediction
            ? (match.points ?? "Pending")
            : "-";

        const scoreText =
            match.home_score !== null &&
            match.home_score !== undefined &&
            match.away_score !== null &&
            match.away_score !== undefined
                ? `${match.home_score} - ${match.away_score}`
                : "-";

        let pointsClass = "";

        if (match.points === 3) {
            pointsClass = "old-points-good";
        } else if (match.points === 1) {
            pointsClass = "old-points-mid";
        } else if (match.points === 0 && hasPrediction) {
            pointsClass = "old-points-zero";
        }

        html += `
            <tr>
                <td>${formatDate(match.utc_date)}</td>
                <td>${formatGroup(match.group_name)}</td>
                <td class="old-team-name">${match.home_team}</td>
                <td class="old-score">${scoreText}</td>
                <td class="old-team-name">${match.away_team}</td>
                <td>${predictionText}</td>
                <td class="${pointsClass}">${pointsText}</td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>

            <div class="old-matches-note">
                Showing ${visibleOldMatches.length} of ${sortedOldMatches.length} previous matches
            </div>
        </div>
    `;

    return html;
}

function toggleOldMatchesTable() {
    showAllOldMatches = !showAllOldMatches;
    renderMatches();
}

function renderMatches() {
    const div = document.getElementById("matches");
    div.innerHTML = "";

    const groupFilter = document.getElementById("groupFilter").value;

    let matches = [...allMatches];

    if (currentFilter === "open") {
        matches = matches.filter(isPredictionOpen);
    }

    if (currentFilter === "live") {
        matches = matches.filter(isLive);
    }

    if (currentFilter === "finished") {
        matches = matches.filter(isFinished);
    }

    if (currentFilter === "mine") {
        matches = matches.filter(match => match.home_pred !== null && match.away_pred !== null);
    }

    if (groupFilter !== "all") {
        matches = matches.filter(match => match.group_name === groupFilter);
    }

    if (matches.length === 0) {
        div.innerHTML = "<p>No matches found for this filter.</p>";
        return;
    }

    const oldMatches = matches.filter(isPreviousDayMatch);
    const currentMatches = matches.filter(match => !isPreviousDayMatch(match));

    div.innerHTML += renderOldMatchesTable(oldMatches);

    currentMatches.forEach(match => {
        div.innerHTML += renderFullMatch(match, false);
    });
}


async function savePrediction(matchApiId) {
    if (!userId) {
        alert("Please login first.");
        return;
    }

    const homePred = document.getElementById("home-" + matchApiId).value;
    const awayPred = document.getElementById("away-" + matchApiId).value;

    if (homePred === "" || awayPred === "") {
        alert("Please enter both scores.");
        return;
    }

    const response = await fetch("/api/predict", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            user_id: Number(userId),
            match_api_id: matchApiId,
            home_pred: Number(homePred),
            away_pred: Number(awayPred)
        })
    });

    const data = await response.json();

    alert(data.message || data.error);

    loadMatches();
    loadLeaderboard();
}


async function loadLiveScores() {
    const response = await fetch("/api/live-scores");
    const matches = await response.json();

    const div = document.getElementById("liveScores");
    div.innerHTML = "";

    if (matches.length === 0) {
        div.innerHTML = "<p>No live match at the moment.</p>";
        return;
    }

    matches.forEach(match => {
        div.innerHTML += `
            <div class="match">

                <div class="match-top">
                    <div class="match-competition">
                        ${formatGroup(match.group_name)} • ${formatStage(match.stage)}
                    </div>

                    <div class="match-date">
                        ${formatDate(match.utc_date)}
                    </div>
                </div>

                <div class="match-main">
                    <div class="team-block">
                        <div class="team-label">Home</div>
                        <div class="team-row">
                            ${getCrestHtml(match.home_crest, match.home_team)}
                            <div class="team-name">${match.home_team}</div>
                        </div>
                    </div>

                    <div class="score-box">
                        ${getScoreText(match) === "-" ? "<span class='vs-box'>VS</span>" : getScoreText(match)}
                    </div>

                    <div class="team-block away-team">
                        <div class="team-label">Away</div>
                        <div class="team-row">
                            ${getCrestHtml(match.away_crest, match.away_team)}
                            <div class="team-name">${match.away_team}</div>
                        </div>
                    </div>
                </div>

                <div class="match-bottom">
                    <div class="status-line">
                        ${getStatusBadge(match)}
                    </div>
                </div>

            </div>
        `;
    });
}


function updateCountdownBadges() {
    document.querySelectorAll("[data-countdown]").forEach(span => {
        const utcDate = span.getAttribute("data-countdown");

        if (!utcDate) {
            return;
        }

        const fakeMatch = {
            utc_date: utcDate,
            status: new Date() < new Date(utcDate) ? "TIMED" : "FINISHED"
        };

        span.textContent = getCountdownText(utcDate);

        span.classList.remove(
            "countdown-normal",
            "countdown-warning",
            "countdown-danger",
            "countdown-closed"
        );

        span.classList.add(getCountdownClass(fakeMatch));
    });
}


// Do not re-render the whole match list every second.
// Re-rendering every second resets the score input boxes back to 0.
// Only countdown badges are updated every second.
setInterval(updateCountdownBadges, 1000);