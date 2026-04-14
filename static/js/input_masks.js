/**
 * Máscaras leves em inputs (sem dependências).
 * Campos: data-mask="cpf" → 000.000.000-00
 *         data-mask="cnpj" → 00.000.000/0000-00
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

    function formatCnpjFromDigits(digits) {
        var d = (digits || '').replace(/\D/g, '').slice(0, 14);
        if (!d.length) {
            return '';
        }
        var out = d.slice(0, 2);
        if (d.length > 2) {
            out += '.' + d.slice(2, 5);
        }
        if (d.length > 5) {
            out += '.' + d.slice(5, 8);
        }
        if (d.length > 8) {
            out += '/' + d.slice(8, 12);
        }
        if (d.length > 12) {
            out += '-' + d.slice(12, 14);
        }
        return out;
    }

    function bindCnpj(el) {
        if (!el || el.getAttribute('data-mask') !== 'cnpj' || el.dataset.cnpjMaskBound) {
            return;
        }
        el.dataset.cnpjMaskBound = '1';
        el.setAttribute('inputmode', 'numeric');
        el.setAttribute('autocomplete', 'off');
        el.setAttribute('maxlength', '18');

        function applyFromValue() {
            el.value = formatCnpjFromDigits(el.value);
        }

        el.addEventListener('input', applyFromValue);
        el.addEventListener('blur', applyFromValue);
        if (el.value) {
            applyFromValue();
        }
    }

    /* —— BR moeda / horas —— */

    function _toPythonMoneyString(raw) {
        var s = String(raw == null ? '' : raw).trim().replace(/\s/g, '');
        if (!s) return '';
        if (s.indexOf('-') !== -1) return '';

        // pt-BR: 1.234,56  | python: 1234.56
        if (s.indexOf(',') !== -1) {
            s = s.replace(/[^\d.,]/g, '');
            s = s.replace(/\./g, '').replace(',', '.');
        } else {
            s = s.replace(/[^\d.]/g, '');
            // múltiplos pontos = milhares -> remove todos
            if ((s.match(/\./g) || []).length > 1) {
                s = s.replace(/\./g, '');
            }
        }

        var parts = s.split('.');
        if (parts.length > 2) return '';
        var intp = (parts[0] || '').replace(/\D/g, '');
        var frac = (parts[1] || '').replace(/\D/g, '');
        if (!intp && !frac) return '';

        // normaliza inteiro (mantém "0" se vazio)
        intp = intp.replace(/^0+(?=\d)/, '');
        if (!intp) intp = '0';

        if (frac.length === 0) frac = '00';
        else if (frac.length === 1) frac = frac + '0';
        else if (frac.length > 2) frac = frac.slice(0, 2);

        // se for 0.00, tratamos como vazio (padrão do sistema)
        if (intp === '0' && frac === '00') return '';
        return intp + '.' + frac;
    }

    function brMoedaToPython(s) {
        return _toPythonMoneyString(s);
    }

    function pythonToBrMoeda(s) {
        var py = _toPythonMoneyString(s);
        if (!py) return '';
        var parts = py.split('.');
        var intp = parts[0];
        var frac = parts[1] || '00';
        intp = intp.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return intp + ',' + frac;
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
        // max_digits=16 (inclui centavos) no backend
        if (d.length > 16) {
            d = d.slice(0, 16);
        }
        if (!/^\d+$/.test(d)) {
            return '';
        }
        if (parseInt(d, 10) === 0) {
            return '';
        }
        // interpreta como centavos sem usar float
        if (d.length === 1) return '0,0' + d;
        if (d.length === 2) return '0,' + d;
        var intp = d.slice(0, -2).replace(/^0+(?=\d)/, '');
        var frac = d.slice(-2);
        intp = intp.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return intp + ',' + frac;
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
            /* raw pode vir já em pt-BR (1.234,56) via initial do Django.
               Normalizar primeiro para "python" (1234.56) e depois formatar para pt-BR. */
            var py = brMoedaToPython(raw);
            if (!py || parseFloat(py) === 0) {
                el.value = '';
                return;
            }
            el.value = pythonToBrMoeda(py);
        }

        function onInput() {
            el.value = formatBrMoedaInputLive(el.value);
        }

        function onBlur() {
            var py = brMoedaToPython(el.value);
            if (py === '') {
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
        scope.querySelectorAll('[data-mask="cnpj"]').forEach(bindCnpj);
        scope.querySelectorAll('[data-mask="br-moeda"]').forEach(bindBrMoeda);
        scope.querySelectorAll('[data-mask="br-hours"]').forEach(bindBrHours);
    }

    window.genesisInputMaskScan = scan;

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
