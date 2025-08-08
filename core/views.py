# financas_pessoais/core/views.py

from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, F, Q, Avg, StdDev
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

import django_filters.rest_framework

from .models import Categoria, Transacao, MetaFinanceira
from .serializers import CategoriaSerializer, TransacaoSerializer, MetaFinanceiraSerializer
from .filters import TransacaoFilter

# Definir monthNamesFull aqui para uso no backend
monthNamesFull = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
]


# ViewSet para o modelo Categoria
class CategoriaViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite que categorias sejam visualizadas ou editadas.
    """
    queryset = Categoria.objects.all().order_by('nome')
    serializer_class = CategoriaSerializer

# ViewSet para o modelo Transacao (AGORA CONSOLIDADO COM FILTROS)
class TransacaoViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite que transações sejam visualizadas ou editadas.
    Agora com suporte a filtros por data, valor, categoria, tipo e status.
    """
    queryset = Transacao.objects.all().order_by('-data_transacao', '-data_criacao')
    serializer_class = TransacaoSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = TransacaoFilter


class AnaliseFinanceiraView(APIView):
    """
    API endpoint para análises financeiras (gastos por categoria por mês e saldo mensal).
    Agora com filtros por mês e categoria.
    """
    def get(self, request, format=None):
        month_param = request.query_params.get('month', None)
        category_param = request.query_params.get('categoria', None)

        filters = Q()
        if month_param:
            filters &= Q(data_transacao__month=month_param)
        if category_param:
            filters &= Q(categoria__id=category_param)

        gastos_por_categoria_mes = (
            Transacao.objects.filter(tipo='despesa')
            .filter(filters)
            .annotate(
                mes=ExtractMonth('data_transacao'),
                ano=ExtractYear('data_transacao'),
                categoria_nome=F('categoria__nome')
            )
            .values('ano', 'mes', 'categoria_nome')
            .annotate(total=Sum('valor'))
            .order_by('ano', 'mes', 'categoria_nome')
        )

        saldo_mensal_filters = Q()
        if month_param:
            saldo_mensal_filters &= Q(data_transacao__month=month_param)


        saldo_mensal = (
            Transacao.objects
            .filter(saldo_mensal_filters)
            .annotate(
                mes=ExtractMonth('data_transacao'),
                ano=ExtractYear('data_transacao')
            )
            .values('ano', 'mes')
            .annotate(
                receita_total=Sum('valor', filter=Q(tipo='receita')),
                despesa_total=Sum('valor', filter=Q(tipo='despesa'))
            )
            .order_by('ano', 'mes')
        )

        saldo_mensal_formatado = []
        for item in saldo_mensal:
            receita = item['receita_total'] if item['receita_total'] is not None else Decimal('0.00')
            despesa = item['despesa_total'] if item['despesa_total'] is not None else Decimal('0.00')
            saldo_mensal_formatado.append({
                'ano': item['ano'],
                'mes': item['mes'],
                'receita_total': receita,
                'despesa_total': despesa,
                'saldo_final': receita - despesa
            })

        data = {
            'gastos_por_categoria_mes': list(gastos_por_categoria_mes),
            'saldo_mensal': saldo_mensal_formatado,
        }
        return Response(data)

# ProjecaoFinanceiraView - COM NOVAS FUNCIONALIDADES E CORREÇÃO DA MÉDIA
class ProjecaoFinanceiraView(APIView):
    """
    API endpoint para projeções financeiras.
    Calcula média de gastos, sugere valor para guardar,
    e agora fornece alertas, sugestões, e diversas projeções e médias.
    """
    def get(self, request, format=None):
        # Parâmetro para o ano selecionado (novo filtro)
        selected_year = int(request.query_params.get('year', timezone.now().year))
        
        # Parâmetro para quantos meses usar na média (padrão 12 meses)
        meses_para_analise = int(request.query_params.get('meses', 12)) 
        
        # Tipo de cálculo da média (mantido para compatibilidade, mas a lógica será mais robusta)
        tipo_media_calculo = request.query_params.get('tipo_media_calculo', 'meses_com_transacao')

        # Definir o período de análise (últimos X meses do ano selecionado, até o mês atual se for o ano corrente)
        end_date_for_analysis = timezone.now().date() if selected_year == timezone.now().year else timezone.datetime(selected_year, 12, 31).date()
        start_date_for_analysis = end_date_for_analysis - timedelta(days=30 * meses_para_analise)
        
        # Garante que a data de início da análise não seja anterior ao início do ano selecionado
        if start_date_for_analysis.year < selected_year:
            start_date_for_analysis = timezone.datetime(selected_year, 1, 1).date()

        # Todas as transações DENTRO DO PERÍODO DE ANÁLISE definido
        all_transactions_in_analysis_period = Transacao.objects.filter(
            data_transacao__gte=start_date_for_analysis,
            data_transacao__lte=end_date_for_analysis,
            data_transacao__year=selected_year # Filtra estritamente pelo ano selecionado
        )
        
        despesas_in_analysis_period = all_transactions_in_analysis_period.filter(tipo='despesa')
        receitas_in_analysis_period = all_transactions_in_analysis_period.filter(tipo='receita')

        # --- CÁLCULO DA MÉDIA GERAL DE DESPESAS E RECEITAS ---
        # 1. Agrupar por mês e ano para obter totais mensais
        monthly_summary = (
            all_transactions_in_analysis_period
            .annotate(month=ExtractMonth('data_transacao'), year=ExtractYear('data_transacao'))
            .values('month', 'year')
            .annotate(
                total_receita_mes=Sum('valor', filter=Q(tipo='receita')),
                total_despesa_mes=Sum('valor', filter=Q(tipo='despesa'))
            )
            .order_by('year', 'month')
        )
        
        # Contar quantos meses *tiveram transações* no período de análise
        months_with_actual_transactions = monthly_summary.count()
        
        # Calcular totais para o período de análise
        total_despesas_analysis_period = despesas_in_analysis_period.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        total_receitas_analysis_period = receitas_in_analysis_period.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        # O divisor para a média mensal geral será o número de meses com transações
        divisor_general_avg = Decimal(months_with_actual_transactions) if months_with_actual_transactions > 0 else Decimal(1)

        media_mensal_despesas_geral = total_despesas_analysis_period / divisor_general_avg
        media_mensal_receitas_geral = total_receitas_analysis_period / divisor_general_avg


        # --- CÁLCULO DA MÉDIA MENSAL DE DESPESAS POR CATEGORIA (CORRIGIDO) ---
        # 1. Agrupar despesas por categoria E por mês/ano para obter o total gasto por categoria em cada mês
        monthly_category_expenses = (
            despesas_in_analysis_period
            .annotate(month=ExtractMonth('data_transacao'), year=ExtractYear('data_transacao'))
            .values('categoria__nome', 'month', 'year')
            .annotate(total_gasto_mes=Sum('valor'))
            .order_by('categoria__nome', 'year', 'month')
        )

        # Dicionário para armazenar as somas mensais por categoria: {categoria: [total_mes1, total_mes2, ...]}
        category_monthly_totals = {}
        for item in monthly_category_expenses:
            cat_name = item['categoria__nome'] or 'Sem Categoria'
            if cat_name not in category_monthly_totals:
                category_monthly_totals[cat_name] = []
            category_monthly_totals[cat_name].append(item['total_gasto_mes'])
        
        # Calcular a média dessas somas mensais para cada categoria
        projecao_despesa_media_mensal_por_categoria = []
        for cat_name, totals_list in category_monthly_totals.items():
            # A média é a soma total da categoria dividida pelo NÚMERO DE MESES EM QUE HOUVE GASTO para aquela categoria
            total_sum_for_category = sum(totals_list)
            num_months_with_expense_for_category = len(totals_list)
            
            avg_valor_for_category = total_sum_for_category / Decimal(num_months_with_expense_for_category)
            
            projecao_despesa_media_mensal_por_categoria.append({
                'categoria__nome': cat_name,
                'avg_valor': avg_valor_for_category,
                'total_gasto_no_ano': total_sum_for_category # Adicionado para debug/informação extra
            })
        
        # Ordenar por nome da categoria
        projecao_despesa_media_mensal_por_categoria.sort(key=lambda x: x['categoria__nome'] or '')

        # --- OUTROS CÁLCULOS (reutilizando médias gerais) ---
        media_diaria_despesas = media_mensal_despesas_geral / Decimal('30.44') # Média de dias no mês
        media_semanal_despesas = media_mensal_despesas_geral / Decimal('4.345') # Média de semanas no mês
        
        projecao_3_meses_despesa = media_mensal_despesas_geral * 3
        projecao_3_meses_receita = media_mensal_receitas_geral * 3
        projecao_3_meses_saldo = projecao_3_meses_receita - projecao_3_meses_despesa

        # --- Recomendação de Guardar (LÓGICA REFINADA) ---
        valor_recomendado_guardar = Decimal('0.00')
        
        # Pegar os saldos mensais do ano selecionado
        positive_monthly_saldos = []
        for item in monthly_summary:
            receita = item['total_receita_mes'] if item['total_receita_mes'] is not None else Decimal('0.00')
            despesa = item['total_despesa_mes'] if item['total_despesa_mes'] is not None else Decimal('0.00')
            saldo_final_mes = receita - despesa
            if saldo_final_mes > 0:
                positive_monthly_saldos.append(saldo_final_mes)
        
        if positive_monthly_saldos:
            # Sugestão 1: Média dos saldos positivos
            avg_positive_saldo = sum(positive_monthly_saldos) / Decimal(len(positive_monthly_saldos))
            valor_recomendado_guardar = avg_positive_saldo
            
            # Se a média dos saldos positivos for muito baixa (ex: menos de 5% da receita média),
            # talvez ainda sugira um mínimo percentual da receita, ou o maior dos dois.
            if media_mensal_receitas_geral > 0:
                min_percent_of_income = media_mensal_receitas_geral * Decimal('0.05') # Ex: 5% da receita
                if valor_recomendado_guardar < min_percent_of_income:
                    valor_recomendado_guardar = min_percent_of_income # Garante um mínimo
        else:
            # Se não houve saldos positivos, sugira um percentual da receita média (ex: 5%)
            if media_mensal_receitas_geral > 0:
                valor_recomendado_guardar = media_mensal_receitas_geral * Decimal('0.05')


        # --- LÓGICA DE ALERTAS E SUGESTÕES ---
        alerts = []
        suggestions = []
        financial_status = "EXCELLENT" # Padrão
        
        # 1. Alerta de Saldo Negativo no Ano Selecionado
        num_negative_months = 0
        total_months_in_summary = monthly_summary.count()
        for item in monthly_summary:
            receita = item['total_receita_mes'] if item['total_receita_mes'] is not None else Decimal('0.00')
            despesa = item['total_despesa_mes'] if item['total_despesa_mes'] is not None else Decimal('0.00')
            saldo_final = receita - despesa
            
            if saldo_final < 0:
                num_negative_months += 1
        
        if total_months_in_summary > 0:
            if num_negative_months > (total_months_in_summary / 2): # Mais da metade dos meses com dados
                alerts.append({
                    'type': 'warning',
                    'message': f"Atenção: Seu saldo foi negativo em {num_negative_months} de {total_months_in_summary} meses com transações no ano {selected_year}. É fundamental revisar suas finanças."
                })
                financial_status = "CRITICAL"
            elif num_negative_months > 0:
                alerts.append({
                    'type': 'info',
                    'message': f"Seu saldo foi negativo em {num_negative_months} meses com transações no ano {selected_year}. Fique de olho!"
                })
                if financial_status == "EXCELLENT": financial_status = "GOOD"
        else:
            alerts.append({'type': 'info', 'message': f"Nenhum dado financeiro para o ano {selected_year}. Adicione transações para ver as projeções!"})


        # 2. Alertas de Gastos em Categorias Excedem Padrões Históricos (em relação à média do ano anterior)
        previous_year = selected_year - 1
        despesas_previous_year_data = Transacao.objects.filter(
            tipo='despesa',
            data_transacao__year=previous_year
        )
        
        # Agrupar despesas do ano anterior por categoria E por mês/ano
        monthly_category_expenses_prev_year = (
            despesas_previous_year_data
            .annotate(month=ExtractMonth('data_transacao'), year=ExtractYear('data_transacao'))
            .values('categoria__nome', 'month', 'year')
            .annotate(total_gasto_mes=Sum('valor'))
            .order_by('categoria__nome', 'year', 'month')
        )
        
        # Calcular a média mensal de gastos por categoria para o ano anterior
        prev_year_category_monthly_totals = {}
        for item in monthly_category_expenses_prev_year:
            cat_name = item['categoria__nome'] or 'Sem Categoria'
            if cat_name not in prev_year_category_monthly_totals:
                prev_year_category_monthly_totals[cat_name] = []
            prev_year_category_monthly_totals[cat_name].append(item['total_gasto_mes'])

        previous_year_avg_map = {}
        for cat_name, totals_list in prev_year_category_monthly_totals.items():
            if totals_list:
                previous_year_avg_map[cat_name] = sum(totals_list) / Decimal(len(totals_list))
            else:
                previous_year_avg_map[cat_name] = Decimal('0.00')


        for item_categoria_atual in projecao_despesa_media_mensal_por_categoria:
            cat_nome = item_categoria_atual['categoria__nome']
            current_avg_valor = item_categoria_atual['avg_valor'] or Decimal('0.00')
            
            if cat_nome in previous_year_avg_map and previous_year_avg_map[cat_name] is not None:
                historic_avg = previous_year_avg_map[cat_name]
                if historic_avg > 0 and current_avg_valor > historic_avg * Decimal('1.25'): # Aumento de 25%
                    alerts.append({
                        'type': 'warning',
                        'message': f"Gasto alto em {cat_nome}: R$ {current_avg_valor:.2f}/mês é significativamente maior que sua média de R$ {historic_avg:.2f}/mês no ano anterior. Analise este aumento!"
                    })
                    if financial_status == "EXCELLENT": financial_status = "GOOD"
                elif historic_avg > 0 and current_avg_valor < historic_avg * Decimal('0.75'): # Redução de 25%
                    suggestions.append({
                        'type': 'success',
                        'message': f"Ótimo trabalho em {cat_nome}! Seus gastos de R$ {current_avg_valor:.2f}/mês estão bem abaixo da média de R$ {historic_avg:.2f}/mês do ano anterior. Continue assim!"
                    })
            elif current_avg_valor > 0 and media_mensal_despesas_geral > 0 and current_avg_valor > media_mensal_despesas_geral * Decimal('0.4'):
                # Se não há histórico na categoria, mas o gasto é grande parte do total
                 alerts.append({
                    'type': 'info',
                    'message': f"Atenção: Grande parte de suas despesas em {selected_year} vem de {cat_nome} (R$ {current_avg_valor:.2f}/mês). Monitore esta categoria de perto."
                })
                 if financial_status == "EXCELLENT": financial_status = "GOOD"
        
        # --- Tendência Geral de Despesas/Receitas (comparar os dois últimos meses com transações) ---
        # Encontrar os dois últimos meses com transações
        last_two_months = (
            Transacao.objects
            .filter(data_transacao__year=selected_year) # Ainda filtrando pelo ano selecionado para contextualizar
            .annotate(month=ExtractMonth('data_transacao'), year=ExtractYear('data_transacao'))
            .order_by('-year', '-month') # Ordenar do mais recente para o mais antigo
            .values('month', 'year')
            .distinct()[:2] # Pegar os dois primeiros (mais recentes)
        )
        
        period_one_data = {'month': None, 'year': None, 'total_despesas': Decimal('0.00'), 'total_receitas': Decimal('0.00')}
        period_two_data = {'month': None, 'year': None, 'total_despesas': Decimal('0.00'), 'total_receitas': Decimal('0.00')}

        if len(last_two_months) >= 1:
            month_one = last_two_months[0]
            period_one_transactions = Transacao.objects.filter(
                data_transacao__year=month_one['year'],
                data_transacao__month=month_one['month']
            )
            period_one_data['month'] = month_one['month']
            period_one_data['year'] = month_one['year']
            period_one_data['total_despesas'] = period_one_transactions.filter(tipo='despesa').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
            period_one_data['total_receitas'] = period_one_transactions.filter(tipo='receita').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        if len(last_two_months) == 2:
            month_two = last_two_months[1]
            period_two_transactions = Transacao.objects.filter(
                data_transacao__year=month_two['year'],
                data_transacao__month=month_two['month']
            )
            period_two_data['month'] = month_two['month']
            period_two_data['year'] = month_two['year']
            period_two_data['total_despesas'] = period_two_transactions.filter(tipo='despesa').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
            period_two_data['total_receitas'] = period_two_transactions.filter(tipo='receita').aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        # Tendência Despesas
        trend_despesas = 0.0
        if period_two_data['total_despesas'] > 0:
            trend_despesas = ((period_one_data['total_despesas'] - period_two_data['total_despesas']) / period_two_data['total_despesas']) * 100
        
        # Tendência Receitas
        trend_receitas = 0.0
        if period_two_data['total_receitas'] > 0:
            trend_receitas = ((period_one_data['total_receitas'] - period_two_data['total_receitas']) / period_two_data['total_receitas']) * 100
        
        # Mensagem para o frontend sobre os meses comparados
        comparison_period_display = "sem dados para comparação"
        if period_one_data['month'] and period_two_data['month']:
            comparison_period_display = f"entre {monthNamesFull[period_one_data['month'] - 1]}/{period_one_data['year']} e {monthNamesFull[period_two_data['month'] - 1]}/{period_two_data['year']}"
        elif period_one_data['month']:
            comparison_period_display = f"dados de {monthNamesFull[period_one_data['month'] - 1]}/{period_one_data['year']}"
        else:
            comparison_period_display = "nenhum mês com transações encontrado."


        # --- Progresso de Meta de Economia (mantido) ---
        meta_economia_ativa = MetaFinanceira.objects.filter(tipo='economizar', concluida=False).order_by('data_limite').first()
        meta_seguida_porcentagem = Decimal('0.00')
        progresso_meta_economia = {
            'nome': None,
            'valor_alvo': Decimal('0.00'),
            'valor_atingido': Decimal('0.00'),
            'progresso_porcentagem': Decimal('0.00'),
            'valor_restante': Decimal('0.00'),
        }

        if meta_economia_ativa:
            meta_seguida_porcentagem = meta_economia_ativa.progresso_porcentagem
            progresso_meta_economia = {
                'nome': meta_economia_ativa.nome,
                'valor_alvo': meta_economia_ativa.valor_alvo,
                'valor_atingido': meta_economia_ativa.valor_atingido,
                'progresso_porcentagem': meta_economia_ativa.progresso_porcentagem,
                'valor_restante': meta_economia_ativa.valor_restante,
            }
            dias_restantes = (meta_economia_ativa.data_limite - timezone.now().date()).days
            if dias_restantes > 0 and meta_economia_ativa.valor_restante > 0:
                if meta_economia_ativa.progresso_porcentagem < 50 and dias_restantes < 90:
                    alerts.append({
                        'type': 'warning',
                        'message': f"Atenção: Sua meta '{meta_economia_ativa.nome}' está com {meta_economia_ativa.progresso_porcentagem:.2f}% de progresso e faltam menos de {dias_restantes} dias para o prazo. Acelere suas economias!"
                    })
                elif meta_economia_ativa.progresso_porcentagem < 20 and dias_restantes < 180:
                     alerts.append({
                        'type': 'warning',
                        'message': f"Sua meta '{meta_economia_ativa.nome}' tem baixo progresso ({meta_economia_ativa.progresso_porcentagem:.2f}%) e o tempo está passando ({dias_restantes} dias restantes). Revise sua estratégia!"
                    })


        # Resumo Financeiro Mensal (Média para o ano selecionado)
        resumo_financeiro_mensal_calculado = {
            'receita_media': media_mensal_receitas_geral,
            'despesa_media': media_mensal_despesas_geral,
            'lucro_prejuizo_medio': media_mensal_receitas_geral - media_mensal_despesas_geral,
        }

        # Calcula a economia real do ano selecionado (saldo anual)
        receita_ano_selecionado_total = Transacao.objects.filter(
            tipo='receita',
            data_transacao__year=selected_year
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        despesa_ano_selecionado_total = Transacao.objects.filter(
            tipo='despesa',
            data_transacao__year=selected_year
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        economia_real_no_ano_selecionado = receita_ano_selecionado_total - despesa_ano_selecionado_total

        # Obter os anos com transações para o filtro no frontend
        years_with_data = Transacao.objects.annotate(year=ExtractYear('data_transacao')).values_list('year', flat=True).distinct().order_by('-year')
        
        # Obter os meses com transações para o ano selecionado
        months_with_data_in_selected_year_query = (
            Transacao.objects
            .filter(data_transacao__year=selected_year)
            .annotate(month=ExtractMonth('data_transacao'))
            .values('month')
            .distinct()
            .order_by('month')
        )
        
        available_months_data = []
        for month_num in months_with_data_in_selected_year_query:
            month_label = monthNamesFull[month_num['month'] - 1] # Usar monthNamesFull
            available_months_data.append({'value': month_num['month'], 'label': month_label})


        # --- Saída de Dados ---
        data = {
            'selected_year': selected_year,
            'available_years': list(years_with_data),
            'available_months_in_selected_year': available_months_data,
            'meses_analisados_para_media': months_with_actual_transactions, # Agora reflete os meses com dados
            'tipo_media_calculo_aplicado': 'meses_com_transacao', # Fixo, pois é o padrão agora
            'meses_com_transacao_no_periodo': months_with_actual_transactions, # Igual ao acima, para clareza
            
            'projecao_despesa_media_mensal_geral': media_mensal_despesas_geral,
            'projecao_despesa_media_mensal_por_categoria': list(projecao_despesa_media_mensal_por_categoria),
            'media_mensal_receitas_geral': media_mensal_receitas_geral,
            'valor_recomendado_guardar': valor_recomendado_guardar,
            
            'status_financeiro': financial_status,
            'economia_recomendada': valor_recomendado_guardar,
            'taxa_atual': (total_receitas_analysis_period - total_despesas_analysis_period) / (total_receitas_analysis_period or Decimal('1')) * 100,
            'meta_seguida_porcentagem': meta_seguida_porcentagem,
            'progresso_meta_economia': progresso_meta_economia,

            'resumo_financeiro_mensal': resumo_financeiro_mensal_calculado,

            'projecao_3_meses_despesa': projecao_3_meses_despesa,
            'projecao_3_meses_receita': projecao_3_meses_receita,
            'projecao_3_meses_saldo': projecao_3_meses_saldo,
            'media_diaria_despesas': media_diaria_despesas,
            'media_semanal_despesas': media_semanal_despesas,
            
            'trend_despesas': trend_despesas,
            'trend_receitas': trend_receitas,
            'comparison_period_display': comparison_period_display,
            
            'alerts': alerts,
            'suggestions': suggestions,
            'economia_real_no_ano_selecionado': economia_real_no_ano_selecionado,
        }
        return Response(data)

# DashboardView - SEM ALTERAÇÕES NESTA CORREÇÃO (mas deve ser definida antes de qualquer uso)
class DashboardView(APIView):
    """
    API endpoint para dados do Dashboard Financeiro.
    Inclui total gasto no mês, despesas pendentes, saldo projetado e gráficos.
    Suporta filtro por mês e ano via query parameters (?month=X&year=Y).
    Adiciona opção para ver dados agregados de todos os meses (?period=all).
    """
    def get(self, request, format=None):
        period = request.query_params.get('period', 'month').lower()

        if period == 'all':
            date_filter = {}
            mes_referencia_display = "Todos os Meses"
        else:
            current_month = int(request.query_params.get('month', timezone.now().month))
            current_year = int(request.query_params.get('year', timezone.now().year))
            date_filter = {
                'data_transacao__year': current_year,
                'data_transacao__month': current_month
            }
            mes_referencia_display = f"{current_month:02d}/{current_year}"

        total_gasto_periodo = Transacao.objects.filter(
            tipo='despesa',
            **date_filter
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        total_despesas_pendentes = Transacao.objects.filter(
            tipo='despesa',
            status='pendente',
            **date_filter
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        receitas_periodo = Transacao.objects.filter(
            tipo='receita',
            **date_filter
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        despesas_pagas_periodo = Transacao.objects.filter(
            tipo='despesa',
            status='pago',
            **date_filter
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')

        saldo_final_projetado = receitas_periodo - despesas_pagas_periodo - total_despesas_pendentes

        gastos_por_categoria_periodo = (
            Transacao.objects.filter(
                tipo='despesa',
                **date_filter
            )
            .values('categoria__nome')
            .annotate(total=Sum('valor'))
            .order_by('categoria__nome')
        )

        gastos_por_status_periodo = (
            Transacao.objects.filter(
                tipo='despesa',
                **date_filter
            )
            .values('status')
            .annotate(total=Sum('valor'))
            .order_by('status')
        )

        data = {
            'mes_referencia': mes_referencia_display,
            'total_gasto_mes': total_gasto_periodo,
            'total_despesas_pendentes': total_despesas_pendentes,
            'saldo_final_projetado': saldo_final_projetado,
            'receitas_mes_atual': receitas_periodo,
            'despesas_pagas_mes_atual': despesas_pagas_periodo,
            'gastos_por_categoria_mes_atual': list(gastos_por_categoria_periodo),
            'gastos_por_status_mes_atual': list(gastos_por_status_periodo),
        }
        return Response(data)

# ViewSet para Metas Financeiras
class MetaFinanceiraViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite que metas financeiras sejam visualizadas ou editadas.
    """
    queryset = MetaFinanceira.objects.all().order_by('data_limite', '-data_criacao')
    serializer_class = MetaFinanceiraSerializer