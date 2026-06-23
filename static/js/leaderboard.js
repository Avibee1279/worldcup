async function loadLeaderboard() {
    const response = await fetch("/api/leaderboard");
    const rows = await response.json();

    const div = document.getElementById("leaderboard");
    div.innerHTML = "";

    if (rows.length === 0) {
        div.innerHTML = "<p>No players yet.</p>";
        return;
    }

    rows.forEach((row, index) => {
        let medal = "";

        if (index === 0) {
            medal = "🥇 ";
        }

        if (index === 1) {
            medal = "🥈 ";
        }

        if (index === 2) {
            medal = "🥉 ";
        }

        const displayName = row.nickname || "Player";

        div.innerHTML += `
            <div class="leaderboard-row">
                <span>
                    <b>${medal}${index + 1}. ${displayName}</b>
                </span>

                <span class="leaderboard-points">
                    ${row.total_points} pts (${row.predictions_made})
                </span>
            </div>
        `;
    });
}
