# financas_pessoais/core/filters.py

import django_filters
from .models import Transacao # Importe o modelo Transacao

class TransacaoFilter(django_filters.FilterSet):
    # Filtro por descrição (contém)
    descricao = django_filters.CharFilter(field_name='descricao', lookup_expr='icontains')

    # Filtro por valor (maior ou igual, menor ou igual)
    valor_min = django_filters.NumberFilter(field_name='valor', lookup_expr='gte')
    valor_max = django_filters.NumberFilter(field_name='valor', lookup_expr='lte')

    # Filtro por data (maior ou igual, menor ou igual)
    data_inicio = django_filters.DateFilter(field_name='data_transacao', lookup_expr='gte')
    data_fim = django_filters.DateFilter(field_name='data_transacao', lookup_expr='lte')

    # Filtro por categoria (ID da categoria)
    categoria = django_filters.NumberFilter(field_name='categoria__id')

    # Filtro por tipo (receita/despesa)
    tipo = django_filters.CharFilter(field_name='tipo')

    # Filtro por status (pendente/paga)
    status = django_filters.CharFilter(field_name='status')

    class Meta:
        model = Transacao
        fields = ['descricao', 'valor', 'data_transacao', 'categoria', 'tipo', 'status']