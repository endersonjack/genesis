/**
 * Leitor 2D modo cunha: botão liga/desliga captura num campo oculto focado.
 * Desligue para usar a busca normal; com modal aberto não rouba o foco.
 */
(function () {
    'use strict';

    function setFeedback(el, msg, isErr) {
        if (!el) return;
        el.textContent = msg || '';
        el.classList.toggle('text-danger', !!isErr);
        el.classList.toggle('text-muted', !isErr);
    }

    function setConsultingUi(btn, on) {
        if (!btn) return;
        btn.classList.toggle('estoque-leitor-btn--busy', on);
        btn.setAttribute('aria-busy', on ? 'true' : 'false');
    }

    /**
     * Evita roubar foco para o campo de captura quando o usuário está em outro controle.
     * Com leitor dentro do modal «Buscar itens», não tomar foco da descrição nem da Qtd solicitada.
     */
    function modalBlocksRefocus(captureEl) {
        var m = document.querySelector('.modal.show');
        if (!m) return false;
        var a = document.activeElement;
        if (captureEl && m.contains(captureEl)) {
            if (a && a !== captureEl && m.contains(a)) {
                var tag = (a.tagName || '').toUpperCase();
                if (
                    tag === 'INPUT' ||
                    tag === 'TEXTAREA' ||
                    tag === 'SELECT'
                ) {
                    return true;
                }
            }
            return false;
        }
        if (a && a.closest && a.closest('.modal.show')) return true;
        return false;
    }

    function leitorStorageKey(empresaPk) {
        return 'genesis.estoque.leitor2d.enabled.' + String(empresaPk);
    }

    function readLeitorPersisted(empresaPk) {
        try {
            if (empresaPk == null || empresaPk === '') return false;
            return window.localStorage.getItem(leitorStorageKey(empresaPk)) === '1';
        } catch (e) {
            return false;
        }
    }

    function writeLeitorPersisted(empresaPk, on) {
        try {
            if (empresaPk == null || empresaPk === '') return;
            window.localStorage.setItem(
                leitorStorageKey(empresaPk),
                on ? '1' : '0'
            );
        } catch (e) {
            /* quota / modo privado */
        }
    }

    function bindWrap(wrap) {
        if (!wrap || wrap.dataset.estoqueLeitorBound === '1') return;
        wrap.dataset.estoqueLeitorBound = '1';

        var btn = wrap.querySelector('.js-estoque-leitor-btn');
        var cap = wrap.querySelector('.js-estoque-leitor-capture');
        var fb = wrap.querySelector('.js-estoque-leitor-fb');
        var resolveUrl = wrap.getAttribute('data-resolve-url');
        var empresaPk = wrap.getAttribute('data-empresa-pk');
        var leitorMode = wrap.getAttribute('data-leitor-mode') || '';
        if (!btn || !cap || !resolveUrl) return;

        var armed = false;
        var busy = false;
        var suspendedByQty = false;

        function setArmed(on, opts) {
            opts = opts || {};
            var persist = opts.persist !== false;
            var clearSearch = opts.clearSearch !== false;
            armed = on;
            if (persist) {
                writeLeitorPersisted(empresaPk, on);
            }
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
            btn.setAttribute(
                'aria-label',
                on ? 'Leitor QR ativo — desligar' : 'Leitor QR desligado — ativar'
            );
            btn.classList.toggle('estoque-leitor-btn--on', on);
            if (on) {
                if (leitorMode === 'requisicao-buscar' && clearSearch) {
                    var rq = document.getElementById('req-itens-q');
                    var rqh = document.getElementById('req-itens-q-hidden');
                    if (rq) {
                        rq.value = '';
                        if (rqh) rqh.value = '';
                        rq.dispatchEvent(
                            new Event('input', { bubbles: true })
                        );
                    }
                }
                cap.focus();
                setFeedback(fb, 'Leitor ativo. Aponte e leia o código.', false);
            } else {
                setFeedback(fb, '', false);
                if (document.activeElement === cap) {
                    cap.blur();
                }
            }
        }

        /** Overlay #global-htmx-loading (extra.js), igual a cliques em links nas páginas estoque. */
        var usePageLoading = leitorMode !== 'requisicao-buscar';

        function clearPageLoadingIfAny() {
            if (
                usePageLoading &&
                typeof window.resetGlobalHtmxLoading === 'function'
            ) {
                window.resetGlobalHtmxLoading();
            }
        }

        function resolve(code) {
            if (busy) return;
            var c = (code || '').trim();
            if (!c) return;
            busy = true;
            setConsultingUi(btn, true);
            if (usePageLoading) {
                if (typeof window.genesisLeitorConsultingBegin === 'function') {
                    window.genesisLeitorConsultingBegin();
                }
                if (typeof window.genesisShowGlobalNavLoading === 'function') {
                    window.genesisShowGlobalNavLoading();
                }
            }
            setFeedback(fb, 'Consultando…', false);
            var u =
                resolveUrl +
                (resolveUrl.indexOf('?') >= 0 ? '&' : '?') +
                'c=' +
                encodeURIComponent(c);
            fetch(u, {
                credentials: 'same-origin',
                headers: { Accept: 'application/json' },
            })
                .then(function (r) {
                    return r.json().then(function (j) {
                        return { ok: r.ok, j: j };
                    });
                })
                .then(function (x) {
                    if (!x.ok || !x.j || !x.j.ok) {
                        clearPageLoadingIfAny();
                        var err = (x.j && x.j.error) || '';
                        if (err === 'not_found') {
                            setFeedback(
                                fb,
                                'Item não encontrado nesta empresa.',
                                true
                            );
                        } else if (err === 'empresa') {
                            setFeedback(
                                fb,
                                'Este QR pertence a outra empresa.',
                                true
                            );
                        } else {
                            setFeedback(
                                fb,
                                'Código inválido. Use o QR do cadastro do item.',
                                true
                            );
                        }
                        return;
                    }
                    cap.value = '';
                    if (
                        leitorMode === 'requisicao-buscar' &&
                        x.j &&
                        x.j.kind === 'ferramenta'
                    ) {
                        clearPageLoadingIfAny();
                        setFeedback(
                            fb,
                            'Este QR é de uma ferramenta, não de um item de estoque.',
                            true
                        );
                        if (armed) {
                            cap.focus();
                        }
                        return;
                    }
                    if (leitorMode === 'requisicao-buscar') {
                        var qEl = document.getElementById('req-itens-q');
                        var qhEl = document.getElementById('req-itens-q-hidden');
                        var itemId = String(x.j.item_id);
                        if (qEl && window.htmx) {
                            var hxGet = qEl.getAttribute('hx-get');
                            if (hxGet) {
                                if (qhEl) qhEl.value = '';
                                qEl.value = '';
                                var sep = hxGet.indexOf('?') >= 0 ? '&' : '?';
                                var reqUrl =
                                    hxGet +
                                    sep +
                                    'q=' +
                                    encodeURIComponent(itemId);
                                htmx.ajax('GET', reqUrl, {
                                    target:
                                        qEl.getAttribute('hx-target') ||
                                        '#req-itens-list',
                                    swap: 'innerHTML',
                                });
                            }
                            // Cunha envia caracteres para o foco: manter foco no campo de captura,
                            // senão a 2ª leitura cai no input de descrição como texto.
                            if (armed) {
                                cap.focus();
                            }
                            setFeedback(
                                fb,
                                'Item localizado na lista abaixo.',
                                false
                            );
                            return;
                        }
                    }
                    setFeedback(fb, '', false);
                    var dest =
                        x.j.detail_url ||
                        (function () {
                            var loc = new URL(window.location.href);
                            loc.searchParams.set(
                                'edit_item',
                                String(x.j.item_id)
                            );
                            return loc.toString();
                        })();
                    if (
                        typeof window.genesisNavigateWithGlobalLoading ===
                        'function'
                    ) {
                        window.genesisNavigateWithGlobalLoading(dest);
                    } else {
                        window.location.href = dest;
                    }
                    return;
                })
                .catch(function () {
                    clearPageLoadingIfAny();
                    setFeedback(fb, 'Falha ao consultar. Tente de novo.', true);
                })
                .finally(function () {
                    busy = false;
                    setConsultingUi(btn, false);
                });
        }

        btn.addEventListener('click', function () {
            suspendedByQty = false;
            setArmed(!armed, { persist: true, clearSearch: true });
        });

        // Requisição: manter leitor ligado, mas pausar enquanto edita "Qtd solicitada".
        if (leitorMode === 'requisicao-buscar' && !wrap.dataset.reqQtyPauseBound) {
            wrap.dataset.reqQtyPauseBound = '1';
            document.addEventListener(
                'focusin',
                function (ev) {
                    var t = ev && ev.target;
                    if (!t || !armed) return;
                    var qty = t.closest ? t.closest('.js-req-item-qtd') : null;
                    if (!qty) return;
                    var modal = document.getElementById('modalPadrao');
                    if (modal && modal.classList.contains('show')) {
                        suspendedByQty = true;
                        setArmed(false, { persist: false, clearSearch: false });
                    }
                },
                true
            );
            document.addEventListener(
                'focusout',
                function (ev) {
                    var t = ev && ev.target;
                    if (!t) return;
                    var qty = t.closest ? t.closest('.js-req-item-qtd') : null;
                    if (!qty) return;
                    if (!suspendedByQty) return;
                    suspendedByQty = false;
                    setTimeout(function () {
                        if (busy) return;
                        // Reativa sem persistir e sem limpar a busca.
                        setArmed(true, { persist: false, clearSearch: false });
                    }, 80);
                },
                true
            );
        }

        cap.addEventListener('keydown', function (ev) {
            if (!armed) return;
            if (ev.key === 'Enter') {
                ev.preventDefault();
                resolve(cap.value);
            }
        });

        cap.addEventListener('blur', function () {
            if (!armed) return;
            setTimeout(function () {
                if (!armed) return;
                if (modalBlocksRefocus(cap)) return;
                if (document.activeElement === btn) return;
                cap.focus();
            }, 60);
        });

        if (readLeitorPersisted(empresaPk)) {
            // Inicial: já persistido. Não regravar.
            setArmed(true, { persist: false, clearSearch: true });
        }
    }

    function initAll() {
        document.querySelectorAll('.js-estoque-leitor-wrap').forEach(bindWrap);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }

    document.body.addEventListener('htmx:afterSwap', function () {
        initAll();
    });
})();
