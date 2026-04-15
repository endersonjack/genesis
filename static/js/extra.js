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
    /** Enquanto o leitor QR consulta / navega, não esconder o overlay por afterRequest de outro HTMX. */
    var LEITOR_CONSULTING_CLASS = 'genesis-leitor-consulting';

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
        var skipModalIds = {
            sectionModal: true,
            modalPadrao: true,
            modalAfLinha: true,
            fornecedorModal: true,
            clienteModal: true,
            obraModal: true,
            copiarCadastroModal: true,
        };
        if (window.bootstrap && bootstrap.Modal) {
            document.querySelectorAll('.modal.show').forEach(function (modalEl) {
                // Não fechar o modal de seções do funcionário aqui: o hide dispara
                // hidden.bs.modal, que limpa #modal-content e remove o <form> ainda em
                // voo no HTMX (upload multipart), impedindo afterRequest e travando o loading.
                // modalPadrao (dashboard / HTMX em #modal-content): fechar aqui remove o backdrop
                // e o fundo deixa de escurecer.
                if (skipModalIds[modalEl.id]) {
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
        var modalPadraoEl = document.getElementById('modalPadrao');
        var sectionModalEl = document.getElementById('sectionModal');
        var keepBackdrop =
            (modalPadraoEl && modalPadraoEl.classList.contains('show')) ||
            (sectionModalEl && sectionModalEl.classList.contains('show'));
        if (keepBackdrop) {
            return;
        }
        document.querySelectorAll('.modal-backdrop').forEach(function (b) {
            b.remove();
        });
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');
    }

    function showGlobalHtmxLoading() {
        var el = getLoadingEl();
        if (!el) return;
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
        loadingCount += 1;
        if (loadingCount === 1) {
            showStartedAt = Date.now();
            hideBootstrapModalsBeforeHtmxLoading();
        }
        applyShow(el);
    }

    function hideGlobalHtmxLoading() {
        loadingCount = Math.max(0, loadingCount - 1);
        if (loadingCount > 0) return;

        if (document.documentElement.classList.contains(LEITOR_CONSULTING_CLASS)) {
            return;
        }

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
        document.documentElement.classList.remove(LEITOR_CONSULTING_CLASS);
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
        var el = getLoadingEl();
        if (el) {
            applyHide(el);
        }
    };

    /**
     * Mesmo overlay que HTMX (contador + cancela timer de hide pendente).
     * Evita lista parcial HTMX “apagar” o loading do leitor QR.
     */
    window.genesisShowGlobalNavLoading = function () {
        showGlobalHtmxLoading();
        var el = getLoadingEl();
        if (el) void el.offsetHeight;
    };

    window.genesisLeitorConsultingBegin = function () {
        document.documentElement.classList.add(LEITOR_CONSULTING_CLASS);
    };

    window.genesisLeitorConsultingEnd = function () {
        document.documentElement.classList.remove(LEITOR_CONSULTING_CLASS);
    };

    /**
     * Navegação full-page: overlay já foi exibido na consulta; só garante pintura antes do href.
     */
    window.genesisNavigateWithGlobalLoading = function (url) {
        if (!url) return;
        var el = getLoadingEl();
        if (el) void el.offsetHeight;
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                window.location.href = url;
            });
        });
    };
})();

/**
 * Fornecedores: o swap HTMX vai para #fornecedorModalSwapTarget; o evento htmx:afterSwap
 * dispara nesse alvo (não no botão/tr), por isso abrimos o modal aqui.
 */
document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail.target;
    if (!t || t.id !== 'fornecedorModalSwapTarget') {
        return;
    }
    var modal = document.getElementById('fornecedorModal');
    if (!(modal && window.bootstrap && bootstrap.Modal)) {
        return;
    }
    bootstrap.Modal.getOrCreateInstance(modal).show();
});

document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail.target;
    if (!t || t.id !== 'clienteModalSwapTarget') {
        return;
    }
    var modal = document.getElementById('clienteModal');
    if (!(modal && window.bootstrap && bootstrap.Modal)) {
        return;
    }
    bootstrap.Modal.getOrCreateInstance(modal).show();
});

document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail.target;
    if (!t || t.id !== 'obraModalSwapTarget') {
        return;
    }
    var modal = document.getElementById('obraModal');
    if (!(modal && window.bootstrap && bootstrap.Modal)) {
        return;
    }
    bootstrap.Modal.getOrCreateInstance(modal).show();
    if (window.genesisInputMaskScan) {
        window.genesisInputMaskScan(modal);
    }
});

/** Cadastros: copiar para outra empresa — conteúdo em #copiarCadastroModalInner */
document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail.target;
    if (!t || t.id !== 'copiarCadastroModalInner') {
        return;
    }
    var modal = document.getElementById('copiarCadastroModal');
    if (!(modal && window.bootstrap && bootstrap.Modal)) {
        return;
    }
    bootstrap.Modal.getOrCreateInstance(modal).show();
    if (window.genesisInputMaskScan) {
        window.genesisInputMaskScan(modal);
    }
});

document.body.addEventListener('closeCopiarCadastroModal', function () {
    var el = document.getElementById('copiarCadastroModal');
    if (!el || !window.bootstrap || !bootstrap.Modal) {
        return;
    }
    var inst = bootstrap.Modal.getInstance(el);
    if (inst) {
        inst.hide();
    }
});

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
 * Toasts disparados pelo servidor via cabeçalho HX-Trigger (ex.: toggle salário família).
 */
document.body.addEventListener('genesisClientToast', function (evt) {
    var d = evt.detail;
    if (!d || typeof window.showGenesisClientToast !== 'function') {
        return;
    }
    window.showGenesisClientToast(
        d.message || 'Atualizado.',
        d.variant || 'success'
    );
});

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

/**
 * Cards de falta (Apontamento): o Collapse do Bootstrap quebra após navegação HTMX
 * (abre e não fecha). Usamos toggle delegado só com classes `.show` / `.collapsed`
 * (mesmo CSS do Bootstrap para .collapse).
 */
function setupApontamentoFaltaCollapseDelegate() {
    if (window.__genesisApontFaltaCollapseDelegate) return;
    window.__genesisApontFaltaCollapseDelegate = true;

    document.body.addEventListener(
        'click',
        function (e) {
            var btn = e.target.closest('.apont-falta-card .apont-falta-card__toggle');
            if (!btn) return;

            var sel = btn.getAttribute('data-bs-target');
            if (!sel || sel.charAt(0) !== '#') return;

            var panel = document.getElementById(sel.slice(1));
            if (!panel || !panel.classList.contains('collapse')) return;

            e.preventDefault();
            e.stopPropagation();

            var willShow = !panel.classList.contains('show');
            panel.classList.toggle('show', willShow);
            btn.classList.toggle('collapsed', !willShow);
            btn.setAttribute('aria-expanded', willShow ? 'true' : 'false');
        },
        true
    );
}

function runBootstrapHtmxReinit() {
    initBootstrapDropdowns();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runBootstrapHtmxReinit);
} else {
    runBootstrapHtmxReinit();
}

document.body.addEventListener('htmx:afterSettle', runBootstrapHtmxReinit);

setupApontamentoFaltaCollapseDelegate();

window.initBootstrapDropdowns = initBootstrapDropdowns;
window.runBootstrapHtmxReinit = runBootstrapHtmxReinit;

/**
 * Voltar com o botão do browser / bfcache: o overlay de loading e o contador podem
 * ficar num estado inconsistente (sem afterRequest). Reset evita loading eterno.
 * Re-inicializar dropdowns após restaurar a página do cache.
 */
window.addEventListener('pageshow', function (event) {
    // Alguns browsers/restaurações (incluindo botão "voltar" do mouse)
    // não sinalizam `event.persisted`, mas ainda podem restaurar o DOM
    // sem disparar o ciclo completo do HTMX (ficando sem afterRequest).
    if (typeof window.resetGlobalHtmxLoading === 'function') {
        window.resetGlobalHtmxLoading();
    }
    if (typeof window.runBootstrapHtmxReinit === 'function') {
        window.runBootstrapHtmxReinit();
    }
});

window.addEventListener('popstate', function () {
    if (typeof window.resetGlobalHtmxLoading === 'function') {
        window.resetGlobalHtmxLoading();
    }
});

// HTMX history restore/popped: ao voltar/avançar, o estado do overlay pode ficar preso.
document.body.addEventListener('htmx:historyRestore', function () {
    if (typeof window.resetGlobalHtmxLoading === 'function') {
        window.resetGlobalHtmxLoading();
    }
    if (typeof window.runBootstrapHtmxReinit === 'function') {
        window.runBootstrapHtmxReinit();
    }
});
document.body.addEventListener('htmx:popped', function () {
    if (typeof window.resetGlobalHtmxLoading === 'function') {
        window.resetGlobalHtmxLoading();
    }
    if (typeof window.runBootstrapHtmxReinit === 'function') {
        window.runBootstrapHtmxReinit();
    }
});

/**
 * Estoque: overlay de navegação em cliques em links internos (carregamento entre páginas).
 * Páginas com `body.estoque-pages`. Respeita `data-no-page-loading`, modais, atalhos e hx-boost.
 */
(function () {
    function isEstoquePage() {
        return document.body && document.body.classList.contains('estoque-pages');
    }

    document.addEventListener(
        'click',
        function (e) {
            if (!isEstoquePage()) return;
            var a = e.target.closest('a[href]');
            if (!a) return;
            if (a.hasAttribute('data-no-page-loading')) return;
            if (a.getAttribute('target') === '_blank') return;
            if (a.getAttribute('download')) return;
            if (e.defaultPrevented) return;
            if (e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
            if (a.closest('.modal')) return;
            if (a.closest('[data-bs-toggle]')) return;
            var href = a.getAttribute('href');
            if (!href || href === '#' || href.startsWith('javascript:')) return;
            try {
                var u = new URL(href, window.location.origin);
                if (u.origin !== window.location.origin) return;
            } catch (err) {
                return;
            }
            if (typeof window.genesisShowGlobalNavLoading === 'function') {
                window.genesisShowGlobalNavLoading();
            }
        },
        true
    );

    window.addEventListener('pageshow', function () {
        if (!isEstoquePage()) return;
        if (typeof window.resetGlobalHtmxLoading === 'function') {
            window.resetGlobalHtmxLoading();
        }
    });
})();

/**
 * Dashboard RH — card Apontamento: miniaturas abrem modal com carrossel (álbum).
 */
(function () {
    var carouselInstance = null;

    document.body.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-apont-album-idx]');
        if (!btn || !window.bootstrap) {
            return;
        }

        var dest = btn.closest('[data-apont-album-scope]');
        if (!dest) {
            return;
        }
        var dataRoot = dest.querySelector('.apont-fotos-album-data');
        if (!dataRoot) {
            return;
        }

        var urls = [];
        dataRoot.querySelectorAll('[data-src]').forEach(function (s) {
            var u = s.getAttribute('data-src');
            if (u) {
                urls.push(u);
            }
        });
        if (!urls.length) {
            return;
        }

        e.preventDefault();

        var startIdx = parseInt(btn.getAttribute('data-apont-album-idx'), 10);
        if (isNaN(startIdx) || startIdx < 0) {
            startIdx = 0;
        }
        if (startIdx >= urls.length) {
            startIdx = 0;
        }

        var modalEl = document.getElementById('apontObsFotosAlbumModal');
        var carouselEl = document.getElementById('apontObsFotosAlbumCarousel');
        var inner = document.getElementById('apontObsFotosAlbumInner');
        var indicators = document.getElementById('apontObsFotosAlbumIndicators');
        var counter = document.getElementById('apontObsFotosAlbumCounter');
        if (!modalEl || !carouselEl || !inner || !indicators || !counter) {
            return;
        }

        if (carouselInstance) {
            carouselInstance.dispose();
            carouselInstance = null;
        }
        if (carouselEl._apontSlidHandler) {
            carouselEl.removeEventListener('slid.bs.carousel', carouselEl._apontSlidHandler);
            delete carouselEl._apontSlidHandler;
        }

        inner.innerHTML = '';
        indicators.innerHTML = '';

        var prevBtn = carouselEl.querySelector('.carousel-control-prev');
        var nextBtn = carouselEl.querySelector('.carousel-control-next');

        urls.forEach(function (url, i) {
            var wrap = document.createElement('div');
            wrap.className = 'carousel-item' + (i === startIdx ? ' active' : '');
            var img = document.createElement('img');
            img.src = url;
            img.className = 'd-block';
            img.alt = 'Foto ' + (i + 1) + ' de ' + urls.length;
            wrap.appendChild(img);
            inner.appendChild(wrap);

            if (urls.length > 1) {
                var ind = document.createElement('button');
                ind.type = 'button';
                ind.setAttribute('data-bs-target', '#apontObsFotosAlbumCarousel');
                ind.setAttribute('data-bs-slide-to', String(i));
                ind.setAttribute('aria-label', 'Ir para foto ' + (i + 1));
                if (i === startIdx) {
                    ind.classList.add('active');
                    ind.setAttribute('aria-current', 'true');
                }
                indicators.appendChild(ind);
            }
        });

        if (urls.length <= 1) {
            indicators.classList.add('d-none');
            if (prevBtn) {
                prevBtn.classList.add('d-none');
            }
            if (nextBtn) {
                nextBtn.classList.add('d-none');
            }
        } else {
            indicators.classList.remove('d-none');
            if (prevBtn) {
                prevBtn.classList.remove('d-none');
            }
            if (nextBtn) {
                nextBtn.classList.remove('d-none');
            }
        }

        function updateCounter(activeIndex) {
            counter.textContent = activeIndex + 1 + ' / ' + urls.length;
        }
        updateCounter(startIdx);

        carouselEl._apontSlidHandler = function (ev) {
            updateCounter(ev.to);
        };
        carouselEl.addEventListener('slid.bs.carousel', carouselEl._apontSlidHandler);

        carouselInstance = new bootstrap.Carousel(carouselEl, {
            interval: false,
            wrap: true,
            ride: false,
        });

        if (startIdx > 0) {
            carouselInstance.to(startIdx);
        }

        var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    });
})();

/**
 * Apontamento: evita duplo clique no envio — botão com `.apont-submit-spinner` + `.apont-submit-label`.
 */
window.genesisApontFormSubmitBusy = function (form, busy) {
    if (!form) return;
    var btn = form.querySelector('button[type="submit"]');
    if (!btn) return;
    var spin = btn.querySelector('.apont-submit-spinner');
    var label = btn.querySelector('.apont-submit-label');
    if (busy) {
        if (label && !label.dataset.apontOrigTxt) {
            label.dataset.apontOrigTxt = (label.textContent || '').trim();
        }
        btn.disabled = true;
        btn.setAttribute('aria-busy', 'true');
        if (spin) spin.classList.remove('d-none');
        if (label) label.textContent = 'Salvando…';
    } else {
        btn.disabled = false;
        btn.removeAttribute('aria-busy');
        if (spin) spin.classList.add('d-none');
        if (label && label.dataset.apontOrigTxt) {
            label.textContent = label.dataset.apontOrigTxt;
            delete label.dataset.apontOrigTxt;
        }
    }
};

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
