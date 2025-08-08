# financas_pessoais/core/migrations/0003_initial_categories.py

from django.db import migrations

def create_initial_categories(apps, schema_editor):
    Categoria = apps.get_model('core', 'Categoria')
    
    initial_categories = [
        {'nome': 'Salário', 'descricao': 'Receita proveniente de salário ou remuneração.'},
        {'nome': 'Despesa', 'descricao': 'Despesas gerais e custos operacionais.'},
    ]

    for cat_data in initial_categories:
        # Crie a categoria apenas se ela não existir
        Categoria.objects.get_or_create(
            nome=cat_data['nome'],
            defaults={'descricao': cat_data['descricao']}
        )

def reverse_initial_categories(apps, schema_editor):
    Categoria = apps.get_model('core', 'Categoria')
    # Remova as categorias criadas por esta migração se a migração for revertida
    Categoria.objects.filter(nome__in=['Salário', 'Despesa']).delete()

class Migration(migrations.Migration):

    dependencies = [
        # <<< IMPORTANTE: SUBSTITUA '0002_your_previous_migration_name' pelo nome REAL da sua migração 0002
        ('core', '0002_metafinanceira'), 
    ]

    operations = [
        migrations.RunPython(create_initial_categories, reverse_initial_categories),
    ]