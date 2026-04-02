/**
 * Garante o header X-CSRFToken em requisições HTMX (ex.: modais carregados dinamicamente).
 */
document.body.addEventListener('htmx:configRequest', function (event) {
    const elt = event.detail.elt;
    if (!elt || elt.tagName !== 'FORM') {
        return;
    }
    const tokenInput = elt.querySelector('[name=csrfmiddlewaretoken]');
    if (tokenInput && tokenInput.value) {
        event.detail.headers['X-CSRFToken'] = tokenInput.value;
    }
});

/**
 * Loading global: qualquer requisição HTMX mostra overlay centralizado.
 * Contador evita esconder cedo quando há requisições paralelas.
 * Tempo mínimo visível evita “piscar” em respostas instantâneas.
 */
(function () {
    var loadingCount = 0;
    var showStartedAt = 0;
    var hideTimer = null;
    var MIN_VISIBLE_MS = 240;

    function getLoadingEl() {
        return document.getElementById('global-htmx-loading');
    }

    function applyShow(el) {
        el.classList.add('global-htmx-loading--show');
        el.setAttribute('aria-hidden', 'false');
        el.setAttribute('aria-busy', 'true');
    }

    function applyHide(el) {
        el.classList.remove('global-htmx-loading--show');
        el.setAttribute('aria-hidden', 'true');
        el.setAttribute('aria-busy', 'false');
    }

    function showGlobalHtmxLoading() {
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
        loadingCount += 1;
        var el = getLoadingEl();
        if (!el) return;
        if (loadingCount === 1) {
            showStartedAt = Date.now();
        }
        applyShow(el);
    }

    function hideGlobalHtmxLoading() {
        loadingCount = Math.max(0, loadingCount - 1);
        if (loadingCount > 0) return;

        var el = getLoadingEl();
        if (!el) return;

        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }

        var wait = Math.max(0, MIN_VISIBLE_MS - (Date.now() - showStartedAt));
        hideTimer = setTimeout(function () {
            hideTimer = null;
            if (loadingCount === 0) {
                applyHide(el);
            }
        }, wait);
    }

    document.addEventListener('htmx:beforeRequest', showGlobalHtmxLoading);
    document.addEventListener('htmx:afterRequest', hideGlobalHtmxLoading);
})();

// Toasts globais (Django messages) renderizados no `templates/base.html`
function showGenesisToasts(scope) {
    if (!window.bootstrap || !bootstrap.Toast) return;

    const root = scope || document;
    const toastEls = root.querySelectorAll('.js-genesis-toast');
    if (!toastEls || toastEls.length === 0) return;

    toastEls.forEach(function (toastEl) {
        const toast = bootstrap.Toast.getOrCreateInstance(toastEl);
        toast.show();
    });
}

document.addEventListener('DOMContentLoaded', function () {
    showGenesisToasts(document);
});

let genesisToastLastRefresh = 0;

async function refreshGenesisToasts() {
    const container = document.getElementById('genesis-toast-container');
    if (!container) return;

    const now = Date.now();
    if (now - genesisToastLastRefresh < 700) return; // evita rajadas de requests
    genesisToastLastRefresh = now;

    const url = `/messages/toasts/?_=${now}`;

    try {
        const res = await fetch(url, {
            method: 'GET',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        if (!res.ok) return;

        const html = await res.text();
        if (!html || !html.trim()) return;

        container.innerHTML = html;
        showGenesisToasts(container);
    } catch (e) {
        // silencioso: não queremos quebrar o fluxo da UI
    }
}

// Depois de qualquer request HTMX, busca mensagens novas no servidor
// e mostra como toasts no canto inferior direito.
document.body.addEventListener('htmx:afterRequest', function () {
    refreshGenesisToasts();
});

function limparFormulario(btn) {
    if (!confirm('Deseja realmente limpar todos os campos?')) return;

    const form = btn.closest('.modal').querySelector('form');

    form.querySelectorAll('input, textarea, select').forEach(field => {
        if (field.name === 'csrfmiddlewaretoken') return;

        if (field.type === 'checkbox' || field.type === 'radio') {
            field.checked = false;
        } else if (field.tagName === 'SELECT') {
            field.selectedIndex = 0;
        } else {
            field.value = '';
        }
    });
}
