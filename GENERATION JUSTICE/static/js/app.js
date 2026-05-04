const state = {
    user: null,
};

function qs(selector) {
    return document.querySelector(selector);
}

function qsa(selector) {
    return Array.from(document.querySelectorAll(selector));
}

function setStatus(element, message, type = "ok") {
    if (!element) return;
    element.textContent = message;
    element.className = "status show " + type;
}

function clearStatus(element) {
    if (!element) return;
    element.textContent = "";
    element.className = "status";
}

async function postJson(url, data) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.detail || "Request failed.");
    }
    return payload;
}

function openLogin() {
    const modal = qs("#loginModal");
    if (!modal) return;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
}

function closeLogin() {
    const modal = qs("#loginModal");
    if (!modal) return;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
}

function updateAuthUI(user) {
    state.user = user;
    const chip = qs("#memberChip");
    const loginButton = qs("#openLoginButton");
    const logoutButton = qs("#logoutButton");

    if (user) {
        if (chip) {
            chip.textContent = user.membership + " Member";
            chip.classList.add("show");
        }
        loginButton?.classList.add("hidden");
        logoutButton?.classList.remove("hidden");
        const commentName = qs("#commentName");
        if (commentName && !commentName.value) {
            commentName.value = user.name;
        }
    } else {
        chip?.classList.remove("show");
        loginButton?.classList.remove("hidden");
        logoutButton?.classList.add("hidden");
    }
}

async function loadCurrentUser() {
    try {
        const response = await fetch("/api/me");
        const payload = await response.json();
        updateAuthUI(payload.user);
    } catch {
        updateAuthUI(null);
    }
}

function makeComment(comment) {
    const item = document.createElement("article");
    item.className = "comment";
    item.innerHTML = "<strong></strong><small></small><p></p>";
    item.querySelector("strong").textContent = comment.user_name;
    item.querySelector("small").textContent = comment.created_at;
    item.querySelector("p").textContent = comment.text;
    return item;
}

function makeBroadcast(broadcast) {
    const item = document.createElement("article");
    item.className = "broadcast-item";
    item.innerHTML = "<strong></strong><span></span><small></small>";
    item.querySelector("strong").textContent = broadcast.title;
    item.querySelector("span").textContent = broadcast.message;
    item.querySelector("small").textContent =
        broadcast.target + " - " + broadcast.status + " - " + broadcast.created_at + " - by " + broadcast.created_by;
    return item;
}

function showBroadcastBanner(broadcast) {
    const host = qs("#liveBroadcastBannerHost");
    if (!host) return;
    host.innerHTML = "";
    const banner = document.createElement("section");
    banner.className = "broadcast-strip";
    banner.id = "liveBroadcastBanner";
    banner.innerHTML = "<strong></strong><span></span><small></small>";
    banner.querySelector("strong").textContent = broadcast.title;
    banner.querySelector("span").textContent = broadcast.message;
    banner.querySelector("small").textContent = broadcast.target + " - by " + broadcast.created_by;
    host.appendChild(banner);
}

function bindLogin() {
    qs("#openLoginButton")?.addEventListener("click", openLogin);
    qsa("[data-open-login]").forEach((button) => button.addEventListener("click", openLogin));
    qs("#closeLoginButton")?.addEventListener("click", closeLogin);

    qs("#loginModal")?.addEventListener("click", (event) => {
        if (event.target.id === "loginModal") {
            closeLogin();
        }
    });

    qs("#loginForm")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const status = qs("#loginStatus");
        clearStatus(status);
        try {
            const payload = await postJson("/api/login", {
                email: qs("#loginEmail").value,
                password: qs("#loginPassword").value,
            });
            updateAuthUI(payload.user);
            setStatus(status, payload.message);
            setTimeout(closeLogin, 700);
        } catch (error) {
            setStatus(status, error.message, "error");
        }
    });

    qs("#logoutButton")?.addEventListener("click", async () => {
        await postJson("/api/logout", {});
        updateAuthUI(null);
    });
}

function bindJoin() {
    qsa("[data-plan-choice]").forEach((button) => {
        button.addEventListener("click", () => {
            const select = qs("#joinMembership");
            const form = qs("#joinForm");
            if (select) select.value = button.dataset.planChoice;
            form?.scrollIntoView({ behavior: "smooth", block: "center" });
            qs("#joinName")?.focus();
        });
    });

    qs("#joinForm")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const status = qs("#joinStatus");
        clearStatus(status);
        try {
            const payload = await postJson("/api/join", {
                name: qs("#joinName").value,
                email: qs("#joinEmail").value,
                password: qs("#joinPassword").value,
                membership: qs("#joinMembership").value,
            });
            updateAuthUI(payload.user);
            setStatus(status, payload.message);
            event.target.reset();
            qs("#joinMembership").value = payload.user.membership;
        } catch (error) {
            setStatus(status, error.message, "error");
        }
    });
}

function bindComments() {
    qs("#commentForm")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const status = qs("#commentStatus");
        clearStatus(status);
        try {
            const payload = await postJson("/api/comments", {
                name: qs("#commentName").value,
                text: qs("#commentText").value,
            });
            qs("#commentList")?.prepend(makeComment(payload.comment));
            qs("#commentText").value = "";
            setStatus(status, "Comment posted.");
        } catch (error) {
            setStatus(status, error.message, "error");
        }
    });
}

function updateBroadcastPreview() {
    const title = qs("#broadcastTitle")?.value || "";
    const target = qs("#broadcastTarget")?.value || "";
    const message = qs("#broadcastMessage")?.value || "";
    if (qs("#broadcastTitlePreview")) qs("#broadcastTitlePreview").textContent = title;
    if (qs("#broadcastTargetPreview")) qs("#broadcastTargetPreview").textContent = target;
    if (qs("#broadcastMessagePreview")) qs("#broadcastMessagePreview").textContent = message;
}

function bindBroadcast() {
    ["#broadcastTitle", "#broadcastTarget", "#broadcastMessage"].forEach((selector) => {
        qs(selector)?.addEventListener("input", updateBroadcastPreview);
        qs(selector)?.addEventListener("change", updateBroadcastPreview);
    });

    qs("#broadcastForm")?.addEventListener("submit", (event) => {
        event.preventDefault();
        updateBroadcastPreview();
        setStatus(qs("#broadcastStatus"), "Preview updated.");
    });

    qs("#startBroadcastButton")?.addEventListener("click", async () => {
        const status = qs("#broadcastStatus");
        clearStatus(status);
        try {
            const payload = await postJson("/api/broadcasts", {
                title: qs("#broadcastTitle").value,
                target: qs("#broadcastTarget").value,
                message: qs("#broadcastMessage").value,
            });
            qs("#broadcastList")?.prepend(makeBroadcast(payload.broadcast));
            showBroadcastBanner(payload.broadcast);
            setStatus(status, "Broadcast is now running.");
        } catch (error) {
            setStatus(status, error.message, "error");
            if (error.message.toLowerCase().includes("log in")) {
                openLogin();
            }
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    bindLogin();
    bindJoin();
    bindComments();
    bindBroadcast();
    loadCurrentUser();
});
