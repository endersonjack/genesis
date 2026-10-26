from datetime import timedelta
from django.db.models import Q
from decimal import Decimal
from django import forms
from django.utils import timezone
from .models import LembretePagamento
from fornecedores.models import Fornecedor


class LembretePagamentoForm(forms.ModelForm):
    valor = forms.DecimalField(label="Valor", max_digits=16, decimal_places=2, min_value=Decimal("0.01"), localize=True)
    class Meta:
        model = LembretePagamento
        fields = ["descricao", "fornecedor", "data_pagamento", "valor", "tipo", "avisar", "observacao"]
        widgets = {
            "data_pagamento": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "observacao": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, empresa, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.empresa = empresa
        self.fields["fornecedor"].queryset = Fornecedor.objects.filter(empresa=empresa).order_by("nome")
        self.fields["fornecedor"].empty_label = "Selecione um fornecedor"
        self.fields["data_pagamento"].initial = timezone.localdate()
        self.fields["valor"].widget.attrs.update({"placeholder": "0,00", "inputmode": "decimal"})
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-select" if isinstance(field.widget, forms.Select) else "form-control"

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.pk or "data_pagamento" in self.changed_data:
            instance.dia_recorrencia = instance.data_pagamento.day
        if commit:
            instance.save()
        return instance


def contexto_lembretes(empresa, form=None):
    hoje = timezone.localdate()
    lembretes = list(LembretePagamento.objects.filter(Q(ativo=True) | Q(ultima_conclusao__isnull=False), empresa=empresa, desativado=False).select_related("fornecedor"))
    avisos = 0
    visiveis = []
    for item in lembretes:
        inicio_aviso = item.data_pagamento - timedelta(days=item.avisar)
        aguardando_proximo_aviso = (
            item.tipo == "recorrente" and item.ultima_conclusao is not None
            and hoje < inicio_aviso
        )
        item.concluido = (not item.ativo and item.ultima_conclusao is not None) or aguardando_proximo_aviso
        if not item.concluido and hoje < inicio_aviso:
            continue
        item.data_exibicao = (
            item.ultima_data_concluida
            if aguardando_proximo_aviso and item.ultima_data_concluida
            else item.data_pagamento
        )
        item.em_aviso = not item.concluido and inicio_aviso <= hoje
        avisos += int(item.em_aviso)
        if item.concluido:
            item.status_texto, item.status_cor = "Concluído", "success"
        elif item.data_pagamento < hoje:
            item.status_texto, item.status_cor = "Atrasado", "danger"
        elif item.data_pagamento == hoje:
            item.status_texto, item.status_cor = "Hoje", "warning"
        else:
            item.status_texto, item.status_cor = "Programado", "secondary"
        item.inicio_aviso = item.data_exibicao - timedelta(days=item.avisar)
        visiveis.append(item)
    visiveis.sort(key=lambda item: (item.concluido, item.data_exibicao, item.pk))
    return {"lembretes": visiveis, "lembretes_avisos": avisos,
            "lembrete_form": form if form is not None else LembretePagamentoForm(empresa=empresa)}
