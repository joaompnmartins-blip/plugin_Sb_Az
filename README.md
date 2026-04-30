# Povoamentos Sb Az - Plugin para QGIS

Plugin QGIS para análise de dados de inventário florestal de Sobreiro (*Quercus suber*) e Azinheira (*Quercus ilex*), com cálculo de buffers de copa e classificação por classes de PAP (Perímetro à Altura do Peito).

## Funcionalidades

Este plugin processa dados de inventário florestal para criar múltiplas camadas de análise:

1. **LIMITE_COPAS** - Buffers individuais de copa de árvores baseados no raio de copa
2. **LIMITE_CONTINUIDADE** - Camada de buffer de 10m dissolvida com cálculo de área
3. **CLASSES_PAP** - Áreas ≥ 0.5 ha com estatísticas detalhadas de classes de PAP
4. **POVOAMENTO** - Áreas de alta densidade que cumprem limiares específicos
5. **PEQUENO_NUCLEO** - Pequenos núcleos < 0.5 ha que cumprem limiares de densidade
6. **OUTROS** - Áreas < 0.5 ha que não cumprem limiares de densidade

## Requisitos

- QGIS 3.0 ou superior
- Uma camada de pontos (qualquer nome) com:
  - Um campo **numérico** com os valores de PAP (Perímetro à Altura do Peito, em cm)
  - Um campo **numérico** com os valores de raio de copa — ou ausente, sendo criado automaticamente
  - Um campo **booleano/inteiro** de filtro de altura (True/1 = incluir, False/0/NULL = excluir)

> Os nomes dos campos e da camada são livres e configurados antes de cada análise através do diálogo de configuração.

## Instalação

### Método 1: Instalação Manual

1. Descarregue ou clone este repositório
2. Copie a pasta completa para o diretório de plugins do QGIS:
   - **Windows**: `C:\Users\{utilizador}\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
3. Reinicie o QGIS
4. Vá a **Extensões → Gerir e Instalar Extensões**
5. Procure "Povoamentos Sb Az" e marque a caixa para ativar

### Método 2: Instalação via ZIP

1. Crie um ficheiro ZIP da pasta do plugin
2. No QGIS, vá a **Extensões → Gerir e Instalar Extensões**
3. Clique em **"Instalar a partir de ZIP"**
4. Selecione o ficheiro ZIP e clique em "Instalar Extensão"

## Utilização

1. Carregue a sua camada de inventário florestal no projeto QGIS
2. Clique no botão **Povoamentos Sb Az** na barra de ferramentas, ou vá a **Extensões → Povoamentos Sb Az → Correr análise de povoamentos**
3. No **diálogo de configuração**, selecione a camada e os campos adequados
4. Clique em **OK** para iniciar a análise
5. Aguarde a conclusão — o progresso é mostrado em tempo real
6. O plugin cria até 6 novas camadas no projeto

## Diálogo de Configuração

Ao executar o plugin, é apresentado um diálogo com as seguintes opções:

| Campo | Descrição |
|---|---|
| **Camada de entrada** | Qualquer camada de pontos carregada no projeto QGIS (qualquer nome) |
| **Campo raio de copa** | Campo numérico existente com valores de raio de copa. Se selecionada a opção *"Calcular de PAP (criar campo)"*, o campo é criado automaticamente e calculado a partir da fórmula PAP |
| **Campo PAP** | Campo numérico com os valores de PAP. Usado para calcular o raio de copa (quando necessário) e sempre para classificação das árvores por classe |
| **Campo alt_1m** | Campo booleano/inteiro que indica se a árvore tem altura > 1m (True/1 = incluir na análise, False/0/NULL = excluir) |

### Comportamento do campo raio de copa

- **Campo existente selecionado**: os valores são usados diretamente para os buffers; o passo de cálculo é saltado automaticamente
- **"Calcular de PAP (criar campo)"**: o campo raio de copa é criado na camada caso não exista, e calculado a partir do campo PAP; o campo PAP é obrigatório

O diálogo recorda a última configuração utilizada.

## Camadas de Saída

### LIMITE_COPAS
Buffers individuais de copa usando o campo de raio de copa.

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
- **Povoamento**: "Sim" se os limiares de densidade forem cumpridos
- **Pov_Repescagem**: Classificação alternativa baseada em pap_class e densidade total

Classes de PAP:
- **under_30** (Classe 1): PAP < 30 cm
- **pap_30_79** (Classe 2): PAP 30–79 cm
- **pap_80_129** (Classe 3): PAP 80–129 cm
- **over_129** (Classe 4): PAP ≥ 130 cm

### POVOAMENTO
Subconjunto de CLASSES_PAP onde `Povoamento = "Sim"` OU `Pov_Repescagem = "Sim"`.

Limiares para Povoamento = "Sim":
- dens_under_30 > 50, OU
- dens_pap_30_79 > 30, OU
- dens_pap_80_129 > 20, OU
- dens_over_129 > 10

### PEQUENO_NUCLEO (áreas < 0.5 ha que cumprem limiares)
- **n_nucleo**: ID sequencial
- **area_ha**, **n_total**, **dens_arv**, **avg_PAP**, **pap_class**

Critério de inclusão: densidade > limiar da classe de PAP (50 / 30 / 20 / 10 árvores/ha).

### OUTROS (áreas < 0.5 ha que NÃO cumprem limiares)
- **n_outros**: ID sequencial
- **area_ha**, **n_total**, **dens_arv**, **avg_PAP**, **pap_class**

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
Se avg_PAP < 30:   pap_class = 1
Se avg_PAP < 80:   pap_class = 2
Se avg_PAP < 130:  pap_class = 3
Se avg_PAP ≥ 130:  pap_class = 4
```

## Fluxo de Trabalho

1. **Configuração**: selecionar camada e campos no diálogo
2. **Passo 1**: Calcular raio de copa a partir de PAP *(saltado automaticamente se o campo já tiver valores)*
3. **Passo 2**: Criar buffers de copa individuais
4. **Passo 3**: Criar camada de continuidade (buffer 10m dissolvido)
5. **Passo 3.5**: Separar áreas por limiar de 0.5 ha
6. **Passo 4**: Analisar classes de PAP (apenas áreas ≥ 0.5 ha)
7. **Passo 5**: Criar camada POVOAMENTO
8. **Passo 6**: Classificar pequenos núcleos em PEQUENO_NUCLEO ou OUTROS

## Resolução de Problemas

**Nenhuma camada de pontos no diálogo**
- Certifique-se de que tem pelo menos uma camada de pontos carregada no projeto QGIS

**Nenhum campo numérico disponível para PAP ou raio de copa**
- Verifique que os campos da camada são do tipo inteiro ou decimal

**Nenhum campo booleano/inteiro disponível para alt_1m**
- Se não existirem campos desse tipo, o diálogo mostra todos os campos como alternativa; selecione o mais adequado

**Erro durante o cálculo do raio de copa**
- Confirme que o campo PAP contém valores numéricos válidos e não está todo a NULL ou zero

**Nenhuma camada POVOAMENTO criada**
- Normal se nenhuma área ≥ 0.5 ha cumprir os limiares de densidade

**Nenhuma camada PEQUENO_NUCLEO ou OUTROS criada**
- Acontece se não existirem áreas < 0.5 ha, ou se todas caírem numa única categoria

**A análise demora muito tempo**
- A análise realiza junções espaciais para cada polígono; conjuntos de dados grandes podem demorar vários minutos
- Verifique o registo de mensagens do QGIS para acompanhar o progresso

## Suporte

Para problemas ou questões:
- Verifique o registo de mensagens do QGIS (**Ver → Painéis → Mensagens de Registo**)
- Procure mensagens do canal "Povoamentos Sb Az"
- Reporte problemas no repositório do projeto

## Licença

Este plugin é disponibilizado sob a GNU General Public License v3.0 ou posterior.

## Autor

João Miguel Martins 
joao_martins@yahoo.com

## Histórico de Versões

**4.0** - Diálogo de configuração flexível
- Seleção livre da camada de entrada (qualquer nome)
- Seleção livre dos campos PAP, raio de copa e alt_1m (qualquer nome)
- Criação automática do campo raio de copa se não existir na camada
- Passo de cálculo saltado automaticamente quando o raio de copa já tem valores
- Diálogo recorda a última configuração utilizada

**3.0** - Atualização major
- Separação de áreas por limiar de 0.5 ha antes da análise
- Aplicação de critérios de densidade a pequenos núcleos
- Nova camada OUTROS para áreas que não cumprem limiares
- Campo pap_class adicionado aos outputs

**2.0** - Alteração minor
- Pequenos ajustes no código

**1.0** - Lançamento inicial
- Cálculo de raio de copa a partir de PAP
- Análise multi-camada com buffers
- Estatísticas de classes de PAP
- Filtragem baseada em densidade
- Identificação de pequenos núcleos
