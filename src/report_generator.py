import pandas as pd
from datetime import datetime
import os
import re
import matplotlib.pyplot as plt
import io
import base64

class ReportGenerator:
    def __init__(self):
        pass

    def generate_markdown_report(self, portfolio_df, total_value, suggestions_df, contribution_df, indicators, ai_analysis=None):
        today = datetime.now().strftime("%d/%m/%Y")
        
        # Resumo Executivo
        report = f"# 📊 Relatório Financeiro Diário - {today}\n\n"
        
        if ai_analysis:
            report += "## 🧠 Análise de IA\n"
            report += f"{ai_analysis}\n\n"
        else:
            report += "## 📝 Resumo Executivo\n"
            report += f"- **Valor Total da Carteira**: R$ {total_value:,.2f}\n"
            selic = indicators.get('selic_meta', 0)
            cdi = indicators.get('cdi', 0)
            ptax = indicators.get('ptax_venda', 0)
            report += f"- **Indicadores**: Selic {selic}% | CDI {cdi:.2f}% | PTAX R$ {ptax:.4f}\n\n"
        
        # Alocação Atual vs Ideal
        report += "## ⚖️ Alocação de Ativos\n"
        report += "| Categoria | Atual % | Ideal % | Status |\n"
        report += "|---|---|---|---|\n"
        
        for _, row in suggestions_df.iterrows():
            report += f"| {row['category']} | {row['current_pct']:.1f}% | {row['target_pct']:.1f}% | {row['status']} |\n"
            
        report += "\n"
        
        # Detalhe por Ativo
        report += "## 📈 Detalhe da Carteira\n"
        cats = portfolio_df['category'].unique()
        for cat in cats:
            cat_df = portfolio_df[portfolio_df['category'] == cat]
            report += f"### {cat}\n"
            report += "| Ativo | Qtd | Preço | Valor Total | Var. 1D | Var. 12M |\n"
            report += "|---|---|---|---|---|---|\n"
            for _, row in cat_df.iterrows():
                report += f"| {row['name']} ({row['ticker']}) | {row['qty']} | R$ {row['price']:,.2f} | R$ {row['value_brl']:,.2f} | {row['change_1d']:.2f}% | {row['change_12m']:.2f}% |\n"
            report += "\n"
            
        # Sugestão de Aporte
        report += "## 💰 Sugestão de Aporte Mensal (R$ 250,00)\n"
        if isinstance(contribution_df, str):
             report += f"{contribution_df}\n"
        else:
            report += "| Categoria | Valor Sugerido |\n"
            report += "|---|---|\n"
            for _, row in contribution_df.iterrows():
                report += f"| {row['category']} | R$ {row['contribution']:,.2f} |\n"
                
        return report

    def generate_allocation_chart(self, portfolio_df):
        # Agrupa por categoria
        data = portfolio_df.groupby('category')['value_brl'].sum()
        
        # Configurações visuais modernas
        colors_list = ['#ff9999','#66b3ff','#99ff99','#ffcc99', '#c2c2f0', '#ffb3e6', '#c4e17f']
        plt.figure(figsize=(6, 6))
        
        # Gráfico de Rosca (Donut)
        plt.pie(data, labels=data.index, colors=colors_list[:len(data)], autopct='%1.1f%%', startangle=90, pctdistance=0.85)
        
        # Círculo branco no meio
        centre_circle = plt.Circle((0,0),0.70,fc='white')
        fig = plt.gcf()
        fig.gca().add_artist(centre_circle)
        
        plt.title('Alocação Atual da Carteira')
        plt.tight_layout()
        
        # Save to BytesIO buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        # Encode to Base64
        chart_b64 = base64.b64encode(buf.read()).decode('utf-8')
        return chart_b64
