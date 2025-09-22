#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para integrar o algoritmo melhorado V2.0 no app principal
Substitui o algoritmo atual pelas melhorias identificadas na análise de Southwell
"""

import shutil
import os
from datetime import datetime

def fazer_backup_app():
    """
    Faz backup do app.py atual antes das modificações
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"app_backup_{timestamp}.py"
    
    try:
        shutil.copy2("app.py", backup_path)
        print(f"✅ Backup criado: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        return None

def integrar_algoritmo_v2():
    """
    Integra o algoritmo V2.0 no app principal
    """
    print("🔄 Iniciando integração do algoritmo V2.0...")
    
    # 1. Fazer backup
    backup_path = fazer_backup_app()
    if not backup_path:
        print("❌ Falha ao criar backup. Abortando integração.")
        return False
    
    try:
        # 2. Ler o app.py atual
        with open("app.py", "r", encoding="utf-8") as f:
            conteudo_app = f.read()
        
        # 3. Ler o algoritmo V2.0
        with open("algoritmo_melhorado_v2.py", "r", encoding="utf-8") as f:
            conteudo_v2 = f.read()
        
        # 4. Extrair a classe AnalisadorCavalosV2
        inicio_classe = conteudo_v2.find("class AnalisadorCavalosV2:")
        if inicio_classe == -1:
            print("❌ Classe AnalisadorCavalosV2 não encontrada")
            return False
        
        # Encontrar o final da classe (próxima definição de classe ou função no nível raiz)
        linhas_v2 = conteudo_v2[inicio_classe:].split('\n')
        classe_v2_linhas = []
        
        for i, linha in enumerate(linhas_v2):
            if i == 0:  # Primeira linha (class AnalisadorCavalosV2:)
                classe_v2_linhas.append(linha)
            elif linha.startswith('class ') or linha.startswith('def ') or linha.startswith('if __name__'):
                break  # Fim da classe
            else:
                classe_v2_linhas.append(linha)
        
        classe_v2_codigo = '\n'.join(classe_v2_linhas)
        
        # 5. Adicionar import no início do app.py (após os imports existentes)
        imports_adicionar = """
# Importar algoritmo melhorado V2.0
from datetime import datetime
import math
"""
        
        # 6. Encontrar onde inserir a nova classe no app.py
        # Inserir após a classe ExtractorCavalos
        pos_inserir = conteudo_app.find("class ExtractorCavalos:")
        if pos_inserir == -1:
            print("❌ Classe ExtractorCavalos não encontrada")
            return False
        
        # Encontrar o final da classe ExtractorCavalos
        linhas_app = conteudo_app.split('\n')
        linha_inicio_extractor = None
        
        for i, linha in enumerate(linhas_app):
            if "class ExtractorCavalos:" in linha:
                linha_inicio_extractor = i
                break
        
        if linha_inicio_extractor is None:
            print("❌ Não foi possível localizar a classe ExtractorCavalos")
            return False
        
        # Encontrar o final da classe ExtractorCavalos
        linha_fim_extractor = None
        for i in range(linha_inicio_extractor + 1, len(linhas_app)):
            linha = linhas_app[i]
            if linha.startswith('class ') or linha.startswith('@app.route') or linha.startswith('if __name__'):
                linha_fim_extractor = i
                break
        
        if linha_fim_extractor is None:
            linha_fim_extractor = len(linhas_app)
        
        # 7. Inserir a nova classe
        linhas_modificadas = (
            linhas_app[:linha_fim_extractor] + 
            ['', '# =' * 50, '# ALGORITMO MELHORADO V2.0', '# =' * 50, ''] +
            classe_v2_codigo.split('\n') +
            ['', '# =' * 50, ''] +
            linhas_app[linha_fim_extractor:]
        )
        
        # 8. Modificar o método de análise para usar o V2.0
        conteudo_modificado = '\n'.join(linhas_modificadas)
        
        # Substituir chamadas do algoritmo antigo pelo V2.0
        substituicoes = [
            # Adicionar instanciação do AnalisadorV2
            ("def extrair_dados_url(self, url):", 
             "def extrair_dados_url(self, url):\n        # Instanciar algoritmo V2.0\n        self.analisador_v2 = AnalisadorCavalosV2()"),
            
            # Substituir análise individual
            ("analise = self._analisar_cavalo_individual(cavalo, i + 1)",
             "# Usar algoritmo V2.0 para análise\n                        analise_v2 = self.analisador_v2.analisar_cavalo(cavalo)\n                        analise = self._converter_analise_v2(analise_v2, cavalo, i + 1)")
        ]
        
        for buscar, substituir in substituicoes:
            conteudo_modificado = conteudo_modificado.replace(buscar, substituir)
        
        # 9. Adicionar método de conversão
        metodo_conversao = '''
    def _converter_analise_v2(self, analise_v2, cavalo_original, posicao):
        """
        Converte resultado do AnalisadorV2 para formato compatível com o app
        """
        return {
            'nome': cavalo_original.get('nome', ''),
            'joquei': cavalo_original.get('joquei', 'Desconhecido'),
            'odds': cavalo_original.get('odds', 'N/A'),
            'peso': cavalo_original.get('peso', 'N/A'),
            'idade': cavalo_original.get('idade', 'N/A'),
            'forma': cavalo_original.get('forma', ''),
            'official_rating': cavalo_original.get('official_rating', 'N/A'),
            'draw': cavalo_original.get('draw', posicao),
            'treinador': cavalo_original.get('treinador', 'Desconhecido'),
            'posicao': posicao,
            'pontuacao_final': analise_v2['score_total'],
            'categoria': analise_v2['categoria'],
            'recomendacao': analise_v2['recomendacao'],
            'fatores_positivos': analise_v2['fatores_positivos'],
            'fatores_negativos': analise_v2['fatores_negativos'],
            'confianca': analise_v2['confianca'],
            'algoritmo_versao': 'V2.0_Melhorado',
            'detalhes_v2': {
                'score_forma_recente': analise_v2['detalhes']['score_forma_recente'],
                'score_joquei': analise_v2['detalhes']['score_joquei'],
                'score_condicoes': analise_v2['detalhes']['score_condicoes'],
                'bonus_outsider': analise_v2['detalhes']['bonus_outsider'],
                'is_value_bet': analise_v2['is_value_bet'],
                'is_dark_horse': analise_v2['is_dark_horse']
            }
        }
'''
        
        # Inserir método de conversão antes do final da classe ExtractorCavalos
        pos_fim_classe = conteudo_modificado.rfind("def extrair_dados_url")
        if pos_fim_classe != -1:
            # Encontrar o início da linha
            inicio_linha = conteudo_modificado.rfind('\n', 0, pos_fim_classe) + 1
            conteudo_modificado = (
                conteudo_modificado[:inicio_linha] + 
                metodo_conversao + '\n' +
                conteudo_modificado[inicio_linha:]
            )
        
        # 10. Salvar o arquivo modificado
        with open("app.py", "w", encoding="utf-8") as f:
            f.write(conteudo_modificado)
        
        print("✅ Algoritmo V2.0 integrado com sucesso!")
        print(f"📁 Backup salvo em: {backup_path}")
        print("\n🎯 Melhorias aplicadas:")
        print("   • Algoritmo V2.0 com pesos ajustados")
        print("   • Detecção de value bets e dark horses")
        print("   • Análise de forma recente melhorada")
        print("   • Sistema de categorização avançado")
        print("   • Compatibilidade mantida com interface atual")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante integração: {e}")
        # Restaurar backup em caso de erro
        if backup_path and os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, "app.py")
                print(f"🔄 Backup restaurado: {backup_path}")
            except:
                print("❌ Falha ao restaurar backup")
        return False

def main():
    """
    Função principal
    """
    print("🏇 INTEGRAÇÃO DO ALGORITMO MELHORADO V2.0")
    print("=" * 50)
    
    # Verificar se os arquivos necessários existem
    if not os.path.exists("app.py"):
        print("❌ Arquivo app.py não encontrado")
        return
    
    if not os.path.exists("algoritmo_melhorado_v2.py"):
        print("❌ Arquivo algoritmo_melhorado_v2.py não encontrado")
        return
    
    # Confirmar integração
    resposta = input("\n⚠️  Deseja integrar o algoritmo V2.0 no app principal? (s/N): ")
    if resposta.lower() not in ['s', 'sim', 'y', 'yes']:
        print("❌ Integração cancelada pelo usuário")
        return
    
    # Executar integração
    sucesso = integrar_algoritmo_v2()
    
    if sucesso:
        print("\n🎉 INTEGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("\n📋 Próximos passos:")
        print("   1. Reiniciar o servidor (Ctrl+C e python app.py)")
        print("   2. Testar uma análise de corrida")
        print("   3. Verificar se as melhorias estão funcionando")
        print("   4. Comparar resultados com versão anterior")
    else:
        print("\n❌ FALHA NA INTEGRAÇÃO")
        print("   • Verifique os logs de erro acima")
        print("   • O backup foi restaurado automaticamente")

if __name__ == "__main__":
    main()