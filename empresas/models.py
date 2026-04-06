from django.db import models


class Empresa(models.Model):
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255, blank=True)
    cnpj = models.CharField(max_length=18, unique=True)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    cor_tema = models.CharField(max_length=7, default='#0d6efd', help_text='Cor em hexadecimal. Ex: #0d6efd')
    endereco = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Endereço',
        help_text='Exibido nos cabeçalhos de PDF (junto com CNPJ e telefone).',
    )
    local_padrao_recibo = models.CharField(
        max_length=120,
        blank=True,
        verbose_name='Local padrão nos recibos',
        help_text='Cidade/UF no rodapé quando a lista não define outro local.',
    )
    texto_declaracao_cesta_padrao = models.TextField(
        blank=True,
        verbose_name='Texto da declaração (cesta básica)',
        help_text='Usado quando a lista deixa o texto da declaração em branco.',
    )
    rodape_extra_recibo = models.TextField(
        blank=True,
        verbose_name='Observação no rodapé do recibo',
        help_text='Texto opcional abaixo da data e local (ex.: nota legal ou contato).',
    )
    logo = models.ImageField(
        upload_to='empresas/logos/',
        blank=True,
        null=True,
        verbose_name='Logo da empresa',
        help_text='PNG, JPG ou WebP. Usado no cabeçalho de recibos e exportações.',
    )
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['razao_social']

    def __str__(self):
        return self.nome_fantasia or self.razao_social