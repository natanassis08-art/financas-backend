# financas_pessoais/core/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoriaViewSet, TransacaoViewSet, AnaliseFinanceiraView, ProjecaoFinanceiraView, DashboardView, MetaFinanceiraViewSet # <<< Importar MetaFinanceiraViewSet

# Cria um roteador para registrar os ViewSets (EXISTENTE, NÃO ALTERAR)
router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet)
router.register(r'transacoes', TransacaoViewSet)
router.register(r'metas', MetaFinanceiraViewSet) # <<< NOVA LINHA AQUI: Registrar MetaFinanceiraViewSet

# As URLs da API para a aplicação 'core'
urlpatterns = [
    path('', include(router.urls)),
    path('analises/', AnaliseFinanceiraView.as_view(), name='analises_financeiras'),
    path('projecoes/', ProjecaoFinanceiraView.as_view(), name='projecoes_financeiras'),
    path('dashboard/', DashboardView.as_view(), name='dashboard_financeiro'),
    # As URLs de metas serão geradas automaticamente pelo router
]