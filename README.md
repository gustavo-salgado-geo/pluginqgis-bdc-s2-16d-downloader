# 🛰️ BDC Downloader — Sentinel-2/MSI L2A | LCF 16 dias

Plugin para **QGIS** que permite buscar, baixar e processar imagens da coleção **Sentinel-2 16 dias** disponibilizadas pelo [Brazil Data Cube (BDC)](https://data.inpe.br/bdc/stac/v1/) do INPE, diretamente na interface do QGIS.

---

## 📋 Descrição

O plugin se conecta à API STAC do Brazil Data Cube e oferece quatro opções de processamento para mosaicos Sentinel-2 (coleção `S2-16D-2`), permitindo desde a visualização rápida via VRT até o download de bandas individuais e geração de máscara vetorial de nuvens.

---

## ✨ Funcionalidades

### Aba 1 — Download e Geração de Dados

| Opção | Descrição |
|-------|-----------|
| **Opção 1** | Cria um VRT da composição RGB (B11/B08/B04) diretamente via `/vsicurl`, sem download local — ideal para visualização rápida |
| **Opção 2** | Realiza o download da composição RGB em 8 bits (B11/B08/B04) com normalização radiométrica + download da banda **PROVENANCE** |
| **Opção 3** | Download de bandas individuais selecionadas pelo usuário (B01–B12, NDVI, EVI, NBR, SCL) |
| **Opção 4** | Gera uma **máscara vetorial de nuvens** (GeoPackage `.gpkg`) a partir da banda SCL, com dissolução e filtragem por área mínima |

### Aba 2 — Pesquisa de Datas da Coleção

- Consulta as datas disponíveis na coleção S2-16D-2 para um tile e período informados
- Exibe as datas encontradas no formato `DD/MM/AAAA`

---

## 🔧 Requisitos

- **QGIS** 3.x
- **Python** 3.x (incluso no QGIS)

### Dependências Python

```
numpy
scipy
requests
pystac-client
gdal (osgeo)
```

> As bibliotecas `gdal`, `numpy` e `PyQt5` geralmente já estão incluídas na instalação padrão do QGIS. Instale as demais via `pip` no ambiente Python do QGIS, se necessário:
>
> ```bash
> pip install pystac-client requests scipy
> ```

---

## 🚀 Instalação

1. Copie a pasta do plugin (contendo `main.py` e `icon.png`) para o diretório de plugins do QGIS:
   - **Linux/macOS:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`

2. No QGIS, vá em **Plugins → Gerenciar e Instalar Plugins → Instalados** e ative o plugin **BDC Downloader S2 16D**.

3. O plugin aparecerá no menu **BiomasBR - Amazônia** e na barra de ferramentas.

---

## 🖥️ Como usar

### Campos de entrada (Aba 1)

- **Lista de Tiles BDC:** informe um ou mais tiles no formato `BBBPPP` (ex: `003016`, `032010`), separados por vírgula ou espaço.
- **Data da Coleção:** informe a data no formato `DD/MM/AAAA` (ex: `15/08/2023`).
- **Pasta de destino:** selecione o diretório onde os arquivos serão salvos.

### Composição RGB padrão

As opções 1 e 2 utilizam a composição **R=B11 / G=B08 / B=B04**, que realça vegetação e permite boa discriminação de uso e cobertura do solo.

### Máscara de Nuvens (Opção 4)

A máscara é gerada a partir dos seguintes valores da banda **SCL** (Scene Classification Layer):

| Valor SCL | Classe |
|-----------|--------|
| 3 | Sombra de nuvem |
| 8 | Nuvem média probabilidade |
| 9 | Nuvem alta probabilidade |
| 10 | Cirrus |

- Polígonos com área inferior a **10.000 m²** são descartados automaticamente.
- O resultado é salvo como **GeoPackage** (`.gpkg`) e carregado automaticamente no QGIS.

### Pesquisa de datas (Aba 2)

1. Informe um tile no formato `BBBPPP`.
2. Defina o intervalo de datas usando os seletores de calendário.
3. Clique em **🔍 Buscar Datas no Servidor**.

---

## 📁 Estrutura do Projeto

```
bdc_downloader_s216d/
├── main.py       # Código principal do plugin
├── icon.png      # Ícone exibido na barra de ferramentas do QGIS
└── README.md     # Este arquivo
```

---

## 🌐 Fonte dos Dados

- **STAC API:** [https://data.inpe.br/bdc/stac/v1/](https://data.inpe.br/bdc/stac/v1/)
- **Coleção:** `S2-16D-2` (Sentinel-2 mosaico de 16 dias, disponível a partir de 01/01/2017)
- **Provedor:** [Brazil Data Cube — INPE](https://brazildatacube.org/)

---

## 📌 Observações

- O plugin foi desenvolvido para o menu **BiomasBR - Amazônia** e é voltado ao monitoramento de biomas brasileiros.
- O download das bandas é feito diretamente da infraestrutura do BDC/INPE, sendo necessária conexão à internet.
- Na Opção 1 (VRT), nenhum arquivo é baixado localmente — a leitura ocorre via protocolo `/vsicurl`.

---

## 📄 Licença

Projeto de uso interno. Consulte a equipe responsável para informações sobre redistribuição e uso.
