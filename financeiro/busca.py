"""Filtros compartilhados entre a tela de busca e suas exportações."""
import re
from decimal import Decimal
from django import forms
from django.utils import timezone
from .models import Caixa, ContaBancaria, CategoriaFinanceira

class BuscaPagamentosForm(forms.Form):
    busca = forms.CharField(label="Busca geral", required=False)
    q = forms.CharField(label="Documento / NF", required=False)
    fornecedor = forms.CharField(label="Pessoa / entidade", required=False)
    valor_contem = forms.RegexField(label="Valor (contém)", regex=r"^[0-9.,]+$", required=False,
        error_messages={"invalid": "Informe apenas números, ponto ou vírgula."})
    status_hoje = forms.BooleanField(label="Vence hoje", required=False)
    descricao = forms.CharField(label="Descrição / observações", required=False)
    tipo = forms.ChoiceField(label="Tipo de pagamento", required=False, choices=[
        ("", "Todos"), ("nf", "Nota fiscal"), ("pessoal", "Pessoal"),
        ("imposto", "Impostos"), ("bancario", "Bancário")])
    categoria = forms.ModelChoiceField(label="Categoria", required=False, queryset=CategoriaFinanceira.objects.none())
    tipo_data = forms.ChoiceField(label="Tipo de data", required=False, choices=[
        ("", "Qualquer data"), ("emissao", "Emissão"), ("vencimento", "Vencimento"), ("pagamento", "Pagamento")])
    data_inicio = forms.DateField(label="Data inicial", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    data_fim = forms.DateField(label="Data final", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    vencimento = forms.ChoiceField(label="Vencimento pendente", required=False, choices=[
        ("", "Todos"), ("vencido", "Vencido"), ("hoje", "Vence hoje"), ("futuro", "A vencer")])
    tipo_valor = forms.ChoiceField(label="Tipo de valor", required=False, choices=[
        ("", "Valor total"), ("valor_pago", "Valor pago"), ("valor_a_pagar", "Saldo pendente")])
    valor_min = forms.DecimalField(label="Valor mínimo", required=False, min_value=0, max_digits=16, decimal_places=2, localize=True)
    valor_max = forms.DecimalField(label="Valor máximo", required=False, min_value=0, max_digits=16, decimal_places=2, localize=True)
    valor = forms.DecimalField(label="Valor exato (documento ou boleto)", required=False, min_value=0, max_digits=16, decimal_places=2, localize=True)
    caixa = forms.ModelChoiceField(label="Caixa", required=False, queryset=Caixa.objects.none())
    conta = forms.ModelChoiceField(label="Conta bancária", required=False, queryset=ContaBancaria.objects.none())
    forma = forms.ChoiceField(label="Forma de pagamento", required=False, choices=[
        ("", "Todos"), ("avista", "À vista"), ("boletos", "Boletos"), ("credito", "Crédito")])
    status_vencido = forms.BooleanField(label="Vencidos", required=False)
    status_aberto = forms.BooleanField(label="Em aberto", required=False)
    status_pago = forms.BooleanField(label="Pagos", required=False)
    status_pago_parcial = forms.BooleanField(label="Pago parcial", required=False)
    status_sem_pagamento = forms.BooleanField(label="Sem pagamento registrado", required=False)

    def __init__(self, data=None, *, empresa, **kwargs):
        super().__init__(data, **kwargs)
        self.fields["categoria"].queryset = CategoriaFinanceira.objects.filter(empresa=empresa, tipo="saida").order_by("nome")
        self.fields["caixa"].queryset = Caixa.objects.filter(empresa=empresa).order_by("nome")
        self.fields["conta"].queryset = ContaBancaria.objects.filter(empresa=empresa).order_by("nome")
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-check-input" if isinstance(field, forms.BooleanField) else (
                "form-select" if isinstance(field.widget, forms.Select) else "form-control")
        self.fields["busca"].widget.attrs["placeholder"] = "Documento, NF, nome ou CPF/CNPJ"
        for key in ("valor_min", "valor_max", "valor"):
            self.fields[key].widget.attrs["placeholder"] = "0,00"

    def clean(self):
        data = super().clean()
        if data.get("data_inicio") and data.get("data_fim") and data["data_inicio"] > data["data_fim"]:
            self.add_error("data_fim", "A data final deve ser igual ou posterior à inicial.")
        if data.get("valor_min") is not None and data.get("valor_max") is not None and data["valor_min"] > data["valor_max"]:
            self.add_error("valor_max", "O valor máximo deve ser igual ou maior que o mínimo.")
        return data

    def grupos(self):
        return [
            ("Quem e o quê", [self[k] for k in ("busca", "tipo", "categoria", "descricao")]),
            ("Quando e quanto", [self[k] for k in ("tipo_data", "vencimento", "tipo_valor", "valor_min", "valor_max", "valor", "status_pago_parcial", "status_sem_pagamento")]),
            ("Origem do dinheiro", [self[k] for k in ("caixa", "conta")]),
        ]

    def filtros_ativos(self, params):
        chips = []
        advanced = 0
        for name, field in self.fields.items():
            raw = params.get(name, "")
            if not raw:
                continue
            value = self.cleaned_data.get(name)
            if isinstance(field, forms.BooleanField):
                if not value:
                    continue
                label = field.label
            else:
                display = str(value) if value is not None else raw
                if isinstance(field, forms.ChoiceField):
                    display = dict(field.choices).get(raw, raw)
                label = f"{field.label}: {display}"
            remaining = params.copy()
            remaining.pop(name, None)
            remaining.pop("origem", None)
            chips.append({"label": label, "url": "?" + remaining.urlencode()})
            if name not in ("q", "fornecedor", "valor_contem", "data_inicio", "data_fim", "forma", "status_hoje", "status_vencido", "status_aberto", "status_pago"):
                advanced += 1
        return chips, advanced

def corresponde_avancado(item, data):
    """As datas são eventos reais; a faixa de valores se refere ao documento."""
    if data.get("tipo") and item["kind"] != data["tipo"]:
        return False
    if data.get("caixa") and item.get("_caixa") != data["caixa"].pk:
        return False
    if data.get("conta") and data["conta"].pk not in item.get("_contas", []):
        return False
    if data.get("forma") and data["forma"] not in item.get("_formas", []):
        return False
    if data.get("descricao") and data["descricao"].casefold() not in item.get("_descricao", "").casefold():
        return False
    if data.get("status_hoje"):
        hoje = timezone.localdate()
        pendentes = item.get("_pendentes", [])
        if not (
            hoje in pendentes
            or (data.get("status_vencido") and any(d and d < hoje for d in pendentes))
            or (data.get("status_aberto") and item.get("valor_a_pagar", 0) > 0)
            or (data.get("status_pago") and item.get("valor_pago", 0) > 0)
            or (data.get("status_pago_parcial") and item.get("valor_pago", 0) > 0 and item.get("valor_a_pagar", 0) > 0)
            or (data.get("status_sem_pagamento") and not item.get("detalhes_avista") and not item.get("detalhes_boletos"))
        ):
            return False
    if data.get("valor_contem"):
        valores = [item.get("valor_total", Decimal("0"))]
        valores.extend(d.get("valor", Decimal("0")) for d in item.get("detalhes_boletos", []))
        if not any(valor_corresponde(data["valor_contem"], v) for v in valores):
            return False
    value = item.get(data.get("tipo_valor") or "valor_total") or Decimal("0")
    if data.get("valor_min") is not None and value < data["valor_min"]:
        return False
    if data.get("valor_max") is not None and value > data["valor_max"]:
        return False
    dates = item.get("_datas", {})
    selected = dates.get(data["tipo_data"], []) if data.get("tipo_data") else [
        day for group in dates.values() for day in group]
    if data.get("data_inicio") or data.get("data_fim"):
        if not any(day and (not data.get("data_inicio") or day >= data["data_inicio"])
                   and (not data.get("data_fim") or day <= data["data_fim"]) for day in selected):
            return False
    if data.get("vencimento"):
        today = timezone.localdate()
        mode = data["vencimento"]
        if not any(day and ((mode == "vencido" and day < today) or (mode == "hoje" and day == today)
                            or (mode == "futuro" and day > today)) for day in item.get("_pendentes", [])):
            return False
    return True

def termo_corresponde(term, *values):
    text = " ".join(str(v or "") for v in values)
    digits = re.sub(r"\D", "", term)
    numeric = bool(re.fullmatch(r"[\d. /()-]+", term))
    return term.casefold() in text.casefold() or bool(numeric and digits and digits in re.sub(r"\D", "", text))


def resultados_bancarios(request, empresa, data):
    from core.urlutils import reverse_empresa
    from .models import PagamentoBancarioParcela, PagamentoBancarioAvulso
    today = timezone.localdate()
    rows = []
    parcelas = PagamentoBancarioParcela.objects.filter(recorrencia__empresa=empresa).exclude(
        status="cancelado").select_related("recorrencia__conta_bancaria", "recorrencia__categoria", "conta_bancaria")
    avulsos = PagamentoBancarioAvulso.objects.filter(empresa=empresa).select_related("conta_bancaria", "categoria")
    for obj in [*parcelas, *avulsos]:
        parcela = isinstance(obj, PagamentoBancarioParcela)
        origem = obj.recorrencia if parcela else obj
        pago = obj.status == "pago" if parcela else True
        vencimento = obj.data_vencimento if parcela else None
        conta = (obj.conta_bancaria or origem.conta_bancaria) if pago else origem.conta_bancaria
        descricao = origem.descricao or ""
        doc = f"Parcela {obj.numero_parcela}" if parcela else f"Avulso {obj.pk}"
        if data.get("q") and not termo_corresponde(data["q"], doc, descricao):
            continue
        if data.get("fornecedor") and not termo_corresponde(data["fornecedor"], conta.nome, conta.banco):
            continue
        if data.get("categoria") and origem.categoria_id != data["categoria"].pk:
            continue
        if data.get("valor") is not None and obj.valor != data["valor"]:
            continue
        flags = [data.get(k) for k in ("status_pago", "status_aberto", "status_vencido", "status_pago_parcial", "status_sem_pagamento")]
        if not data.get("status_hoje") and any(flags) and not (
            (data.get("status_pago") and pago)
            or (data.get("status_aberto") and not pago)
            or (data.get("status_sem_pagamento") and not pago)
            or (data.get("status_vencido") and not pago and vencimento and vencimento < today)):
            continue
        status = "Pago Completo" if pago else ("Vencido" if vencimento < today else "Em Aberto")
        rows.append({
            "kind": "bancario", "tipo_registro": "Bancário",
            "export_id": f"bancario_parcela:{obj.pk}" if parcela else f"bancario_avulso:{obj.pk}",
            "entidade": conta.nome, "entidade_doc": "", "documento": doc,
            "numero_doc": doc, "categoria_label": origem.categoria.nome,
            "data": None,
            "vencimento": vencimento, "vencimento_status": vencimento,
            "data_pagamento": obj.data_pagamento, "valor_total": obj.valor,
            "valor_pago": obj.valor if pago else Decimal("0"),
            "valor_a_pagar": Decimal("0") if pago else obj.valor,
            "forma_pagamento": "À vista" if pago else "Sem pagamento",
            "forma_total_key": "avista" if pago else "",
            "status_label": status,
            "status_badge_class": "text-bg-success" if pago else ("text-bg-danger" if status == "Vencido" else "text-bg-secondary"),
            "url": reverse_empresa(request, "financeiro:pagamento_bancario_detalhe", kwargs={"pk": origem.pk}) if parcela else reverse_empresa(request, "financeiro:pagamento_bancario_lista"),
            "detalhes_avista": [{"situacao": "Pago", "data": obj.data_pagamento,
                "valor": obj.valor, "acrescimos": Decimal("0"), "descontos": Decimal("0"),
                "pagamento_realizado_em": conta.nome, "observacao": obj.observacao or descricao}] if pago else [],
            "detalhes_boletos": [],
            "_caixa": origem.caixa_id, "_contas": [conta.pk] if pago else [],
            "_formas": ["avista"] if pago else [],
            "_descricao": descricao + " " + (obj.observacao or ""),
            "_busca": descricao + " " + doc + " " + conta.nome + " " + conta.banco,
            "_datas": {"emissao": [], "vencimento": [vencimento], "pagamento": [obj.data_pagamento]},
            "_pendentes": [vencimento] if not pago else [],
        })
    return rows


def preparar_resultados(resultados, filtros):
    """Prioriza datas e valores sem alterar a composição ou os totais da consulta."""
    pendentes = any(filtros.get(k) for k in ("vencimento", "status_vencido", "status_aberto", "status_pago_parcial", "status_hoje"))
    tipo_data = filtros.get("tipo_data") or ("vencimento" if pendentes else "pagamento" if filtros.get("status_pago") else "")
    filtra_valor = bool(filtros.get("valor_contem")) or any(filtros.get(k) is not None for k in ("valor_min", "valor_max", "valor"))
    valor_key = filtros.get("tipo_valor") or (
        "valor_total" if filtra_valor else "valor_a_pagar" if pendentes else
        "valor_pago" if filtros.get("status_pago") else "valor_total")
    valor_label = {"valor_total": "Valor total", "valor_pago": "Valor pago", "valor_a_pagar": "Saldo pendente"}[valor_key]
    labels = {"emissao": "Emissão", "vencimento": "Vencimento", "pagamento": "Pagamento"}

    def no_periodo(day):
        return bool(day and (not filtros.get("data_inicio") or day >= filtros["data_inicio"])
                    and (not filtros.get("data_fim") or day <= filtros["data_fim"]))

    for item in resultados:
        formas = set(item.get("_formas", []))
        item["forma_pagamento"] = ("Misto" if len(formas) > 1 else
            {"avista": "À vista", "boletos": "Boletos", "credito": "Crédito"}.get(next(iter(formas), ""), "Sem pagamento"))
        vencimentos = [day for day in item.get("_pendentes", []) if day]
        item["vencimento_status"] = min(vencimentos) if vencimentos else None
        dates = item.get("_datas", {})
        pagamentos = ([d.get("data_pagamento") for d in item.get("detalhes_boletos", [])]
                      if formas == {"boletos"} else dates.get("pagamento", []))
        item["data_pagamento"] = max((day for day in pagamentos if day), default=None)
        item["valor_vencido"] = item.get("_valor_vencido", (
            item.get("valor_a_pagar") or Decimal("0")
        ) if any(d < timezone.localdate() for d in vencimentos) else Decimal("0"))
        for key in ("valor_total", "valor_vencido", "valor_pago", "valor_a_pagar"):
            item[key + "_sort"] = str(item.get(key) or Decimal("0"))

        mode = tipo_data
        has_period = bool(filtros.get("data_inicio") or filtros.get("data_fim"))
        if not mode:
            priorities = ("vencimento", "pagamento", "emissao")
            mode = next((key for key in priorities if any(no_periodo(d) for d in dates.get(key, []))), "emissao")
        candidates = [d for d in dates.get(mode, []) if d and (not has_period or no_periodo(d))]
        if mode == "vencimento" and pendentes:
            candidates = [d for d in candidates if d in item.get("_pendentes", [])]
            today = timezone.localdate()
            due = filtros.get("vencimento") or ("hoje" if filtros.get("status_hoje") and not any(filtros.get(k) for k in ("status_vencido", "status_aberto", "status_pago", "status_pago_parcial", "status_sem_pagamento")) else "vencido" if filtros.get("status_vencido") and not filtros.get("status_hoje") else "")
            if due:
                candidates = [d for d in candidates if (due == "hoje" and d == today)
                              or (due == "vencido" and d < today) or (due == "futuro" and d > today)]
        selected = (min(candidates) if mode == "vencimento" else max(candidates)) if candidates else None
        item["data_destaque"] = selected
        item["data_destaque_label"] = labels[mode]
        item["datas_adicionais"] = max(0, len(set(candidates)) - 1)
        item["valor_destaque"] = item.get(valor_key) or Decimal("0")
        item["valor_destaque_label"] = valor_label
        item["valor_destaque_sort"] = str(item["valor_destaque"])
        item["descricao_resumo"] = item.get("_descricao", "").strip()
        term = filtros.get("busca") or filtros.get("q") or ""
        item["destaque_documento"] = bool(term and termo_corresponde(term, item.get("numero_doc"), item.get("doc_match_label")))
        person = filtros.get("busca") or filtros.get("fornecedor") or ""
        item["destaque_entidade"] = bool(person and termo_corresponde(person, item.get("entidade"), item.get("entidade_doc")))
        reasons = []
        if filtros.get("descricao"):
            text = item["descricao_resumo"]
            index = text.casefold().find(filtros["descricao"].casefold())
            if index >= 0:
                item["descricao_trecho"] = ("…" if index > 45 else "") + text[max(0, index-45):index+125]
                reasons.append("Descrição correspondente")
        if item["destaque_documento"]:
            reasons.append("Documento correspondente")
        if item["destaque_entidade"]:
            reasons.append("Pessoa / entidade correspondente")
        if has_period:
            reasons.append("Data no período consultado")
        item["correspondencias"] = reasons
        for detail in item.get("detalhes_boletos", []):
            detail["destaque_contexto"] = bool(
                (term and termo_corresponde(term, detail.get("doc")))
                or (selected and detail.get("vencimento" if mode == "vencimento" else "data_pagamento") == selected)
                or (filtros.get("valor") is not None and detail.get("valor") == filtros["valor"])
                or (filtros.get("valor_contem") and valor_corresponde(filtros["valor_contem"], detail.get("valor", Decimal("0")))))
        for detail in item.get("detalhes_avista", []):
            detail["destaque_contexto"] = bool(mode == "pagamento" and selected and detail.get("data") == selected)
    # Vencimentos próximos/antigos primeiro; pagamentos e emissões mais recentes primeiro.
    reverse_date = tipo_data != "vencimento" and not pendentes
    resultados.sort(key=lambda item: (
        item["data_destaque"] is None,
        -(item["data_destaque"].toordinal()) if reverse_date and item["data_destaque"] else
        item["data_destaque"].toordinal() if item["data_destaque"] else 0,
        str(item.get("entidade", "")).casefold(),
    ))
    return {
        "valor_label": valor_label,
        "data_label": labels.get(tipo_data, "Data relevante"),
        "ordem_label": "Datas mais recentes primeiro" if reverse_date else "Vencimentos mais antigos primeiro",
    }


def valor_corresponde(termo, valor):
    # Ignore thousand separators, retain decimals: 250 matches 1.250,00.
    needle = termo.replace(".", "")
    if not any(c.isdigit() for c in needle):
        return False
    return needle in format(valor or Decimal("0"), ".2f").replace(".", ",")
