async function loadGroupStandings() {
    const response = await fetch("/api/group-standings");
    const groups = await response.json();

    const container = document.getElementById("groupStandings");
    container.innerHTML = "";

    const groupNames = Object.keys(groups).sort();

    if (groupNames.length === 0) {
        container.innerHTML = "<p>No group data available yet.</p>";
        return;
    }

    groupNames.forEach(groupName => {
        const teams = groups[groupName];

        let html = `
            <div class="group-card">
                <div class="group-title">${formatGroup(groupName)}</div>

                <table class="group-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th class="team-col">Team</th>
                            <th>P</th>
                            <th>W</th>
                            <th>D</th>
                            <th>L</th>
                            <th>GF</th>
                            <th>GA</th>
                            <th>GD</th>
                            <th>Pts</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        teams.forEach(team => {
            let qualifyClass = "";

            if (team.rank === 1 || team.rank === 2) {
                qualifyClass = "qualified-row";
            }

            html += `
                <tr class="${qualifyClass}">
                    <td>${team.rank}</td>
                    <td class="team-col">${team.team}</td>
                    <td>${team.played}</td>
                    <td>${team.won}</td>
                    <td>${team.drawn}</td>
                    <td>${team.lost}</td>
                    <td>${team.goals_for}</td>
                    <td>${team.goals_against}</td>
                    <td>${team.goal_difference}</td>
                    <td class="points-col">${team.points}</td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>

                <div class="group-note">Top 2 highlighted</div>
            </div>
        `;

        container.innerHTML += html;
    });
}


document.addEventListener("DOMContentLoaded", function () {
    loadGroupStandings();

    setInterval(loadGroupStandings, 60000);
});