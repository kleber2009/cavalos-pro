# 🐎 Analisador de Cavalos - Aplicação Web

Uma aplicação web moderna para extrair e analisar dados de corridas de cavalos de qualquer URL.

## 🚀 Características

- **Interface Web Moderna**: Design responsivo e intuitivo
- **Extração Automática**: Suporte para múltiplos sites de corridas
- **Análise Inteligente**: Sistema de pontuação baseado em múltiplos fatores
- **Exportação de Dados**: Suporte para CSV e JSON
- **Dados de Exemplo**: Sistema de fallback com dados realistas

## 🌐 Sites Suportados

- Racing Post (racingpost.com)
- Timeform (timeform.com)
- At The Races (attheraces.com)
- Racing.com (racing.com)
- Extração genérica para outros sites

## 📋 Pré-requisitos

- Python 3.7+
- Pip (gerenciador de pacotes Python)

## 🔧 Instalação

1. **Clone ou baixe o projeto**
   ```bash
   cd projeto-cavalos
   ```

2. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

3. **Execute a aplicação**
   ```bash
   python app.py
   ```

4. **Acesse no navegador**
   ```
   http://localhost:5000
   ```

## 🎯 Como Usar

### 1. Análise de URL
1. Cole a URL de uma corrida de cavalos no campo de entrada
2. Clique em "🔍 Analisar"
3. Aguarde a extração e análise dos dados
4. Visualize os resultados na tabela

### 2. Interpretação dos Resultados

#### Sistema de Pontuação
- **Score Total**: 0-100 pontos baseado em:
  - **Jóquei (30%)**: Qualidade do jóquei
  - **Forma (30%)**: Performance recente
  - **Tendência OR (15%)**: Tendência do Official Rating
  - **Peso (10%)**: Peso carregado
  - **Tendência Peso (8%)**: Análise de peso
  - **Idade (5%)**: Idade do cavalo
  - **Performance Jóquei (2%)**: Jóquei + forma

#### Recomendações
- 🏆 **FORTE FAVORITO** (85+): Apostar com confiança
- ⭐ **BOA OPÇÃO** (75-84): Considerável para apostas
- ✅ **CONSIDERÁVEL** (65-74): Risco médio
- ⚠️ **RISCO MÉDIO** (55-64): Apostar com cautela
- ❌ **RISCO ALTO** (45-54): Evitar
- 🚫 **EVITAR** (<45): Muito alto risco

### 3. Exportação
- **📄 JSON**: Dados completos em formato JSON
- **📊 CSV**: Tabela para Excel/Google Sheets

## 🔍 Funcionalidades Técnicas

### Extração de Dados
- Web scraping inteligente
- Headers realistas para evitar bloqueios
- Sistema de fallback com dados de exemplo
- Análise avançada de tendências

### Análise Avançada
- Algoritmo de pontuação ponderada
- Análise de forma recente
- Avaliação de jóqueis famosos
- Consideração de peso e idade

### Interface
- Design responsivo (mobile-friendly)
- Animações suaves
- Feedback visual em tempo real
- Tratamento de erros elegante

## 📊 Exemplo de Uso

```
URL: https://www.racingpost.com/results/...

Resultados:
┌─────┬──────────────┬─────────────────┬──────┬───────┬─────────────────────────────┐
│ Pos │ Cavalo       │ Jóquei          │ Odds │ Score │ Recomendação                │
├─────┼──────────────┼─────────────────┼──────┼───────┼─────────────────────────────┤
│  1  │ Thunder Strike│ Frankie Dettori │ 2.50 │ 87.2  │ 🏆 FORTE FAVORITO          │
│  2  │ Royal Storm  │ Ryan Moore      │ 3.20 │ 82.1  │ ⭐ BOA OPÇÃO               │
│  3  │ Lightning Bolt│ William Buick   │ 4.50 │ 76.8  │ ⭐ BOA OPÇÃO               │
└─────┴──────────────┴─────────────────┴──────┴───────┴─────────────────────────────┘
```

## 🛠️ Estrutura do Projeto

```
projeto-cavalos/
├── app.py                 # Aplicação Flask principal
├── templates/
│   └── index.html         # Interface web
├── requirements.txt       # Dependências Python
└── README.md             # Documentação
```

## 🔧 Configuração Avançada

### Personalizar Jóqueis
Edite a lista `joqueis_famosos` em `app.py`:
```python
self.joqueis_famosos = [
    'Seu Jóquei Favorito',
    'Frankie Dettori',
    # ...
]
```

### Ajustar Sistema de Pontuação
Modifique os pesos em `_analisar_cavalo_individual()`:
```python
score_total = round(
    (score_odds * 0.35 +      # Peso das odds
     score_joquei * 0.25 +    # Peso do jóquei
     score_forma * 0.25 +     # Peso da forma
     score_peso * 0.10 +      # Peso do peso
     score_idade * 0.05), 1   # Peso da idade
)
```

## 🚨 Limitações

- Alguns sites podem bloquear requisições automatizadas
- A qualidade da extração varia por site
- Dados de exemplo são usados quando a extração falha
- Requer conexão com internet

## 🆘 Solução de Problemas

### Erro de Conexão
- Verifique sua conexão com internet
- Alguns sites podem estar temporariamente indisponíveis

### Dados Não Extraídos
- O sistema automaticamente usa dados de exemplo
- Verifique se a URL está correta

### Erro de Instalação
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 📝 Licença

Este projeto é para fins educacionais e de demonstração.

## 🤝 Contribuição

Sugestões e melhorias são bem-vindas!

---

**Desenvolvido com ❤️ para entusiastas de corridas de cavalos**