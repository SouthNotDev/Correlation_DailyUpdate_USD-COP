# Análisis Diario USD/COP con LLM

Sistema automatizado que genera **briefings profesionales** sobre el movimiento del dólar frente al peso colombiano, ejecutándose diariamente a través de **GitHub Actions**.

## 🚀 Características

- **Pipeline automatizado diario** a las 7:00 AM UTC
- **Análisis de relaciones** entre USD/COP y múltiples factores (DXY, petróleo, monedas regionales, etc.)
- **Generación de briefings con LLM** (GPT-4/GPT-5) usando OpenAI API
- **Scraping de noticias** relevantes del día
- **Múltiples formatos de salida**: Texto LLM, Markdown, HTML, JSON, CSV
- **Completamente serverless** en GitHub Actions (sin base de datos)

## 📋 Requisitos

- Python 3.11+
- Cuenta OpenAI con acceso a GPT-4 (o GPT-5 cuando esté disponible)
- GitHub Actions habilitado en tu repositorio

## ⚙️ Instalación Local

### 1. Clonar el repositorio
```bash
git clone <tu-repo>
cd <tu-repo>
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crear archivo `.env` en la raíz:
```bash
cp .env.example .env
# Editar .env y agregar tu OpenAI API key
OPENAI_API_KEY=sk-your-key-here
```

## 🔧 Configuración

### Tickers y Fuentes de Datos
Editar `config/settings.yaml`:

```yaml
yfinance:
  tickers:
    - COP=X      # USD/COP
    - BZ=F       # Brent Oil
    - ^VIX       # Volatility Index
    - DX-Y.NYB   # US Dollar Index
    - USDMXN=X   # USD/MXN
    - USDCLP=X   # USD/CLP
    # ... agregar más según necesidad
  period_years: 5
  interval: 1d

news:
  enabled: true
  keywords: ["peso", "dolar", "USDCOP", "TRM", "petroleo"]
  sources_csv: info_sources.csv
```

### Fuentes de Noticias
Editar `info_sources.csv` para agregar/remover fuentes RSS.

## 🏃 Uso

### Ejecución Local (Completa)
```bash
python src/scripts/daily_update.py --date today
```

### Ejecución Local (sin LLM)
```bash
python src/scripts/daily_update.py --date today --skip-llm
```

### Solo Análisis de Relaciones
```bash
python src/scripts/run_relations.py
```

### Salida Esperada
```
[2025-10-18] Iniciando pipeline diario...
[2025-10-18] Descargando precios...
[2025-10-18] ✓ Precios guardados (17000 registros)
[2025-10-18] Generando análisis de relaciones...
[2025-10-18] ✓ Análisis de relaciones generado
[2025-10-18] Scrapeando noticias...
[2025-10-18] ✓ Noticias obtenidas (12 items)
[2025-10-18] Generando briefing con LLM...
[2025-10-18] ✓ Briefing LLM generado
[2025-10-18] ✓ Resumen JSON guardado
[2025-10-18] ✓ Briefings Markdown y HTML generados
[2025-10-18] ✓ Pipeline completado
```

## 🤖 Configuración en GitHub Actions

### 1. Agregar Secrets
En tu repositorio GitHub, ir a:
**Settings → Secrets and variables → Actions → New repository secret**

Agregar:
- `OPENAI_API_KEY`: Tu clave de API de OpenAI

### 2. Workflow Automático
El archivo `.github/workflows/daily-briefing.yml` ejecuta automáticamente cada día a las **7:00 AM UTC**.

**Puedes también ejecutar manualmente:**
- Ve a **Actions → Daily Briefing Generation → Run workflow**

## 📁 Estructura de Carpetas

```
.
├── config/
│   └── settings.yaml          # Configuración principal
├── data/
│   ├── raw/                   # Se crea diariamente
│   │   ├── news/
│   │   └── prices/
│   └── processed/
│       └── market_daily.parquet
├── reports/
│   ├── briefings/
│   │   ├── briefing_llm_YYYY-MM-DD.txt      # Briefing del LLM ← PRINCIPAL
│   │   ├── briefing_YYYY-MM-DD.json         # JSON estructurado
│   │   ├── briefing_YYYY-MM-DD.md           # Markdown
│   │   └── briefing_YYYY-MM-DD.html         # HTML
│   └── relations/
│       └── relations_YYYY-MM-DD.json        # Análisis de relaciones
├── src/
│   ├── analysis/               # Análisis de relaciones
│   ├── data/                   # Descarga y procesamiento de datos
│   ├── llm/                    # Generación de briefings con LLM
│   ├── news/                   # Scraping de noticias
│   ├── scripts/                # Scripts principales
│   └── utils/                  # Utilidades
├── .github/workflows/
│   └── daily-briefing.yml      # Automatización en GitHub Actions
├── .env.example                # Plantilla de variables de entorno
├── .gitignore                  # Git ignore (excluye datos y .env)
└── requirements.txt            # Dependencias Python
```

## 📊 Archivos de Salida Principales

### `briefing_llm_YYYY-MM-DD.txt`
Texto natural y profesional generado por el LLM. **Este es el archivo principal para tu website.**

Ejemplo:
```
El dólar subió 0.5% frente al peso colombiano hoy. El principal impulso 
vino del dólar global, que presionó al alza reflejando fortaleza en mercados 
internacionales. Las monedas de la región acompañaron el movimiento, con el 
peso mexicano y chileno también cediendo terreno. El petróleo, por su parte, 
se debilitó, lo que moderó parte del movimiento alcista. Una fracción importante 
del movimiento no fue explicada por los activos observados, sugiriendo efectos 
locales o ajustes en tasas.
```

### `briefing_YYYY-MM-DD.json`
Estructura JSON para acceso programático:
```json
{
  "date": "2025-10-18",
  "briefing": "El dólar subió 0.5%...",
  "factors_count": 9,
  "news_count": 12
}
```

### `relations_YYYY-MM-DD.json`
Análisis técnico completo de factores (CSV con análisis de correlaciones).

## 🔗 Integración con tu Website

El archivo `briefing_llm_YYYY-MM-DD.txt` puede ser:

1. **Descargado directamente** desde el repositorio
2. **Accedido vía API de GitHub** (raw content)
3. **Procesado por tu website** al leer el JSON del día

### Ejemplo para tu Website:
```javascript
// Obtener briefing del día
const today = new Date().toISOString().split('T')[0];
const url = `https://raw.githubusercontent.com/tu-usuario/tu-repo/main/reports/briefings/briefing_${today}.json`;

fetch(url)
  .then(r => r.json())
  .then(data => {
    document.querySelector('.briefing').innerHTML = data.briefing;
  });
```

## 🧹 Limpieza de Datos Históricos

Los datos se regeneran cada día desde cero. Para mantener limpio el repo:

```bash
# Eliminar datos antiguos manualmente (opcional)
rm -rf data/raw/*
# Git mantiene limpio automáticamente según .gitignore
```

## 🚨 Troubleshooting

### Error: `OPENAI_API_KEY not found`
- Verifica que agregaste el secret en GitHub Settings
- En local, verifica que `.env` tiene `OPENAI_API_KEY=sk-...`

### Error: `News scraping failed`
- Verifica que `info_sources.csv` tiene URLs válidas
- Algunos sitios pueden bloquear requests; considera agregar User-Agent

### Error: `Insufficient data for analysis`
- El análisis de relaciones necesita al menos 90 días de datos
- Verifica que `period_years` en `settings.yaml` es suficiente

## 📝 Próximas Mejoras

- [ ] Soporte para GPT-5 cuando esté disponible
- [ ] Webhook para notificaciones (Slack, email)
- [ ] Dashboard con histórico de briefings
- [ ] Alertas cuando movimientos excedan umbrales
- [ ] Análisis de sentimiento de noticias

## 📄 Licencia

MIT

## 👤 Autor

Generado automáticamente por GitHub Actions diariamente a las 7:00 AM UTC.

---

**Última actualización**: Script ejecutado automáticamente
