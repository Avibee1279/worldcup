function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
function closeSquadModal() { document.getElementById("squadModal").style.display = "none"; }
function getPositionOrder(position) {
    const order = {"Goalkeeper":1,"Defence":2,"Defender":2,"Midfield":3,"Midfielder":3,"Offence":4,"Attacker":4,"Forward":4,"Coach":5};
    return order[position] || 99;
}
async function showSquad(teamId) {
    if (!teamId || teamId === "null") { alert("Team ID not available. Run /admin/sync first."); return; }
    const modal = document.getElementById("squadModal");
    const title = document.getElementById("squadModalTitle");
    const content = document.getElementById("squadModalContent");
    modal.style.display = "flex";
    title.innerText = "Loading squad...";
    content.innerHTML = "<p>Loading...</p>";
    const response = await fetch("/api/team-squad/" + teamId);
    const data = await response.json();
    if (!response.ok) {
        title.innerText = "Squad unavailable";
        content.innerHTML = `<p class="locked-text">${escapeHtml(data.error || "Could not load squad.")}</p>`;
        return;
    }
    const squad = data.squad || [];
    title.innerText = data.name || "Squad";
    if (squad.length === 0) {
        content.innerHTML = `<div class="squad-header">${data.crest ? `<img src="${data.crest}" alt="${escapeHtml(data.name)} crest">` : ""}<div><h3>${escapeHtml(data.name || "Team")}</h3><p>No squad players returned by the API.</p></div></div>`;
        return;
    }
    const groups = {};
    squad.forEach(player => {
        const position = player.position || "Other";
        if (!groups[position]) groups[position] = [];
        groups[position].push(player);
    });
    const sortedPositions = Object.keys(groups).sort((a,b) => getPositionOrder(a) - getPositionOrder(b));
    let html = `<div class="squad-header">${data.crest ? `<img src="${data.crest}" alt="${escapeHtml(data.name)} crest">` : ""}<div><h3>${escapeHtml(data.name || "Team")}</h3><p>${squad.length} players in squad</p></div></div>`;
    sortedPositions.forEach(position => {
        html += `<div class="squad-section"><h4>${escapeHtml(position)}</h4><div class="player-grid">`;
        groups[position].forEach(player => {
            html += `<div class="player-card"><div class="player-name">${escapeHtml(player.name)}</div><div class="player-meta">${escapeHtml(player.nationality || "")}${player.dateOfBirth ? " • DOB: " + escapeHtml(player.dateOfBirth) : ""}</div></div>`;
        });
        html += `</div></div>`;
    });
    content.innerHTML = html;
}
document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("squadModal").addEventListener("click", function(event) {
        if (event.target.id === "squadModal") closeSquadModal();
    });
});
