#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

def analisar_corrida_southwell():
    """
    Analisa a corrida específica de Southwell para comparar com nossas análises
    """
    
    url = 'https://www.attheraces.com/racecard/Southwell/21-September-2025/1537'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        print("🔍 Analisando corrida de Southwell...")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Erro ao acessar a página: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cavalos que estávamos analisando
        cavalos_analise = {
            'bella delizia': {'posicao_prevista': 1, 'favorito': True},
            'capitalization': {'posicao_prevista': 2, 'favorito': True}, 
            'crimson rambler': {'posicao_prevista': 3, 'favorito': True},
            'hypnotysed': {'posicao_prevista': None, 'favorito': False, 'resultado': 1},
            'yellow diamonds': {'posicao_prevista': None, 'favorito': False, 'resultado': 2}
        }
        
        print("\n📊 ANÁLISE COMPARATIVA DA CORRIDA")
        print("=" * 50)
        
        # Buscar informações dos cavalos na página
        cavalos_encontrados = []
        
        # Procurar por diferentes seletores possíveis
        possible_selectors = [
            '.runner-name',
            '.horse-name', 
            '[data-horse-name]',
            '.racecard-runner',
            '.runner'
        ]
        
        for selector in possible_selectors:
            elementos = soup.select(selector)
            if elementos:
                print(f"✅ Encontrados {len(elementos)} elementos com seletor: {selector}")
                for elem in elementos[:10]:  # Limitar a 10 para não sobrecarregar
                    texto = elem.get_text(strip=True).lower()
                    if any(cavalo in texto for cavalo in cavalos_analise.keys()):
                        cavalos_encontrados.append({
                            'elemento': elem,
                            'texto': texto,
                            'seletor': selector
                        })
                break
        
        # Se não encontrou com seletores específicos, buscar no texto geral
        if not cavalos_encontrados:
            print("🔍 Buscando cavalos no texto geral da página...")
            texto_pagina = soup.get_text().lower()
            
            for nome_cavalo in cavalos_analise.keys():
                if nome_cavalo in texto_pagina:
                    print(f"✅ Encontrado: {nome_cavalo.title()}")
                    cavalos_encontrados.append({
                        'nome': nome_cavalo,
                        'encontrado': True
                    })
        
        # Análise dos resultados
        print("\n🏆 RESULTADOS DA CORRIDA:")
        print("-" * 30)
        print("1º Lugar: HYPNOTYSED (não estava entre nossos favoritos)")
        print("2º Lugar: YELLOW DIAMONDS (não estava entre nossos favoritos)")
        
        print("\n📈 NOSSOS FAVORITOS:")
        print("-" * 30)
        print("1º Favorito: Bella Delizia")
        print("2º Favorito: Capitalization")
        print("3º Favorito: Crimson Rambler")
        
        print("\n🤔 ANÁLISE DO RESULTADO:")
        print("-" * 30)
        print("• Os 3 favoritos da nossa análise NÃO ficaram no pódio")
        print("• O vencedor (Hypnotysed) não estava entre nossos favoritos")
        print("• O 2º colocado (Yellow Diamonds) também não estava previsto")
        print("• Isso indica que nossa análise pode ter alguns pontos de melhoria")
        
        # Buscar mais informações sobre os cavalos vencedores
        print("\n🔍 INFORMAÇÕES ADICIONAIS DOS VENCEDORES:")
        print("-" * 30)
        
        # Procurar por odds, jóqueis, etc.
        odds_elements = soup.find_all(text=re.compile(r'\d+/\d+|\d+\.\d+'))
        if odds_elements:
            print(f"📊 Encontradas {len(odds_elements)} referências a odds na página")
        
        # Salvar dados para análise posterior
        dados_analise = {
            'data_corrida': '21-September-2025',
            'horario': '15:37',
            'hipódromo': 'Southwell',
            'url': url,
            'nossos_favoritos': ['Bella Delizia', 'Capitalization', 'Crimson Rambler'],
            'resultado_real': ['Hypnotysed', 'Yellow Diamonds'],
            'acerto_previsao': False,
            'cavalos_encontrados': len(cavalos_encontrados),
            'timestamp_analise': datetime.now().isoformat()
        }
        
        # Salvar em arquivo JSON
        with open('analise_southwell_resultado.json', 'w', encoding='utf-8') as f:
            json.dump(dados_analise, f, indent=2, ensure_ascii=False)
        
        print("\n💾 Dados salvos em: analise_southwell_resultado.json")
        
        print("\n🎯 RECOMENDAÇÕES PARA MELHORIA:")
        print("-" * 30)
        print("1. Revisar critérios de análise de favoritos")
        print("2. Incluir análise de cavalos com odds mais altas")
        print("3. Considerar fatores como condições da pista")
        print("4. Analisar histórico recente dos jóqueis")
        print("5. Verificar forma atual vs. histórico geral")
        
        return dados_analise
        
    except requests.RequestException as e:
        print(f"❌ Erro na requisição: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return None

if __name__ == "__main__":
    resultado = analisar_corrida_southwell()
    if resultado:
        print("\n✅ Análise concluída com sucesso!")
    else:
        print("\n❌ Falha na análise.")