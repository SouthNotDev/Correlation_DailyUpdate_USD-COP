# Correlation Daily Update: USD/COP

Proyecto dividido en dos capas bien diferenciadas:

1. **Research (análisis histórico):** experimentar con métricas sencillas (betas, regresiones lineales, R², correlaciones móviles) para entender qué variables han estado más correlacionadas con los movimientos del USD/COP. Este trabajo se realiza aparte (notebooks, hojas de cálculo, scripts ad hoc) y produce conclusiones resumidas.
2. **Pipeline diario (este repositorio):** automatiza la ingesta de precios y noticias y genera un briefing diario. El pipeline consume los resultados del research (en forma de un resumen que se incorpora al system prompt) pero no alberga todo el estudio ni DataFrames pesados.

El objetivo es mantener la solución simple y eficiente, con la menor cantidad de archivos indispensable para ejecutar la rutina diaria.


## Objetivos

- **Research (fuera del pipeline):** iterar sobre modelos simples para identificar drivers relevantes y resumir los hallazgos (por ejemplo, qué tan sensible fue el USD/COP a Brent o DXY en el pasado).
- **Pipeline diario:** automatizar la ingesta de precios y noticias, guardar solo los datos esenciales y producir un briefing conciso en español que aproveche las conclusiones del research.


## Fuentes de Datos y Símbolos

- Yahoo Finance (yfinance):
  - USD/COP: `COP=X`
  - Brent Crude Oil Last Day Financial: `BZ=F`
  - US Dollar Index (DXY): `DX-Y.NYB`
  - Volatilidad: `^VIX`
- Investing.com (vía investiny):
  - Rentabilidad del bono Colombia 5 años
  - Rentabilidad del bono Colombia 10 años

Notas:
- Validaremos los símbolos exactos soportados por yfinance en el entorno antes de fijarlos.
- Para Investing.com con investiny se requiere obtener el `instrument_id` de cada bono y respetar sus Términos de Uso.
- Configura config/settings.yaml > investiny (interval, lookback_days e instrument_id) antes de ejecutar el pipeline.


## Alcance (MVP)

- Descargar y almacenar cierres diarios (5 años) de `COP=X`, `BZ=F`, `^DXY`, `^VIX` vía yfinance.
- Consolidar los datos en un DataFrame largo con columnas mínimas (`date`, `ticker`, `close`, `pct_change`).
- Guardar datos crudos (CSV por ticker) y dataset procesado (`market_daily.parquet`).
- Scraping básico de noticias filtradas por palabras clave, guardadas en JSONL.
- Generar un briefing diario (Markdown + HTML) que combine precios, titulares y las conclusiones resumidas del research.
- Evitar archivos redundantes; mantener el código modular pero ligero.


## Arquitectura y Flujo Diario

1. Ingesta de precios (yfinance) → `data/raw/prices/YYYY-MM-DD/*.csv`.
2. Limpieza ligera y consolidación → `data/processed/market_daily.parquet` (solo columnas esenciales).
3. Scraping de noticias (usando `info_sources.csv` + palabras clave) → `data/raw/news/YYYY-MM-DD/articles.jsonl`.
4. Construcción de contexto mínimo del día (`src/analysis/features.py`).
5. Generación del briefing (Markdown/HTML) en `reports/briefings/`.
6. Orquestación con el CLI (`src/scripts/daily_update.py`) y workflow programado en GitHub Actions.
7. Las conclusiones del research (generadas fuera del pipeline) se inyectan manualmente en el prompt cuando se actualicen.


## Estructura actual del proyecto

```
.
├─ README.md
├─ requirements.txt
├─ info_sources.csv
├─ config/
│  └─ settings.yaml
├─ src/
│  ├─ data/
│  │  ├─ prices_yf.py
│  │  └─ combine.py
│  ├─ news/
│  │  ├─ keywords.yaml
│  │  └─ scrape.py
│  ├─ analysis/
│  │  └─ features.py
│  ├─ llm/
│  │  ├─ prompt.md
│  │  └─ summarize.py
│  └─ scripts/
│     └─ daily_update.py
├─ data/
│  ├─ raw/
│  │  ├─ prices/
│  │  └─ news/
│  └─ processed/
├─ reports/
│  └─ briefings/
└─ .github/
   └─ workflows/
      └─ daily.yml
```

### Descripción básica por componente

- `requirements.txt`: lista de dependencias de Python necesarias para ejecutar todo el pipeline.
- `config/settings.yaml`: parámetros de ejecución (tickers, keywords, rutas de salida, idioma, zona horaria).
- `info_sources.csv`: catálogo editable de medios con los que el scraper inicia la búsqueda diaria.
- `src/data/prices_yf.py`: descarga precios históricos con yfinance, los guarda por ticker y los deja listos en formato largo.
- `src/data/combine.py`: agrega columnas derivadas mínimas (`pct_change`). El estudio de correlaciones no vive aquí.
- `src/news/scrape.py`: lee `info_sources.csv`, filtra titulares por palabras clave y guarda artículos relevantes en JSONL.
- `src/news/keywords.yaml`: lista inicial de palabras clave utilizadas para filtrar enlaces.
- `src/analysis/features.py`: helpers ligeros para obtener el snapshot diario que alimentará el briefing.
- `src/llm/prompt.md`: guía en texto para la LLM; aquí se pueden incrustar los hallazgos resumidos del research externo.
- `src/llm/summarize.py`: construye el briefing en Markdown y HTML aprovechando los datos y titulares recopilados.
- `src/scripts/daily_update.py`: orquestador CLI que ejecuta las etapas del pipeline (precios, noticias, briefing).
- `data/`: carpeta de trabajo. `raw/` almacena extracciones diarias (CSV por ticker y noticias en JSONL). `processed/` guarda el dataset limpio (`market_daily.parquet`).
- `reports/briefings/`: destino final del informe diario en formatos `.md` y `.html` listos para email o web.
- `.github/workflows/daily.yml`: workflow de GitHub Actions que programa la corrida automática (lunes-viernes, 10:00 UTC) y publica artefactos.

> Nota: al ejecutar el pipeline se crean subcarpetas por fecha dentro de `data/raw/` y archivos de briefing dentro de `reports/briefings/`. El entorno virtual `.venv/` es local y no forma parte del repositorio.


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
pip install requests beautifulsoup4 lxml feedparser pyyaml pyarrow
## Integracion con Investiny
El pipeline descarga los instrumentos definidos en config/settings.yaml cuando investiny.enabled es true. Los CSV crudos se guardan en data/raw/investiny/<fecha> y los precios procesados se agregan a data/processed/market_daily.parquet. Completa instrument_id y, si quieres renombrar la serie, ajusta el campo alias.

## Configuración

Archivo `config/settings.yaml` (ejemplo):

```yaml
yfinance:
  tickers:
    - COP=X     # USD/COP
    - BZ=F      # Brent
    - ^VIX      # VIX
    - DX-Y.NYB  # DXY
  period_years: 5
  interval: 1d
investiny:
  enabled: true
  interval: D
  lookback_days: 365
  instruments:
    col_bond_5y:
      id: 29240
      alias: COL_BOND_5Y
    col_bond_10y:
      id: 29236
      alias: COL_BOND_10Y
news:
  enabled: true
  keywords: ["peso", "dólar", "dolar", "USDCOP", "TRM", "Brent", "petróleo", "petroleo", "tasa", "inflación", "inflacion", "TES"]
  sources_csv: info_sources.csv
llm:
  enabled: false
  provider: null   # openai, azure, etc.
  model: null
storage:
  base_dir: data
reports:
  dir: reports/briefings
```


## Uso Previsto del pipeline

- Ejecutar el CLI único:

```bash
python -m src.scripts.daily_update --date today --config config/settings.yaml
```

- Salida: `reports/briefings/briefing_YYYY-MM-DD.{md,html}` con el contexto diario.
- Las conclusiones del research se añaden manualmente al prompt (`src/llm/prompt.md`) cuando haya nuevas versiones.


## Roadmap / Plan de Trabajo

Fase Research (fuera del pipeline)
- [ ] Correr análisis históricos de betas, regresiones y correlaciones simples.
- [ ] Documentar conclusiones clave (drivers principales, sensibilidad aproximada).
- [ ] Resumir hallazgos en 3–5 bullets para el system prompt.

Fase 1 — Datos de mercado (pipeline)
- [x] Confirmar símbolo principal (`^DXY`) y evaluar fallbacks.
- [x] Implementar `src/data/prices_yf.py` (descarga 5y, cierre 1d).
- [x] Unión + limpieza liviana → `data/processed/market_daily.parquet`.

Fase 2 — Noticias (pipeline)
- [x] Definir fuentes iniciales via `info_sources.csv` (homepage scraping con filtro por keywords).
- [x] Palabras clave iniciales en `src/news/keywords.yaml` (español con y sin acento).
- [x] `src/news/scrape.py` extracción diaria + guardado JSONL.

Fase 3 — Briefing (pipeline)
- [x] Definir prompt en `src/llm/prompt.md`.
- [x] `src/llm/summarize.py` (Markdown + HTML listos para email/web).
- [x] Generar `reports/briefings/*.md` y `.html` con el pipeline.

Fase 4 — Orquestación y Calidad (pipeline)
- [x] `src/scripts/daily_update.py` (CLI inicial con logging básico).
- [ ] Validaciones (fechas, vacíos, NaN, gaps).
- [x] Programación (workflow GitHub Actions + artefactos diarios).


## Consideraciones y Cumplimiento

- Revisar Términos de Uso de Yahoo Finance, Investing.com e índices.
- Mantener un `User-Agent` responsable y respetar robots/ratelimits en scraping.
- Uso de datos con fines personales/analíticos; no redistribuir sin permiso.


## Próximos Pasos Inmediatos

1. Completar el research externo y destilar 3–5 bullets para el system prompt.
2. Implementar fallback de DXY (`^DXY` → `DX-Y.NYB` → `DX=F`) y alertar si no hay datos.
3. Ajustar lista de palabras clave (añadir/quitar según señal).
4. Validar calidad del scraping por sitio y ajustar selectores si hace falta.
5. Refinar formato del briefing para email/website (HTML más estilizado si se requiere).
6. (Opcional) Añadir conversión Markdown→HTML real y plantilla de email.
7. (Opcional) Añadir bonos COL con investiny y correlaciones móviles.


## Preguntas Abiertas

- Confirmado: DXY `^DXY`.
- Medios iniciales: gestionados por `info_sources.csv` (puedes editarlo libremente).
- Idioma: español.
- Ejecución: se incluye workflow de GitHub Actions (diario, L-V).
- Salida: Markdown y HTML listos para email/website.
