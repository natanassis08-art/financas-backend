# financas_pessoais/core/models.py

from django.db import models
from django.utils import timezone

# Modelo para Categorias de Transações - CORRIGIDO
class Categoria(models.Model):
    TIPO_CHOICES = [ # Choices para o novo campo tipo_categoria
        ('receita', 'Receita'),
        ('despesa', 'Despesa'),
        ('ambos', 'Ambos'), # Para categorias que possam ser de receita ou despesa
    ]

    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    tipo_categoria = models.CharField( # <<< NOVO CAMPO AQUI
        max_length=10,
        choices=TIPO_CHOICES,
        default='despesa', # Padrão para despesa, pois a maioria das categorias é de despesa
        verbose_name="Tipo de Categoria"
    )

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_categoria_display()})" # Mostra o tipo também

# Modelo para Transações (Receitas e Despesas)
class Transacao(models.Model):
    TIPO_CHOICES = [
        ('receita', 'Receita'),
        ('despesa', 'Despesa'),
    ]

    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Paga'),
    ]

    descricao = models.CharField(max_length=255, verbose_name="Descrição")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor")
    data_transacao = models.DateField(default=timezone.now, verbose_name="Data da Transação")
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        default='despesa',
        verbose_name="Tipo"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name="Status"
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL, # Se a categoria for deletada, o campo fica NULL
        null=True,
        blank=True,
        related_name='transacoes',
        verbose_name="Categoria"
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")

    class Meta:
        verbose_name = "Transação"
        verbose_name_plural = "Transações"
        ordering = ['-data_transacao', '-data_criacao'] # Ordena pelas transações mais recentes

    def __str__(self):
        return f"{self.descricao} ({self.tipo.capitalize()}) - R$ {self.valor:.2f}"
    
    # NOVO MODELO PARA METAS FINANCEIRAS
class MetaFinanceira(models.Model):
    TIPOS_META_CHOICES = [
        ('economizar', 'Economizar'),
        ('investir', 'Investir'),
        ('abater_divida', 'Abater Dívida'),
        ('outros', 'Outros'),
    ]

    nome = models.CharField(max_length=255, verbose_name="Nome da Meta")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    tipo = models.CharField(
        max_length=20,
        choices=TIPOS_META_CHOICES,
        default='economizar',
        verbose_name="Tipo de Meta"
    )
    valor_alvo = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor Alvo")
    valor_atingido = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Valor Atingido")
    data_inicio = models.DateField(default=timezone.now, verbose_name="Data de Início")
    data_limite = models.DateField(verbose_name="Data Limite")
    concluida = models.BooleanField(default=False, verbose_name="Concluída")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")

    class Meta:
        verbose_name = "Meta Financeira"
        verbose_name_plural = "Metas Financeiras"
        ordering = ['data_limite', '-data_criacao'] # Ordena por data limite mais próxima

    def __str__(self):
        return f"{self.nome} - R$ {self.valor_atingido:.2f} de R$ {self.valor_alvo:.2f}"

    @property
    def progresso_porcentagem(self):
        if self.valor_alvo > 0:
            return (self.valor_atingido / self.valor_alvo) * 100
        return 0

    @property
    def valor_restante(self):
        return self.valor_alvo - self.valor_atingido