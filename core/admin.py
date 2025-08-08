# financas_pessoais/core/admin.py

from django.contrib import admin
from .models import Categoria, Transacao, MetaFinanceira # Importe seus modelos

# Registre seus modelos aqui.
admin.site.register(Categoria)
admin.site.register(Transacao)
admin.site.register(MetaFinanceira)