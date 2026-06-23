function toggleAdmin() { document.getElementById("adminTools").classList.toggle("hidden"); }
async function forceLiveSync() {
    document.getElementById("liveStatus").innerText = "Running live sync...";
    const response = await fetch("/admin/live-sync");
    document.getElementById("liveStatus").innerText = await response.text();
    loadLiveScores(); loadMatches(); loadLeaderboard();
}
async function syncScores() {
    document.getElementById("adminStatus").innerText = "Syncing scores from API...";
    const response = await fetch("/admin/sync");
    document.getElementById("adminStatus").innerText = await response.text();
    loadLiveScores(); loadMatches(); loadLeaderboard();
}
async function calculatePoints() {
    document.getElementById("adminStatus").innerText = "Calculating points...";
    const response = await fetch("/admin/calculate");
    document.getElementById("adminStatus").innerText = await response.text();
    loadMatches(); loadLeaderboard();
}
async function smartCheck() {
    document.getElementById("adminStatus").innerText = "Running smart check...";
    const response = await fetch("/admin/smart-check");
    document.getElementById("adminStatus").innerText = await response.text();
    loadLiveScores(); loadMatches(); loadLeaderboard();
}
