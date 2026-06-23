

function isAdminMode() {
    const params = new URLSearchParams(window.location.search);

    if (params.get("admin") === "1") {
        localStorage.setItem("admin_mode", "1");
        return true;
    }

    return localStorage.getItem("admin_mode") === "1";
}


function updateAdminVisibility() {
    const isAdmin = isAdminMode();

    document.querySelectorAll(".admin-only").forEach(el => {
        if (isAdmin) {
            el.classList.remove("hidden");
        } else {
            el.classList.add("hidden");
        }
    });
}


function showMobileSection(sectionName) {
    document.querySelectorAll(".mobile-section").forEach(el => {
        el.classList.remove("active");
    });

    document.querySelectorAll(".mobile-app-tab").forEach(el => {
        el.classList.remove("active");
    });

    const section = document.querySelector(".mobile-section-" + sectionName);
    const tab = document.getElementById(
        "mobileTab" + sectionName.charAt(0).toUpperCase() + sectionName.slice(1)
    );

    if (section) section.classList.add("active");
    if (tab) tab.classList.add("active");

    if (sectionName === "leaderboard") {
        smartRefreshNow();
    }

    if (sectionName === "live") {
        loadLiveScores();
    }
}

let userId = localStorage.getItem("user_id");
let nicknameSaved = localStorage.getItem("nickname");
let allMatches = [];
let currentFilter = "all";

function updateAuthUI(message) {
    const authPage = document.getElementById("authPage");
    const appPage = document.getElementById("appPage");
    const loggedInName = document.getElementById("loggedInName");
    const loginStatus = document.getElementById("loginStatus");

    if (userId && nicknameSaved) {
        if (authPage) authPage.classList.add("hidden");
        if (appPage) appPage.classList.remove("hidden");
        if (loggedInName) loggedInName.innerText = "Logged in as " + nicknameSaved;
        if (loginStatus) loginStatus.innerText = "";
    } else {
        if (authPage) authPage.classList.remove("hidden");
        if (appPage) appPage.classList.add("hidden");
        if (loginStatus) loginStatus.innerText = message || "";
    }
}


function clearAuthInputs() {
    const fieldsToClear = [
        "loginIdentifier",
        "loginPin",
        "signupNickname",
        "signupPhoneNumber",
        "signupPin"
    ];

    fieldsToClear.forEach(function (fieldId) {
        const field = document.getElementById(fieldId);
        if (field) {
            field.value = "";
        }
    });

    const whatsappOptIn = document.getElementById("whatsappOptIn");
    if (whatsappOptIn) {
        whatsappOptIn.checked = false;
    }
}

function showAuthTab(tabName) {
    const loginPanel = document.getElementById("loginPanel");
    const signupPanel = document.getElementById("signupPanel");
    const loginTab = document.getElementById("loginTab");
    const signupTab = document.getElementById("signupTab");
    const loginStatus = document.getElementById("loginStatus");

    if (loginStatus) loginStatus.innerText = "";

    if (tabName === "signup") {
        loginPanel.classList.add("hidden");
        signupPanel.classList.remove("hidden");
        loginTab.classList.remove("active");
        signupTab.classList.add("active");
    } else {
        signupPanel.classList.add("hidden");
        loginPanel.classList.remove("hidden");
        signupTab.classList.remove("active");
        loginTab.classList.add("active");
    }
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
    const loginStatus = document.getElementById("loginStatus");

    if (nickname === "" || phoneNumber === "" || pin === "") {
        alert("Please enter nickname, phone number and PIN.");
        return;
    }

    loginStatus.innerText = "Creating account...";

    try {
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

        if (!response.ok || !data.user_id) {
            loginStatus.innerText = data.error || "Registration failed.";
            return;
        }

        // Auto-login immediately after successful registration.
        userId = data.user_id;
        nicknameSaved = data.nickname;

        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("nickname", data.nickname);

        clearAuthInputs();
        updateAuthUI("Registered and logged in as " + data.nickname);
        updateAdminVisibility();

        await smartRefreshNow();
    } catch (error) {
        loginStatus.innerText = "Registration failed. Please try again.";
    }
}


async function login() {
    const identifier = document.getElementById("loginIdentifier").value.trim();
    const pin = document.getElementById("loginPin").value.trim();

    if (identifier === "" || pin === "") {
        alert("Please enter phone number / nickname and PIN.");
        return;
    }

    const response = await fetch("/api/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            identifier: identifier,
            pin: pin
        })
    });

    const data = await response.json();

    if (data.user_id) {
        userId = data.user_id;

        localStorage.setItem("user_id", data.user_id);
        localStorage.setItem("nickname", data.nickname);
        nicknameSaved = data.nickname;
        clearAuthInputs();
        updateAuthUI("Logged in as " + data.nickname);
        updateAdminVisibility();

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
    nicknameSaved = null;

    clearAuthInputs();
    updateAuthUI("Logged out.");
    updateAdminVisibility();
    showAuthTab("login");
}

document.addEventListener("DOMContentLoaded", function () {
    updateAuthUI();
    updateAdminVisibility();
    showMobileSection("matches");

    if (userId && nicknameSaved) {
        smartRefreshNow();
    }

    // Check quietly for score/status updates.
    // When a score changes, matches + leaderboard refresh automatically.
    setInterval(function () {
        if (userId && nicknameSaved) {
            checkForScoreUpdates();
        }
    }, 30000);

    // User actions such as returning to the tab or clicking the leaderboard area
    // refresh the latest points immediately.
    document.addEventListener("visibilitychange", function () {
        if (!document.hidden && userId && nicknameSaved) {
            smartRefreshNow();
        }
    });

    window.addEventListener("focus", function () {
        if (userId && nicknameSaved) {
            smartRefreshNow();
        }
    });
});
