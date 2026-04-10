"""
Ficheiros de marca Genesis em static/img — favicon, PWA, login e sidebar (não usar logo da empresa).

Nomes suportados (o primeiro existente ganha prioridade):
- favicon: favicon.ico → favicon.svg → logo.png → pwa-icon.svg
- Apple Touch: apple-touch-icon.png → apple-touch-icon-180.png → pwa-192.png → pwa-512.png → logo.png → pwa-icon.svg
- Manifest: pwa-192.png, pwa-512.png, logo.png (fallback), pwa-icon.svg
"""

from __future__ import annotations

from typing import Any

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage


def static_exists(path: str) -> bool:
    """
    Ficheiros em STATICFILES_DIRS / apps: finders encontram mesmo sem collectstatic.
    Em produção, fallback para o storage (STATIC_ROOT + manifest).
    """
    if finders.find(path):
        return True
    try:
        return bool(staticfiles_storage.exists(path))
    except OSError:
        return False


def abs_static_url(request, path: str) -> str | None:
    if not static_exists(path):
        return None
    u = staticfiles_storage.url(path)
    if u.startswith("/"):
        return request.build_absolute_uri(u)
    return u


def favicon_info() -> dict[str, str] | None:
    if static_exists("img/favicon.ico"):
        return {"path": "img/favicon.ico", "type": ""}
    if static_exists("img/favicon.svg"):
        return {"path": "img/favicon.svg", "type": "image/svg+xml"}
    if static_exists("img/logo.png"):
        return {"path": "img/logo.png", "type": "image/png"}
    if static_exists("img/pwa-icon.svg"):
        return {"path": "img/pwa-icon.svg", "type": "image/svg+xml"}
    return None


def apple_touch_path() -> str | None:
    for p in (
        "img/apple-touch-icon.png",
        "img/apple-touch-icon-180.png",
        "img/pwa-192.png",
        "img/pwa-512.png",
        "img/logo.png",
        "img/pwa-icon.svg",
    ):
        if static_exists(p):
            return p
    return None


def manifest_icons(request) -> list[dict[str, Any]]:
    icons: list[dict[str, Any]] = []

    u192 = abs_static_url(request, "img/pwa-192.png")
    if u192:
        icons.append(
            {
                "src": u192,
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            }
        )

    u512 = abs_static_url(request, "img/pwa-512.png")
    if u512:
        icons.append(
            {
                "src": u512,
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            }
        )
        icons.append(
            {
                "src": u512,
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            }
        )

    if not u192 and not u512:
        ulogo = abs_static_url(request, "img/logo.png")
        if ulogo:
            icons.append(
                {
                    "src": ulogo,
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any",
                }
            )

    usvg = abs_static_url(request, "img/pwa-icon.svg")
    if usvg:
        icons.append(
            {
                "src": usvg,
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any",
            }
        )
        icons.append(
            {
                "src": usvg,
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "maskable",
            }
        )

    return icons
