/**
 * Garante o header X-CSRFToken em requisições HTMX mutáveis.
 * Formulários: token do próprio form. Botões/links hx-post etc.: primeiro hidden da página ou cookie csrftoken.
 */
document.body.addEventListener('htmx:configRequest', function (event) {
    const method = (event.detail.verb || 'GET').toUpperCase();
    if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        return;
    }
    const elt = event.detail.elt;
    if (elt && elt.tagName === 'FORM') {
        const tokenInput = elt.querySelector('[name=csrfmiddlewaretoken]');
        if (tokenInput && tokenInput.value) {
            event.detail.headers['X-CSRFToken'] = tokenInput.value;
        }
        return;
    }
    const globalInput = document.querySelector('input[name=csrfmiddlewaretoken]');
    if (globalInput && globalInput.value) {
        event.detail.headers['X-CSRFToken'] = globalInput.value;
        return;
    }
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    if (m) {
        try {
            event.detail.headers['X-CSRFToken'] = decodeURIComponent(m[1]);
        } catch (e) {
            event.detail.headers['X-CSRFToken'] = m[1];
        }
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

    /**
     * Enquanto o overlay de loading está ativo, modais abertos ficavam visíveis
     * (por baixo ou piscando) até o HX-Refresh — fecha e limpa backdrop na hora.
     */
    function hideBootstrapModalsBeforeHtmxLoading() {
        if (window.bootstrap && bootstrap.Modal) {
            document.querySelectorAll('.modal.show').forEach(function (modalEl) {
                // Não fechar o modal de seções do funcionário aqui: o hide dispara
                // hidden.bs.modal, que limpa #modal-content e remove o <form> ainda em
                // voo no HTMX (upload multipart), impedindo afterRequest e travando o loading.
                if (modalEl.id === 'sectionModal') {
                    return;
                }
                var inst = bootstrap.Modal.getInstance(modalEl);
                if (inst) {
                    inst.hide();
                }
                modalEl.classList.remove('show');
                modalEl.setAttribute('aria-hidden', 'true');
                modalEl.style.display = 'none';
            });
        }
        document.querySelectorAll('.modal-backdrop').forEach(function (b) {
            b.remove();
        });
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');
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
            hideBootstrapModalsBeforeHtmxLoading();
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

    function eltSkipsGlobalLoading(elt) {
        return !!(elt && elt.closest && elt.closest('[data-no-global-loading]'));
    }

    document.addEventListener('htmx:beforeRequest', function (evt) {
        if (eltSkipsGlobalLoading(evt.detail.elt)) {
            return;
        }
        showGlobalHtmxLoading();
    });
    document.addEventListener('htmx:afterRequest', function (evt) {
        if (eltSkipsGlobalLoading(evt.detail.elt)) {
            return;
        }
        hideGlobalHtmxLoading();
    });

    /** Zera contador e esconde overlay (ex.: ao fechar modal após hx-get leve) */
    window.resetGlobalHtmxLoading = function () {
        loadingCount = 0;
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
        var el = getLoadingEl();
        if (el) {
            applyHide(el);
        }
    };
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

// Depois de request HTMX, busca mensagens no servidor para toasts — exceto quando a resposta
// pede HX-Refresh (página inteira recarrega e o HTML já traz {% messages %}).
document.body.addEventListener('htmx:afterRequest', function (evt) {
    const xhr = evt.detail.xhr;
    if (xhr && xhr.getResponseHeader('HX-Refresh')) {
        return;
    }
    refreshGenesisToasts();
});

/**
 * Copia texto para a área de transferência (Clipboard API ou fallback execCommand).
 * @param {string} text
 * @returns {Promise<void>}
 */
function copyTextToClipboard(text) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
        try {
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.setAttribute('readonly', '');
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            ta.style.top = '0';
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            ta.setSelectionRange(0, text.length);
            var ok = document.execCommand('copy');
            document.body.removeChild(ta);
            if (ok) {
                resolve();
            } else {
                reject(new Error('execCommand'));
            }
        } catch (e) {
            reject(e);
        }
    });
}

/**
 * Toast no canto (mesmo estilo dos Django messages), sem round-trip ao servidor.
 * @param {string} message
 * @param {'success'|'error'|'warning'|'info'} [variant]
 */
function showGenesisClientToast(message, variant) {
    if (!window.bootstrap || !bootstrap.Toast) {
        window.alert(message);
        return;
    }
    var container = document.getElementById('genesis-toast-container');
    if (!container) {
        window.alert(message);
        return;
    }
    var v = variant || 'success';
    var bgClass = 'text-bg-success';
    if (v === 'error') {
        bgClass = 'text-bg-danger';
    } else if (v === 'warning') {
        bgClass = 'text-bg-warning';
    } else if (v === 'info') {
        bgClass = 'text-bg-primary';
    }

    var el = document.createElement('div');
    el.className = 'toast align-items-end border-0 js-genesis-toast ' + bgClass;
    el.setAttribute('role', 'alert');
    el.setAttribute('aria-live', 'polite');
    el.setAttribute('aria-atomic', 'true');
    el.setAttribute('data-bs-delay', '4200');
    el.setAttribute('data-bs-autohide', 'true');

    var header = document.createElement('div');
    header.className = 'toast-header border-0 bg-transparent';
    var closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'btn-close btn-close-white ms-auto m-auto';
    closeBtn.setAttribute('data-bs-dismiss', 'toast');
    closeBtn.setAttribute('aria-label', 'Fechar');
    header.appendChild(closeBtn);

    var body = document.createElement('div');
    body.className = 'toast-body';
    body.textContent = message;

    el.appendChild(header);
    el.appendChild(body);
    container.appendChild(el);

    var toast = new bootstrap.Toast(el, {
        autohide: true,
        delay: 4200,
    });
    el.addEventListener('hidden.bs.toast', function onHidden() {
        el.removeEventListener('hidden.bs.toast', onHidden);
        el.remove();
    });
    toast.show();
}

window.copyTextToClipboard = copyTextToClipboard;
window.showGenesisClientToast = showGenesisClientToast;

/**
 * Bootstrap Dropdown: após swap HTMX em `body`, `evt.detail.target` pode não cobrir
 * toda a árvore; em páginas como VT o botão de configurações ficava “morto”.
 * Varremos sempre `document.body` e repetimos no primeiro paint (F5 / entrada direta).
 */
function initBootstrapDropdowns() {
    if (!window.bootstrap || !bootstrap.Dropdown) return;
    var root = document.body;
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll('[data-bs-toggle="dropdown"]').forEach(function (el) {
        try {
            bootstrap.Dropdown.getOrCreateInstance(el);
        } catch (e) {
            /* ignore */
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBootstrapDropdowns);
} else {
    initBootstrapDropdowns();
}

document.body.addEventListener('htmx:afterSettle', function () {
    initBootstrapDropdowns();
});

window.initBootstrapDropdowns = initBootstrapDropdowns;

/**
 * Voltar com o botão do browser / bfcache: o overlay de loading e o contador podem
 * ficar num estado inconsistente (sem afterRequest). Reset evita loading eterno.
 * Re-inicializar dropdowns após restaurar a página do cache.
 */
window.addEventListener('pageshow', function (event) {
    if (event.persisted && typeof window.resetGlobalHtmxLoading === 'function') {
        window.resetGlobalHtmxLoading();
    }
    if (typeof initBootstrapDropdowns === 'function') {
        initBootstrapDropdowns();
    }
});

window.addEventListener('popstate', function () {
    if (typeof window.resetGlobalHtmxLoading === 'function') {
        window.resetGlobalHtmxLoading();
    }
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
