# 🏗️ Arquitectura del Sistema

## 📊 Flujo Completo Diario

```
┌─────────────────────────────────────────────────────────────────┐
│                    CADA DÍA A LAS 7:00 AM UTC                  │
│                   (vía GitHub Actions)                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ GITHUB  │
                    │ ACTIONS │
                    └────┬────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐      ┌────▼────┐     ┌────▼────┐
   │ DESCARGAR│      │ DOWNLOAD │     │ CONFIGURE│
   │  PYTHON  │      │ DEPS     │     │ ENV VARS │
   │  3.11    │      │ (pip)    │     │          │
   └────┬────┘      └────┬────┘     └────┬────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                    ┌────▼─────────────────┐
                    │ RUN DAILY_UPDATE.PY  │
                    └────┬─────────────────┘
                         │
        ┌────────────────┼────────────────────────────────────┐
        │                │                                    │
   ┌────▼─────┐     ┌────▼─────┐      ┌────────▼──────┐
   │ DESCARGAR │     │ ANÁLISIS  │      │ SCRAPPING     │
   │  PRECIOS  │     │  RELACIONES│      │ NOTICIAS      │
   │ (yfinance)│     │ (OLS HAC)  │      │ (RSS/HTML)    │
   │           │     │            │      │               │
   │ - DXY     │     │ - Betas    │      │ - Títulos     │
   │ - USDCOP  │     │ - Contrib. │      │ - Fuentes     │
   │ - Petróleo│     │ - Residual │      │ - Links       │
   │ - etc     │     │ - Scores   │      │               │
   └────┬─────┘     └────┬─────┘      └────────┬──────┘
        │                │                     │
        └────────────────┼─────────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │  LLAMAR OpenAI API (GPT-4)      │
        │  con datos + noticias + prompt  │
        │  especial (15 reglas)           │
        └────────────┬───────────────────┘
                     │
        ┌────────────▼────────────┐
        │ GENERAR BRIEFING FINAL  │
        │ (natural, profesional,  │
        │  2-3 min de lectura)    │
        └────────────┬────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
 ┌───▼──┐        ┌───▼──┐      ┌────▼─────┐
 │ .txt │        │ .json│      │ .md/.html │
 │ ⭐   │        │      │      │           │
 └───┬──┘        └───┬──┘      └────┬─────┘
     │               │              │
     └───────────────┼──────────────┘
                     │
          ┌──────────▼──────────┐
          │  COMMIT & PUSH      │
          │  a GitHub (optional)│
          └──────────┬──────────┘
                     │
     ┌───────────────▼────────────────┐
     │  WEBSITE PUEDE ACCEDER         │
     │  VÍA GITHUB RAW CONTENT URL    │
     │  https://raw.githubusercontent │
     │  ...briefing_llm_YYYY-MM-DD.txt│
     └───────────────┬────────────────┘
                     │
              ┌──────▼──────┐
              │  MOSTRAR    │
              │  EN WEB     │
              └─────────────┘
```

---

## 🗂️ Estructura de Directorios

```
proyecto/
│
├── .github/workflows/
│   ├── daily-briefing.yml       ← ⚙️ GitHub Actions (ejecuta todo)
│   └── daily.yml                (legacy)
│
├── src/
│   ├── analysis/
│   │   ├── features.py          (contexto diario)
│   │   └── relations.py         (análisis de factores)
│   │
│   ├── data/
│   │   ├── prices_yf.py         (descarga yfinance)
│   │   └── combine.py           (procesa datos)
│   │
│   ├── llm/
│   │   └── summarize.py         (✨ genera briefings con OpenAI)
│   │
│   ├── news/
│   │   ├── scrape.py            (extrae noticias)
│   │   └── keywords.yaml
│   │
│   ├── scripts/
│   │   ├── daily_update.py      (🚀 orquestador principal)
│   │   └── run_relations.py
│   │
│   └── utils/
│       └── io.py
│
├── data/
│   ├── raw/                     (generado cada día)
│   │   ├── prices/YYYY-MM-DD/
│   │   │   ├── COP=X.csv
│   │   │   ├── BZ=F.csv
│   │   │   ├── DX-Y.NYB.csv
│   │   │   └── ...
│   │   └── news/YYYY-MM-DD/
│   │       └── articles.jsonl
│   │
│   └── processed/
│       └── market_daily.parquet
│
├── reports/
│   ├── briefings/               (📊 SALIDA PRINCIPAL)
│   │   ├── briefing_llm_YYYY-MM-DD.txt     ⭐
│   │   ├── briefing_YYYY-MM-DD.json
│   │   ├── briefing_YYYY-MM-DD.md
│   │   └── briefing_YYYY-MM-DD.html
│   │
│   └── relations/
│       └── relations_YYYY-MM-DD.json
│
├── config/
│   └── settings.yaml            (configuración)
│
├── .env.example
├── .env                         (nunca subir a Git)
├── .gitignore
├── requirements.txt
├── README.md
├── DEPLOY.md
├── QUICK_START.md
└── SETUP_COMPLETE.md
```

---

## 🔄 Ciclo de Datos

### 1️⃣ INGESTA (cada día a las 7am)

```
Yahoo Finance ──→ yfinance ──→ CSV por ticker ──→ market_daily.parquet
                                (17 tickers)      (long format)
```

**Tickers descargados:**
- USD/COP (COP=X)
- Dólar Global (DX-Y.NYB)
- Petróleo Brent (BZ=F)
- Volatilidad (^VIX)
- Monedas regionales (USDMXN=X, USDCLP=X)
- Y más según config/settings.yaml

### 2️⃣ ANÁLISIS DE RELACIONES

```
market_daily.parquet
    ↓
    ├─→ Calcular retornos 1d y 5d
    ├─→ Aplicar lags (DXY_L1, BZ_lag1)
    ├─→ Estandarizar (ventana 90d)
    ├─→ Regresiones OLS HAC (rolling 90d)
    ├─→ Calcular contribuciones
    ├─→ Capping automático de contribuciones
    ├─→ Calcular scores
    │
    └─→ relations_YYYY-MM-DD.json
        (tabla con: factor, retorno, beta, contribución, corr, score)
```

### 3️⃣ NOTICIAS

```
info_sources.csv
    ↓
    ├─→ RSS feeds + HTML scraping
    ├─→ Filtrar por keywords
    ├─→ Extraer título, fuente, link
    │
    └─→ articles.jsonl
        [{titulo, fuente, link, fecha}, ...]
```

### 4️⃣ GENERACIÓN DE BRIEFING (LLM)

```
relations_YYYY-MM-DD.json + articles.jsonl + prompt especial
    ↓
    ├─→ OpenAI API (GPT-4)
    │   - Mapear factores a nombres humanos
    │   - Calcular % del movimiento
    │   - Generar narrativa natural
    │   - Aplicar 15 reglas de escritura
    │
    └─→ briefing_llm_YYYY-MM-DD.txt
        (2-3 párrafos, sin jerga técnica)
```

---

## 🔐 Variables de Entorno

```
OPENAI_API_KEY=sk-...    ← Se agrega en GitHub Secrets
                          ← Nunca debe estar en .env local
```

---

## ⏰ Timeline de Ejecución

```
7:00 AM UTC    ┌─ Checkout del código
               ├─ Setup Python 3.11
               ├─ Install dependencies (30-40s)
               │
7:01 AM        └─ daily_update.py inicia
               ├─ Descargar precios (40-50s)
               ├─ Análisis de relaciones (20-30s)
               ├─ Scraping de noticias (10-20s)
               │
7:03 AM        └─ Llamar OpenAI API (10-20s)
               ├─ Generar briefings (5-10s)
               ├─ Commit & push (5-10s)
               │
7:04 AM        └─ ✅ COMPLETADO
               
Total: ~3-4 minutos por día
```

---

## 🎯 Puntos de Entrada

### Para Desarrolladores

```python
# Ejecutar todo:
python src/scripts/daily_update.py --date today

# Sin LLM (testing):
python src/scripts/daily_update.py --date today --skip-llm

# Solo relaciones:
python src/scripts/run_relations.py

# Custom:
python -m src.scripts.daily_update --date 2025-10-18 --config custom.yaml
```

### Para Usuarios

1. **GitHub Actions Panel**: Run workflow manualmente
2. **Website**: Cargar `briefing_llm_YYYY-MM-DD.txt` vía URL
3. **API**: JSON disponible en `briefing_YYYY-MM-DD.json`

---

## 🔗 Dependencias Externas

```
┌─────────────────────────────────────────────────┐
│         DEPENDENCIAS EXTERNAS                    │
├─────────────────────────────────────────────────┤
│                                                  │
│  Yahoo Finance ──────→ yfinance (descarga)      │
│  OpenAI API ─────────→ openai (genera texto)    │
│  RSS Feeds/HTML ─────→ feedparser, bs4 (noticias)
│  GitHub ─────────────→ git (commit)             │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Cero dependencias de base de datos.**
**Cero dependencias de servidores externos** (excepto APIs públicas).

---

## 📈 Escalabilidad

### Agregar nuevos tickers

```yaml
# config/settings.yaml
yfinance:
  tickers:
    - COP=X
    - BZ=F
    - AAPL        ← Nuevo
    - GLD         ← Nuevo
```

### Cambiar hora de ejecución

```yaml
# .github/workflows/daily-briefing.yml
schedule:
  - cron: '0 8 * * *'     # 8:00 AM UTC en vez de 7:00 AM
```

### Usar modelo diferente

```python
# src/scripts/daily_update.py
build_briefing_with_llm(..., model="gpt-4-turbo")  # en vez de gpt-4
```

---

## ✨ Características Clave

✅ **Zero-Knowledge**: No requiere mantener estado  
✅ **Regenerable**: Todo se calcula desde cero cada día  
✅ **Seguro**: API keys en GitHub Secrets  
✅ **Modular**: Cada componente es independiente  
✅ **Testeable**: Puede ejecutarse offline con --skip-llm  
✅ **Observable**: Logs detallados en GitHub Actions  
✅ **Escalable**: Agregar tickers o modelos sin cambiar arquitectura  

---

**Arquitectura lista para producción. 🚀**
