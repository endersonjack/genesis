// Abrir, fechar e persistir estado da sidebar (localStorage + reapós navegação HTMX).

const DESKTOP_BREAKPOINT = 992;
const STORAGE_KEY = 'genesis_sidebar_collapsed';

function isDesktop() {
    return window.innerWidth >= DESKTOP_BREAKPOINT;
}

function getSidebarElements() {
    return {
        appWrapper: document.querySelector('.app-wrapper'),
        sidebar: document.getElementById('sidebar'),
        backdrop: document.getElementById('sidebarBackdrop'),
    };
}

function openMobileSidebar() {
    const { sidebar, backdrop } = getSidebarElements();
    if (!sidebar) return;
    sidebar.classList.add('mobile-open');
    backdrop?.classList.add('show');
    document.body.classList.add('overflow-hidden');
}

function closeMobileSidebar() {
    const { sidebar, backdrop } = getSidebarElements();
    if (!sidebar) return;
    sidebar.classList.remove('mobile-open');
    backdrop?.classList.remove('show');
    document.body.classList.remove('overflow-hidden');
}

function applyDesktopState() {
    const { appWrapper } = getSidebarElements();
    if (!appWrapper) return;
    const collapsed = localStorage.getItem(STORAGE_KEY) === 'true';
    appWrapper.classList.toggle('sidebar-collapsed', collapsed);
}

function toggleDesktopSidebar() {
    const { appWrapper } = getSidebarElements();
    if (!appWrapper) return;
    const willCollapse = !appWrapper.classList.contains('sidebar-collapsed');
    appWrapper.classList.toggle('sidebar-collapsed', willCollapse);
    localStorage.setItem(STORAGE_KEY, willCollapse ? 'true' : 'false');
}

function syncSidebarAfterNavigation() {
    const { appWrapper } = getSidebarElements();
    if (!appWrapper) return;
    if (isDesktop()) {
        applyDesktopState();
        closeMobileSidebar();
    } else {
        appWrapper.classList.remove('sidebar-collapsed');
        closeMobileSidebar();
    }
}

(function bindSidebarHandlersOnce() {
    if (window.__genesisSidebarHandlersBound) return;
    window.__genesisSidebarHandlersBound = true;

    document.addEventListener('click', function (e) {
        const openBtn = e.target.closest('#openSidebarBtn');
        const closeBtn = e.target.closest('#closeSidebarBtn');
        const toggleBtn = e.target.closest('#toggleSidebarDesktopBtn');
        const backdrop = e.target.closest('#sidebarBackdrop');

        if (toggleBtn && isDesktop()) {
            e.preventDefault();
            toggleDesktopSidebar();
            return;
        }
        if (openBtn && !isDesktop()) {
            e.preventDefault();
            openMobileSidebar();
            return;
        }
        if (closeBtn) {
            e.preventDefault();
            closeMobileSidebar();
            return;
        }
        if (backdrop) {
            closeMobileSidebar();
        }
    });

    window.addEventListener('resize', function () {
        const { appWrapper } = getSidebarElements();
        if (!appWrapper) return;
        if (isDesktop()) {
            applyDesktopState();
            closeMobileSidebar();
        } else {
            appWrapper.classList.remove('sidebar-collapsed');
            closeMobileSidebar();
        }
    });

    // Qualquer swap HTMX (incl. hx-target="body") pode substituir sidebar/topbar; não usar
    // evt.detail.target === document.body — o alvo nem sempre coincide com document.body.
    document.addEventListener('htmx:afterSettle', function () {
        syncSidebarAfterNavigation();
    });
})();

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', syncSidebarAfterNavigation);
} else {
    syncSidebarAfterNavigation();
}
