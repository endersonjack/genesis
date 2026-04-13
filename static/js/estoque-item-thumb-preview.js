/**
 * Lista de itens (estoque): pré-visualização grande ao hover — position:fixed no body,
 * acima da tabela (evita recorte por overflow / stacking de <tr>).
 */
(function () {
    var floater = null;
    var hideTimer = null;

    function ensureFloater() {
        if (floater) return floater;
        floater = document.createElement('div');
        floater.className = 'estoque-item-thumb-preview-float';
        floater.setAttribute('aria-hidden', 'true');
        var img = document.createElement('img');
        img.alt = '';
        floater.appendChild(img);
        document.body.appendChild(floater);

        floater.addEventListener('mouseenter', function () {
            if (hideTimer) {
                clearTimeout(hideTimer);
                hideTimer = null;
            }
        });
        floater.addEventListener('mouseleave', function () {
            hideNow();
        });
        return floater;
    }

    function hideNow() {
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
        if (floater) {
            floater.style.display = 'none';
            floater.style.visibility = 'hidden';
        }
    }

    function scheduleHide() {
        if (hideTimer) clearTimeout(hideTimer);
        hideTimer = setTimeout(hideNow, 140);
    }

    function positionFloater(thumbRect) {
        var box = ensureFloater();
        var pad = 12;
        var vw = window.innerWidth;
        var vh = window.innerHeight;
        box.style.display = 'block';
        box.style.visibility = 'hidden';
        var bw = box.offsetWidth;
        var bh = box.offsetHeight;
        var left = thumbRect.right + pad;
        var top = thumbRect.top + thumbRect.height / 2 - bh / 2;
        if (left + bw > vw - pad) {
            left = thumbRect.left - bw - pad;
        }
        if (left < pad) left = pad;
        if (top + bh > vh - pad) top = vh - bh - pad;
        if (top < pad) top = pad;
        box.style.left = left + 'px';
        box.style.top = top + 'px';
        box.style.visibility = 'visible';
    }

    function showForWrap(wrap) {
        var thumb = wrap.querySelector('img.item-thumb');
        if (!thumb || !thumb.getAttribute('src')) return;
        if (hideTimer) {
            clearTimeout(hideTimer);
            hideTimer = null;
        }
        var box = ensureFloater();
        var fi = box.querySelector('img');
        var rect = wrap.getBoundingClientRect();

        function apply() {
            positionFloater(rect);
        }

        fi.onload = apply;
        fi.src = thumb.src;
        if (fi.complete && fi.naturalWidth) {
            apply();
        }
    }

    function bindWrap(wrap) {
        if (wrap.dataset.estoqueThumbPreviewBound) return;
        wrap.dataset.estoqueThumbPreviewBound = '1';
        wrap.addEventListener('mouseenter', function () {
            showForWrap(wrap);
        });
        wrap.addEventListener('mouseleave', function (e) {
            if (floater && (e.relatedTarget === floater || floater.contains(e.relatedTarget))) {
                return;
            }
            scheduleHide();
        });
    }

    function scan(root) {
        if (!root || !root.querySelectorAll) return;
        root.querySelectorAll('.estoque-item-thumb-wrap').forEach(bindWrap);
    }

    function init() {
        var inner = document.getElementById('estoque-list-inner');
        if (inner) scan(inner);
        var mov = document.getElementById('movimentar-list-inner');
        if (mov) scan(mov);
    }

    document.addEventListener('DOMContentLoaded', init);
    document.body.addEventListener('htmx:afterSwap', function (evt) {
        var t = evt.detail.target;
        if (!t) return;
        if (t.id === 'estoque-list-inner' || t.id === 'movimentar-list-inner') {
            scan(t);
        }
    });
    window.addEventListener(
        'scroll',
        function () {
            hideNow();
        },
        true
    );
})();
