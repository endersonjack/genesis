// lógica de abrir, fechar e salvar o estado da sidebar.

document.addEventListener('DOMContentLoaded', function () {
    const appWrapper = document.querySelector('.app-wrapper');
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');

    const openSidebarBtn = document.getElementById('openSidebarBtn');
    const closeSidebarBtn = document.getElementById('closeSidebarBtn');
    const toggleSidebarDesktopBtn = document.getElementById('toggleSidebarDesktopBtn');

    if (!appWrapper || !sidebar) return;

    const DESKTOP_BREAKPOINT = 992;
    const STORAGE_KEY = 'genesis_sidebar_collapsed';

    function isDesktop() {
        return window.innerWidth >= DESKTOP_BREAKPOINT;
    }

    function openMobileSidebar() {
        sidebar.classList.add('mobile-open');
        backdrop?.classList.add('show');
        document.body.classList.add('overflow-hidden');
    }

    function closeMobileSidebar() {
        sidebar.classList.remove('mobile-open');
        backdrop?.classList.remove('show');
        document.body.classList.remove('overflow-hidden');
    }

    function applyDesktopState() {
        const collapsed = localStorage.getItem(STORAGE_KEY) === 'true';
        appWrapper.classList.toggle('sidebar-collapsed', collapsed);
    }

    function toggleDesktopSidebar() {
        const willCollapse = !appWrapper.classList.contains('sidebar-collapsed');
        appWrapper.classList.toggle('sidebar-collapsed', willCollapse);
        localStorage.setItem(STORAGE_KEY, willCollapse ? 'true' : 'false');
    }

    if (isDesktop()) {
        applyDesktopState();
        closeMobileSidebar();
    } else {
        appWrapper.classList.remove('sidebar-collapsed');
        closeMobileSidebar();
    }

    openSidebarBtn?.addEventListener('click', function () {
        if (isDesktop()) return;
        openMobileSidebar();
    });

    closeSidebarBtn?.addEventListener('click', function () {
        closeMobileSidebar();
    });

    backdrop?.addEventListener('click', function () {
        closeMobileSidebar();
    });

    toggleSidebarDesktopBtn?.addEventListener('click', function () {
        if (!isDesktop()) return;
        toggleDesktopSidebar();
    });

    window.addEventListener('resize', function () {
        if (isDesktop()) {
            applyDesktopState();
            closeMobileSidebar();
        } else {
            appWrapper.classList.remove('sidebar-collapsed');
            closeMobileSidebar();
        }
    });
});

// FIM lógica de abrir, fechar e salvar o estado da sidebar.