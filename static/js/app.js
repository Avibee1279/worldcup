let userId = localStorage.getItem("user_id");
let nicknameSaved = localStorage.getItem("nickname");
let allMatches = [];
let currentFilter = "all";

if (userId && nicknameSaved) {
    document.getElementById("loginStatus").innerText = "Logged in as " + nicknameSaved;
}

function formatDate(utcDateText) {
    if (!utcDateText) {
        return "-";
    }

    const date = new Date(utcDateText);

    return date.toLocaleString([], {
        weekday: "short",
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit"
    });
}

function formatStage(stage) {
    return stage ? stage.replaceAll("_", " ") : "-";
}

function formatGroup(groupName) {
    return groupName ? groupName.replace("GROUP_", "Group ") : "-";
}

function getScoreText(match) {
    return match.home_score !== null && match.away_score !== null
        ? match.home_score + " - " + match.away_score
        : "-";
}

function isLive(match) {
    return match.status === "IN_PLAY" ||
           match.status === "PAUSED" ||
           match.status === "LIVE";
}

function isFinished(match) {
    return match.status === "FINISHED";
}

function isPredictionOpen(match) {
    if (!(match.status === "TIMED" || match.status === "SCHEDULED")) {
        return false;
    }

    if (!match.utc_date) {
        return false;
    }

    return new Date() < new Date(match.utc_date);
}

function getStatusBadge(match) {
    if (match.status === "PAUSED") {
        return `<span class="status-badge status-paused">HALF-TIME</span>`;
    }

    if (isLive(match)) {
        return `<span class="status-badge status-live">LIVE / IN PROGRESS</span>`;
    }

    if (isFinished(match)) {
        return `<span class="status-badge status-finished">FINISHED</span>`;
    }

    if (isPredictionOpen(match)) {
        return `<span class="status-badge status-open">PREDICTION OPEN</span>`;
    }

    return `<span class="status-badge status-locked">PREDICTION LOCKED</span>`;
}

function getCountryCode(teamName) {
    const map = {
        "Mexico": "mx",
        "South Africa": "za",
        "South Korea": "kr",
        "Czechia": "cz",
        "Canada": "ca",
        "Bosnia-Herzegovina": "ba",
        "Bosnia and Herzegovina": "ba",
        "Qatar": "qa",
        "Switzerland": "ch",
        "Brazil": "br",
        "Morocco": "ma",
        "Haiti": "ht",
        "Scotland": "gb-sct",
        "United States": "us",
        "USA": "us",
        "Paraguay": "py",
        "Australia": "au",
        "Turkey": "tr",
        "Türkiye": "tr",
        "Germany": "de",
        "Curaçao": "cw",
        "Curacao": "cw",
        "Ivory Coast": "ci",
        "Côte d’Ivoire": "ci",
        "Ecuador": "ec",
        "Netherlands": "nl",
        "Japan": "jp",
        "Sweden": "se",
        "Tunisia": "tn",
        "Belgium": "be",
        "Egypt": "eg",
        "Iran": "ir",
        "New Zealand": "nz",
        "Spain": "es",
        "Cape Verde": "cv",
        "Saudi Arabia": "sa",
        "Uruguay": "uy",
        "France": "fr",
        "Senegal": "sn",
        "Iraq": "iq",
        "Norway": "no",
        "Argentina": "ar",
        "Algeria": "dz",
        "Austria": "at",
        "Jordan": "jo",
        "Portugal": "pt",
        "Congo DR": "cd",
        "DR Congo": "cd",
        "England": "gb-eng",
        "Croatia": "hr",
        "Ghana": "gh",
        "Panama": "pa",
        "Uzbekistan": "uz",
        "Colombia": "co"
    };

    return map[teamName] || null;
}

function getCrestHtml(crestUrl, teamName) {
    const countryCode = getCountryCode(teamName);

    if (countryCode) {
        return `<img class="crest" src="https://flagcdn.com/w80/${countryCode}.png" alt="${teamName} flag">`;
    }

    if (crestUrl && crestUrl !== "null") {
        return `<img class="crest" src="${crestUrl}" alt="${teamName} badge">`;
    }

    return `<div class="crest-fallback">${teamName ? teamName.charAt(0).toUpperCase() : "?"}</div>`;
}

function setFilter(filter) {
    currentFilter = filter;
    renderMatches();
}

function cleanPhoneNumber(phoneNumber) {
    return phoneNumber
        .trim()
        .replaceAll(" ", "")
        .replaceAll("-", "")
        .replaceAll("(", "")
        .replaceAll(")", "");
}

async function registerUser() {
    const nickname = document.getElementById("signupNickname").value.trim();
    const phoneNumber = cleanPhoneNumber(document.getElementById("signupPhoneNumber").value);
    const pin = document.getElementById("signupPin").value.trim();
    const whatsappOptIn = document.getElementById("whatsappOptIn").checked;

    if (nickname === "" || phoneNumber === "" || pin === "") {
        alert("Please enter nickname, phone number and PIN.");
        return;
    }

    const response = await fetch("/api/register", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            nickname: nickname,
            phone_number: phoneNumber,
            pin: pin,
            whatsapp_opt_in: whatsappOptIn
        })
    });

    const data = await response.json();

    if (data.user_id) {
        userId = data.user_id;

        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("nickname", data.nickname);

        document.getElementById("loginStatus").innerText = "Registered and logged in as " + data.nickname;

        loadMatches();
        loadLeaderboard();
    } else {
        document.getElementById("loginStatus").innerText = data.error || "Registration failed.";
    }
}

async function login() {
    const phoneNumber = cleanPhoneNumber(document.getElementById("loginPhoneNumber").value);
    const pin = document.getElementById("loginPin").value.trim();

    if (phoneNumber === "" || pin === "") {
        alert("Please enter phone number and PIN.");
        return;
    }

    const response = await fetch("/api/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            phone_number: phoneNumber,
            pin: pin
        })
    });

    const data = await response.json();

    if (data.user_id) {
        userId = data.user_id;

        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("nickname", data.nickname);

        document.getElementById("loginStatus").innerText = "Logged in as " + data.nickname;

        loadMatches();
        loadLeaderboard();
    } else {
        document.getElementById("loginStatus").innerText = data.error || "Login failed.";
    }
}

function logout() {
    localStorage.removeItem("user_id");
    localStorage.removeItem("nickname");

    userId = null;

    document.getElementById("loginStatus").innerText = "Logged out.";

    loadMatches();
    loadLeaderboard();
}

document.addEventListener("DOMContentLoaded", function () {
    loadLiveScores();
    loadMatches();
    loadLeaderboard();

    setInterval(loadLiveScores, 30000);
    setInterval(loadMatches, 60000);
});
