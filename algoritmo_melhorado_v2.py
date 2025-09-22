#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Algoritmo Melhorado de Análise de Cavalos - Versão 2.0
Baseado nos aprendizados da corrida de Southwell

Melhorias implementadas:
1. Análise de todos os cavalos, não apenas favoritos
2. Maior peso para forma recente
3. Identificação de "dark horses"
4. Sistema de alertas para outsiders
5. Análise de value bets
"""

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class AnalisadorCavalosV2:
    def __init__(self):
        self.peso_forma_recente = 0.4  # Aumentado de 0.3
        self.peso_joquei = 0.25        # Aumentado de 0.2
        self.peso_historico = 0.2      # Diminuído de 0.3
        self.peso_condicoes = 0.15     # Novo fator
        
        # Novos parâmetros para identificar outsiders
        self.threshold_dark_horse = 7.0  # Score mínimo para dark horse
        self.odds_max_favorito = 4.0     # Odds máximas para ser considerado favorito
        self.odds_min_outsider = 6.0     # Odds mínimas para ser considerado outsider
    
    def calcular_score_melhorado(self, cavalo: Dict) -> Dict:
        """
        Calcula score melhorado baseado nos aprendizados
        """
        score_components = {
            'forma_recente': 0,
            'joquei': 0,
            'historico': 0,
            'condicoes': 0,
            'bonus_outsider': 0
        }
        
        # 1. FORMA RECENTE (peso aumentado)
        score_components['forma_recente'] = self._analisar_forma_recente(cavalo)
        
        # 2. ANÁLISE DE JÓQUEI (peso aumentado)
        score_components['joquei'] = self._analisar_joquei(cavalo)
        
        # 3. HISTÓRICO GERAL (peso diminuído)
        score_components['historico'] = self._analisar_historico(cavalo)
        
        # 4. CONDIÇÕES ESPECÍFICAS (novo)
        score_components['condicoes'] = self._analisar_condicoes(cavalo)
        
        # 5. BÔNUS PARA OUTSIDERS COM POTENCIAL (novo)
        score_components['bonus_outsider'] = self._calcular_bonus_outsider(cavalo)
        
        # Calcular score final
        score_final = (
            score_components['forma_recente'] * self.peso_forma_recente +
            score_components['joquei'] * self.peso_joquei +
            score_components['historico'] * self.peso_historico +
            score_components['condicoes'] * self.peso_condicoes +
            score_components['bonus_outsider']
        )
        
        return {
            'score_final': round(score_final, 2),
            'components': score_components,
            'categoria': self._classificar_cavalo(cavalo, score_final),
            'recomendacao': self._gerar_recomendacao_melhorada(cavalo, score_final)
        }
    
    def _analisar_forma_recente(self, cavalo: Dict) -> float:
        """
        Análise mais detalhada da forma recente (últimas 3-5 corridas)
        """
        score = 0
        
        # Simular análise de forma recente
        ultimas_posicoes = cavalo.get('ultimas_posicoes', [])
        if not ultimas_posicoes:
            return 5.0  # Score neutro se não há dados
        
        # Dar mais peso às corridas mais recentes
        pesos = [0.5, 0.3, 0.2]  # Última corrida tem peso 50%
        
        for i, posicao in enumerate(ultimas_posicoes[:3]):
            if i < len(pesos):
                # Converter posição em score (1º = 10, 2º = 8, etc.)
                score_corrida = max(0, 11 - posicao)
                score += score_corrida * pesos[i]
        
        # Bônus por consistência
        if len(ultimas_posicoes) >= 3:
            posicoes_top3 = sum(1 for p in ultimas_posicoes[:3] if p <= 3)
            if posicoes_top3 >= 2:
                score += 1.0  # Bônus por consistência
        
        return min(score, 10.0)
    
    def _analisar_joquei(self, cavalo: Dict) -> float:
        """
        Análise melhorada do jóquei
        """
        joquei = cavalo.get('joquei', '')
        
        # Simular dados de jóquei
        joqueis_top = {
            'ryan moore': 9.5,
            'frankie dettori': 9.3,
            'william buick': 9.0,
            'oisin murphy': 8.8,
            'tom marquand': 8.5
        }
        
        score_base = joqueis_top.get(joquei.lower(), 6.0)
        
        # Bônus por parceria cavalo-jóquei
        if cavalo.get('parceria_joquei_vitorias', 0) > 0:
            score_base += 0.5
        
        return score_base
    
    def _analisar_historico(self, cavalo: Dict) -> float:
        """
        Análise do histórico geral (peso reduzido)
        """
        vitorias = cavalo.get('vitorias', 0)
        corridas = cavalo.get('corridas_total', 1)
        
        taxa_vitoria = vitorias / corridas if corridas > 0 else 0
        
        # Score baseado na taxa de vitória
        score = taxa_vitoria * 10
        
        # Ajuste por experiência
        if corridas < 5:
            score *= 0.8  # Penalizar inexperiência
        elif corridas > 20:
            score *= 1.1  # Bônus por experiência
        
        return min(score, 10.0)
    
    def _analisar_condicoes(self, cavalo: Dict) -> float:
        """
        Novo: Análise de condições específicas
        """
        score = 5.0  # Score neutro
        
        # Tipo de pista
        tipo_pista = cavalo.get('tipo_pista_preferida', 'turf')
        tipo_corrida = cavalo.get('tipo_pista_corrida', 'turf')
        
        if tipo_pista == tipo_corrida:
            score += 1.5
        
        # Distância
        distancia_preferida = cavalo.get('distancia_preferida', 1600)
        distancia_corrida = cavalo.get('distancia_corrida', 1600)
        
        diferenca_distancia = abs(distancia_preferida - distancia_corrida)
        if diferenca_distancia <= 200:
            score += 1.0
        elif diferenca_distancia <= 400:
            score += 0.5
        
        # Condições climáticas
        if cavalo.get('performance_chuva', False) and cavalo.get('previsao_chuva', False):
            score += 0.5
        
        return min(score, 10.0)
    
    def _calcular_bonus_outsider(self, cavalo: Dict) -> float:
        """
        Novo: Bônus para identificar dark horses
        """
        odds = cavalo.get('odds', 5.0)
        
        # Só aplicar bônus para outsiders (odds > 6.0)
        if odds < self.odds_min_outsider:
            return 0
        
        # Fatores que podem indicar um dark horse
        bonus = 0
        
        # Jóquei experiente em cavalo com odds altas
        if cavalo.get('joquei_rating', 0) > 7.5:
            bonus += 0.5
        
        # Melhoria recente de forma
        ultimas_posicoes = cavalo.get('ultimas_posicoes', [])
        if len(ultimas_posicoes) >= 2:
            if ultimas_posicoes[0] < ultimas_posicoes[1]:  # Melhorou na última
                bonus += 0.3
        
        # Primeira vez com novo jóquei top
        if cavalo.get('novo_joquei_top', False):
            bonus += 0.4
        
        # Volta após descanso
        if cavalo.get('dias_descanso', 0) > 30:
            bonus += 0.2
        
        return bonus
    
    def _classificar_cavalo(self, cavalo: Dict, score: float) -> str:
        """
        Classificação melhorada dos cavalos
        """
        odds = cavalo.get('odds', 5.0)
        
        if score >= 8.5:
            if odds <= self.odds_max_favorito:
                return 'FAVORITO_FORTE'
            else:
                return 'DARK_HORSE'  # Alto score mas odds altas
        elif score >= 7.5:
            if odds <= self.odds_max_favorito:
                return 'FAVORITO'
            else:
                return 'VALUE_BET'  # Bom score com odds interessantes
        elif score >= 6.5:
            return 'COMPETITIVO'
        elif score >= 5.5:
            return 'OUTSIDER_POTENCIAL'
        else:
            return 'EVITAR'
    
    def _gerar_recomendacao_melhorada(self, cavalo: Dict, score: float) -> str:
        """
        Recomendações mais específicas
        """
        categoria = self._classificar_cavalo(cavalo, score)
        odds = cavalo.get('odds', 5.0)
        
        recomendacoes = {
            'FAVORITO_FORTE': f'🔥 APOSTA FORTE - Score {score} com odds {odds}',
            'DARK_HORSE': f'💎 DARK HORSE - Alto potencial com odds {odds}!',
            'FAVORITO': f'✅ APOSTA SEGURA - Score {score}',
            'VALUE_BET': f'💰 VALUE BET - Bom score {score} com odds {odds}',
            'COMPETITIVO': f'⚖️ COMPETITIVO - Pode surpreender',
            'OUTSIDER_POTENCIAL': f'🎯 OUTSIDER - Para apostas pequenas',
            'EVITAR': f'❌ EVITAR - Score baixo {score}'
        }
        
        return recomendacoes.get(categoria, 'Análise incompleta')
    
    def analisar_corrida_completa(self, cavalos: List[Dict]) -> Dict:
        """
        Análise completa de todos os cavalos da corrida
        """
        resultados = []
        
        for cavalo in cavalos:
            analise = self.calcular_score_melhorado(cavalo)
            cavalo_completo = {
                **cavalo,
                **analise
            }
            resultados.append(cavalo_completo)
        
        # Ordenar por score
        resultados.sort(key=lambda x: x['score_final'], reverse=True)
        
        # Identificar diferentes categorias
        favoritos = [c for c in resultados if c['categoria'] in ['FAVORITO_FORTE', 'FAVORITO']]
        dark_horses = [c for c in resultados if c['categoria'] == 'DARK_HORSE']
        value_bets = [c for c in resultados if c['categoria'] == 'VALUE_BET']
        
        return {
            'todos_cavalos': resultados,
            'top_3_score': resultados[:3],
            'favoritos': favoritos,
            'dark_horses': dark_horses,
            'value_bets': value_bets,
            'recomendacao_principal': self._gerar_estrategia_apostas(resultados),
            'timestamp': datetime.now().isoformat()
        }
    
    def _gerar_estrategia_apostas(self, cavalos: List[Dict]) -> str:
        """
        Gera estratégia de apostas baseada na análise
        """
        if not cavalos:
            return "Sem dados suficientes para estratégia"
        
        estrategia = []
        
        # Aposta principal
        melhor = cavalos[0]
        estrategia.append(f"🎯 APOSTA PRINCIPAL: {melhor['nome']} (Score: {melhor['score_final']})")
        
        # Dark horses
        dark_horses = [c for c in cavalos if c['categoria'] == 'DARK_HORSE']
        if dark_horses:
            estrategia.append(f"💎 DARK HORSE: {dark_horses[0]['nome']} - ATENÇÃO ESPECIAL!")
        
        # Value bets
        value_bets = [c for c in cavalos if c['categoria'] == 'VALUE_BET']
        if value_bets:
            estrategia.append(f"💰 VALUE BET: {value_bets[0]['nome']} - Odds interessantes")
        
        return " | ".join(estrategia)

# Exemplo de uso
if __name__ == "__main__":
    analisador = AnalisadorCavalosV2()
    
    # Dados de exemplo baseados na corrida de Southwell
    cavalos_exemplo = [
        {
            'nome': 'Bella Delizia',
            'odds': 3.5,
            'joquei': 'ryan moore',
            'ultimas_posicoes': [2, 1, 3],
            'vitorias': 5,
            'corridas_total': 12
        },
        {
            'nome': 'Hypnotysed',
            'odds': 8.0,  # Era outsider
            'joquei': 'tom marquand',
            'ultimas_posicoes': [3, 2, 1],  # Forma melhorando
            'vitorias': 3,
            'corridas_total': 8,
            'novo_joquei_top': True  # Fator que perdemos
        },
        {
            'nome': 'Yellow Diamonds',
            'odds': 12.0,  # Outsider maior
            'joquei': 'oisin murphy',
            'ultimas_posicoes': [4, 3, 2],  # Consistente melhoria
            'vitorias': 2,
            'corridas_total': 6,
            'dias_descanso': 45  # Volta após descanso
        }
    ]
    
    resultado = analisador.analisar_corrida_completa(cavalos_exemplo)
    
    print("🔍 ANÁLISE COM ALGORITMO MELHORADO:")
    print("=" * 50)
    
    for cavalo in resultado['todos_cavalos']:
        print(f"\n🐎 {cavalo['nome']}:")
        print(f"   Score: {cavalo['score_final']} | Categoria: {cavalo['categoria']}")
        print(f"   {cavalo['recomendacao']}")
    
    print(f"\n🎯 ESTRATÉGIA: {resultado['recomendacao_principal']}")
    
    if resultado['dark_horses']:
        print(f"\n💎 DARK HORSES IDENTIFICADOS: {len(resultado['dark_horses'])}")
        for dh in resultado['dark_horses']:
            print(f"   - {dh['nome']} (Score: {dh['score_final']}, Odds: {dh['odds']})")