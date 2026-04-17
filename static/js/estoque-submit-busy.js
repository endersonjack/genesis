/**
 * Estoque (body.estoque-pages): evita duplo clique em envios importantes.
 * Marque o <form> com `js-estoque-form-busy` e, opcionalmente,
 * `data-estoque-busy-label="Texto…"` no botão (padrão: "Salvando…").
 *
 * - POST página inteira: mantém estado até a navegação.
 * - Formulário HTMX em modal: durante o voo da requisição; após resposta,
 *   reativa se o formulário ainda estiver no DOM (ex.: erro de validação).
 * - Ao fechar o modal (hidden.bs.modal), todos os formulários marcados
 *   dentro dele são reativados.
 */
(function () {
    'use strict';

    function isEstoquePage() {
        return document.body && document.body.classList.contains('estoque-pages');
    }

    function allSubmitButtons(form) {
        var list = Array.prototype.slice.call(form.querySelectorAll('button[type="submit"]'));
        if (form.id) {
            var sel;
            if (typeof CSS !== 'undefined' && CSS.escape) {
                sel = 'button[type="submit"][form="' + CSS.escape(form.id) + '"]';
            } else {
                sel =
                    'button[type="submit"][form="' +
                    form.id.replace(/\\/g, '\\\\').replace(/"/g, '\\"') +
                    '"]';
            }
            try {
                document.querySelectorAll(sel).forEach(function (b) {
                    list.push(b);
                });
            } catch (e) {
                // ignore
            }
        }
        return list;
    }

    function defaultBusyLabel(form) {
        var raw = (form.getAttribute('data-estoque-busy-label') || '').trim();
        return raw || 'Salvando…';
    }

    function applySubmitBusy(btn, busy, waitText) {
        if (!btn) return;
        if (busy) {
            if (!btn.dataset.estoqueOrigInner) {
                btn.dataset.estoqueOrigInner = btn.innerHTML;
            }
            btn.disabled = true;
            btn.setAttribute('aria-busy', 'true');
            btn.innerHTML =
                '<span class="spinner-border spinner-border-sm align-middle" role="status" aria-hidden="true"></span> ' +
                '<span class="align-middle">' +
                (waitText || 'Salvando…') +
                '</span>';
        } else {
            btn.disabled = false;
            btn.removeAttribute('aria-busy');
            if (btn.dataset.estoqueOrigInner) {
                btn.innerHTML = btn.dataset.estoqueOrigInner;
                delete btn.dataset.estoqueOrigInner;
            }
        }
    }

    function resetFormBusy(form) {
        if (!form) return;
        delete form.dataset.estoqueBusyLocked;
        allSubmitButtons(form).forEach(function (b) {
            applySubmitBusy(b, false);
        });
    }

    function isHtmxForm(form) {
        return !!(form.getAttribute('hx-post') || form.getAttribute('hx-get'));
    }

    if (!document.body) {
        return;
    }

    document.body.addEventListener(
        'submit',
        function (e) {
            if (!isEstoquePage()) return;
            var form = e.target;
            if (!form || form.tagName !== 'FORM') return;
            if (!form.classList.contains('js-estoque-form-busy')) return;
            if (form.dataset.estoqueBusyLocked === '1') {
                e.preventDefault();
                e.stopPropagation();
                return;
            }
            form.dataset.estoqueBusyLocked = '1';
            var waitLabel = defaultBusyLabel(form);
            allSubmitButtons(form).forEach(function (b) {
                applySubmitBusy(b, true, waitLabel);
            });
        },
        true
    );

    document.body.addEventListener('hidden.bs.modal', function (e) {
        if (!isEstoquePage()) return;
        var modal = e.target;
        if (!modal || !modal.querySelectorAll) return;
        modal.querySelectorAll('form.js-estoque-form-busy').forEach(resetFormBusy);
    });

    document.body.addEventListener('htmx:afterRequest', function (e) {
        if (!isEstoquePage()) return;
        var form = e.detail.elt;
        if (!form || form.tagName !== 'FORM' || !form.classList.contains('js-estoque-form-busy')) return;
        if (!isHtmxForm(form)) return;
        if (e.detail.successful && e.detail.xhr) {
            var loc = e.detail.xhr.getResponseHeader('HX-Redirect');
            if (loc) {
                return;
            }
        }
        if (form.isConnected) {
            resetFormBusy(form);
        }
    });

    window.addEventListener('pageshow', function () {
        if (!isEstoquePage()) return;
        document.querySelectorAll('form.js-estoque-form-busy').forEach(resetFormBusy);
    });
})();
