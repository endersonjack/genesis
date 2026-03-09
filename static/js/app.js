document.addEventListener("DOMContentLoaded", function () {
    const body = document.body;
    const sidebar = document.getElementById("sidebar");
    const openBtn = document.getElementById("openSidebarBtn");
    const closeBtn = document.getElementById("closeSidebarBtn");
    const backdrop = document.getElementById("sidebarBackdrop");
    const desktopToggleBtn = document.getElementById("toggleSidebarDesktopBtn");

    function openSidebar() {
        if (sidebar) sidebar.classList.add("show");
        if (backdrop) backdrop.classList.add("show");
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove("show");
        if (backdrop) backdrop.classList.remove("show");
    }

    function toggleDesktopSidebar() {
        body.classList.toggle("sidebar-collapsed");

        if (body.classList.contains("sidebar-collapsed")) {
            localStorage.setItem("sidebarCollapsed", "true");
        } else {
            localStorage.setItem("sidebarCollapsed", "false");
        }
    }

    if (window.innerWidth >= 992) {
        const savedState = localStorage.getItem("sidebarCollapsed");
        if (savedState === "true") {
            body.classList.add("sidebar-collapsed");
        }
    }

    if (openBtn) openBtn.addEventListener("click", openSidebar);
    if (closeBtn) closeBtn.addEventListener("click", closeSidebar);
    if (backdrop) backdrop.addEventListener("click", closeSidebar);
    if (desktopToggleBtn) desktopToggleBtn.addEventListener("click", toggleDesktopSidebar);

    window.addEventListener("resize", function () {
        if (window.innerWidth < 992) {
            body.classList.remove("sidebar-collapsed");
        } else {
            const savedState = localStorage.getItem("sidebarCollapsed");
            if (savedState === "true") {
                body.classList.add("sidebar-collapsed");
            }
        }
    });
});