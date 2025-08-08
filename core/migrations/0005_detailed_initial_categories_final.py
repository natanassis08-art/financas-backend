# financas_pessoais/core/migrations/0005_detailed_initial_categories_final.py

from django.db import migrations

def create_and_update_detailed_categories(apps, schema_editor):
    Categoria = apps.get_model('core', 'Categoria')
    
    # Categorias de Receita
    receita_categories = [
        {'nome': 'Salário', 'descricao': 'Receita proveniente de salário ou remuneração.', 'tipo_categoria': 'receita'},
        {'nome': 'Rendimento de investimentos', 'descricao': 'Ganhos de aplicações financeiras.', 'tipo_categoria': 'receita'},
        {'nome': 'Freelance / Autônomo', 'descricao': 'Receita de trabalhos independentes.', 'tipo_categoria': 'receita'},
        {'nome': 'Outras Receitas', 'descricao': 'Receitas diversas não categorizadas.', 'tipo_categoria': 'receita'},
    ]

    # Categorias de Despesa
    despesa_categories = [
        {'nome': 'Alimentação', 'descricao': 'Gastos com comida e bebida.', 'tipo_categoria': 'despesa'},
        {'nome': 'Moradia', 'descricao': 'Aluguel, condomínio, IPTU, etc.', 'tipo_categoria': 'despesa'},
        {'nome': 'Transporte', 'descricao': 'Combustível, passagens, manutenção de veículo.', 'tipo_categoria': 'despesa'},
        {'nome': 'Saúde', 'descricao': 'Consultas, medicamentos, plano de saúde.', 'tipo_categoria': 'despesa'},
        {'nome': 'Educação', 'descricao': 'Mensalidades, cursos, materiais escolares.', 'tipo_categoria': 'despesa'},
        {'nome': 'Outras Despesas', 'descricao': 'Despesas diversas não categorizadas.', 'tipo_categoria': 'despesa'},
        {'nome': 'Lazer', 'descricao': 'Entretenimento, viagens, hobbies.', 'tipo_categoria': 'despesa'},
        {'nome': 'Cartão', 'descricao': 'Despesas pagas via cartão de crédito.', 'tipo_categoria': 'despesa'},
        {'nome': 'Assinaturas', 'descricao': 'Serviços de assinatura (streaming, software).', 'tipo_categoria': 'despesa'},
        {'nome': 'Contas Fixas', 'descricao': 'Água, luz, internet, telefone.', 'tipo_categoria': 'despesa'},
    ]

    all_categories_data = receita_categories + despesa_categories

    for cat_data in all_categories_data:
        categoria, created = Categoria.objects.get_or_create(
            nome=cat_data['nome'],
            defaults={'descricao': cat_data['descricao'], 'tipo_categoria': cat_data['tipo_categoria']}
        )
        if not created:
            if categoria.tipo_categoria != cat_data['tipo_categoria']:
                categoria.tipo_categoria = cat_data['tipo_categoria']
                categoria.save()


def reverse_detailed_initial_categories(apps, schema_editor):
    Categoria = apps.get_model('core', 'Categoria')
    categories_to_remove_names = [
        'Rendimento de investimentos', 'Freelance / Autônomo', 'Outras Receitas',
        'Alimentação', 'Moradia', 'Transporte', 'Saúde', 'Educação', 'Outras Despesas',
        'Lazer', 'Cartão', 'Assinaturas', 'Contas Fixas'
    ]
    # Certifique-se de que 'Salário' e 'Despesa' (a antiga) não sejam removidas por aqui
    # Isso pode ser complexo se você reverteu e aplicou várias vezes.
    # Para ser seguro, esta função pode ser deixada vazia se a reversão não for uma prioridade de dados exatos.
    # Ou filtrar apenas as categorias que você sabe que esta migração *adicionou*.
    Categoria.objects.filter(nome__in=categories_to_remove_names).delete()


class Migration(migrations.Migration):

    dependencies = [
        # ESTA É A DEPENDENCIA CORRETA AGORA!
        ('core', '0004_categoria_tipo_categoria'),
    ]

    operations = [
        migrations.RunPython(create_and_update_detailed_categories, reverse_detailed_initial_categories),
    ]