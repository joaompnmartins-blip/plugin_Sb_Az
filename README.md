# Povoamentos Sb Az - Plugin para QGIS

Plugin QGIS para análise de dados de inventário florestal de Sobreiro (Quercus suber) e Azinheira (Quercus ilex), com cálculo de buffers de copa e classificação por classes de PAP (Perímetro à Altura do Peito).

## Funcionalidades

Este plugin processa dados de inventário florestal para criar múltiplas camadas de análise:

1. **LIMITE_COPAS** - Buffers individuais de copa de árvores baseados no raio de copa calculado
2. **LIMITE_CONTINUIDADE** - Camada de buffer de 10m dissolvida com cálculo de área
3. **CLASSES_PAP** - Áreas ≥ 0.5 ha com estatísticas detalhadas de classes de PAP
4. **POVOAMENTO** - Áreas de alta densidade que cumprem limiares específicos
5. **PEQUENO_NUCLEO** - Pequenos núcleos < 0.5 ha que cumprem limiares de densidade
6. **OUTROS** - Áreas < 0.5 ha que não cumprem limiares de densidade

## Requisitos

- QGIS 3.0 ou superior
- Uma camada de pontos com o nome **"SB_AZ"** contendo os seguintes campos:
  - **PAP** (numérico) - Perímetro à Altura do Peito em centímetros
  - **raio_copa** (numérico) - Campo para raio de copa calculado (pode estar vazio)
  - **alt_1m** (booleano/numérico) - Campo de filtro para árvores > 1m altura (True/1 = incluir, False/0/NULL = excluir)

## Instalação

### Método 1: Instalação Manual

1. Descarregue ou clone este repositório
2. Copie a pasta completa `povoamentos_sb_az` para o diretório de plugins do QGIS:
   - **Windows**: `C:\Users\{utilizador}\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`

3. Reinicie o QGIS
4. Vá a **Extensões → Gerir e Instalar Extensões**
5. Procure "Povoamentos Sb Az" e marque a caixa para ativar

### Método 2: Instalação via ZIP

1. Crie um ficheiro ZIP da pasta `povoamentos_sb_az`
2. No QGIS, vá a **Extensões → Gerir e Instalar Extensões**
3. Clique em **"Instalar a partir de ZIP"**
4. Selecione o ficheiro ZIP e clique em "Instalar Extensão"

## Utilização

1. Carregue a sua camada de inventário florestal (deve ter o nome "SB_AZ")
2. Certifique-se de que os campos obrigatórios existem e contêm dados válidos
3. Clique no botão **Povoamentos Sb Az** na barra de ferramentas, ou vá a **Extensões → Povoamentos Sb Az → Correr análise de povoamentos**
4. Confirme a operação quando solicitado
5. Aguarde a conclusão da análise (o progresso será mostrado)
6. O plugin criará até 6 novas camadas no seu projeto

## Camadas de Saída

### LIMITE_COPAS
Buffers individuais de copa de árvores utilizando o campo calculado `raio_copa`.
- Apenas árvores com `alt_1m = True/1` são incluídas

### LIMITE_CONTINUIDADE
Buffer de 10m em torno das copas dissolvidas, dividido em polígonos individuais.
- **area_ha**: Área em hectares

### CLASSES_PAP (áreas ≥ 0.5 ha)
Análise detalhada de classificação de PAP para áreas grandes:
- **area_ha**: Área em hectares
- **n_[classe]**: Número de árvores por classe de PAP
- **avg_[classe]**: PAP médio por classe
- **dens_[classe]**: Densidade de árvores (árvores/ha) por classe
- **n_total**: Número total de árvores
- **avg_total**: PAP médio total
- **dens_total**: Densidade total de árvores
- **pap_class**: Classe de PAP dominante (1-4)
- **Povoamento**: "Sim" se os limiares de densidade forem cumpridos, "Não" caso contrário
- **Pov_Repescagem**: Classificação alternativa baseada em pap_class e densidade total

Classes de PAP:
- **under_30** (Classe 1): PAP < 30 cm
- **pap_30_79** (Classe 2): PAP 30-79 cm
- **pap_80_129** (Classe 3): PAP 80-129 cm
- **over_129** (Classe 4): PAP ≥ 130 cm

### POVOAMENTO
Subconjunto de CLASSES_PAP onde `Povoamento = "Sim"` OU `Pov_Repescagem = "Sim"` (áreas de alta densidade).

Limiares para Povoamento = "Sim":
- dens_under_30 > 50 OU
- dens_pap_30_79 > 30 OU
- dens_pap_80_129 > 20 OU
- dens_over_129 > 10

### PEQUENO_NUCLEO (áreas < 0.5 ha que cumprem limiares)
Pequenos núcleos que cumprem os mesmos critérios de densidade do POVOAMENTO:
- **n_nucleo**: ID sequencial
- **area_ha**: Área em hectares
- **n_total**: Número total de árvores
- **dens_arv**: Densidade de árvores (árvores/ha)
- **avg_PAP**: Valor médio de PAP
- **pap_class**: Classe de PAP (1-4)

Critério de inclusão: A densidade deve exceder o limiar correspondente à sua classe de PAP:
- Classe 1: densidade > 50 árvores/ha
- Classe 2: densidade > 30 árvores/ha
- Classe 3: densidade > 20 árvores/ha
- Classe 4: densidade > 10 árvores/ha

### OUTROS (áreas < 0.5 ha que NÃO cumprem limiares)
Pequenas áreas que não atingem os limiares de densidade:
- **n_outros**: ID sequencial
- **area_ha**: Área em hectares
- **n_total**: Número total de árvores
- **dens_arv**: Densidade de árvores (árvores/ha)
- **avg_PAP**: Valor médio de PAP
- **pap_class**: Classe de PAP (1-4)

Estas áreas representam manchas dispersas ou núcleos não produtivos.

## Fórmulas

### Cálculo do Raio de Copa
```
raio_copa = ((PAP ^ 0.6849) * 0.299) / 2
```

### Cálculo de Densidade
```
densidade = número_de_árvores / área_em_hectares
```

### Classificação de PAP
```
Se avg_PAP < 30:     pap_class = 1
Se avg_PAP < 80:     pap_class = 2
Se avg_PAP < 130:    pap_class = 3
Se avg_PAP ≥ 130:    pap_class = 4
```

## Fluxo de Trabalho

1. **Passo 1**: Calcular raio de copa a partir de PAP
2. **Passo 2**: Criar buffers de copa individuais
3. **Passo 3**: Criar camada de continuidade (buffer 10m dissolvido)
4. **Passo 3.5**: Separar áreas por limiar de 0.5 ha
5. **Passo 4**: Analisar classes de PAP (apenas áreas ≥ 0.5 ha)
6. **Passo 5**: Criar camada POVOAMENTO (áreas produtivas ≥ 0.5 ha)
7. **Passo 6**: Classificar pequenos núcleos (< 0.5 ha) em PEQUENO_NUCLEO ou OUTROS

## Resolução de Problemas

**Erro: Camada 'SB_AZ' não encontrada**
- Certifique-se de que a sua camada de pontos se chama exatamente "SB_AZ"

**Erro: Campo 'PAP' não encontrado**
- Garanta que a sua camada tem um campo chamado "PAP" com valores numéricos

**Erro: Campo 'raio_copa' não encontrado**
- Adicione um campo numérico chamado "raio_copa" à sua camada (pode estar vazio)

**Erro: Campo 'alt_1m' não encontrado**
- Adicione um campo chamado "alt_1m" (tipo booleano ou numérico)
- Use valores: True/1 para incluir, False/0/NULL para excluir

**Nenhuma camada POVOAMENTO criada**
- Isto é normal se nenhuma área cumprir os limiares de densidade

**Nenhuma camada PEQUENO_NUCLEO ou OUTROS criada**
- Isto acontece se não existirem áreas < 0.5 ha
- Ou se todas as áreas pequenas caírem numa única categoria

**A análise demora muito tempo**
- A análise realiza junções espaciais para cada polígono
- Conjuntos de dados grandes podem demorar vários minutos a processar
- Verifique a caixa de diálogo de progresso para ver o estado

## Suporte

Para problemas, questões ou sugestões:
- Verifique o registo de mensagens do QGIS (Ver → Painéis → Mensagens de Registo)
- Procure mensagens "Povoamentos Sb Az"
- Reporte problemas no repositório do projeto

## Licença

Este plugin é disponibilizado sob a GNU General Public License v3.0 ou posterior.

## Autor

Your Name
your.email@example.com

## Histórico de Versões

**2.0** - Atualização major
- Separação de áreas por limiar de 0.5 ha antes da análise
- Aplicação de critérios de densidade a pequenos núcleos
- Nova camada OUTROS para áreas que não cumprem limiares
- Campo pap_class adicionado aos outputs
- Melhorias na documentação

**1.0** - Lançamento inicial
- Cálculo de raio de copa a partir de PAP
- Análise multi-camada com buffers
- Estatísticas de classes de PAP
- Filtragem baseada em densidade
- Identificação de pequenos núcleos
