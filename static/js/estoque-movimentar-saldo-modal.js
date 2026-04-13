(function () {
    'use strict';

    function parseQty(raw) {
        if (raw == null || String(raw).trim() === '') return null;
        var s = String(raw).trim().replace(/\s/g, '').replace(',', '.');
        if (s === '' || s === '.') return null;
        var n = Number(s);
        return Number.isFinite(n) ? n : NaN;
    }

    function fmtQty(n) {
        if (n == null || !Number.isFinite(n)) return '—';
        return n.toLocaleString('pt-BR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 4,
        });
    }

    function syncMovimentarSaldoVisual(root, operacao) {
        var mc = document.getElementById('modal-content');
        if (mc) {
            mc.classList.remove('movimentar-saldo--add', 'movimentar-saldo--retirar');
            if (operacao === 'adicionar') {
                mc.classList.add('movimentar-saldo--add');
            } else {
                mc.classList.add('movimentar-saldo--retirar');
            }
        }
        var submit = root.querySelector('.js-movimentar-saldo-submit');
        if (submit) {
            submit.classList.remove('btn-primary', 'btn-danger');
            if (operacao === 'adicionar') {
                submit.classList.add('btn-primary');
            } else {
                submit.classList.add('btn-danger');
            }
        }
    }

    function updateLegend(root) {
        var saldo = parseFloat(root.getAttribute('data-saldo-atual'), 10);
        if (!Number.isFinite(saldo)) saldo = 0;
        var opEl = root.querySelector('[name="operacao"]');
        var qtyEl = root.querySelector('[name="quantidade"]');
        var leg = root.querySelector('.js-movimentar-saldo-legenda');
        if (!opEl || !qtyEl || !leg) return;
        var op = opEl.value;
        var q = parseQty(qtyEl.value);
        var und = root.getAttribute('data-unidade') || '';
        var undTxt = und ? ' ' + und : '';

        var depois;
        if (q == null || !Number.isFinite(q)) {
            depois = null;
        } else if (op === 'adicionar') {
            depois = saldo + q;
        } else {
            depois = saldo - q;
        }

        var atualStr = fmtQty(saldo) + undTxt;
        var depoisStr =
            depois == null || !Number.isFinite(depois)
                ? '—'
                : fmtQty(depois) + undTxt;

        leg.textContent =
            'Saldo atual: ' + atualStr + ' · Após o movimento: ' + depoisStr;

        syncMovimentarSaldoVisual(root, op);

        if (op === 'retirar' && Number.isFinite(saldo) && saldo >= 0) {
            qtyEl.setAttribute('max', String(saldo));
        } else {
            qtyEl.removeAttribute('max');
        }
    }

    function initMovimentarSaldoModal(root) {
        if (!root || root._movimentarSaldoInit) return;
        root._movimentarSaldoInit = true;

        var opEl = root.querySelector('[name="operacao"]');
        var qtyEl = root.querySelector('[name="quantidade"]');
        if (opEl) {
            opEl.addEventListener('change', function () {
                updateLegend(root);
            });
        }
        if (qtyEl) {
            qtyEl.addEventListener('input', function () {
                updateLegend(root);
            });
            qtyEl.addEventListener('change', function () {
                updateLegend(root);
            });
        }
        updateLegend(root);
    }

    document.body.addEventListener('htmx:afterSwap', function (e) {
        var t = e.detail && e.detail.target;
        if (!t || t.id !== 'modal-content') return;
        var root = t.querySelector('.js-movimentar-saldo-modal');
        if (root) {
            initMovimentarSaldoModal(root);
        } else {
            t.classList.remove('movimentar-saldo--add', 'movimentar-saldo--retirar');
        }
    });

    var modalPadrao = document.getElementById('modalPadrao');
    if (modalPadrao) {
        modalPadrao.addEventListener('hidden.bs.modal', function () {
            var mc = document.getElementById('modal-content');
            if (mc) {
                mc.classList.remove('movimentar-saldo--add', 'movimentar-saldo--retirar');
            }
        });
    }
})();
