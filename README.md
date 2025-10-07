# Correlation Daily Update: USD/COP

Proyecto para construir un pipeline diario que:

- Descarga precios de activos relevantes (USD/COP, Brent, DXY, VIX) de Yahoo Finance (yfinance) y, más adelante, rendimientos de bonos COL 5y y 10y desde Investing.com via investiny.
- Agrega y normaliza los datos (cierres diarios de los últimos 5 años) en Pandas.
- Extrae titulares/noticias diarias de medios definidos con palabras clave (por ejemplo: "peso", "dólar", "USD/COP", "petróleo", "Brent").
- Genera un briefing corto con una LLM que explique posibles drivers del movimiento del USD/COP en relación a cambios de mercado y noticias del día anterior.


## Objetivos

- Automación diaria de ingesta y consolidación de precios y noticias.
- Estandarización de un dataset de cierres diarios (últimos 5 años).
- Correlaciones iniciales USD/COP vs. drivers (Brent, DXY, VIX, bonos COL).
- Producción de un briefing diario, conciso y accionable.


## Fuentes de Datos y Símbolos

- Yahoo Finance (yfinance):
  - USD/COP: `COP=X`
  - Brent Crude Oil Last Day Financial: `BZ=F`
  - US Dollar Index (DXY): `DX-Y.NYB` (verificar símbolo disponible en yfinance; algunos entornos usan `DX-Y.NYB` o `DX-Y.NYB`/`DX=F`/`^DXY`).
  - Volatilidad: `^VIX`
- Investing.com (vía investiny):
  - Rentabilidad del bono Colombia 5 años
  - Rentabilidad del bono Colombia 10 años

Notas:
- Validaremos los símbolos exactos soportados por yfinance en el entorno antes de fijarlos.
- Para Investing.com con investiny se requiere obtener el `instrument_id` de cada bono y respetar sus Términos de Uso.


## Alcance (MVP)

- Descargar y almacenar cierres diarios 5 años de: `COP=X`, `BZ=F`, DXY, `^VIX`.
- Unificar en un único DataFrame por fecha (cols: `close`, `ticker`, `pct_change`, etc.).
- Cálculo simple de cambios diarios y correlaciones móviles básicas.
- Esqueleto para ingestión de bonos vía investiny (sin bloquear el MVP).
- Esqueleto para scraping de noticias y un prompt base para el resumen con LLM.


## Arquitectura y Flujo Diario

1. Ingesta precios (yfinance) → `data/raw/prices/YYYY-MM-DD/*.csv`.
2. (Opcional) Ingesta bonos (investiny) → `data/raw/bonds/YYYY-MM-DD/*.csv`.
3. Limpieza y unión → `data/processed/market_daily.parquet`.
4. Scraping de noticias (fuentes/keywords configurables) → `data/raw/news/YYYY-MM-DD/*.json`.
5. Feature engineering (cambios, z-scores, correlaciones móviles) → `data/processed/context_YYYY-MM-DD.parquet`.
6. LLM briefing → `reports/briefings/briefing_YYYY-MM-DD.md`.
7. Orquestación y logging (CLI/cron/GitHub Actions) + validaciones.


## Estructura de Carpetas Propuesta

```
.
├─ src/
│  ├─ data/
│  │  ├─ prices_yf.py        # yfinance
│  │  ├─ bonds_investiny.py  # investiny (stub inicial)
│  │  └─ combine.py          # unión y limpieza
│  ├─ news/
│  │  ├─ sources.yaml        # dominios RSS/HTML
│  │  ├─ keywords.yaml       # palabras clave
│  │  └─ scrape.py           # scraping/parsing
│  ├─ analysis/
│  │  └─ features.py         # cambios, correlaciones
│  ├─ llm/
│  │  ├─ prompt.md           # plantilla
│  │  └─ summarize.py        # integración LLM (provider-agnostic)
│  └─ scripts/
│     └─ daily_update.py     # entrypoint orquestador
├─ data/
│  ├─ raw/
│  │  ├─ prices/
│  │  └─ news/
│  └─ processed/
├─ reports/
│  └─ briefings/
├─ config/
│  └─ settings.yaml
├─ tests/
└─ README.md
```


## Requisitos e Instalación

- Python >= 3.10
- Dependencias principales: `pandas`, `numpy`, `yfinance`, `pytz`, `python-dateutil`
- Para futuras etapas: `investiny`, `requests`, `beautifulsoup4`/`lxml`, `feedparser` o `newspaper3k`, y cliente de la LLM elegida.

Instalación sugerida:

```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install pandas numpy yfinance pytz python-dateutil
# Más adelante: pip install investiny requests beautifulsoup4 lxml feedparser
```


## Configuración

Archivo `config/settings.yaml` (ejemplo):

```yaml
yfinance:
  tickers:
    - COP=X     # USD/COP
    - BZ=F      # Brent
    - ^VIX      # VIX
    - DX-Y.NYB  # DXY (verificar)
  period_years: 5
  interval: 1d
investiny:
  enabled: false
  instruments:
    col_bond_5y: null   # completar con instrument_id
    col_bond_10y: null
news:
  enabled: false
  keywords: ["peso", "dólar", "USDCOP", "Brent", "petróleo"]
  sources_file: src/news/sources.yaml
llm:
  enabled: false
  provider: null   # openai, azure, etc.
  model: null
storage:
  base_dir: data
reports:
  dir: reports/briefings
```


## Uso Previsto

- Ingesta rápida de precios (ejemplo):

```python
import yfinance as yf
import pandas as pd

symbols = ["COP=X", "BZ=F", "^VIX", "DX-Y.NYB"]
prices = {}
for s in symbols:
    df = yf.download(s, period="5y", interval="1d")["Close"].rename(s)
    prices[s] = df

merged = pd.concat(prices.values(), axis=1)
merged.index.name = "date"
merged.to_csv("data/raw/prices/latest_prices.csv")
```

- Orquestación diaria (objetivo):

```
python -m src.scripts.daily_update --date today
```

- Salida: `reports/briefings/briefing_YYYY-MM-DD.md` con resumen corto de drivers.


## Roadmap / Plan de Trabajo

Fase 1 — MVP de precios (yfinance)
- [ ] Confirmar símbolos válidos para DXY en entorno yfinance.
- [ ] Implementar `src/data/prices_yf.py` (descarga 5y, cierre 1d).
- [ ] Unión + limpieza → `data/processed/market_daily.parquet`.
- [ ] Cálculo de `pct_change` y verificación básica.

Fase 2 — Bonos COL (investiny)
- [ ] Obtener `instrument_id` 5y y 10y.
- [ ] Implementar `src/data/bonds_investiny.py` (ratelimits, reintentos).
- [ ] Integrar al dataset consolidado.

Fase 3 — Noticias
- [ ] Definir fuentes iniciales (RSS/HTML) en `src/news/sources.yaml`.
- [ ] Palabras clave en `src/news/keywords.yaml`.
- [ ] `src/news/scrape.py` con extracción diaria + guardado JSONL.

Fase 4 — Análisis y contexto
- [ ] `src/analysis/features.py` (cambios, z-scores, correlaciones móviles).
- [ ] Ensamblar contexto del día (mercado + titulares).

Fase 5 — Briefing con LLM
- [ ] Definir prompt en `src/llm/prompt.md`.
- [ ] `src/llm/summarize.py` (provider-agnostic, variables por env).
- [ ] Generar `reports/briefings/*.md`.

Fase 6 — Orquestación y Calidad
- [ ] `src/scripts/daily_update.py` (CLI, logging, retries).
- [ ] Validaciones (fechas, vacíos, NaN, gaps).
- [ ] Programación (cron local / GitHub Actions) y notificaciones (opcional).


## Consideraciones y Cumplimiento

- Revisar Términos de Uso de Yahoo Finance, Investing.com e índices.
- Mantener un `User-Agent` responsable y respetar robots/ratelimits en scraping.
- Uso de datos con fines personales/analíticos; no redistribuir sin permiso.


## Próximos Pasos Inmediatos

1. Confirmar símbolo correcto para DXY en yfinance.
2. Acordar fuentes iniciales de noticias (3–6 sitios) y formato (RSS vs HTML).
3. Definir formato de persistencia principal (`parquet` recomendado) y zonas `raw/processed`.
4. Alinear parámetros base (ventana de 5 años, hora de corte, zona horaria).
5. Crear `src/` con módulos mínimos y un CLI básico para el MVP.


## Preguntas Abiertas

- ¿Qué símbolo de DXY prefieres usar si `DX-Y.NYB` no está disponible en tu entorno (`DX=F` o `^DXY`)?
- Lista inicial de medios a scrapear (ej., Portafolio, La República, Bloomberg Línea, El Tiempo, Reuters, WSJ?).
- ¿Idioma del briefing: español, inglés o bilingüe?
- ¿Dónde quieres ejecutar el job diario (local, servidor, GitHub Actions)?
- ¿Formato de salida preferido para el briefing (Markdown, HTML, email, Slack)?

