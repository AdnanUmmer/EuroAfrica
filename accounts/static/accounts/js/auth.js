const ready = (callback) => {
    if (document.readyState !== "loading") {
        callback();
        return;
    }
    document.addEventListener("DOMContentLoaded", callback);
};

ready(() => {
    document.querySelectorAll(".luxury-toast-close").forEach((button) => {
        button.addEventListener("click", () => {
            button.closest(".luxury-toast")?.remove();
        });
    });

    document.querySelectorAll("[data-dropdown]").forEach((dropdown) => {
        const trigger = dropdown.querySelector("[data-dropdown-trigger]");
        const toggle = (force) => dropdown.classList.toggle("is-open", force);

        trigger?.addEventListener("click", () => {
            dropdown.classList.toggle("is-open");
        });

        document.addEventListener("click", (event) => {
            if (!dropdown.contains(event.target)) {
                toggle(false);
            }
        });
    });

    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const input = button.parentElement?.querySelector("input");
            if (!input) {
                return;
            }

            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";
            button.classList.toggle("is-visible", isPassword);
            button.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
        });
    });

    document.querySelectorAll("[data-loading-form]").forEach((form) => {
        form.addEventListener("submit", () => {
            const button = form.querySelector("[data-loading-button]");
            if (!button) {
                return;
            }

            button.classList.add("is-loading");
            button.setAttribute("disabled", "disabled");
        });
    });

    const modal = document.getElementById("auth-modal");
    const modalTitle = document.getElementById("auth-modal-title");
    const modalMessage = document.getElementById("auth-modal-message");
    const modalLogin = document.getElementById("auth-modal-login");
    const modalSignup = document.getElementById("auth-modal-signup");

    const closeModal = () => {
        if (modal) {
            modal.hidden = true;
        }
    };

    document.querySelector(".luxury-modal-close")?.addEventListener("click", closeModal);
    modal?.addEventListener("click", (event) => {
        if (event.target === modal) {
            closeModal();
        }
    });

    document.querySelectorAll(".wishlist-link").forEach((link) => {
        if (document.body.dataset.authenticated === "true") {
            return;
        }

        link.addEventListener("click", async (event) => {
            const href = link.getAttribute("href");
            const modalUrl = link.dataset.authModalUrl || `/accounts/auth-modal/?next=${encodeURIComponent(href)}`;
            if (!modal) {
                return;
            }

            event.preventDefault();

            try {
                const response = await fetch(modalUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } });
                const data = await response.json();
                modalTitle.textContent = data.title;
                modalMessage.textContent = data.message;
                modalLogin.href = data.login_url;
                modalSignup.href = data.signup_url;
                modal.hidden = false;
            } catch (error) {
                window.location.href = `/accounts/login/?next=${encodeURIComponent(href)}`;
            }
        });
    });
});

