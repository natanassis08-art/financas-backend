from rest_framework import serializers
from .models import Categoria, Transacao, MetaFinanceira # <<< Importar MetaFinanceira

# Serializer para o modelo Categoria
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__' # Inclui todos os campos do modelo Categoria

# Serializer para o modelo Transacao
class TransacaoSerializer(serializers.ModelSerializer):
    # O campo 'categoria' agora exibirá o nome da categoria, não apenas o ID
    # Isso é útil para visualização no frontend
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True)

    class Meta:
        model = Transacao
        fields = '__all__' # Inclui todos os campos do modelo Transacao
        # Se quiser incluir o nome da categoria na resposta da API,
        # adicione 'categoria_nome' aqui junto com os outros campos.
        # Ex: fields = ['id', 'descricao', 'valor', 'data_transacao', 'tipo', 'status', 'categoria', 'categoria_nome', 'data_criacao', 'data_atualizacao']
        # Por enquanto, '__all__' já incluirá 'categoria_nome' se ele for um campo declarado acima.
        
        # NOVO SERIALIZER PARA METAS FINANCEIRAS
class MetaFinanceiraSerializer(serializers.ModelSerializer):
    # Campos @property do modelo não são incluídos automaticamente.
    # Adicionamos eles manualmente como read-only.
    progresso_porcentagem = serializers.ReadOnlyField()
    valor_restante = serializers.ReadOnlyField()

    class Meta:
        model = MetaFinanceira
        fields = '__all__' # Inclui todos os campos do modelo, incluindo os @property acima