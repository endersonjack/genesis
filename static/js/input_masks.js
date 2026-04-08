/**
 * Máscaras leves em inputs (sem dependências).
 * Campos: data-mask="cpf" → 000.000.000-00
 *         data-mask="br-moeda" → digitação em centavos + formatação ao vivo (1.234,56) — envio 1234.56
 *         data-mask="br-hours" → ponto decimal, filtro ao vivo (12.50) — envio 12.50
 */
(function () {
    function formatCpfFromDigits(digits) {
        var d = (digits || '').replace(/\D/g, '').slice(0, 11);
        if (!d.length) return '';
        var out = d.slice(0, 3);
        if (d.length > 3) out += '.' + d.slice(3, 6);
        if (d.length > 6) out += '.' + d.slice(6, 9);
        if (d.length > 9) out += '-' + d.slice(9, 11);
        return out;
    }

    function bindCpf(el) {
        if (!el || el.getAttribute('data-mask') !== 'cpf' || el.dataset.cpfMaskBound) {
            return;
        }
        el.dataset.cpfMaskBound = '1';
        el.setAttribute('inputmode', 'numeric');
        el.setAttribute('autocomplete', 'off');
        el.setAttribute('maxlength', '14');

        function applyFromValue() {
            el.value = formatCpfFromDigits(el.value);
        }

        el.addEventListener('input', applyFromValue);
        el.addEventListener('blur', applyFromValue);
        if (el.value) {
            applyFromValue();
        }
    }

    /* —— BR moeda / horas —— */

    function brMoedaToPython(s) {
        s = String(s || '')
            .trim()
            .replace(/\s/g, '');
        if (!s) {
            return '';
        }
        s = s.replace(/\./g, '').replace(',', '.');
        var n = parseFloat(s);
        if (isNaN(n) || n < 0) {
            return '';
        }
        return n.toFixed(2);
    }

    function pythonToBrMoeda(s) {
        if (s === '' || s == null) {
            return '';
        }
        var n = parseFloat(String(s).replace(',', '.'));
        if (isNaN(n) || n < 0) {
            return '';
        }
        var parts = n.toFixed(2).split('.');
        var intp = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return intp + ',' + parts[1];
    }

    function brHoursToPython(s) {
        s = String(s || '')
            .trim()
            .replace(/\s/g, '');
        if (!s) {
            return '';
        }
        s = s.replace(',', '.');
        var dot = s.indexOf('.');
        var intp;
        var frac;
        if (dot === -1) {
            intp = s.replace(/\D/g, '');
            frac = '';
        } else {
            intp = s.slice(0, dot).replace(/\D/g, '');
            frac = s.slice(dot + 1).replace(/\D/g, '').slice(0, 2);
        }
        if (!intp && !frac) {
            return '';
        }
        var num = parseFloat(intp + (frac !== '' ? '.' + frac : ''));
        if (isNaN(num) || num < 0) {
            return '';
        }
        return num.toFixed(2);
    }

    function pythonToBrHours(s) {
        if (s === '' || s == null) {
            return '';
        }
        var n = parseFloat(String(s).replace(',', '.'));
        if (isNaN(n) || n < 0) {
            return '';
        }
        return n.toFixed(2);
    }

    /**
     * Moeda ao digitar: só dígitos, interpretados como centavos (como máscara de cartão/CPF).
     * Ex.: digitar 1 2 3 4 5 6 → 1.234,56
     */
    function formatBrMoedaInputLive(raw) {
        var d = String(raw || '').replace(/\D/g, '');
        if (!d.length) {
            return '';
        }
        if (d.length > 15) {
            d = d.slice(0, 15);
        }
        var n = parseInt(d, 10) / 100;
        if (!isFinite(n) || n < 0) {
            return '';
        }
        if (n === 0) {
            return '';
        }
        return pythonToBrMoeda(n.toFixed(2));
    }

    /**
     * Horas ao digitar: só dígitos e um ponto; até 2 casas decimais.
     */
    function formatBrHoursInputLive(raw) {
        var s = String(raw || '')
            .replace(/,/g, '.')
            .replace(/[^\d.]/g, '');
        var dot = s.indexOf('.');
        if (dot === -1) {
            return s.slice(0, 12);
        }
        var intp = s.slice(0, dot).replace(/\./g, '');
        var frac = s
            .slice(dot + 1)
            .replace(/\./g, '')
            .slice(0, 2);
        return intp + '.' + frac;
    }

    function bindBrMoeda(el) {
        if (!el || el.getAttribute('data-mask') !== 'br-moeda' || el.dataset.brMoedaBound) {
            return;
        }
        el.dataset.brMoedaBound = '1';

        function refreshFromServer() {
            var raw = String(el.value || '').trim();
            if (!raw) {
                el.value = '';
                return;
            }
            var py = brMoedaToPython(pythonToBrMoeda(raw));
            if (!py || parseFloat(py) === 0) {
                el.value = '';
                return;
            }
            el.value = pythonToBrMoeda(raw);
        }

        function onInput() {
            el.value = formatBrMoedaInputLive(el.value);
        }

        function onBlur() {
            var py = brMoedaToPython(el.value);
            if (py === '' || parseFloat(py) === 0) {
                el.value = '';
                return;
            }
            el.value = pythonToBrMoeda(py);
        }

        refreshFromServer();
        el.addEventListener('input', onInput);
        el.addEventListener('blur', onBlur);
    }

    function bindBrHours(el) {
        if (!el || el.getAttribute('data-mask') !== 'br-hours' || el.dataset.brHoursBound) {
            return;
        }
        el.dataset.brHoursBound = '1';

        function refreshFromServer() {
            var raw = String(el.value || '').trim();
            if (!raw) {
                el.value = '';
                return;
            }
            var n = parseFloat(raw.replace(',', '.'));
            if (isNaN(n) || n === 0) {
                el.value = '';
                return;
            }
            el.value = pythonToBrHours(raw);
        }

        function onInput() {
            el.value = formatBrHoursInputLive(el.value);
        }

        function onBlur() {
            var py = brHoursToPython(el.value);
            if (py === '' || parseFloat(py) === 0) {
                el.value = '';
                return;
            }
            el.value = pythonToBrHours(py);
        }

        refreshFromServer();
        el.addEventListener('input', onInput);
        el.addEventListener('blur', onBlur);
    }

    function normalizeBrMasksForSubmit(form) {
        if (!form || !form.querySelectorAll) {
            return;
        }
        form.querySelectorAll('[data-mask="br-moeda"]').forEach(function (inp) {
            var py = brMoedaToPython(inp.value);
            inp.value = py === '' ? '0.00' : py;
        });
        form.querySelectorAll('[data-mask="br-hours"]').forEach(function (inp) {
            var py = brHoursToPython(inp.value);
            inp.value = py === '' ? '0.00' : py;
        });
    }

    document.body.addEventListener('htmx:beforeRequest', function (evt) {
        var elt = evt.detail && evt.detail.elt;
        if (!elt) {
            return;
        }
        /* Com submit por botão, o elt costuma ser o <button>, não o <form>. */
        var form = elt.tagName === 'FORM' ? elt : elt.closest ? elt.closest('form') : null;
        if (!form || !form.querySelector('[data-mask="br-moeda"], [data-mask="br-hours"]')) {
            return;
        }
        normalizeBrMasksForSubmit(form);
    });

    function scan(root) {
        var scope = root && root.querySelectorAll ? root : document;
        scope.querySelectorAll('[data-mask="cpf"]').forEach(bindCpf);
        scope.querySelectorAll('[data-mask="br-moeda"]').forEach(bindBrMoeda);
        scope.querySelectorAll('[data-mask="br-hours"]').forEach(bindBrHours);
    }

    document.addEventListener('DOMContentLoaded', function () {
        scan(document);
    });

    document.body.addEventListener('htmx:afterSettle', function () {
        /* evt.detail.target costuma ser o elemento que *disparou* o hx (ex.: a linha da
           tabela), não o destino do swap (#modalAfLinhaContent). Só varrer o documento
           para aplicar máscaras em fragmentos HTMX recém-inseridos (binds são idempotentes). */
        scan(document);
    });
})();
