(function () {
    "use strict";

    function setupCopyButton() {
        const input = document.getElementById("created-plugin-token");
        const button = document.getElementById("copy-plugin-token");
        const status = document.getElementById("copy-plugin-token-status");
        if (!input || !button || !status) return;

        function selectToken() {
            input.focus();
            input.select();
            input.setSelectionRange(0, input.value.length);
        }

        input.addEventListener("focus", function () { input.select(); });
        button.addEventListener("click", function () {
            status.textContent = "";

            function copied() {
                status.textContent = "Token copied.";
            }

            function fallback() {
                selectToken();
                let success = false;
                try {
                    success = typeof document.execCommand === "function" && document.execCommand("copy");
                } catch (error) {
                    success = false;
                }
                status.textContent = success
                    ? "Token copied."
                    : "Automatic copy unavailable. The token is selected; copy it manually.";
            }

            if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
                try {
                    Promise.resolve(navigator.clipboard.writeText(input.value)).then(copied, fallback);
                } catch (error) {
                    fallback();
                }
            } else {
                fallback();
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupCopyButton);
    } else {
        setupCopyButton();
    }
})();
