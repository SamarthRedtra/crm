(function () {
    const OLD_TITLE = "Frappe Framework";
    const NEW_TITLE = "Redtra Framework";

    function replace() {
        document.querySelectorAll(".app-title, .app-item-title").forEach(el => {
            if (el.textContent.trim() === OLD_TITLE) {
                el.textContent = NEW_TITLE;
            }
        });
    }

    // 1) Run when page fully loads
    window.addEventListener("load", () => {
        replace();
    });

    // 2) Keep checking every 500ms until it appears
    const interval = setInterval(() => {
        replace();
        // Stop after it succeeds
        if (document.querySelector('.app-title')?.textContent.includes(NEW_TITLE)) {
            clearInterval(interval);
        }
    }, 500);

    // 3) Observe DOM changes (app switcher, desk navigation, etc.)
    const observer = new MutationObserver(() => replace());
    observer.observe(document.body, { childList: true, subtree: true });
})();
