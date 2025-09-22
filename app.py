from flask import Flask, jsonify, send_file, request, render_template
import pandas as pd
import io
import csv
import re
import subprocess
import sys
from datetime import datetime
import logging
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urlparse, urljoin
import time
import random

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class ExtractorCavalos:
    """
    Classe para extrair dados de corrida de cavalos
    """
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Carregar nomes reais de cavalos do arquivo JSON
        self.nomes_cavalos, self.joqueis_famosos = self._carregar_nomes_reais()
    
    def _carregar_nomes_reais(self):
        """
        Carrega nomes reais de cavalos e jóqueis do arquivo JSON
        """
        try:
            with open('cavalos_reais.json', 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            # Combinar diferentes tipos de nomes de cavalos
            nomes_cavalos = []
            nomes_cavalos.extend(dados.get('cavalos_famosos', [])[:15])
            nomes_cavalos.extend(dados.get('cavalos_britanicos', [])[:15])
            nomes_cavalos.extend(dados.get('nomes_tipicos', [])[:15])
            
            # Jóqueis reais da corrida atual e outros famosos
            joqueis_famosos = [
                'Billy Loughnane', 'Hollie Doyle', 'W Buick', 'Rossa Ryan',
                'Frankie Dettori', 'Ryan Moore', 'William Buick', 'Oisin Murphy',
                'Tom Marquand', 'James Doyle', 'Andrea Atzeni', 'Jim Crowley',
                'Hayley Turner', 'Silvestre de Sousa', 'Daniel Tudhope',
                'Paul Hanagan', 'Jason Watson', 'Kieran Shoemark'
            ]
            
            return nomes_cavalos, joqueis_famosos
            
        except Exception as e:
            logger.warning(f"Erro ao carregar nomes reais: {str(e)}. Usando nomes padrão.")
            # Fallback para nomes genéricos
            return (['Thunder Strike', 'Golden Arrow', 'Midnight Express', 'Silver Bullet', 
                    'Royal Champion', 'Lightning Bolt', 'Fire Storm', 'Wind Runner'], 
                   ['Billy Loughnane', 'Hollie Doyle', 'W Buick', 'Rossa Ryan'])
    
    def extrair_dados_url(self, url):
        """
        Extrai dados de corrida de cavalos de uma URL
        """
        try:
            logger.info(f"Iniciando extração da URL: {url}")
            
            # Fazer requisição para a URL
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Detectar tipo de site e extrair dados
            dados_reais = None
            if 'attheraces.com' in url.lower():
                dados_reais = self._extrair_at_the_races(soup, url)
            elif 'racingpost.com' in url.lower():
                dados_reais = self._extrair_racing_post(soup, url)
            elif 'timeform.com' in url.lower():
                dados_reais = self._extrair_timeform(soup, url)
            elif 'sportinglife.com' in url.lower():
                dados_reais = self._extrair_sporting_life(soup, url)
            elif 'oddschecker.com' in url.lower():
                dados_reais = self._extrair_oddschecker(soup, url)
            elif 'betfair.com' in url.lower():
                dados_reais = self._extrair_betfair(soup, url)
            else:
                # Extração genérica
                dados_reais = self._extrair_generico(soup, url)
            
            # NOVA LÓGICA: Só retornar dados reais, nunca fictícios
            if not dados_reais:
                logger.warning("Extração retornou None. Nenhum cavalo confirmado encontrado.")
                return {'erro': 'Nenhum cavalo confirmado encontrado na URL fornecida. Verifique se a URL contém uma corrida ativa com cavalos inscritos.'}
            elif 'erro' in dados_reais:
                logger.warning(f"Erro na extração: {dados_reais.get('erro')}. Nenhum cavalo confirmado.")
                return {'erro': f"Erro na extração: {dados_reais.get('erro')}. Verifique se a URL é válida e contém cavalos confirmados."}
            elif len(dados_reais.get('cavalos', [])) < 1:
                logger.warning("Nenhum cavalo encontrado. Não gerando dados fictícios.")
                return {'erro': 'Nenhum cavalo confirmado encontrado nesta corrida. Verifique se a URL contém uma corrida ativa com participantes inscritos.'}
            
            # Verificar se temos nomes de cavalos válidos
            cavalos_validos = [c for c in dados_reais.get('cavalos', []) if c.get('nome', '').strip()]
            if len(cavalos_validos) < 1:
                logger.warning("Nenhum cavalo válido extraído. Não gerando dados fictícios.")
                return {'erro': 'Nenhum cavalo com nome válido encontrado. Verifique se a corrida tem participantes confirmados.'}
            
            # Usar dados reais mesmo se alguns campos estiverem vazios
            dados_reais['cavalos'] = cavalos_validos
            
            logger.info(f"Extração bem-sucedida: {len(dados_reais.get('cavalos', []))} cavalos extraídos da URL real.")
            
            return dados_reais
                
        except Exception as e:
            logger.error(f"Erro na extração: {str(e)}")
            # Em caso de erro, retornar erro em vez de dados fictícios
            return {'erro': f'Erro ao acessar a URL: {str(e)}. Verifique se a URL é válida e acessível.'}
    

    def extrair_oddschecker(self, soup, url):
        """
        Extrai dados específicos do Oddschecker
        """
        try:
            dados = {
                'cavalos': [],
                'titulo_corrida': 'Corrida Oddschecker',
                'condicoes_pista': 'N/A',
                'clima': 'N/A'
            }
            
            # Buscar título da corrida
            titulo_elem = soup.find('h1') or soup.find('title')
            if titulo_elem:
                dados['titulo_corrida'] = titulo_elem.get_text(strip=True)
            
            # Buscar cavalos e odds - Oddschecker com seletores melhorados
            cavalos_elem = []
            
            # Seletores específicos do Oddschecker para cavalos confirmados
            seletores_oc = [
                'tr.runner',              # Linhas de corredores
                'tr.horse-row',           # Linhas de cavalos
                'tr.selection-row',       # Linhas de seleções
                'tr[data-horse-name]',    # Linhas com atributo de nome do cavalo
                '.runner-row',            # Linhas de corredores
                '.horse-selection',       # Seleções de cavalos
                'tr.bet-button-row',      # Linhas com botões de aposta
                '.odds-row',              # Linhas de odds
                'tr[class*="runner"]',   # Qualquer linha com "runner" na classe
                'tr[class*="horse"]'     # Qualquer linha com "horse" na classe
            ]
            
            for seletor in seletores_oc:
                try:
                    elementos = soup.select(seletor)
                    if elementos:
                        cavalos_elem.extend(elementos)
                        logger.info(f"Oddschecker - {len(elementos)} cavalos encontrados com: {seletor}")
                except Exception as e:
                    logger.debug(f"Erro no seletor {seletor}: {e}")
            
            # Remover duplicados mantendo ordem
            cavalos_unicos = []
            elementos_vistos = set()
            for elem in cavalos_elem:
                elem_id = id(elem)  # Usar ID do objeto para identificar duplicados
                if elem_id not in elementos_vistos:
                    cavalos_unicos.append(elem)
                    elementos_vistos.add(elem_id)
            
            cavalos_elem = cavalos_unicos[:15]  # Limitar a 15 cavalos
            logger.info(f"Oddschecker - Total de cavalos únicos encontrados: {len(cavalos_elem)}")
            
            for i, elem in enumerate(cavalos_elem[:15]):
                nome_elem = elem.find('a') or elem.find('span', class_=re.compile(r'name|horse'))
                odds_elem = elem.find('span', class_=re.compile(r'odds|price'))
                
                cavalo_data = {
                    'nome': nome_elem.get_text(strip=True) if nome_elem else f"Cavalo {i + 1}",
                    'joquei': "Jóquei N/A",
                    'odds': odds_elem.get_text(strip=True) if odds_elem else "N/A",
                    'peso': "N/A",
                    'idade': "N/A",
                    'forma': "N/A",
                    'official_rating': "N/A",
                    'draw': i + 1,
                    'treinador': "N/A",
                    'historico_detalhado': []
                }
                dados['cavalos'].append(cavalo_data)
            
            # APLICAR RANKING COMPARATIVO AOS DADOS EXTRAÍDOS
            if dados['cavalos']:
                try:
                    logger.info(f"Oddschecker: Aplicando ranking comparativo a {len(dados['cavalos'])} cavalos")
                    
                    # Analisar cada cavalo individualmente
                    analises = []
                    for i, cavalo in enumerate(dados['cavalos']):
                        analise = self._analisar_cavalo_individual(cavalo, i + 1)
                        analises.append(analise)
                    
                    # Aplicar ranking comparativo
                    analises_com_ranking = self._aplicar_ranking_comparativo(analises)
                    
                    # Ordenar por pontuação final ajustada (maior para menor)
                    analises_ordenadas = sorted(
                        analises_com_ranking, 
                        key=lambda x: x.get('pontuacao_final_ajustada', x.get('pontuacao_final', 0)), 
                        reverse=True
                    )
                    
                    # Atualizar posições finais e percentis
                    total_cavalos = len(analises_ordenadas)
                    for i, analise in enumerate(analises_ordenadas):
                        analise['posicao_final'] = i + 1
                        analise['percentil'] = ((total_cavalos - i) / total_cavalos) * 100
                    
                    # Identificar grupos de performance
                    analises_com_grupos = self._identificar_grupos_performance(analises_ordenadas)
                    
                    # Atualizar dados com cavalos rankeados
                    dados['cavalos'] = analises_com_grupos
                    dados['ranking_info'] = {
                        'total_cavalos': total_cavalos,
                        'metodo_ranking': 'comparativo_oddschecker',
                        'criterios': ['rating', 'forma', 'peso', 'joquei', 'treinador', 'odds', 'consistencia', 'momentum']
                    }
                    
                    logger.info(f"Oddschecker: Ranking aplicado com sucesso. Melhor cavalo: {dados['cavalos'][0]['nome']}")
                    
                except Exception as e:
                    logger.warning(f"Erro ao aplicar ranking no Oddschecker: {str(e)}")
                    # Em caso de erro, manter dados originais
                    pass
            
            return dados if dados['cavalos'] else None
            
        except Exception as e:
            logger.warning(f"Erro ao extrair dados do Oddschecker: {str(e)}")
            return None
    
    def extrair_betfair(self, soup, url):
        """
        Extrai dados específicos do Betfair
        """
        try:
            dados = {
                'cavalos': [],
                'titulo_corrida': 'Corrida Betfair',
                'condicoes_pista': 'N/A',
                'clima': 'N/A'
            }
            
            # Buscar título da corrida
            titulo_elem = soup.find('h1') or soup.find('title')
            if titulo_elem:
                dados['titulo_corrida'] = titulo_elem.get_text(strip=True)
            
            # Buscar cavalos na interface do Betfair
            cavalos_elem = soup.find_all('div', class_=re.compile(r'runner|selection|market-item'))
            
            for i, elem in enumerate(cavalos_elem[:15]):
                nome_elem = elem.find('span', class_=re.compile(r'name|runner-name'))
                odds_elem = elem.find('span', class_=re.compile(r'odds|price|back-price'))
                
                cavalo_data = {
                    'nome': nome_elem.get_text(strip=True) if nome_elem else f"Cavalo {i + 1}",
                    'joquei': "Jóquei N/A",
                    'odds': odds_elem.get_text(strip=True) if odds_elem else "N/A",
                    'peso': "N/A",
                    'idade': "N/A",
                    'forma': "N/A",
                    'official_rating': "N/A",
                    'draw': i + 1,
                    'treinador': "N/A",
                    'historico_detalhado': []
                }
                dados['cavalos'].append(cavalo_data)
            
            # APLICAR RANKING COMPARATIVO AOS DADOS EXTRAÍDOS
            if dados['cavalos']:
                try:
                    logger.info(f"Betfair: Aplicando ranking comparativo a {len(dados['cavalos'])} cavalos")
                    
                    # Analisar cada cavalo individualmente
                    analises = []
                    for i, cavalo in enumerate(dados['cavalos']):
                        analise = self._analisar_cavalo_individual(cavalo, i + 1)
                        analises.append(analise)
                    
                    # Aplicar ranking comparativo
                    analises_com_ranking = self._aplicar_ranking_comparativo(analises)
                    
                    # Ordenar por pontuação final ajustada (maior para menor)
                    analises_ordenadas = sorted(
                        analises_com_ranking, 
                        key=lambda x: x.get('pontuacao_final_ajustada', x.get('pontuacao_final', 0)), 
                        reverse=True
                    )
                    
                    # Atualizar posições finais e percentis
                    total_cavalos = len(analises_ordenadas)
                    for i, analise in enumerate(analises_ordenadas):
                        analise['posicao_final'] = i + 1
                        analise['percentil'] = ((total_cavalos - i) / total_cavalos) * 100
                    
                    # Identificar grupos de performance
                    analises_com_grupos = self._identificar_grupos_performance(analises_ordenadas)
                    
                    # Atualizar dados com cavalos rankeados
                    dados['cavalos'] = analises_com_grupos
                    dados['ranking_info'] = {
                        'total_cavalos': total_cavalos,
                        'metodo_ranking': 'comparativo_betfair',
                        'criterios': ['rating', 'forma', 'peso', 'joquei', 'treinador', 'odds', 'consistencia', 'momentum']
                    }
                    
                    logger.info(f"Betfair: Ranking aplicado com sucesso. Melhor cavalo: {dados['cavalos'][0]['nome']}")
                    
                except Exception as e:
                    logger.warning(f"Erro ao aplicar ranking no Betfair: {str(e)}")
                    # Em caso de erro, manter dados originais
                    pass
            
            return dados if dados['cavalos'] else None
            
        except Exception as e:
            logger.warning(f"Erro ao extrair dados do Betfair: {str(e)}")
            return None

    def gerar_dados_exemplo(self, url):
        """
        Gera dados de exemplo para demonstração
        """
        try:
            num_cavalos = random.randint(8, 16)
            cavalos = []
            
            for i in range(num_cavalos):
                # Gerar odds realistas
                odds_decimal = random.uniform(1.5, 25.0)
                if random.random() < 0.3:  # 30% chance de odds fracionais
                    if odds_decimal < 2:
                        odds = "evens"
                    else:
                        num = int((odds_decimal - 1) * random.randint(1, 4))
                        den = random.randint(1, 4)
                        odds = f"{num}/{den}"
                else:
                    odds = f"{odds_decimal:.2f}"
                
                # Dados específicos para os primeiros três cavalos
                if i == 0:
                    # Earl Of Rochester
                    cavalo = {
                        'numero': '1',
                        'nome': 'Earl Of Rochester',
                        'joquei': 'Frankie Dettori',
                        'odds': '3.50',
                        'official_rating': '95',
                        'peso': '9-2',
                        'idade': '4',
                        'forma': '11234',
                        'historico_detalhado': [
                            {'posicao': '1', 'data': '15/08/2024', 'local': 'Newmarket', 'distancia': '1m 2f'},
                            {'posicao': '1', 'data': '28/07/2024', 'local': 'Ascot', 'distancia': '1m 1f'},
                            {'posicao': '2', 'data': '10/07/2024', 'local': 'York', 'distancia': '1m'},
                            {'posicao': '3', 'data': '22/06/2024', 'local': 'Cheltenham', 'distancia': '1m 4f'},
                            {'posicao': '4', 'data': '05/06/2024', 'local': 'Doncaster', 'distancia': '1m 2f'}
                        ]
                    }
                elif i == 1:
                    # Miss Cartesian
                    cavalo = {
                        'numero': '2',
                        'nome': 'Miss Cartesian',
                        'joquei': 'Ryan Moore',
                        'odds': '4.20',
                        'official_rating': '88',
                        'peso': '8-12',
                        'idade': '3',
                        'forma': '21135',
                        'historico_detalhado': [
                            {'posicao': '2', 'data': '18/08/2024', 'local': 'Goodwood', 'distancia': '7f'},
                            {'posicao': '1', 'data': '01/08/2024', 'local': 'Newmarket', 'distancia': '1m'},
                            {'posicao': '1', 'data': '14/07/2024', 'local': 'York', 'distancia': '6f'},
                            {'posicao': '3', 'data': '26/06/2024', 'local': 'Ascot', 'distancia': '7f'},
                            {'posicao': '5', 'data': '08/06/2024', 'local': 'Cheltenham', 'distancia': '1m'}
                        ]
                    }
                elif i == 2:
                    # Moe's Legacy
                    cavalo = {
                        'numero': '3',
                        'nome': "Moe's Legacy",
                        'joquei': 'William Buick',
                        'odds': '5.80',
                        'official_rating': '82',
                        'peso': '9-0',
                        'idade': '5',
                        'forma': '31242',
                        'historico_detalhado': [
                            {'posicao': '3', 'data': '20/08/2024', 'local': 'Doncaster', 'distancia': '1m 4f'},
                            {'posicao': '1', 'data': '03/08/2024', 'local': 'Goodwood', 'distancia': '1m 2f'},
                            {'posicao': '2', 'data': '16/07/2024', 'local': 'Newmarket', 'distancia': '1m 1f'},
                            {'posicao': '4', 'data': '28/06/2024', 'local': 'York', 'distancia': '1m'},
                            {'posicao': '2', 'data': '10/06/2024', 'local': 'Ascot', 'distancia': '1m 2f'}
                        ]
                    }
                else:
                    # Gerar dados aleatórios para os demais cavalos
                    # Gerar forma realista
                    forma_chars = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-']
                    forma = ''.join(random.choices(forma_chars, k=random.randint(5, 10)))
                    
                    # Gerar peso
                    peso_st = random.randint(8, 10)
                    peso_lb = random.randint(0, 13)
                    peso = f"{peso_st}-{peso_lb}"
                    
                    # Gerar Official Rating (OR) realista
                    official_rating = random.randint(60, 120)
                    
                    # Gerar histórico detalhado baseado na forma
                    historico_detalhado = []
                    for j, pos_char in enumerate(forma[:5]):  # Máximo 5 corridas
                        if pos_char.isdigit():
                            posicao = pos_char
                        elif pos_char == '0':
                            posicao = '10+'
                        elif pos_char == '-':
                            posicao = 'NF'
                        else:
                            posicao = pos_char
                        
                        # Gerar data fictícia (últimas semanas)
                        dias_atras = (j + 1) * random.randint(14, 28)
                        from datetime import datetime, timedelta
                        data_corrida = (datetime.now() - timedelta(days=dias_atras)).strftime('%d/%m/%Y')
                        
                        historico_detalhado.append({
                            'posicao': posicao,
                            'data': data_corrida,
                            'local': random.choice(['Newmarket', 'Ascot', 'York', 'Cheltenham', 'Doncaster', 'Goodwood']),
                            'distancia': random.choice(['1m', '1m 1f', '1m 2f', '1m 4f', '7f', '6f'])
                        })
                    
                    # Selecionar nome único que não foi usado ainda
                    nomes_usados = [c['nome'] for c in cavalos]
                    nomes_disponiveis = [nome for nome in self.nomes_cavalos if nome not in nomes_usados]
                    
                    # Se não há nomes disponíveis, gerar um nome único
                    if not nomes_disponiveis:
                        nome_cavalo = f"Cavalo {i + 1}"
                    else:
                        nome_cavalo = random.choice(nomes_disponiveis)
                    
                    cavalo = {
                        'numero': str(i + 1),
                        'nome': nome_cavalo,
                        'joquei': random.choice(self.joqueis_famosos),
                        'odds': odds,
                        'official_rating': str(official_rating),
                        'peso': peso,
                        'idade': str(random.randint(3, 8)),
                        'forma': forma,
                        'historico_detalhado': historico_detalhado
                    }
                
                cavalos.append(cavalo)
            
            return {
                'fonte': 'Dados de Exemplo',
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'corrida': {
                    'nome': f'Corrida de Exemplo - {datetime.now().strftime("%H:%M")}',
                    'distancia': f'{random.randint(1000, 3200)}m',
                    'tipo': random.choice(['Plano', 'Obstáculos', 'Handicap']),
                    'premio': f'£{random.randint(5000, 50000):,}'
                },
                'cavalos': cavalos,
                'aviso': 'Estes são dados de exemplo para demonstração da funcionalidade.'
            }
            
        except Exception as e:
            return {
                'erro': f'Erro ao gerar dados de exemplo: {str(e)}',
                'url': url,
                'timestamp': datetime.now().isoformat()
            }
    
    def _analisar_cavalo_individual(self, cavalo, posicao):
        """
        Analisa um cavalo individual usando algoritmo híbrido (quantitativo + qualitativo)
        Combina dados objetivos com fatores contextuais dos especialistas
        """
        nome = cavalo.get('nome', '')
        joquei = cavalo.get('joquei', 'Desconhecido')
        odds = cavalo.get('odds', 'N/A')
        peso = cavalo.get('peso', 'N/A')
        idade = cavalo.get('idade', 'N/A')
        forma = cavalo.get('forma', '')
        official_rating = cavalo.get('official_rating', 'N/A')
        draw = cavalo.get('draw', posicao)  # Usar posição como draw se não disponível
        treinador = cavalo.get('treinador', 'Desconhecido')
        
        # Obter estatísticas extraídas
        joquei_stats = cavalo.get('joquei_stats')
        treinador_stats = cavalo.get('treinador_stats')
        
        # Calcular scores individuais usando algoritmo híbrido
        rating_score = self._calcular_score_rating(official_rating)
        forma_score = self._calcular_score_forma_melhorado(forma)
        peso_score = self._calcular_score_peso_melhorado(peso)
        joquei_score = self._calcular_score_joquei_melhorado(joquei, joquei_stats)
        treinador_score = self._calcular_score_treinador(treinador, treinador_stats)
        idade_pts = self._idade_para_pontos(idade)
        draw_score = self._calcular_score_draw(draw)
        
        # NOVOS FATORES QUALITATIVOS (inspirados na análise de especialistas)
        momentum_score = self._calcular_momentum_qualitativo(cavalo)
        contexto_score = self._analisar_contexto_corrida(cavalo)
        valor_aposta_score = self._calcular_valor_aposta(odds, rating_score)
        
        # Se muitos dados estão faltando, usar score baseado na posição
        dados_faltando = sum([1 for x in [official_rating, joquei, peso, idade, forma] if not x or x in ['N/A', 'Desconhecido', '']])
        if dados_faltando >= 3:
            # Score baseado na posição (primeiros cavalos tendem a ser melhores)
            score_posicao = max(5, 10 - (posicao * 0.5))
            rating_score = score_posicao
            joquei_score = score_posicao
            forma_score = score_posicao
        
        # ALGORITMO HÍBRIDO - Pesos dos critérios (quantitativos + qualitativos)
        pesos = {
            'Rating': 0.20,
            'Forma': 0.16,
            'Peso': 0.08,
            'Jockey': 0.12,
            'Treinador': 0.08,
            'Idade_pts': 0.07,
            'Draw': 0.07,
            'Odds': 0.04,
            'Momentum': 0.08,  # Novo fator qualitativo
            'Contexto': 0.06,  # Novo fator qualitativo
            'Valor_Aposta': 0.04  # Novo fator qualitativo
        }
        
        # Calcular score de odds
        odds_score = self._calcular_score_odds(odds)
        
        # Cálculo da pontuação final usando fórmula híbrida
        pontuacao_final = (
            rating_score * pesos['Rating'] +
            forma_score * pesos['Forma'] +
            peso_score * pesos['Peso'] +
            joquei_score * pesos['Jockey'] +
            treinador_score * pesos['Treinador'] +
            idade_pts * pesos['Idade_pts'] +
            draw_score * pesos['Draw'] +
            odds_score * pesos['Odds'] +
            momentum_score * pesos['Momentum'] +
            contexto_score * pesos['Contexto'] +
            valor_aposta_score * pesos['Valor_Aposta']
        )
        
        # Converter para escala 0-100 para compatibilidade
        score_total = round(pontuacao_final * 10, 1)
        
        # ANÁLISE AVANÇADA ADICIONAL - Manter funcionalidades existentes
        tendencia_peso = self._analisar_tendencia_peso(forma, peso)
        tendencia_or = self._analisar_tendencia_official_rating(forma, official_rating)
        performance_joquei = self._analisar_performance_joquei(joquei, forma)
        consistencia = self._calcular_consistencia(forma)
        momentum = self._calcular_momentum(forma)
        
        # Análise de distância preferida
        historico_detalhado = cavalo.get('historico_detalhado', [])
        distancia_score = self._analisar_distancia_preferida(historico_detalhado)
        
        # Análise de condições da pista (se disponível)
        condicoes_pista = cavalo.get('condicoes_pista', 'N/A')
        pista_score = self._analisar_adaptacao_pista(forma, condicoes_pista)
        
        # Score de probabilidade de vitória
        probabilidade_vitoria = self._calcular_probabilidade_vitoria_melhorada(
            rating_score, joquei_score, forma_score, peso_score, idade_pts,
            tendencia_peso, tendencia_or, performance_joquei, consistencia, momentum
        )
        
        # Gerar recomendação baseada na nova pontuação e momentum
        recomendacao = self._gerar_recomendacao_melhorada(pontuacao_final, score_total, momentum)
        
        return {
            'posicao': posicao,
            'nome': nome,
            'joquei': joquei,
            'odds': odds,
            'official_rating': official_rating,
            'peso': peso,
            'idade': idade,
            'forma': forma,
            'draw': draw,
            'treinador': treinador,
            'score_odds': 10,  # Mantido para compatibilidade
            'score_joquei': joquei_score * 10,  # Convertido para escala antiga
            'score_forma': forma_score * 10,
            'score_peso': peso_score * 10,
            'score_idade': idade_pts * 10,
            'rating_score': rating_score,
            'forma_score': forma_score,
            'peso_score': peso_score,
            'joquei_score': joquei_score,
            'treinador_score': treinador_score,
            'idade_pts': idade_pts,
            'draw_score': draw_score,
            'odds_score': odds_score,
            'momentum_score': momentum_score,
            'contexto_score': contexto_score,
            'valor_aposta_score': valor_aposta_score,
            'pontuacao_final': round(pontuacao_final, 2),
            'tendencia_peso': tendencia_peso,
            'tendencia_or': tendencia_or,
            'performance_joquei': performance_joquei,
            'consistencia': consistencia,
            'momentum': momentum,
            'distancia_score': distancia_score,
            'pista_score': pista_score,
            'probabilidade_vitoria': probabilidade_vitoria,
            'score_total': score_total,
            'recomendacao': recomendacao,
            'analise_hibrida': {
                'quantitativo': {
                    'rating': rating_score,
                    'forma': forma_score,
                    'peso': peso_score,
                    'joquei': joquei_score,
                    'treinador': treinador_score
                },
                'qualitativo': {
                    'momentum': momentum_score,
                    'contexto': contexto_score,
                    'valor_aposta': valor_aposta_score
                },
                'metodo': 'hibrido_especialistas_algoritmo'
            }
        }
    
    def _calcular_score_odds(self, odds_str):
        """
        Calcula score baseado nas odds (reintegrado como fator de mercado)
        """
        if not odds_str or odds_str == 'N/A':
            return 5
        
        try:
            # Converter odds fracionais para decimal
            if '/' in odds_str:
                if odds_str.lower() == 'evens':
                    odds_decimal = 2.0
                else:
                    parts = odds_str.split('/')
                    if len(parts) == 2:
                        numerator = float(parts[0])
                        denominator = float(parts[1])
                        odds_decimal = (numerator / denominator) + 1
                    else:
                        return 5
            else:
                # Odds já em formato decimal
                odds_decimal = float(odds_str)
            
            # Score baseado nas odds (odds menores = score maior)
            if odds_decimal <= 2.0:  # Favorito absoluto
                return 10
            elif odds_decimal <= 3.0:  # Forte favorito
                return 8
            elif odds_decimal <= 5.0:  # Favorito moderado
                return 6
            elif odds_decimal <= 10.0:  # Chance média
                return 4
            elif odds_decimal <= 20.0:  # Outsider
                return 2
            else:  # Longshot
                return 1
                
        except:
            return 5
    
    def _idade_para_pontos(self, idade):
        """
        Função para converter idade em pontos (novo algoritmo)
        """
        if not idade or idade == 'N/A':
            return 5
        
        try:
            idade_num = int(str(idade).replace('yo', '').strip())
            
            if 4 <= idade_num <= 6:
                return 10
            elif idade_num == 3 or idade_num == 7:
                return 6
            else:
                return 5
        except:
            return 5
    
    def _calcular_momentum_qualitativo(self, cavalo):
        """
        Calcula momentum qualitativo baseado em padrões de especialistas
        Considera: forma recente, mudanças de classe, retorno de lesão, etc.
        """
        forma = cavalo.get('forma', '')
        nome = cavalo.get('nome', '')
        
        momentum_score = 5  # Score neutro
        
        # Análise da forma recente (últimas 3 corridas)
        if forma and len(forma) >= 3:
            forma_recente = forma[:3]  # Últimas 3 corridas
            
            # Padrão de melhoria (ex: 543 -> melhorando)
            if len(forma_recente) >= 3:
                try:
                    pos1, pos2, pos3 = int(forma_recente[0]), int(forma_recente[1]), int(forma_recente[2])
                    if pos1 < pos2 < pos3:  # Melhorando consistentemente
                        momentum_score += 3
                    elif pos1 < pos2:  # Melhorou na última
                        momentum_score += 2
                    elif pos1 > pos2 > pos3:  # Piorando
                        momentum_score -= 2
                except:
                    pass
            
            # Vitórias recentes
            vitorias_recentes = forma_recente.count('1')
            if vitorias_recentes >= 2:
                momentum_score += 3
            elif vitorias_recentes == 1:
                momentum_score += 1
            
            # Placings consistentes (top 3)
            placings = sum(1 for c in forma_recente if c in '123')
            if placings >= 2:
                momentum_score += 1
        
        # Indicadores textuais de momentum (baseado em análises de especialistas)
        nome_lower = nome.lower()
        
        # Palavras-chave que indicam momentum positivo
        indicadores_positivos = [
            'backed up', 'return to form', 'regained', 'improving', 'progressive',
            'on the upgrade', 'going the right way', 'bounced back'
        ]
        
        # Palavras-chave que indicam momentum negativo
        indicadores_negativos = [
            'disappointing', 'below par', 'struggling', 'out of form',
            'needs to bounce back', 'question marks'
        ]
        
        return max(0, min(10, momentum_score))
    
    def _analisar_contexto_corrida(self, cavalo):
        """
        Analisa contexto específico da corrida (mudanças de distância, superfície, classe)
        Inspirado na análise contextual dos especialistas
        """
        contexto_score = 5  # Score neutro
        
        # Análise de adaptação (baseada em padrões de especialistas)
        official_rating = cavalo.get('official_rating', 'N/A')
        peso = cavalo.get('peso', 'N/A')
        
        # Cavalo com rating baixo mas peso favorável (oportunidade)
        try:
            if official_rating != 'N/A' and peso != 'N/A':
                rating_num = int(str(official_rating))
                if rating_num < 70:  # Rating baixo
                    contexto_score += 1  # Pode ter chance em classe mais baixa
        except:
            pass
        
        # Análise de condições favoráveis
        forma = cavalo.get('forma', '')
        if forma:
            # Se teve boas performances recentes, contexto favorável
            if '1' in forma[:2] or '2' in forma[:2]:  # Top 2 nas últimas 2
                contexto_score += 2
        
        # Fatores de classe e competitividade
        joquei = cavalo.get('joquei', '')
        treinador = cavalo.get('treinador', '')
        
        # Jóquei/treinador de qualidade em corrida mais fácil
        if joquei != 'N/A' and joquei != 'Desconhecido':
            contexto_score += 0.5
        
        if treinador != 'N/A' and treinador != 'Desconhecido':
            contexto_score += 0.5
        
        return max(0, min(10, contexto_score))
    
    def _calcular_valor_aposta(self, odds, rating_score):
        """
        Calcula valor de aposta comparando odds com rating real
        Identifica cavalos subestimados pelo mercado
        """
        if not odds or odds == 'N/A':
            return 5
        
        try:
            # Converter odds para probabilidade implícita
            if '/' in odds:
                if odds.lower() == 'evens':
                    prob_implicita = 50
                else:
                    parts = odds.split('/')
                    if len(parts) == 2:
                        num, den = float(parts[0]), float(parts[1])
                        odds_decimal = (num / den) + 1
                        prob_implicita = (1 / odds_decimal) * 100
                    else:
                        return 5
            else:
                odds_decimal = float(odds)
                prob_implicita = (1 / odds_decimal) * 100
            
            # Comparar com rating score (nossa avaliação)
            nossa_prob = (rating_score / 10) * 100  # Converter para percentual
            
            # Se nossa avaliação é maior que a do mercado = valor
            diferenca = nossa_prob - prob_implicita
            
            if diferenca > 20:  # Muito subestimado
                return 9
            elif diferenca > 10:  # Subestimado
                return 7
            elif diferenca > 0:  # Ligeiramente subestimado
                return 6
            elif diferenca > -10:  # Fairly priced
                return 5
            elif diferenca > -20:  # Ligeiramente superestimado
                return 4
            else:  # Muito superestimado
                return 2
                
        except:
            return 5
    
    def _calcular_score_rating(self, rating):
        """
        Calcula score baseado no Official Rating
        """
        if not rating or rating == 'N/A':
            return 5
        
        try:
            rating_num = float(rating)
            # Normalizar rating (assumindo range 40-120) para escala 0-10
            score = (rating_num / 50) * 10
            return min(max(score, 0), 10)
        except:
            return 5
    
    def _calcular_score_forma_melhorado(self, forma_str):
        """
        Calcula score de forma melhorado (escala 0-10)
        """
        if not forma_str or len(forma_str) < 3:
            return 5
        
        try:
            # Últimas performances: 1º=10, 2º=8, 3º=6, etc.
            score = 0
            peso_posicao = [1.0, 0.7, 0.5, 0.3, 0.2]  # Pesos decrescentes
            
            for i, char in enumerate(forma_str[:5]):
                if i < len(peso_posicao):
                    if char == '1':
                        score += 10 * peso_posicao[i]
                    elif char == '2':
                        score += 8 * peso_posicao[i]
                    elif char == '3':
                        score += 6 * peso_posicao[i]
                    elif char == '4':
                        score += 4 * peso_posicao[i]
                    elif char == '5':
                        score += 2 * peso_posicao[i]
            
            return min(score, 10)
        except:
            return 5
    
    def _calcular_score_peso_melhorado(self, peso):
        """
        Calcula score de peso melhorado (escala 0-10)
        """
        if not peso or peso == 'N/A':
            return 5
        
        try:
            # Peso ideal = 10, ajustar conforme necessário
            if '-' in peso:
                stones, pounds = peso.split('-')
                total_pounds = int(stones) * 14 + int(pounds)
                
                # Score baseado no peso (pesos menores = scores maiores)
                if total_pounds <= 120:  # 8-8 ou menos
                    return 10
                elif total_pounds <= 126:  # 9-0 ou menos
                    return 9
                elif total_pounds <= 133:  # 9-7 ou menos
                    return 10  # Peso ideal
                elif total_pounds <= 140:  # 10-0 ou menos
                    return 9
                else:
                    return 8
            else:
                return 10  # Peso ideal por padrão
        except:
            return 5
    
    def _calcular_score_joquei_melhorado(self, joquei_str, joquei_stats=None):
        """
        Calcula score de jóquei melhorado usando estatísticas reais (escala 0-10)
        """
        if not joquei_str:
            return 5
        
        joquei_lower = joquei_str.lower()
        base_score = 5
        
        # Jóqueis famosos (base alta)
        joqueis_elite = [
            'frankie dettori', 'f dettori', 'dettori',
            'ryan moore', 'r moore', 'moore',
            'william buick', 'w buick', 'buick',
            'oisin murphy', 'o murphy', 'murphy',
            'tom marquand', 't marquand', 'marquand',
            'hollie doyle', 'h doyle', 'doyle'
        ]
        
        is_elite = any(joquei_elite in joquei_lower for joquei_elite in joqueis_elite)
        if is_elite:
            base_score = 8
        elif len(joquei_str) > 5 and any(c.isupper() for c in joquei_str):
            base_score = 6
        
        # Usar estatísticas reais se disponíveis
        if joquei_stats and isinstance(joquei_stats, dict):
            win_percentage = joquei_stats.get('win_percentage', 0)
            rides = joquei_stats.get('rides', 0)
            
            # Ajustar score baseado na porcentagem de vitórias
            if win_percentage >= 25:  # Excelente
                stats_bonus = 2
            elif win_percentage >= 20:  # Muito bom
                stats_bonus = 1.5
            elif win_percentage >= 15:  # Bom
                stats_bonus = 1
            elif win_percentage >= 10:  # Médio
                stats_bonus = 0.5
            elif win_percentage >= 5:  # Baixo
                stats_bonus = 0
            else:  # Muito baixo
                stats_bonus = -1
            
            # Bonus por experiência (número de corridas)
            if rides >= 500:
                experience_bonus = 0.5
            elif rides >= 200:
                experience_bonus = 0.3
            elif rides >= 50:
                experience_bonus = 0.1
            else:
                experience_bonus = 0
            
            final_score = base_score + stats_bonus + experience_bonus
            return min(10, max(0, final_score))
        
        return base_score
    
    def _calcular_score_treinador(self, treinador_str, treinador_stats=None):
        """
        Calcula score baseado no treinador usando estatísticas reais (escala 0-10)
        """
        if not treinador_str or treinador_str == 'Desconhecido':
            return 5
        
        treinador_lower = treinador_str.lower()
        base_score = 5
        
        # Treinadores famosos (base alta)
        treinadores_elite = [
            'aidan o\'brien', 'a o\'brien', 'o\'brien',
            'john gosden', 'j gosden', 'gosden',
            'charlie appleby', 'c appleby', 'appleby',
            'william haggas', 'w haggas', 'haggas',
            'sir michael stoute', 'm stoute', 'stoute'
        ]
        
        is_elite = any(treinador_elite in treinador_lower for treinador_elite in treinadores_elite)
        if is_elite:
            base_score = 7
        elif len(treinador_str) > 5:
            base_score = 6
        
        # Usar estatísticas reais se disponíveis
        if treinador_stats and isinstance(treinador_stats, dict):
            win_percentage = treinador_stats.get('win_percentage', 0)
            runs = treinador_stats.get('runs', 0)
            
            # Ajustar score baseado na porcentagem de vitórias
            if win_percentage >= 30:  # Excelente
                stats_bonus = 2
            elif win_percentage >= 25:  # Muito bom
                stats_bonus = 1.5
            elif win_percentage >= 20:  # Bom
                stats_bonus = 1
            elif win_percentage >= 15:  # Médio
                stats_bonus = 0.5
            elif win_percentage >= 10:  # Baixo
                stats_bonus = 0
            else:  # Muito baixo
                stats_bonus = -1
            
            # Bonus por experiência (número de corridas)
            if runs >= 1000:
                experience_bonus = 0.5
            elif runs >= 500:
                experience_bonus = 0.3
            elif runs >= 100:
                experience_bonus = 0.1
            else:
                experience_bonus = 0
            
            final_score = base_score + stats_bonus + experience_bonus
            return min(10, max(0, final_score))
        
        return base_score
    
    def _calcular_score_draw(self, draw):
        """
        Calcula score baseado na posição de largada (escala 0-10)
        """
        try:
            draw_num = int(draw)
            
            # Posições ideais (meio do campo)
            if 3 <= draw_num <= 8:
                return 8
            elif draw_num <= 2 or draw_num >= 12:
                return 6
            else:
                return 7
        except:
            return 7
    
    def _calcular_score_joquei(self, joquei_str):
        """
        Calcula score baseado no jóquei
        """
        if not joquei_str:
            return 5
        
        joquei_lower = joquei_str.lower()
        
        # Jóqueis famosos
        joqueis_elite = [
            'frankie dettori', 'f dettori', 'dettori',
            'ryan moore', 'r moore', 'moore',
            'william buick', 'w buick', 'buick',
            'oisin murphy', 'o murphy', 'murphy',
            'tom marquand', 't marquand', 'marquand',
            'hollie doyle', 'h doyle', 'doyle'
        ]
        
        for joquei_elite in joqueis_elite:
            if joquei_elite in joquei_lower:
                return 25
        
        # Jóqueis experientes (com iniciais)
        if len(joquei_str) > 5 and any(c.isupper() for c in joquei_str):
            return 15
        
        return 10
    
    def _calcular_score_forma(self, forma_str):
        """
        Calcula score baseado na forma
        """
        if not forma_str or len(forma_str) < 3:
            return 5
        
        try:
            # Contar vitórias (1s) na forma
            vitorias = forma_str.count('1')
            colocacoes = forma_str.count('2') + forma_str.count('3')
            
            score = vitorias * 5 + colocacoes * 2
            return min(score, 20)  # Máximo 20 pontos
            
        except:
            return 5
    
    def _calcular_score_peso(self, peso):
        """
        Calcula score baseado no peso carregado
        """
        if not peso or peso == 'N/A':
            return 50
        
        try:
            # Extrair peso em stones e pounds (formato: "9-7" ou "10-0")
            if '-' in peso:
                stones, pounds = peso.split('-')
                total_pounds = int(stones) * 14 + int(pounds)
                
                # Score baseado no peso (pesos menores = scores maiores)
                if total_pounds <= 120:  # 8-8 ou menos
                    return 85
                elif total_pounds <= 126:  # 9-0 ou menos
                    return 75
                elif total_pounds <= 133:  # 9-7 ou menos
                    return 65
                elif total_pounds <= 140:  # 10-0 ou menos
                    return 55
                else:
                    return 45
            else:
                return 50
        except:
            return 50
    
    def _analisar_tendencia_peso(self, forma, peso_atual):
        """
        Analisa a tendência de peso comparando com performances anteriores
        """
        try:
            if not forma or not peso_atual or peso_atual == 'N/A':
                return 50
            
            # Simular análise de peso histórico baseado na forma
            vitorias_recentes = forma[:3].count('1') if len(forma) >= 3 else 0
            colocacoes_recentes = forma[:3].count('2') + forma[:3].count('3') if len(forma) >= 3 else 0
            
            # Se teve boas performances recentes, peso atual é favorável
            if vitorias_recentes >= 2:
                return 85  # Peso ótimo para vitórias
            elif vitorias_recentes >= 1 or colocacoes_recentes >= 2:
                return 75  # Peso bom para colocações
            elif colocacoes_recentes >= 1:
                return 65  # Peso razoável
            else:
                return 45  # Peso pode estar afetando performance
                
        except:
            return 50
    

    
    def _analisar_tendencia_official_rating(self, forma, or_atual):
        """
        Analisa a tendência do Official Rating comparando com a forma recente
        """
        try:
            if not forma or not or_atual or or_atual == 'N/A':
                return 50
            
            or_atual_num = float(str(or_atual))
            
            # Analisar forma recente (últimas 5 corridas)
            forma_recente = forma[:5] if len(forma) >= 5 else forma
            vitorias = forma_recente.count('1')
            colocacoes = forma_recente.count('2') + forma_recente.count('3')
            
            # OR alto com boa forma = consistência excelente
            if or_atual_num >= 90 and vitorias >= 2:
                return 95  # Elite com forma
            elif or_atual_num >= 85 and vitorias >= 1:
                return 85  # Muito bom com forma
            elif or_atual_num >= 80 and colocacoes >= 2:
                return 80  # Bom e consistente
            elif or_atual_num >= 75 and vitorias >= 1:
                return 75  # Médio com potencial
            elif or_atual_num >= 90 and vitorias == 0:
                return 60  # Alto OR mas sem forma recente
            elif or_atual_num <= 70 and vitorias >= 1:
                return 70  # OR baixo mas mostrando melhora
            elif or_atual_num >= 85:
                return 70  # OR alto, forma média
            elif or_atual_num >= 75:
                return 60  # OR médio
            else:
                return 45  # OR baixo
                
        except:
            return 50
    
    def _analisar_performance_joquei(self, joquei, forma):
        """
        Analisa a performance do jóquei baseada na forma do cavalo
        """
        try:
            if not joquei or not forma:
                return 50
            
            joquei_lower = joquei.lower()
            
            # Jóqueis de elite com boa forma = excelente
            joqueis_elite = ['dettori', 'moore', 'buick', 'murphy', 'marquand', 'doyle']
            is_elite = any(elite in joquei_lower for elite in joqueis_elite)
            
            vitorias = forma[:5].count('1') if len(forma) >= 5 else forma.count('1')
            colocacoes = forma[:5].count('2') + forma[:5].count('3') if len(forma) >= 5 else forma.count('2') + forma.count('3')
            
            if is_elite:
                if vitorias >= 2:
                    return 95  # Elite + boa forma
                elif vitorias >= 1 or colocacoes >= 2:
                    return 85  # Elite + forma razoável
                else:
                    return 70  # Elite mas forma ruim
            else:
                if vitorias >= 2:
                    return 80  # Jóquei regular + boa forma
                elif vitorias >= 1 or colocacoes >= 2:
                    return 65  # Jóquei regular + forma razoável
                else:
                    return 45  # Jóquei regular + forma ruim
                    
        except:
            return 50
    
    def _calcular_consistencia(self, forma):
        """
        Calcula a consistência baseada na regularidade das colocações
        """
        try:
            if not forma or len(forma) < 3:
                return 50
            
            # Analisar últimas 5 corridas
            forma_recente = forma[:5] if len(forma) >= 5 else forma
            
            colocacoes_boas = 0
            for pos in forma_recente:
                if pos in ['1', '2', '3']:
                    colocacoes_boas += 1
            
            consistencia_pct = (colocacoes_boas / len(forma_recente)) * 100
            
            if consistencia_pct >= 80:
                return 90  # Muito consistente
            elif consistencia_pct >= 60:
                return 75  # Consistente
            elif consistencia_pct >= 40:
                return 60  # Moderadamente consistente
            else:
                return 40  # Inconsistente
                
        except:
            return 50
    
    def _analisar_distancia_preferida(self, historico_detalhado):
        """
        Analisa a performance do cavalo em diferentes distâncias
        """
        try:
            if not historico_detalhado or len(historico_detalhado) < 3:
                return 50  # Score neutro se não há dados suficientes
            
            # Contar performances por categoria de distância
            distancias_curtas = 0  # até 1m
            distancias_medias = 0  # 1m a 1m4f
            distancias_longas = 0  # acima de 1m4f
            
            vitorias_curtas = 0
            vitorias_medias = 0
            vitorias_longas = 0
            
            for corrida in historico_detalhado:
                distancia = corrida.get('distancia', '').lower()
                posicao = corrida.get('posicao', '')
                
                # Classificar distância
                if any(d in distancia for d in ['6f', '7f', '1m']):
                    if '1m 1f' not in distancia and '1m 2f' not in distancia:
                        distancias_curtas += 1
                        if posicao == '1':
                            vitorias_curtas += 1
                elif any(d in distancia for d in ['1m 1f', '1m 2f', '1m 3f', '1m 4f']):
                    distancias_medias += 1
                    if posicao == '1':
                        vitorias_medias += 1
                else:
                    distancias_longas += 1
                    if posicao == '1':
                        vitorias_longas += 1
            
            # Calcular taxa de sucesso por distância
            taxa_curtas = (vitorias_curtas / distancias_curtas * 100) if distancias_curtas > 0 else 0
            taxa_medias = (vitorias_medias / distancias_medias * 100) if distancias_medias > 0 else 0
            taxa_longas = (vitorias_longas / distancias_longas * 100) if distancias_longas > 0 else 0
            
            # Retornar a melhor taxa de sucesso
            melhor_taxa = max(taxa_curtas, taxa_medias, taxa_longas)
            return min(melhor_taxa, 100)
            
        except Exception as e:
            logger.warning(f"Erro ao analisar distância preferida: {str(e)}")
            return 50
    
    def _analisar_adaptacao_pista(self, forma, condicoes_pista):
        """
        Analisa como o cavalo se adapta às condições da pista
        """
        try:
            if not forma or condicoes_pista == 'N/A':
                return 50  # Score neutro
            
            # Score base baseado na forma recente
            forma_recente = forma[:3] if len(forma) >= 3 else forma
            vitorias_recentes = forma_recente.count('1')
            colocacoes_recentes = forma_recente.count('2') + forma_recente.count('3')
            
            score_base = (vitorias_recentes * 30 + colocacoes_recentes * 15)
            
            # Ajustar baseado nas condições da pista
            if condicoes_pista.lower() in ['firme', 'firm', 'good']:
                # Pista firme favorece cavalos com boa forma
                if vitorias_recentes >= 2:
                    score_base += 20
                elif vitorias_recentes >= 1:
                    score_base += 10
            elif condicoes_pista.lower() in ['pesada', 'heavy', 'soft']:
                # Pista pesada pode nivelar o campo
                score_base += 15  # Bonus por adaptabilidade
            
            return min(score_base, 100)
            
        except Exception as e:
            logger.warning(f"Erro ao analisar adaptação à pista: {str(e)}")
            return 50
    
    def _calcular_momentum(self, forma):
        """
        Calcula o momentum baseado nas últimas 3 corridas
        """
        try:
            if not forma or len(forma) < 3:
                return 50
            
            ultimas_3 = forma[:3]
            
            # Pontuação por posição (1=10pts, 2=7pts, 3=5pts, 4=3pts, 5+=1pt)
            pontos = 0
            for pos in ultimas_3:
                if pos == '1':
                    pontos += 10
                elif pos == '2':
                    pontos += 7
                elif pos == '3':
                    pontos += 5
                elif pos == '4':
                    pontos += 3
                else:
                    pontos += 1
            
            # Converter para escala 0-100
            momentum_score = min((pontos / 30) * 100, 100)
            
            return round(momentum_score)
            
        except:
            return 50
    
    def _calcular_probabilidade_vitoria_melhorada(self, rating_score, joquei_score, forma_score, 
                                                 peso_score, idade_pts, tendencia_peso, 
                                                 tendencia_or, performance_joquei, 
                                                 consistencia, momentum):
        """
        Calcula probabilidade de vitória usando novo algoritmo
        """
        try:
            # Combinar scores principais
            score_base = (
                rating_score * 0.3 +
                forma_score * 0.25 +
                joquei_score * 0.2 +
                peso_score * 0.15 +
                idade_pts * 0.1
            )
            
            # Adicionar fatores avançados
            score_avancado = (
                tendencia_peso * 0.1 +
                tendencia_or * 0.1 +
                performance_joquei * 0.05 +
                consistencia * 0.05 +
                momentum * 0.05
            ) / 100  # Normalizar
            
            probabilidade = (score_base + score_avancado) * 10
            return min(max(probabilidade, 0), 100)
        except:
            return 50
    
    def _calcular_probabilidade_vitoria(self, score_odds, score_joquei, score_forma, 
                                       score_peso, score_idade, tendencia_peso, 
                                       tendencia_or, performance_joquei, 
                                       consistencia, momentum):
        """
        Calcula a probabilidade de vitória usando fórmula avançada
        """
        try:
            # Fórmula ponderada para probabilidade (sem odds)
            probabilidade = (
                score_forma * 0.35 +          # Forma recente crucial
                tendencia_or * 0.25 +         # Tendência Official Rating
                performance_joquei * 0.20 +   # Jóquei + forma
                momentum * 0.12 +             # Momentum recente
                consistencia * 0.05 +         # Consistência
                tendencia_peso * 0.03         # Tendência de peso
            )
            
            return round(min(probabilidade, 100), 1)
            
        except:
            return 50.0
    
    def _gerar_recomendacao_melhorada(self, pontuacao_final, score_total, momentum):
        """
        Gera recomendação baseada na nova pontuação e momentum
        Intervalos de momentum:
        - Abaixo de 30: momentum baixo
        - 31 a 60: aposta moderada
        - 61 a 80: boa aposta
        - Acima de 81: ótima aposta
        """
        try:
            # Classificação do momentum
            if momentum < 30:
                momentum_nivel = "baixo"
            elif momentum <= 60:
                momentum_nivel = "moderado"
            elif momentum <= 80:
                momentum_nivel = "bom"
            else:
                momentum_nivel = "ótimo"
            
            # Recomendações baseadas na pontuação final e momentum
            if pontuacao_final >= 8.5:
                if momentum < 30:
                    return "⚠️ APOSTA CAUTELOSA - Excelente candidato (momentum baixo)"
                elif momentum <= 60:
                    return "✅ APOSTA MODERADA - Excelente candidato"
                elif momentum <= 80:
                    return "⭐ APOSTA BOA - Excelente candidato"
                else:
                    return "🏆 ÓTIMA APOSTA - Excelente candidato (momentum ótimo)"
            elif pontuacao_final >= 7.5:
                if momentum < 30:
                    return "⚠️ APOSTA CAUTELOSA - Forte candidato (momentum baixo)"
                elif momentum <= 60:
                    return "✅ APOSTA MODERADA - Forte candidato"
                elif momentum <= 80:
                    return "⭐ APOSTA BOA - Forte candidato"
                else:
                    return "🏆 ÓTIMA APOSTA - Forte candidato (momentum ótimo)"
            elif pontuacao_final >= 6.5:
                if momentum < 30:
                    return "❌ EVITAR - Candidato sólido (momentum baixo)"
                elif momentum <= 60:
                    return "✅ APOSTA MODERADA - Candidato sólido"
                elif momentum <= 80:
                    return "⭐ APOSTA BOA - Candidato sólido"
                else:
                    return "🏆 ÓTIMA APOSTA - Candidato sólido (momentum ótimo)"
            elif pontuacao_final >= 5.5:
                if momentum < 30:
                    return "❌ EVITAR - Candidato médio (momentum baixo)"
                elif momentum <= 60:
                    return "✅ APOSTA MODERADA - Candidato médio"
                elif momentum <= 80:
                    return "⭐ APOSTA BOA - Candidato médio"
                else:
                    return "🏆 ÓTIMA APOSTA - Candidato médio (momentum ótimo)"
            else:
                return "❌ EVITAR - Candidato fraco"
        except:
            return "❓ ANÁLISE INCOMPLETA"
    
    def _gerar_recomendacao_avancada(self, probabilidade, score_total):
        """
        Gera recomendação baseada na probabilidade de vitória
        """
        try:
            if probabilidade >= 85:
                return '🏆 FAVORITO ABSOLUTO - Altíssima probabilidade de vitória'
            elif probabilidade >= 75:
                return '⭐ FORTE FAVORITO - Excelente chance de vitória'
            elif probabilidade >= 65:
                return '✅ BOA OPÇÃO - Boa probabilidade de colocação'
            elif probabilidade >= 55:
                return '⚠️ OPÇÃO CONSIDERÁVEL - Chance moderada'
            elif probabilidade >= 45:
                return '❓ RISCO MÉDIO - Apostar com cautela'
            elif probabilidade >= 35:
                return '❌ RISCO ALTO - Baixa probabilidade'
            else:
                return '🚫 EVITAR - Probabilidade muito baixa'
                
        except:
            return '❓ ANÁLISE INCONCLUSIVA'
            
        try:
            # Formato: "9-7" (9 stones, 7 pounds)
            if '-' in str(peso):
                parts = str(peso).split('-')
                stones = int(parts[0])
                pounds = int(parts[1]) if len(parts) > 1 else 0
                total_pounds = stones * 14 + pounds
                
                # Peso ideal entre 126-140 pounds (9-0 a 10-0)
                if 126 <= total_pounds <= 140:
                    return 80
                elif 120 <= total_pounds <= 145:
                    return 70
                elif 115 <= total_pounds <= 150:
                    return 60
                else:
                    return 40
            else:
                return 50
        except:
            return 50
    
    def _calcular_score_idade(self, idade):
        """
        Calcula score baseado na idade do cavalo
        """
        if not idade or idade == 'N/A':
            return 50
            
        try:
            idade_num = int(str(idade).replace('yo', '').strip())
            
            if 4 <= idade_num <= 6:
                return 80
            elif idade_num == 3 or idade_num == 7:
                return 70
            elif idade_num == 8:
                return 60
            elif idade_num >= 9:
                return 40
            else:
                return 50
        except:
            return 50
    
    def _gerar_recomendacao(self, score_total):
        """
        Gera recomendação baseada no score total
        """
        if score_total >= 85:
            return "🏆 FORTE FAVORITO - Apostar com confiança"
        elif score_total >= 75:
            return "⭐ BOA OPÇÃO - Considerável para apostas"
        elif score_total >= 65:
            return "✅ OPÇÃO CONSIDERÁVEL - Risco médio"
        elif score_total >= 55:
            return "⚠️ RISCO MÉDIO - Apostar com cautela"
        elif score_total >= 45:
            return "❌ RISCO ALTO - Evitar"
        else:
            return "🚫 EVITAR - Muito alto risco"
    
    def _gerar_estatisticas(self, analises):
        """
        Gera estatísticas gerais da análise
        """
        if not analises:
            return {}
        
        scores = [a.get('score_total', 0) for a in analises]
        
        return {
            'total_cavalos': len(analises),
            'score_medio': round(sum(scores) / len(scores), 1),
            'melhor_score': max(scores),
            'pior_score': min(scores),
            'favorito': analises[0]['nome'] if analises else 'N/A',
            'recomendacoes': {
                rec: len([a for a in analises if a.get('recomendacao') == rec])
                for rec in ["🏆 FORTE FAVORITO", "⭐ BOA OPÇÃO", "✅ CONSIDERÁVEL", "⚠️ RISCO MÉDIO", "❌ EVITAR"]
            }
        }
    
    def analisar_cavalos(self, dados_extraidos):
        """
        Analisa os cavalos extraídos e retorna o resultado formatado com ranking aprimorado
        """
        try:
            if not dados_extraidos or 'cavalos' not in dados_extraidos:
                return {'erro': 'Dados de cavalos não encontrados'}
            
            cavalos = dados_extraidos['cavalos']
            if not cavalos:
                return {'erro': 'Nenhum cavalo encontrado para análise'}
            
            # Validação final para remover duplicados antes da análise
            cavalos_unicos = []
            nomes_vistos = set()
            
            for cavalo in cavalos:
                nome = cavalo.get('nome', '').strip()
                if nome and nome not in nomes_vistos:
                    cavalos_unicos.append(cavalo)
                    nomes_vistos.add(nome)
                else:
                    logger.warning(f"Cavalo duplicado removido na análise: {nome}")
            
            logger.info(f"Analisando {len(cavalos_unicos)} cavalos únicos (removidos {len(cavalos) - len(cavalos_unicos)} duplicados)...")
            
            # Analisar cada cavalo individualmente
            analises = []
            for i, cavalo in enumerate(cavalos_unicos):
                analise = self._analisar_cavalo_individual(cavalo, i + 1)
                analises.append(analise)
            
            # NOVO SISTEMA DE RANKING APRIMORADO
            # 1. Aplicar ranking comparativo entre cavalos
            analises = self._aplicar_ranking_comparativo(analises)
            
            # 2. Ordenar por pontuação final (maior para menor)
            analises.sort(key=lambda x: x.get('pontuacao_final_ajustada', x.get('pontuacao_final', 0)), reverse=True)
            
            # 3. Atualizar posições finais no ranking
            for i, analise in enumerate(analises):
                analise['posicao_final'] = i + 1
                analise['percentil'] = round((len(analises) - i) / len(analises) * 100, 1)
            
            # 4. Identificar grupos de performance
            analises = self._identificar_grupos_performance(analises)
            
            # Gerar estatísticas gerais aprimoradas
            estatisticas = self._gerar_estatisticas_aprimoradas(analises)
            
            # Preparar resultado final
            resultado = {
                'dados': {
                    'titulo_corrida': dados_extraidos.get('titulo_corrida', 'Corrida de Cavalos'),
                    'condicoes_pista': dados_extraidos.get('condicoes_pista', 'N/A'),
                    'clima': dados_extraidos.get('clima', 'N/A'),
                    'analises': analises
                },
                'estatisticas': estatisticas,
                'timestamp': datetime.now().isoformat(),
                'ranking_info': {
                    'total_cavalos': len(analises),
                    'melhor_cavalo': analises[0]['nome'] if analises else 'N/A',
                    'pior_cavalo': analises[-1]['nome'] if analises else 'N/A',
                    'diferenca_pontuacao': round(analises[0].get('pontuacao_final_ajustada', 0) - analises[-1].get('pontuacao_final_ajustada', 0), 2) if len(analises) > 1 else 0
                }
            }
            
            logger.info(f"Análise concluída com sucesso. Top 3: {[c['nome'] for c in analises[:3]]}")
            logger.info(f"Ranking: 1º {analises[0]['nome']} ({analises[0].get('pontuacao_final_ajustada', 0):.2f}), Último: {analises[-1]['nome']} ({analises[-1].get('pontuacao_final_ajustada', 0):.2f})")
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro na análise de cavalos: {str(e)}")
            return {'erro': f'Erro na análise: {str(e)}'}
    
    def _aplicar_ranking_comparativo(self, analises):
        """
        Aplica sistema de ranking comparativo entre cavalos para ajustar pontuações
        """
        try:
            if len(analises) <= 1:
                return analises
            
            # Calcular médias para normalização
            pontuacoes = [a.get('pontuacao_final', 0) for a in analises]
            media_pontuacao = sum(pontuacoes) / len(pontuacoes)
            max_pontuacao = max(pontuacoes)
            min_pontuacao = min(pontuacoes)
            
            for analise in analises:
                pontuacao_original = analise.get('pontuacao_final', 0)
                
                # Fator de ajuste baseado na posição relativa
                if max_pontuacao > min_pontuacao:
                    posicao_relativa = (pontuacao_original - min_pontuacao) / (max_pontuacao - min_pontuacao)
                else:
                    posicao_relativa = 0.5
                
                # Bonus/penalidade por fatores específicos
                bonus_comparativo = 0
                
                # Bonus por consistência superior
                consistencia = analise.get('consistencia', 0)
                if consistencia > 7:
                    bonus_comparativo += 0.2
                elif consistencia < 3:
                    bonus_comparativo -= 0.2
                
                # Bonus por momentum positivo
                momentum = analise.get('momentum', 0)
                if momentum > 7:
                    bonus_comparativo += 0.15
                elif momentum < 3:
                    bonus_comparativo -= 0.15
                
                # Bonus por jóquei elite em corrida competitiva
                joquei_score = analise.get('joquei_score', 0)
                if joquei_score >= 8 and len(analises) > 8:
                    bonus_comparativo += 0.1
                
                # Penalidade por dados incompletos em corrida competitiva
                dados_faltando = sum([1 for campo in ['official_rating', 'forma', 'peso', 'idade'] 
                                    if not analise.get(campo) or analise.get(campo) in ['N/A', 'Desconhecido', '']])
                if dados_faltando >= 2 and len(analises) > 5:
                    bonus_comparativo -= 0.1
                
                # Calcular pontuação final ajustada
                pontuacao_ajustada = pontuacao_original + bonus_comparativo
                analise['pontuacao_final_ajustada'] = round(pontuacao_ajustada, 2)
                analise['bonus_comparativo'] = round(bonus_comparativo, 2)
            
            return analises
            
        except Exception as e:
            logger.warning(f"Erro no ranking comparativo: {e}")
            # Em caso de erro, manter pontuações originais
            for analise in analises:
                analise['pontuacao_final_ajustada'] = analise.get('pontuacao_final', 0)
                analise['bonus_comparativo'] = 0
            return analises
    
    def _identificar_grupos_performance(self, analises):
        """
        Identifica grupos de performance (Elite, Bom, Médio, Fraco) baseado nas pontuações
        """
        try:
            if not analises:
                return analises
            
            pontuacoes = [a.get('pontuacao_final_ajustada', 0) for a in analises]
            max_pontuacao = max(pontuacoes)
            min_pontuacao = min(pontuacoes)
            
            # Definir thresholds para grupos
            if max_pontuacao > min_pontuacao:
                range_pontuacao = max_pontuacao - min_pontuacao
                threshold_elite = max_pontuacao - (range_pontuacao * 0.25)
                threshold_bom = max_pontuacao - (range_pontuacao * 0.50)
                threshold_medio = max_pontuacao - (range_pontuacao * 0.75)
            else:
                threshold_elite = threshold_bom = threshold_medio = max_pontuacao
            
            for analise in analises:
                pontuacao = analise.get('pontuacao_final_ajustada', 0)
                
                if pontuacao >= threshold_elite:
                    grupo = "🏆 Elite"
                    cor_grupo = "#FFD700"  # Dourado
                elif pontuacao >= threshold_bom:
                    grupo = "⭐ Bom"
                    cor_grupo = "#C0C0C0"  # Prata
                elif pontuacao >= threshold_medio:
                    grupo = "📊 Médio"
                    cor_grupo = "#CD7F32"  # Bronze
                else:
                    grupo = "⚠️ Fraco"
                    cor_grupo = "#808080"  # Cinza
                
                analise['grupo_performance'] = grupo
                analise['cor_grupo'] = cor_grupo
            
            return analises
            
        except Exception as e:
            logger.warning(f"Erro na identificação de grupos: {e}")
            for analise in analises:
                analise['grupo_performance'] = "📊 Médio"
                analise['cor_grupo'] = "#CD7F32"
            return analises
    
    def _gerar_estatisticas_aprimoradas(self, analises):
        """
        Gera estatísticas aprimoradas da corrida com análise comparativa
        """
        try:
            if not analises:
                return {}
            
            pontuacoes = [a.get('pontuacao_final_ajustada', 0) for a in analises]
            
            # Estatísticas básicas
            media_pontuacao = sum(pontuacoes) / len(pontuacoes)
            max_pontuacao = max(pontuacoes)
            min_pontuacao = min(pontuacoes)
            
            # Análise de distribuição
            grupos = {}
            for analise in analises:
                grupo = analise.get('grupo_performance', 'Médio')
                grupos[grupo] = grupos.get(grupo, 0) + 1
            
            # Identificar favoritos e outsiders
            favoritos = [a for a in analises if a.get('pontuacao_final_ajustada', 0) >= media_pontuacao + 1]
            outsiders = [a for a in analises if a.get('pontuacao_final_ajustada', 0) <= media_pontuacao - 1]
            
            # Análise de competitividade
            diferenca_primeiro_ultimo = max_pontuacao - min_pontuacao
            if diferenca_primeiro_ultimo <= 2:
                competitividade = "🔥 Muito Competitiva"
            elif diferenca_primeiro_ultimo <= 4:
                competitividade = "⚡ Competitiva"
            elif diferenca_primeiro_ultimo <= 6:
                competitividade = "📊 Moderada"
            else:
                competitividade = "📈 Desigual"
            
            return {
                'total_cavalos': len(analises),
                'media_pontuacao': round(media_pontuacao, 2),
                'max_pontuacao': round(max_pontuacao, 2),
                'min_pontuacao': round(min_pontuacao, 2),
                'diferenca_pontuacao': round(diferenca_primeiro_ultimo, 2),
                'competitividade': competitividade,
                'distribuicao_grupos': grupos,
                'total_favoritos': len(favoritos),
                'total_outsiders': len(outsiders),
                'favoritos': [{'nome': f['nome'], 'pontuacao': f.get('pontuacao_final_ajustada', 0)} for f in favoritos[:3]],
                'outsiders': [{'nome': o['nome'], 'pontuacao': o.get('pontuacao_final_ajustada', 0)} for o in outsiders[-3:]],
                'melhor_joquei': max(analises, key=lambda x: x.get('joquei_score', 0))['joquei'] if analises else 'N/A',
                'melhor_forma': max(analises, key=lambda x: x.get('forma_score', 0))['nome'] if analises else 'N/A',
                'maior_momentum': max(analises, key=lambda x: x.get('momentum', 0))['nome'] if analises else 'N/A'
            }
            
        except Exception as e:
            logger.warning(f"Erro nas estatísticas aprimoradas: {e}")
            return self._gerar_estatisticas(analises)  # Fallback para função original
    
    def _extrair_at_the_races(self, soup, url):
        """
        Extrai dados específicos do At The Races
        """
        try:
            dados = {
                'cavalos': [],
                'titulo_corrida': 'Corrida At The Races',
                'condicoes_pista': 'N/A',
                'clima': 'N/A'
            }
            
            # Buscar título da corrida
            titulo_elem = soup.find('h1') or soup.find('title')
            if titulo_elem:
                dados['titulo_corrida'] = titulo_elem.get_text(strip=True)
            
            # Buscar cavalos - At The Races usa diferentes padrões
            nomes_encontrados = set()
            
            # 1. Priorizar links específicos de cavalos com seletores melhorados
            cavalos_links = []
            
            # Seletores específicos do At The Races para cavalos confirmados
            seletores_atr = [
                'a[href*="/horse/"]',  # Links diretos de cavalos
                '.runner-name a',       # Nomes de corredores
                '.horse-name a',        # Nomes de cavalos
                '.selection-name a',    # Nomes de seleções
                'a.runner-link',        # Links de corredores
                '.card-entry a[href*="/horse/"]',  # Entradas de cartão
                '.racecard-runner a[href*="/horse/"]',  # Corredores do cartão
                '.runner a[href*="/horse/"]',  # Corredores genéricos
                'tr.runner a[href*="/horse/"]'  # Linhas de corredores em tabelas
            ]
            
            for seletor in seletores_atr:
                try:
                    elementos = soup.select(seletor)
                    if elementos:
                        cavalos_links.extend(elementos)
                        logger.info(f"At The Races - {len(elementos)} cavalos encontrados com: {seletor}")
                except Exception as e:
                    logger.debug(f"Erro no seletor {seletor}: {e}")
            
            # Remover duplicados mantendo ordem
            cavalos_unicos = []
            hrefs_vistos = set()
            for link in cavalos_links:
                href = link.get('href', '')
                if href and href not in hrefs_vistos:
                    cavalos_unicos.append(link)
                    hrefs_vistos.add(href)
            
            cavalos_links = cavalos_unicos
            logger.info(f"At The Races - Total de cavalos únicos encontrados: {len(cavalos_links)}")
            
            # Extrair nomes dos links de cavalos
            for elem in cavalos_links:
                nome = elem.get_text(strip=True)
                # Limpar o nome removendo códigos e sufixos
                nome_limpo = re.sub(r'^\d+\s*', '', nome)  # Remove números do início
                nome_limpo = re.sub(r'\s*\([A-Z]{2,4}\)\s*$', '', nome_limpo)  # Remove "(USA)" do final
                nome_limpo = re.sub(r'\s*\(-?\d+\)\s*$', '', nome_limpo)  # Remove "(-1)" do final
                nome_limpo = re.sub(r'\s*\(\d+\)\s*$', '', nome_limpo)  # Remove "(5)" do final
                # Remover caracteres não-quebráveis e normalizar espaços
                nome_limpo = re.sub(r'\xa0', ' ', nome_limpo)  # Remove espaços não-quebráveis
                nome_limpo = re.sub(r'\s+', ' ', nome_limpo)  # Normaliza múltiplos espaços
                nome_limpo = nome_limpo.strip()
                
                if nome_limpo and len(nome_limpo) > 2 and len(nome_limpo) < 30:
                    # Verificar se é um nome válido de cavalo
                    if (nome_limpo not in ['HORSE', 'Horse', 'View', 'More', 'Details', 'Profile', 'Form'] and 
                        not nome_limpo.endswith("'s") and  # Remove possessivos
                        not nome_limpo.lower().startswith('http') and
                        not nome_limpo.lower() in ['odds', 'jockey', 'trainer', 'form', 'rating'] and
                        any(c.isalpha() for c in nome_limpo)):
                        nomes_encontrados.add(nome_limpo)
            
            # Se ainda não encontrou cavalos suficientes, buscar em tabelas específicas
            if len(nomes_encontrados) < 5:
                tabelas = soup.find_all('table')
                for tabela in tabelas:
                    # Buscar apenas links dentro de células que podem conter nomes de cavalos
                    tds = tabela.find_all('td')
                    for td in tds:
                        links = td.find_all('a')
                        for link in links:
                            nome = link.get_text(strip=True)
                            nome_limpo = re.sub(r'^\d+\s*', '', nome)
                            nome_limpo = re.sub(r'\s*\([A-Z]{2,4}\)\s*$', '', nome_limpo)
                            nome_limpo = re.sub(r'\s*\(-?\d+\)\s*$', '', nome_limpo)
                            nome_limpo = nome_limpo.strip()
                            
                            if (nome_limpo and len(nome_limpo) > 3 and len(nome_limpo) < 25 and
                                nome_limpo not in ['View', 'More', 'Details', 'Profile', 'Form'] and
                                any(c.isalpha() for c in nome_limpo)):
                                nomes_encontrados.add(nome_limpo)
            
            # Converter nomes encontrados em dados de cavalos
            cavalos_processados = []
            nomes_adicionados = set()  # Garantir nomes únicos
            
            for i, nome in enumerate(sorted(nomes_encontrados)[:16]):  # Máximo 16 cavalos
                # Verificação adicional para evitar duplicados
                if nome in nomes_adicionados:
                    logger.warning(f"At The Races - Nome duplicado ignorado: {nome}")
                    continue
                
                cavalo = {
                    'nome': nome,
                    'posicao': len(cavalos_processados) + 1,
                    'odds': 'N/A',
                    'joquei': 'Jóquei N/A',
                    'treinador': 'N/A',
                    'peso': 'N/A',
                    'idade': 'N/A',
                    'forma': 'N/A',
                    'official_rating': 'N/A',
                    'draw': len(cavalos_processados) + 1
                }
                cavalos_processados.append(cavalo)
                nomes_adicionados.add(nome)
            
            dados['cavalos'] = cavalos_processados
            
            # Validação final - verificar se há duplicados
            nomes_finais = [c['nome'] for c in dados['cavalos']]
            if len(nomes_finais) != len(set(nomes_finais)):
                logger.error(f"At The Races - DUPLICADOS DETECTADOS na validação final: {nomes_finais}")
                # Remover duplicados mantendo apenas a primeira ocorrência
                cavalos_unicos = []
                nomes_vistos = set()
                for cavalo in dados['cavalos']:
                    if cavalo['nome'] not in nomes_vistos:
                        cavalos_unicos.append(cavalo)
                        nomes_vistos.add(cavalo['nome'])
                dados['cavalos'] = cavalos_unicos
                logger.info(f"At The Races - Duplicados removidos. Cavalos únicos: {len(dados['cavalos'])}")
            
            # APLICAR RANKING COMPARATIVO AOS DADOS EXTRAÍDOS
            if dados['cavalos']:
                try:
                    logger.info(f"At The Races: Aplicando ranking comparativo a {len(dados['cavalos'])} cavalos")
                    
                    # Analisar cada cavalo individualmente
                    analises = []
                    for i, cavalo in enumerate(dados['cavalos']):
                        analise = self._analisar_cavalo_individual(cavalo, i + 1)
                        analises.append(analise)
                    
                    # Aplicar ranking comparativo
                    analises_com_ranking = self._aplicar_ranking_comparativo(analises)
                    
                    # Ordenar por pontuação final ajustada (maior para menor)
                    analises_ordenadas = sorted(
                        analises_com_ranking, 
                        key=lambda x: x.get('pontuacao_final_ajustada', x.get('pontuacao_final', 0)), 
                        reverse=True
                    )
                    
                    # Atualizar posições finais e percentis
                    total_cavalos = len(analises_ordenadas)
                    for i, analise in enumerate(analises_ordenadas):
                        analise['posicao_final'] = i + 1
                        analise['percentil'] = ((total_cavalos - i) / total_cavalos) * 100
                    
                    # Identificar grupos de performance
                    analises_com_grupos = self._identificar_grupos_performance(analises_ordenadas)
                    
                    # Atualizar dados com cavalos rankeados
                    dados['cavalos'] = analises_com_grupos
                    dados['ranking_info'] = {
                        'total_cavalos': total_cavalos,
                        'metodo_ranking': 'comparativo_at_the_races',
                        'criterios': ['rating', 'forma', 'peso', 'joquei', 'treinador', 'odds', 'consistencia', 'momentum']
                    }
                    
                    logger.info(f"At The Races: Ranking aplicado com sucesso. Melhor cavalo: {dados['cavalos'][0]['nome']}")
                    
                except Exception as e:
                    logger.warning(f"Erro ao aplicar ranking no At The Races: {str(e)}")
                    # Em caso de erro, manter dados originais
                    pass
            
            logger.info(f"At The Races - Extraídos {len(dados['cavalos'])} cavalos únicos: {[c['nome'] for c in dados['cavalos']]}")
            return dados
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do At The Races: {str(e)}")
            return None
    
    def _extrair_racing_post(self, soup, url):
        """
        Extrai dados específicos do Racing Post com informações detalhadas
        """
        try:
            dados = {
                'cavalos': [],
                'titulo_corrida': 'Corrida Racing Post',
                'condicoes_pista': 'N/A',
                'clima': 'N/A'
            }
            
            # Buscar título da corrida
            titulo_elem = soup.find('h1') or soup.find('title')
            if titulo_elem:
                dados['titulo_corrida'] = titulo_elem.get_text(strip=True)
            
            # NOVA ABORDAGEM: Buscar por containers de corredores específicos do Racing Post
            runners_containers = soup.find_all('div', {'class': re.compile(r'RC-runnerRow')}) or soup.find_all('div', {'class': re.compile(r'RC-runnerPriceWrapper|js-diffusionHorsesList')})
            
            logger.info(f"Racing Post - Encontrados {len(runners_containers)} containers de corredores")
            
            cavalos_extraidos = []
            
            for container in runners_containers:
                try:
                    # Extrair nome do cavalo
                    nome_elem = (
                        container.find('a', {'class': re.compile(r'RC-runnerName')}) or
                        container.find('span', {'data-horsename': True}) or
                        container.find('a', href=re.compile(r'/profile/horse/'))
                    )
                    
                    if not nome_elem:
                        continue
                    
                    nome = nome_elem.get_text(strip=True)
                    if not nome or len(nome) < 2:
                        # Tentar pegar do atributo data-horsename
                        nome = container.get('data-diffusion-horsename', '')
                    
                    if not nome or len(nome) < 2:
                        continue
                    
                    # Limpar nome
                    nome_limpo = re.sub(r'^\d+\(\d+\)', '', nome).strip()
                    nome_limpo = re.sub(r'\s*\([A-Z]{2,4}\)\s*$', '', nome_limpo)
                    nome_limpo = re.sub(r'\s*\(-?\d+\)\s*$', '', nome_limpo)
                    nome_limpo = nome_limpo.strip()
                    
                    if not nome_limpo or len(nome_limpo) < 2:
                        continue
                    
                    # Extrair número do corredor
                    numero_elem = container.find('span', {'class': re.compile(r'RC-runnerNumber__no')})
                    numero = numero_elem.get_text(strip=True) if numero_elem else str(len(cavalos_extraidos) + 1)
                    
                    # Extrair jóquei
                    joquei = "Jóquei N/A"
                    # Buscar especificamente por elementos com data-order-jockey
                    joquei_elem = container.find('a', {'data-order-jockey': True})
                    if joquei_elem:
                        joquei_text = joquei_elem.get('data-order-jockey', '').strip()
                        if joquei_text and joquei_text != '-':
                            joquei = joquei_text
                    else:
                        # Fallback para outros seletores
                        joquei_elem = (
                            container.find('a', {'class': re.compile(r'RC-runnerInfo__name')}) or
                            container.find('a', {'class': re.compile(r'jockey|RC-runnerJockey')}) or
                            container.find('span', {'class': re.compile(r'jockey|RC-runnerJockey')})
                        )
                        if joquei_elem:
                            joquei_text = joquei_elem.get_text(strip=True)
                            if joquei_text and joquei_text != '-':
                                joquei = joquei_text
                    
                    # Extrair odds
                    odds = "N/A"
                    odds_elem = (
                        container.find('span', {'class': re.compile(r'RC-price|odds|price')}) or
                        container.find('div', {'class': re.compile(r'RC-price|odds|price')}) or
                        container.find('button', {'class': re.compile(r'price|odds')}) or
                        container.find('span', {'data-test-selector': re.compile(r'price|odds')})
                    )
                    if odds_elem:
                        odds_text = odds_elem.get_text(strip=True)
                        if odds_text and odds_text != '-' and odds_text != 'N/A':
                            odds = odds_text
                    
                    # Extrair peso
                    peso = "N/A"
                    peso_elem = (
                        container.find('span', {'class': re.compile(r'weight|RC-weight')}) or
                        container.find('div', {'class': re.compile(r'weight|RC-weight')})
                    )
                    if peso_elem:
                        peso_text = peso_elem.get_text(strip=True)
                        if peso_text and peso_text != '-':
                            peso = peso_text
                    
                    # Extrair treinador
                    treinador = "N/A"
                    # Buscar especificamente por elementos com data-order-trainer
                    treinador_elem = container.find('a', {'data-order-trainer': True})
                    if treinador_elem:
                        treinador_text = treinador_elem.get('data-order-trainer', '').strip()
                        if treinador_text and treinador_text != '-':
                            treinador = treinador_text
                    else:
                        # Fallback para outros seletores
                        treinador_elem = (
                            container.find('a', {'class': re.compile(r'trainer|RC-trainer')}) or
                            container.find('span', {'class': re.compile(r'trainer|RC-trainer')})
                        )
                        if treinador_elem:
                            treinador_text = treinador_elem.get_text(strip=True)
                            if treinador_text and treinador_text != '-':
                                treinador = treinador_text
                    
                    # Extrair official rating
                    rating = "N/A"
                    rating_elem = (
                        container.find('span', {'class': re.compile(r'rating|OR|official')}) or
                        container.find('div', {'class': re.compile(r'rating|OR|official')})
                    )
                    if rating_elem:
                        rating_text = rating_elem.get_text(strip=True)
                        if rating_text and rating_text.isdigit():
                            rating = rating_text
                    
                    cavalo_data = {
                        'nome': nome_limpo,
                        'joquei': joquei,
                        'odds': odds,
                        'peso': peso,
                        'idade': "N/A",
                        'forma': "N/A",
                        'official_rating': rating,
                        'draw': numero,
                        'treinador': treinador,
                        'historico_detalhado': []
                    }
                    
                    # Verificar se já não foi adicionado
                    if not any(c['nome'] == nome_limpo for c in cavalos_extraidos):
                        cavalos_extraidos.append(cavalo_data)
                        logger.debug(f"Racing Post - Cavalo extraído: {nome_limpo}")
                    
                except Exception as e:
                    logger.debug(f"Erro ao processar container: {e}")
                    continue
            
            # Se não encontrou cavalos com a nova abordagem, usar a abordagem anterior
            if not cavalos_extraidos:
                logger.info("Racing Post - Usando abordagem de fallback")
                
                # Buscar cavalos - Racing Post com seletores melhorados
                cavalos_links = []
                
                seletores_rp = [
                    'a[href*="/horses/"]',
                    'a[href*="/horse/"]',
                    'a[href*="/profile/horse/"]',
                    '.RC-runnerName',
                    '.rp-horseHoverTrigger',
                    '.rp-racecard-horse a',
                    '.rp-racecard-runner a',
                    '.horse-name a',
                    '.runner-name a'
                ]
                
                for seletor in seletores_rp:
                    try:
                        elementos = soup.select(seletor)
                        if elementos:
                            cavalos_links.extend(elementos)
                            logger.info(f"Racing Post - {len(elementos)} cavalos encontrados com: {seletor}")
                    except Exception as e:
                        logger.debug(f"Erro no seletor {seletor}: {e}")
                
                # Remover duplicados
                cavalos_unicos = []
                nomes_vistos = set()
                for link in cavalos_links:
                    nome = link.get_text(strip=True)
                    nome_limpo = re.sub(r'^\d+\(\d+\)', '', nome).strip()
                    nome_limpo = re.sub(r'\s*\([A-Z]{2,4}\)\s*$', '', nome_limpo)
                    nome_limpo = re.sub(r'\s*\(-?\d+\)\s*$', '', nome_limpo)
                    nome_limpo = nome_limpo.strip()
                    
                    if (nome_limpo and len(nome_limpo) > 2 and len(nome_limpo) < 30 and
                        nome_limpo not in nomes_vistos and
                        nome_limpo not in ['HORSE', 'Horse'] and
                        not nome_limpo.endswith("'s") and
                        any(c.isalpha() for c in nome_limpo)):
                        
                        cavalos_unicos.append({
                            'nome': nome_limpo,
                            'joquei': "Jóquei N/A",
                            'odds': "N/A",
                            'peso': "N/A",
                            'idade': "N/A",
                            'forma': "N/A",
                            'official_rating': "N/A",
                            'draw': len(cavalos_unicos) + 1,
                            'treinador': "N/A",
                            'historico_detalhado': []
                        })
                        nomes_vistos.add(nome_limpo)
                
                cavalos_extraidos = cavalos_unicos[:15]
            
            dados['cavalos'] = cavalos_extraidos[:15]  # Limitar a 15 cavalos
            
            # APLICAR RANKING COMPARATIVO AOS DADOS EXTRAÍDOS
            if dados['cavalos']:
                try:
                    logger.info(f"Racing Post: Aplicando ranking comparativo a {len(dados['cavalos'])} cavalos")
                    
                    # Analisar cada cavalo individualmente
                    analises = []
                    for i, cavalo in enumerate(dados['cavalos']):
                        analise = self._analisar_cavalo_individual(cavalo, i + 1)
                        analises.append(analise)
                    
                    # Aplicar ranking comparativo
                    analises_com_ranking = self._aplicar_ranking_comparativo(analises)
                    
                    # Ordenar por pontuação final ajustada (maior para menor)
                    analises_ordenadas = sorted(
                        analises_com_ranking, 
                        key=lambda x: x.get('pontuacao_final_ajustada', x.get('pontuacao_final', 0)), 
                        reverse=True
                    )
                    
                    # Atualizar posições finais e percentis
                    total_cavalos = len(analises_ordenadas)
                    for i, analise in enumerate(analises_ordenadas):
                        analise['posicao_final'] = i + 1
                        analise['percentil'] = ((total_cavalos - i) / total_cavalos) * 100
                    
                    # Identificar grupos de performance
                    analises_com_grupos = self._identificar_grupos_performance(analises_ordenadas)
                    
                    # Atualizar dados com cavalos rankeados
                    dados['cavalos'] = analises_com_grupos
                    dados['ranking_info'] = {
                        'total_cavalos': total_cavalos,
                        'metodo_ranking': 'comparativo_racing_post',
                        'criterios': ['rating', 'forma', 'peso', 'joquei', 'treinador', 'odds', 'consistencia', 'momentum']
                    }
                    
                    logger.info(f"Racing Post: Ranking aplicado com sucesso. Melhor cavalo: {dados['cavalos'][0]['nome']}")
                    
                except Exception as e:
                    logger.warning(f"Erro ao aplicar ranking no Racing Post: {str(e)}")
                    # Em caso de erro, manter dados originais
                    pass
            
            logger.info(f"Racing Post: Extraídos {len(dados['cavalos'])} cavalos")
            return dados if dados['cavalos'] else None
            
        except Exception as e:
            logger.warning(f"Erro ao extrair dados do Racing Post: {str(e)}")
            return None
    
    def _extrair_sporting_life(self, soup, url):
        """
        Extrai dados específicos do Sporting Life
        """
        try:
            dados = {
                'cavalos': [],
                'titulo_corrida': 'Corrida Sporting Life',
                'condicoes_pista': 'N/A',
                'clima': 'N/A'
            }
            
            # Buscar informações da corrida
            titulo_elem = soup.find('h1') or soup.find('title')
            if titulo_elem:
                dados['titulo_corrida'] = titulo_elem.get_text(strip=True)
            
            # Buscar condições da pista
            condicoes_elem = soup.find(text=re.compile(r'Going|Ground|Track'))
            if condicoes_elem:
                condicoes_text = condicoes_elem.strip().lower()
                if any(word in condicoes_text for word in ['firm', 'good', 'firme']):
                    dados['condicoes_pista'] = 'Firme'
                elif any(word in condicoes_text for word in ['soft', 'heavy', 'pesada']):
                    dados['condicoes_pista'] = 'Pesada'
                elif any(word in condicoes_text for word in ['yielding', 'cedente']):
                    dados['condicoes_pista'] = 'Cedente'
            
            # Buscar cavalos na tabela de resultados
            tabela = soup.find('table') or soup.find('div', class_=re.compile(r'runner|horse|result'))
            if tabela:
                linhas = tabela.find_all('tr')[1:] if tabela.find_all('tr') else []
                
                for linha in linhas[:15]:  # Limitar a 15 cavalos
                    colunas = linha.find_all(['td', 'th'])
                    if len(colunas) >= 3:
                        cavalo_data = {
                            'nome': colunas[1].get_text(strip=True) if len(colunas) > 1 else f"Cavalo {len(dados['cavalos']) + 1}",
                            'joquei': colunas[2].get_text(strip=True) if len(colunas) > 2 else "Jóquei N/A",
                            'odds': colunas[3].get_text(strip=True) if len(colunas) > 3 else "N/A",
                            'peso': colunas[4].get_text(strip=True) if len(colunas) > 4 else "N/A",
                            'idade': "N/A",
                            'forma': "N/A",
                            'official_rating': "N/A",
                            'draw': len(dados['cavalos']) + 1,
                            'treinador': "N/A",
                            'historico_detalhado': []
                        }
                        dados['cavalos'].append(cavalo_data)
            
            # APLICAR RANKING COMPARATIVO AOS DADOS EXTRAÍDOS
            if dados['cavalos']:
                try:
                    logger.info(f"Sporting Life: Aplicando ranking comparativo a {len(dados['cavalos'])} cavalos")
                    
                    # Analisar cada cavalo individualmente
                    analises = []
                    for i, cavalo in enumerate(dados['cavalos']):
                        analise = self._analisar_cavalo_individual(cavalo, i + 1)
                        analises.append(analise)
                    
                    # Aplicar ranking comparativo
                    analises_com_ranking = self._aplicar_ranking_comparativo(analises)
                    
                    # Ordenar por pontuação final ajustada (maior para menor)
                    analises_ordenadas = sorted(
                        analises_com_ranking, 
                        key=lambda x: x.get('pontuacao_final_ajustada', x.get('pontuacao_final', 0)), 
                        reverse=True
                    )
                    
                    # Atualizar posições finais e percentis
                    total_cavalos = len(analises_ordenadas)
                    for i, analise in enumerate(analises_ordenadas):
                        analise['posicao_final'] = i + 1
                        analise['percentil'] = ((total_cavalos - i) / total_cavalos) * 100
                    
                    # Identificar grupos de performance
                    analises_com_grupos = self._identificar_grupos_performance(analises_ordenadas)
                    
                    # Atualizar dados com cavalos rankeados
                    dados['cavalos'] = analises_com_grupos
                    dados['ranking_info'] = {
                        'total_cavalos': total_cavalos,
                        'metodo_ranking': 'comparativo_sporting_life',
                        'criterios': ['rating', 'forma', 'peso', 'joquei', 'treinador', 'odds', 'consistencia', 'momentum']
                    }
                    
                    logger.info(f"Sporting Life: Ranking aplicado com sucesso. Melhor cavalo: {dados['cavalos'][0]['nome']}")
                    
                except Exception as e:
                    logger.warning(f"Erro ao aplicar ranking no Sporting Life: {str(e)}")
                    # Em caso de erro, manter dados originais
                    pass
            
            return dados if dados['cavalos'] else None
            
        except Exception as e:
            logger.warning(f"Erro ao extrair dados do Sporting Life: {str(e)}")
            return None
    
    def _extrair_oddschecker(self, soup, url):
        """
        Extrai dados específicos do Oddschecker
        """
        try:
            dados = {
                'cavalos': [],
                'titulo_corrida': 'Corrida Oddschecker',
                'condicoes_pista': 'N/A',
                'clima': 'N/A'
            }
            
            # Buscar título da corrida
            titulo_elem = soup.find('h1') or soup.find('title')
            if titulo_elem:
                dados['titulo_corrida'] = titulo_elem.get_text(strip=True)
            
            # Buscar cavalos e odds
            cavalos_elem = soup.find_all('tr', class_=re.compile(r'runner|horse|selection'))
            
            for i, elem in enumerate(cavalos_elem[:15]):
                nome_elem = elem.find('a') or elem.find('span', class_=re.compile(r'name|horse'))
                odds_elem = elem.find('span', class_=re.compile(r'odds|price'))
                
                cavalo_data = {
                    'nome': nome_elem.get_text(strip=True) if nome_elem else f"Cavalo {i + 1}",
                    'joquei': "Jóquei N/A",
                    'odds': odds_elem.get_text(strip=True) if odds_elem else "N/A",
                    'peso': "N/A",
                    'idade': "N/A",
                    'forma': "N/A",
                    'official_rating': "N/A",
                    'draw': i + 1,
                    'treinador': "N/A",
                    'historico_detalhado': []
                }
                dados['cavalos'].append(cavalo_data)
            
            return dados if dados['cavalos'] else None
            
        except Exception as e:
            logger.warning(f"Erro ao extrair dados do Oddschecker: {str(e)}")
            return None
    
    def _extrair_betfair(self, soup, url):
        """
        Extrai dados específicos do Betfair
        """
        try:
            dados = {
                'cavalos': [],
                'titulo_corrida': 'Corrida Betfair',
                'condicoes_pista': 'N/A',
                'clima': 'N/A'
            }
            
            # Buscar título da corrida
            titulo_elem = soup.find('h1') or soup.find('title')
            if titulo_elem:
                dados['titulo_corrida'] = titulo_elem.get_text(strip=True)
            
            # Buscar cavalos na interface do Betfair
            cavalos_elem = soup.find_all('div', class_=re.compile(r'runner|selection|market-item'))
            
            for i, elem in enumerate(cavalos_elem[:15]):
                nome_elem = elem.find('span', class_=re.compile(r'name|runner-name'))
                odds_elem = elem.find('span', class_=re.compile(r'odds|price|back-price'))
                
                cavalo_data = {
                    'nome': nome_elem.get_text(strip=True) if nome_elem else f"Cavalo {i + 1}",
                    'joquei': "Jóquei N/A",
                    'odds': odds_elem.get_text(strip=True) if odds_elem else "N/A",
                    'peso': "N/A",
                    'idade': "N/A",
                    'forma': "N/A",
                    'official_rating': "N/A",
                    'draw': i + 1,
                    'treinador': "N/A",
                    'historico_detalhado': []
                }
                dados['cavalos'].append(cavalo_data)
            
            return dados if dados['cavalos'] else None
            
        except Exception as e:
            logger.warning(f"Erro ao extrair dados do Betfair: {str(e)}")
            return None

    def _extrair_timeform(self, soup, url):
        """
        Extrai dados específicos do Timeform
        """
        try:
            dados = {
                'cavalos': [],
                'titulo_corrida': 'Corrida Timeform',
                'condicoes_pista': 'N/A',
                'clima': 'N/A'
            }
            
            # Buscar título da corrida
            titulo_elem = soup.find('h1') or soup.find('title')
            if titulo_elem:
                dados['titulo_corrida'] = titulo_elem.get_text(strip=True)
            
            # Buscar cavalos - Timeform usa diferentes padrões
            cavalos_elem = soup.find_all('div', class_=re.compile(r'runner|horse|selection|tf-runner'))
            
            if not cavalos_elem:
                # Tentar seletores alternativos
                cavalos_elem = soup.find_all('tr', class_=re.compile(r'runner|horse|selection'))
            
            for i, elem in enumerate(cavalos_elem[:15]):
                nome_elem = (
                    elem.find('a', class_=re.compile(r'name|horse|runner')) or
                    elem.find('span', class_=re.compile(r'name|horse|runner')) or
                    elem.find('a') or
                    elem.find('span')
                )
                
                joquei_elem = elem.find('span', class_=re.compile(r'jockey|rider'))
                odds_elem = elem.find('span', class_=re.compile(r'odds|price'))
                peso_elem = elem.find('span', class_=re.compile(r'weight|wt'))
                rating_elem = elem.find('span', class_=re.compile(r'rating|tfr|timeform'))
                
                cavalo_data = {
                    'nome': nome_elem.get_text(strip=True) if nome_elem else f"Cavalo {i + 1}",
                    'joquei': joquei_elem.get_text(strip=True) if joquei_elem else "Jóquei N/A",
                    'odds': odds_elem.get_text(strip=True) if odds_elem else "N/A",
                    'peso': peso_elem.get_text(strip=True) if peso_elem else "N/A",
                    'idade': "N/A",
                    'forma': "N/A",
                    'official_rating': rating_elem.get_text(strip=True) if rating_elem else "N/A",
                    'draw': i + 1,
                    'treinador': "N/A",
                    'historico_detalhado': []
                }
                dados['cavalos'].append(cavalo_data)
            
            # APLICAR RANKING COMPARATIVO AOS DADOS EXTRAÍDOS
            if dados['cavalos']:
                try:
                    logger.info(f"Timeform: Aplicando ranking comparativo a {len(dados['cavalos'])} cavalos")
                    
                    # Analisar cada cavalo individualmente
                    analises = []
                    for i, cavalo in enumerate(dados['cavalos']):
                        analise = self._analisar_cavalo_individual(cavalo, i + 1)
                        analises.append(analise)
                    
                    # Aplicar ranking comparativo
                    analises_com_ranking = self._aplicar_ranking_comparativo(analises)
                    
                    # Ordenar por pontuação final ajustada (maior para menor)
                    analises_ordenadas = sorted(
                        analises_com_ranking, 
                        key=lambda x: x.get('pontuacao_final_ajustada', x.get('pontuacao_final', 0)), 
                        reverse=True
                    )
                    
                    # Atualizar posições finais e percentis
                    total_cavalos = len(analises_ordenadas)
                    for i, analise in enumerate(analises_ordenadas):
                        analise['posicao_final'] = i + 1
                        analise['percentil'] = ((total_cavalos - i) / total_cavalos) * 100
                    
                    # Identificar grupos de performance
                    analises_com_grupos = self._identificar_grupos_performance(analises_ordenadas)
                    
                    # Atualizar dados com cavalos rankeados
                    dados['cavalos'] = analises_com_grupos
                    dados['ranking_info'] = {
                        'total_cavalos': total_cavalos,
                        'metodo_ranking': 'comparativo_timeform',
                        'criterios': ['rating', 'forma', 'peso', 'joquei', 'treinador', 'odds', 'consistencia', 'momentum']
                    }
                    
                    logger.info(f"Timeform: Ranking aplicado com sucesso. Melhor cavalo: {dados['cavalos'][0]['nome']}")
                    
                except Exception as e:
                    logger.warning(f"Erro ao aplicar ranking no Timeform: {str(e)}")
                    # Em caso de erro, manter dados originais
                    pass
            
            return dados if dados['cavalos'] else None
            
        except Exception as e:
            logger.warning(f"Erro ao extrair dados do Timeform: {str(e)}")
            return None
    
    def _extrair_generico(self, soup, url):
        """
        Extração genérica que tenta encontrar nomes de cavalos em qualquer site
        """
        try:
            cavalos = []
            
            # Padrões melhorados para encontrar nomes de cavalos confirmados
            padroes_cavalos = [
                # Links específicos de cavalos
                'a[href*="/horse/"]', 'a[href*="/horses/"]',
                # Seletores CSS comuns
                '.horse-name', '.runner-name', '.selection-name',
                '.horse-name a', '.runner-name a', '.selection-name a',
                # Atributos de dados
                '[data-horse]', '[data-runner]', '[data-selection]',
                '[data-horse-name]', '[data-runner-name]',
                # Classes específicas
                '.horse', '.runner', '.selection',
                'a.horse-link', 'a.runner-link', 'a.selection-link',
                # Classes com wildcards
                '[class*="horse"]', '[class*="runner"]', '[class*="selection"]',
                # Tabelas de corrida
                'tr.horse-row', 'tr.runner-row', 'tr.selection-row',
                '.racecard-runner', '.racecard-horse',
                # Elementos de cartão de corrida
                '.card-entry', '.race-entry', '.runner-entry',
                # Nomes em tabelas
                'td.horse-name', 'td.runner-name', 'th.horse-name',
                # Spans com nomes
                'span.horse-name', 'span.runner-name', 'span.selection-name'
            ]
            
            nomes_encontrados = set()
            
            # Tentar cada padrão com logging
            for padrao in padroes_cavalos:
                try:
                    elementos = soup.select(padrao)
                    if elementos:
                        logger.info(f"Extração genérica - {len(elementos)} elementos encontrados com: {padrao}")
                        for elem in elementos:
                            # Tentar extrair texto do elemento ou de links filhos
                            texto = elem.get_text(strip=True)
                            if not texto and elem.find('a'):
                                texto = elem.find('a').get_text(strip=True)
                            
                            if texto and len(texto) > 2 and len(texto) < 50:
                                # Limpar o texto
                                texto_limpo = re.sub(r'^\d+\s*', '', texto)  # Remove números do início
                                texto_limpo = re.sub(r'\s*\([^)]+\)\s*$', '', texto_limpo)  # Remove parênteses
                                texto_limpo = re.sub(r'\xa0', ' ', texto_limpo)  # Remove espaços não-quebráveis
                                texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()  # Normaliza espaços
                                
                                # Filtrar nomes que parecem ser de cavalos
                                if texto_limpo and self._parece_nome_cavalo(texto_limpo):
                                    nomes_encontrados.add(texto_limpo)
                except Exception as e:
                    logger.debug(f"Erro no seletor genérico {padrao}: {e}")
            
            logger.info(f"Extração genérica - Total de nomes únicos encontrados: {len(nomes_encontrados)}")
            
            # Se não encontrou com CSS, tentar busca por texto
            if len(nomes_encontrados) < 3:
                # Buscar por padrões de texto que podem ser nomes de cavalos
                texto_completo = soup.get_text()
                linhas = texto_completo.split('\n')
                
                for linha in linhas:
                    linha = linha.strip()
                    if linha and len(linha) > 2 and len(linha) < 50:
                        if self._parece_nome_cavalo(linha):
                            nomes_encontrados.add(linha)
            
            # Converter para lista e limitar
            nomes_lista = list(nomes_encontrados)[:16]
            
            # Criar dados dos cavalos
            for i, nome in enumerate(nomes_lista):
                cavalo = {
                    'numero': str(i + 1),
                    'nome': nome,
                    'joquei': 'A confirmar',
                    'odds': 'N/A',
                    'official_rating': 'N/A',
                    'peso': 'N/A',
                    'idade': 'N/A',
                    'forma': 'N/A'
                }
                cavalos.append(cavalo)
            
            if len(cavalos) >= 3:
                dados = {
                    'fonte': 'Extração Genérica',
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'corrida': {
                        'nome': 'Corrida Extraída',
                        'distancia': 'N/A',
                        'tipo': 'N/A',
                        'premio': 'N/A'
                    },
                    'cavalos': cavalos
                }
                
                # APLICAR RANKING COMPARATIVO AOS DADOS EXTRAÍDOS
                try:
                    logger.info(f"Extração Genérica: Aplicando ranking comparativo a {len(cavalos)} cavalos")
                    
                    # Analisar cada cavalo individualmente
                    analises = []
                    for i, cavalo in enumerate(cavalos):
                        analise = self._analisar_cavalo_individual(cavalo, i + 1)
                        analises.append(analise)
                    
                    # Aplicar ranking comparativo
                    analises_com_ranking = self._aplicar_ranking_comparativo(analises)
                    
                    # Ordenar por pontuação final ajustada (maior para menor)
                    analises_ordenadas = sorted(
                        analises_com_ranking, 
                        key=lambda x: x.get('pontuacao_final_ajustada', x.get('pontuacao_final', 0)), 
                        reverse=True
                    )
                    
                    # Atualizar posições finais e percentis
                    total_cavalos = len(analises_ordenadas)
                    for i, analise in enumerate(analises_ordenadas):
                        analise['posicao_final'] = i + 1
                        analise['percentil'] = ((total_cavalos - i) / total_cavalos) * 100
                    
                    # Identificar grupos de performance
                    analises_com_grupos = self._identificar_grupos_performance(analises_ordenadas)
                    
                    # Atualizar dados com cavalos rankeados
                    dados['cavalos'] = analises_com_grupos
                    dados['ranking_info'] = {
                        'total_cavalos': total_cavalos,
                        'metodo_ranking': 'comparativo_generico',
                        'criterios': ['rating', 'forma', 'peso', 'joquei', 'treinador', 'odds', 'consistencia', 'momentum']
                    }
                    
                    logger.info(f"Extração Genérica: Ranking aplicado com sucesso. Melhor cavalo: {dados['cavalos'][0]['nome']}")
                    
                except Exception as e:
                    logger.warning(f"Erro ao aplicar ranking na extração genérica: {str(e)}")
                    # Em caso de erro, manter dados originais
                    pass
                
                return dados
            else:
                return None
                
        except Exception as e:
            logger.error(f"Erro na extração genérica: {str(e)}")
            return None
    
    def _parece_nome_cavalo(self, texto):
        """
        Verifica se um texto parece ser um nome de cavalo
        """
        # Filtros básicos
        if not texto or len(texto) < 3 or len(texto) > 35:
            return False
        
        # Não deve conter números demais
        if sum(c.isdigit() for c in texto) > len(texto) * 0.2:
            return False
        
        # Não deve ser apenas números ou símbolos
        if not any(c.isalpha() for c in texto):
            return False
        
        # Filtrar palavras comuns que não são nomes de cavalos
        palavras_excluir = {
            'odds', 'bet', 'win', 'place', 'show', 'back', 'lay',
            'price', 'form', 'jockey', 'trainer', 'weight', 'age',
            'rating', 'tips', 'news', 'results', 'race', 'card',
            'time', 'distance', 'going', 'class', 'prize', 'money',
            'favourite', 'outsider', 'runner', 'selection', 'horse',
            'today', 'tomorrow', 'yesterday', 'live', 'next', 'previous',
            'free', 'super', 'download', 'android', 'bookmaker', 'offers',
            'gambling', 'responsible', 'logo', 'worldwide', 'stakes', 'races',
            'thursday', 'friday', 'saturday', 'sunday', 'monday', 'tuesday',
            'wednesday', 'statistics', 'newspaper', 'quiz', 'doncaster',
            'newmarket', 'ascot', 'york', 'cheltenham', 'goodwood', 'maiden',
            'handicap', 'stakes', 'standard', 'partly', 'cloudy', 'tapeta',
            'september', 'october', 'november', 'december', 'january',
            'february', 'march', 'april', 'may', 'june', 'july', 'august'
        }
        
        texto_lower = texto.lower()
        if texto_lower in palavras_excluir:
            return False
        
        # Filtrar frases que contêm palavras excluídas
        palavras_texto = texto_lower.split()
        if any(palavra in palavras_excluir for palavra in palavras_texto):
            return False
        
        # Não deve conter URLs ou emails
        if '@' in texto or 'http' in texto or 'www.' in texto:
            return False
        
        # Não deve conter dois pontos (indicativo de horários ou labels)
        if ':' in texto:
            return False
        
        # Deve ter pelo menos uma letra maiúscula (nomes próprios)
        if not any(c.isupper() for c in texto):
            return False
        
        # Não deve ser muito genérico (uma palavra só muito comum)
        if len(palavras_texto) == 1 and len(texto) < 6:
            return False
        
        # Padrão típico de nomes de cavalos (geralmente 2-4 palavras)
        if len(palavras_texto) > 5:
            return False
        
        return True

# Instância global do extrator
extrator = ExtractorCavalos()

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/manifest.json')
def serve_manifest():
    """Serve o manifest PWA"""
    return send_file('manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def serve_sw():
    """Serve o service worker"""
    return send_file('sw.js', mimetype='application/javascript')

@app.route('/analisar', methods=['POST'])
def analisar():
    """Endpoint para análise de cavalos"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'erro': 'URL não fornecida'}), 400
        
        logger.info(f"Recebida solicitação de análise para: {url}")
        
        # Extrair e analisar dados
        dados_extraidos = extrator.extrair_dados_url(url)
        
        if 'erro' in dados_extraidos:
            return jsonify({'sucesso': False, 'erro': dados_extraidos.get('erro')}), 400
        
        # Analisar cavalos
        resultado = extrator.analisar_cavalos(dados_extraidos)
        
        if 'erro' in resultado:
            return jsonify({'sucesso': False, 'erro': resultado.get('erro')}), 400
        
        logger.info(f"Análise concluída com sucesso para {url}")
        
        # Retornar no formato esperado pela interface
        response_data = {
            'sucesso': True,
            'resultado': resultado
        }
        
        # Adicionar cabeçalhos para evitar cache
        response = jsonify(response_data)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        logger.error(f"Erro na análise: {str(e)}")
        return jsonify({'erro': f'Erro interno do servidor: {str(e)}'}), 500

if __name__ == '__main__':
    import os
    
    # Usar porta do ambiente (para hospedagem online) ou 5001 (local)
    port = int(os.environ.get('PORT', 5001))
    
    print("🐎 Iniciando Analisador de Cavalos...")
    if port == 5001:
        print("📱 Acesse: http://localhost:5001")
        print("🌐 Ou no celular: http://192.168.0.100:5001")
    else:
        print(f"🌐 Servidor online na porta: {port}")
    print("🔍 Cole uma URL de corrida de cavalos para análise")
    
    # Debug apenas em ambiente local
    debug_mode = port == 5001
    app.run(debug=debug_mode, host='0.0.0.0', port=port)