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

    /**
     * Evita roubar foco quando outro elemento dentro de um modal está ativo.
     * Se o campo de captura estiver dentro do .modal.show (ex.: leitor no «Buscar itens»),
     * não bloqueia — o refocus do cunha continua a funcionar.
     */
    function modalBlocksRefocus(captureEl) {
        var m = document.querySelector('.modal.show');
        if (!m) return false;
        if (captureEl && m.contains(captureEl)) return false;
        var a = document.activeElement;
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

        function setArmed(on) {
            armed = on;
            writeLeitorPersisted(empresaPk, on);
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
            btn.setAttribute(
                'aria-label',
                on ? 'Leitor QR ativo — desligar' : 'Leitor QR desligado — ativar'
            );
            btn.classList.toggle('estoque-leitor-btn--on', on);
            if (on) {
                cap.focus();
                setFeedback(fb, 'Leitor ativo. Aponte e leia o código.', false);
            } else {
                setFeedback(fb, '', false);
                if (document.activeElement === cap) {
                    cap.blur();
                }
            }
        }

        function resolve(code) {
            if (busy) return;
            var c = (code || '').trim();
            if (!c) return;
            busy = true;
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
                    busy = false;
                    if (!x.ok || !x.j || !x.j.ok) {
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
                    if (leitorMode === 'requisicao-buscar') {
                        var qEl = document.getElementById('req-itens-q');
                        var qhEl = document.getElementById('req-itens-q-hidden');
                        if (qEl) {
                            qEl.value = String(x.j.item_id);
                            if (qhEl) qhEl.value = qEl.value;
                            qEl.dispatchEvent(
                                new Event('input', { bubbles: true })
                            );
                            qEl.focus();
                            setFeedback(
                                fb,
                                'Item localizado na lista abaixo.',
                                false
                            );
                            return;
                        }
                    }
                    setFeedback(fb, '', false);
                    var loc = new URL(window.location.href);
                    loc.searchParams.set('edit_item', String(x.j.item_id));
                    window.location.href = loc.toString();
                })
                .catch(function () {
                    busy = false;
                    setFeedback(fb, 'Falha ao consultar. Tente de novo.', true);
                });
        }

        btn.addEventListener('click', function () {
            setArmed(!armed);
        });

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
            setArmed(true);
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
