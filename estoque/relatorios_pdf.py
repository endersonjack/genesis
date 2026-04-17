"""PDF dos relatórios de estoque (mesmos filtros da página HTML)."""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape as xml_escape

from django.http import HttpResponse
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from controles_rh.views.cesta_export import _nome_empresa_pdf


def _clip(s, max_len: int = 140) -> str:
    if s is None:
        return '—'
    t = str(s).replace('\n', ' ').strip()
    if not t:
        return '—'
    if len(t) > max_len:
        return t[: max_len - 1] + '…'
    return t


def _p(html: str, style):
    return Paragraph(xml_escape(html) if '<' not in html else html, style)


def _story_table(
    story,
    styles,
    headers: list[str],
    rows: list[list[str]],
    col_widths=None,
):
    if not rows:
        story.append(_p('<i>Nenhum registro nos filtros.</i>', styles['Normal']))
        story.append(Spacer(1, 4 * mm))
        return
    data = [[_clip(h, 80) for h in headers]] + [[_clip(c) for c in r] for r in rows]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 5 * mm))


def build_http_response(request, empresa, ctx: dict) -> HttpResponse:
    sec = ctx.get('secao_relat') or 'funcionario'
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.fontSize = 14
    h2 = styles['Heading2']
    h2.fontSize = 11
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title='Relatórios de estoque',
    )
    story = []
    nome_emp = _nome_empresa_pdf(empresa) or 'Empresa'
    story.append(_p(f'<b>{xml_escape(nome_emp)}</b>', title_style))
    story.append(
        _p(
            f'Relatórios de estoque · {timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M")}',
            styles['Normal'],
        )
    )
    story.append(Spacer(1, 4 * mm))

    _SECAO_LABEL = {
        'funcionario': 'Funcionário (resumo)',
        'funcionario_requisicao': 'Funcionário × Requisição (detalhe)',
        'funcionario_ferramenta': 'Funcionário × Ferramenta (cautelas)',
        'ferramenta': 'Ferramenta',
        'item': 'Item (entradas / saídas)',
        'auditoria_movimentar': 'Auditoria — Movimentar',
        'auditoria_cautelas': 'Auditoria — Cautelas',
    }
    story.append(_p(f'<b>Seção:</b> {_SECAO_LABEL.get(sec, sec)}', h2))
    story.append(Spacer(1, 3 * mm))

    if sec == 'funcionario':
        func = ctx.get('funcionario')
        if not func:
            story.append(_p('<i>Selecione um funcionário na página de relatórios.</i>', styles['Normal']))
        else:
            story.append(_p(f'<b>Funcionário:</b> {xml_escape(str(func))}', styles['Normal']))
            story.append(Spacer(1, 2 * mm))
            story.append(_p('<b>Requisições</b>', h2))
            rpage = ctx.get('requisicoes_func_page')
            rqs = list(rpage) if rpage else []
            rows = []
            for req in rqs:
                rows.append(
                    [
                        req.criado_em.strftime('%d/%m/%Y %H:%M') if req.criado_em else '—',
                        str(getattr(req, 'n_itens', '') or ''),
                        str(req.get_status_display() if hasattr(req, 'get_status_display') else req.status),
                        f'#{req.pk}',
                    ]
                )
            _story_table(
                story,
                styles,
                ['Data', 'Itens', 'Situação', 'Nº'],
                rows,
                col_widths=[32 * mm, 18 * mm, 28 * mm, 16 * mm],
            )
            story.append(_p('<b>Cautelas</b>', h2))
            cpage = ctx.get('cautelas_func_page')
            cauts = list(cpage) if cpage else []
            rows2 = []
            for c in cauts:
                rows2.append(
                    [
                        c.data_inicio_cautela.strftime('%d/%m/%Y')
                        if c.data_inicio_cautela
                        else '—',
                        str(getattr(c, 'n_ferramentas', '') or ''),
                        f'{c.get_situacao_display()} · {c.get_entrega_display()}',
                        f'#{c.pk}',
                    ]
                )
            _story_table(
                story,
                styles,
                ['Início', 'Ferramentas', 'Situação / entrega', 'Nº'],
                rows2,
                col_widths=[24 * mm, 22 * mm, 70 * mm, 16 * mm],
            )

    elif sec == 'funcionario_requisicao':
        func = ctx.get('funcionario')
        if not func:
            story.append(_p('<i>Selecione um funcionário na página de relatórios.</i>', styles['Normal']))
        else:
            story.append(_p(f'<b>Funcionário:</b> {xml_escape(str(func))}', styles['Normal']))
            story.append(Spacer(1, 2 * mm))
            fpage = ctx.get('freq_det_page')
            for req in list(fpage) if fpage else []:
                head = (
                    f'Requisição #{req.pk} · '
                    f'{req.criado_em.strftime("%d/%m/%Y %H:%M") if req.criado_em else "—"} · '
                    f'{req.get_status_display() if hasattr(req, "get_status_display") else req.status}'
                )
                story.append(_p(f'<b>{xml_escape(head)}</b>', h2))
                lines = []
                for line in req.itens.all():
                    u = ''
                    try:
                        u = line.item.unidade_medida.abreviada or ''
                    except Exception:
                        pass
                    lines.append(
                        [
                            _clip(line.item.descricao, 60),
                            u,
                            str(line.quantidade),
                        ]
                    )
                _story_table(
                    story,
                    styles,
                    ['Item', 'Unid.', 'Qtd'],
                    lines,
                    col_widths=[100 * mm, 20 * mm, 24 * mm],
                )

    elif sec == 'funcionario_ferramenta':
        func = ctx.get('funcionario')
        if not func:
            story.append(_p('<i>Selecione um funcionário na página de relatórios.</i>', styles['Normal']))
        else:
            story.append(_p(f'<b>Funcionário:</b> {xml_escape(str(func))}', styles['Normal']))
            story.append(Spacer(1, 2 * mm))
            fpage = ctx.get('func_ff_page')
            rows = []
            for row in list(fpage) if fpage else []:
                c = row['cautela']
                ferrs = row.get('ferramentas') or []
                ferr_txt = '; '.join(_clip(f.descricao, 80) for f in ferrs[:12])
                if len(ferrs) > 12:
                    ferr_txt += '…'
                entregas = row.get('entregas') or []
                ent_txt = ' | '.join(
                    f'{e.data_entrega:%d/%m/%Y} — {e.get_tipo_display()}'
                    for e in entregas[:5]
                )
                rows.append(
                    [
                        f'#{c.pk}',
                        row['retirada'].strftime('%d/%m/%Y') if row.get('retirada') else '—',
                        c.get_situacao_display(),
                        c.get_entrega_display(),
                        ferr_txt,
                        ent_txt or '—',
                    ]
                )
            _story_table(
                story,
                styles,
                ['Cautela', 'Início', 'Situação', 'Entrega', 'Ferramentas', 'Devoluções'],
                rows,
                col_widths=[16 * mm, 22 * mm, 28 * mm, 28 * mm, 52 * mm, 52 * mm],
            )

    elif sec == 'ferramenta':
        ferr = ctx.get('ferramenta')
        if not ferr:
            story.append(_p('<i>Selecione uma ferramenta na página de relatórios.</i>', styles['Normal']))
        else:
            story.append(
                _p(
                    f'<b>{xml_escape(ferr.descricao)}</b> — '
                    f'{xml_escape(ferr.get_situacao_cautela_display())}',
                    styles['Normal'],
                )
            )
            story.append(Spacer(1, 2 * mm))
            lpage = ctx.get('ferramenta_linhas_page')
            rows = []
            for row in list(lpage) if lpage else []:
                tipo = 'Devolução' if row.get('tipo') == 'devolucao' else 'Em cautela'
                det = ''
                if row.get('tipo') == 'devolucao' and row.get('entrega_reg'):
                    er = row['entrega_reg']
                    det = er.get_tipo_display()
                    if getattr(er, 'situacao_ferramentas', None):
                        det += f' · {er.situacao_ferramentas}'
                else:
                    det = f"{row.get('situacao_cautela', '')} · {row.get('entrega', '')}"
                rows.append(
                    [
                        row['data'].strftime('%d/%m/%Y') if row.get('data') else '—',
                        tipo,
                        _clip(row.get('funcionario'), 40),
                        f"#{row['cautela'].pk}",
                        _clip(det, 100),
                    ]
                )
            _story_table(
                story,
                styles,
                ['Data', 'Tipo', 'Funcionário', 'Cautela', 'Detalhe'],
                rows,
                col_widths=[22 * mm, 22 * mm, 45 * mm, 18 * mm, 95 * mm],
            )

    elif sec == 'item':
        item = ctx.get('item_obj')
        if not item:
            story.append(_p('<i>Selecione um item na página de relatórios.</i>', styles['Normal']))
        else:
            story.append(_p(f'<b>Item:</b> {xml_escape(item.descricao)}', styles['Normal']))
            story.append(Spacer(1, 2 * mm))
            lpage = ctx.get('item_logs_page_obj')
            rows = []
            for r in list(lpage) if lpage else []:
                user = '—'
                if r.usuario:
                    user = r.usuario.nome_completo or r.usuario.username
                rows.append(
                    [
                        r.criado_em.strftime('%d/%m/%Y %H:%M') if r.criado_em else '—',
                        _clip(user, 36),
                        _clip(getattr(r, 'mov_acao_kind', '') or r.resumo, 40),
                        _clip(getattr(r, 'mov_qtd_label', ''), 16),
                        _clip(getattr(r, 'mov_saldo_label', ''), 16),
                    ]
                )
            _story_table(
                story,
                styles,
                ['Data / hora', 'Usuário', 'Ação', 'Qtd', 'Saldo'],
                rows,
                col_widths=[32 * mm, 45 * mm, 55 * mm, 22 * mm, 22 * mm],
            )

    elif sec == 'auditoria_movimentar':
        story.append(
            _p(
                f'<b>Busca:</b> {xml_escape(ctx.get("log_busca") or "(todas)")}',
                styles['Normal'],
            )
        )
        story.append(Spacer(1, 2 * mm))
        lpage = ctx.get('logs_page_obj')
        rows = []
        for r in list(lpage) if lpage else []:
            user = '—'
            if r.usuario:
                user = r.usuario.nome_completo or r.usuario.username
            rows.append(
                [
                    r.criado_em.strftime('%d/%m/%Y %H:%M') if r.criado_em else '—',
                    _clip(user, 28),
                    _clip(getattr(r, 'mov_item_label', '') or '', 44),
                    _clip(getattr(r, 'mov_acao_kind', '') or '', 28),
                    _clip(getattr(r, 'mov_qtd_label', ''), 14),
                    _clip(getattr(r, 'mov_saldo_label', ''), 14),
                ]
            )
        _story_table(
            story,
            styles,
            ['Data / hora', 'Usuário', 'Item', 'Ação', 'Qtd', 'Saldo'],
            rows,
            col_widths=[30 * mm, 36 * mm, 48 * mm, 32 * mm, 22 * mm, 22 * mm],
        )

    elif sec == 'auditoria_cautelas':
        story.append(
            _p(
                f'<b>Busca:</b> {xml_escape(ctx.get("clog_busca") or "(todas)")}',
                styles['Normal'],
            )
        )
        story.append(Spacer(1, 2 * mm))
        lpage = ctx.get('cautela_logs_page_obj')
        rows = []
        for r in list(lpage) if lpage else []:
            user = '—'
            if r.usuario:
                user = r.usuario.nome_completo or r.usuario.username
            rows.append(
                [
                    r.criado_em.strftime('%d/%m/%Y %H:%M') if r.criado_em else '—',
                    _clip(user, 28),
                    _clip(getattr(r, 'cautela_op_label', ''), 36),
                    f"#{r.cautela_pk}" if getattr(r, 'cautela_pk', None) else '—',
                    _clip(r.resumo, 120),
                ]
            )
        _story_table(
            story,
            styles,
            ['Data / hora', 'Usuário', 'Operação', 'Cautela', 'Resumo'],
            rows,
            col_widths=[30 * mm, 36 * mm, 40 * mm, 18 * mm, 68 * mm],
        )

    doc.build(story)
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorios-estoque.pdf"'
    return response
