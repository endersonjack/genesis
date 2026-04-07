/**
 * Máscaras leves em inputs (sem dependências).
 * Campos: data-mask="cpf" → 000.000.000-00
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

    function scan(root) {
        var scope = root && root.querySelectorAll ? root : document;
        scope.querySelectorAll('[data-mask="cpf"]').forEach(bindCpf);
    }

    document.addEventListener('DOMContentLoaded', function () {
        scan(document);
    });

    document.body.addEventListener('htmx:afterSettle', function (evt) {
        var target = evt.detail && evt.detail.target;
        if (target && target.nodeType === 1) {
            scan(target);
        } else {
            scan(document);
        }
    });
})();
