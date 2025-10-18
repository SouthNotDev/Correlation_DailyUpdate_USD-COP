# 📋 Guía de Despliegue en GitHub Actions

Este documento contiene las instrucciones paso a paso para desplegar el sistema en GitHub Actions.

## ⚡ TL;DR (Configuración Rápida)

1. **Clonar el repositorio**
   ```bash
   git clone <tu-repo>
   cd <tu-repo>
   ```

2. **Crear OpenAI API Key**
   - Ve a https://platform.openai.com/api-keys
   - Crea una nueva secret key
   - Cópiala

3. **Agregar Secret en GitHub**
   - Ve a tu repositorio en GitHub
   - **Settings → Secrets and variables → Actions**
   - Click en **New repository secret**
   - Nombre: `OPENAI_API_KEY`
   - Valor: Pega tu key de OpenAI

4. **¡Listo!** El pipeline se ejecutará automáticamente cada día a las 7:00 AM UTC

---

## 📦 Requisitos Previos

- ✅ Repositorio GitHub (público o privado)
- ✅ Cuenta OpenAI con acceso a GPT-4
- ✅ GitHub Actions habilitado (por defecto en repos públicos)

## 🔑 Paso 1: Crear OpenAI API Key

### Opción A: Crear una nueva clave (recomendado)

1. Ve a: https://platform.openai.com/account/api-keys
2. Click en **+ Create new secret key**
3. Dale un nombre descriptivo (ej: "USD-COP Daily Briefing")
4. **Muy importante:** Copia la clave inmediatamente (solo se muestra una vez)
5. Guárdala en un lugar seguro

### Opción B: Usar clave existente

Si ya tienes una clave funcionando, puedes reutilizarla.

**⚠️ NUNCA subas la clave a Git. Usa GitHub Secrets.**

## 🔐 Paso 2: Configurar Secret en GitHub

### Instrucciones:

1. **Ve a tu repositorio en GitHub**

2. **Click en Settings (pestaña) → Secrets and variables → Actions**
   ![settings-location]

3. **Click en el botón verde "New repository secret"**

4. **Rellena el formulario:**
   - **Name:** `OPENAI_API_KEY`
   - **Secret:** Pega la clave que copiaste (comienza con `sk-`)
   
   ![secret-form]

5. **Click en "Add secret"**

### Verificar que se agregó:

La clave debe aparecer en la lista de secrets con un ícono de secreto.

**Los secrets nunca se muestran en los logs, solo GitHub Actions puede acceder.**

## ⏰ Paso 3: Verificar Configuración del Workflow

El archivo `.github/workflows/daily-briefing.yml` ya está configurado para ejecutarse:

- **Diariamente** a las **7:00 AM UTC**
- También puede ejecutarse **manualmente** desde la pestaña **Actions**

### Para verificar:

1. Ve a **Actions** en tu repositorio
2. Busca el workflow **"Daily Briefing Generation"**
3. Si lo ves, está listo ✅

### Ejecutar manualmente (para pruebas):

1. Ve a **Actions → Daily Briefing Generation**
2. Click en el botón azul **"Run workflow"**
3. Selecciona **"Run workflow"** en el modal

El pipeline ejecutará y generará los archivos en `reports/`.

## 📊 Paso 4: Verificar Resultados

### Ver logs del workflow:

1. Ve a **Actions** en tu repositorio
2. Click en la última ejecución
3. Click en el trabajo **"generate-briefing"**
4. Ver los logs con los detalles de ejecución

### Archivos generados:

Después de ejecutarse, encontrarás en `reports/briefings/`:

```
briefing_llm_YYYY-MM-DD.txt    ← ⭐ PRINCIPAL: El texto del LLM
briefing_YYYY-MM-DD.json        ← Versión estructurada en JSON
briefing_YYYY-MM-DD.md          ← Markdown (compatibilidad)
briefing_YYYY-MM-DD.html        ← HTML (compatibilidad)
```

Y en `reports/relations/`:

```
relations_YYYY-MM-DD.json       ← Análisis técnico de factores
```

## 🌐 Paso 5: Integración con tu Website

### Opción A: Acceder vía Raw Content

Puedes acceder al archivo de texto directamente:

```
https://raw.githubusercontent.com/tu-usuario/tu-repo/main/reports/briefings/briefing_llm_YYYY-MM-DD.txt
```

Ejemplo para hoy:

```javascript
const today = new Date().toISOString().split('T')[0];
const url = `https://raw.githubusercontent.com/tu-usuario/tu-repo/main/reports/briefings/briefing_llm_${today}.txt`;

fetch(url)
  .then(r => r.text())
  .then(text => {
    document.querySelector('.briefing-container').innerText = text;
  });
```

### Opción B: Usar JSON (más estructurado)

```javascript
const today = new Date().toISOString().split('T')[0];
const url = `https://raw.githubusercontent.com/tu-usuario/tu-repo/main/reports/briefings/briefing_${today}.json`;

fetch(url)
  .then(r => r.json())
  .then(data => {
    console.log(data.briefing);        // Texto del briefing
    console.log(data.factors_count);   // Cantidad de factores
    console.log(data.news_count);      // Cantidad de noticias
    document.querySelector('.briefing').innerHTML = data.briefing;
  });
```

### Opción C: Webhook personalizado

Si necesitas hacer algo más complejo, puedes:

1. Crear un webhook que se dispare cuando se actualicen los archivos
2. O crear tu propio script que descargue los datos cada hora

## 🔧 Paso 6: Configuración Avanzada

### Cambiar hora de ejecución

El workflow se ejecuta a las 7:00 AM UTC. Para cambiar:

1. Edita `.github/workflows/daily-briefing.yml`
2. Busca la línea: `- cron: '0 7 * * *'`
3. Cambia según el formato `'minuto hora * * *'`

Ejemplos:

```yaml
# 8:00 AM UTC
- cron: '0 8 * * *'

# 2:00 PM UTC
- cron: '0 14 * * *'

# 6:30 AM UTC
- cron: '30 6 * * *'

# Solo lunes a viernes a las 9 AM UTC
- cron: '0 9 * * 1-5'
```

Referencia: https://crontab.guru/

### Cambiar modelo OpenAI

En `src/scripts/daily_update.py`, busca:

```python
model="gpt-4"  # Cambiar a "gpt-5" cuando esté disponible
```

Puedes usar:

- `gpt-4-turbo` (más rápido, más barato)
- `gpt-4` (más preciso)
- `gpt-5` (cuando esté disponible)

### Agregar más tickers

En `config/settings.yaml`:

```yaml
yfinance:
  tickers:
    - COP=X
    - BZ=F
    - ^VIX
    # Agregar aquí más tickers
    - AAPL
    - GOLD
```

## 🐛 Troubleshooting

### Error: "OPENAI_API_KEY not found"

**Causa:** El secret no está configurado o tiene un nombre diferente.

**Solución:**

1. Ve a **Settings → Secrets and variables → Actions**
2. Verifica que existe un secret llamado `OPENAI_API_KEY` (mayúsculas exactas)
3. Si no existe, créalo como en el Paso 2

### Error: "401 Unauthorized" de OpenAI

**Causa:** La API key es inválida o expiró.

**Solución:**

1. Ve a https://platform.openai.com/account/api-keys
2. Verifica que la clave está activa
3. Copia la clave nuevamente
4. Actualiza el secret en GitHub
5. Espera a que el workflow se ejecute nuevamente o ejecuta manualmente

### Error: "Insufficient_quota"

**Causa:** Tu cuenta OpenAI se quedó sin créditos.

**Solución:**

1. Ve a https://platform.openai.com/account/billing/overview
2. Agrega un método de pago o un crédito
3. Espera a que se procese (5-10 minutos)
4. Reintentar el workflow

### Los archivos no se están guardando

**Causa:** Probablemente el workflow tiene error.

**Solución:**

1. Ve a **Actions**
2. Click en el último workflow
3. Lee los logs para ver dónde falló
4. Abre un issue con los detalles

### Las noticias no se están scrapeando

**Causa:** Las fuentes en `info_sources.csv` pueden estar inactivas o bloqueadas.

**Solución:**

1. Edita `info_sources.csv`
2. Verifica que las URLs son válidas
3. Reemplaza fuentes rotas con otras actuales
4. Reintentar el workflow

## 📈 Monitoreo

### Ver estadísticas de uso:

1. https://platform.openai.com/account/usage/overview
2. Verifica tokens usados y costo

### Ver histórico de ejecutancias:

En GitHub **Actions → Daily Briefing Generation** puedes ver:

- Historial de todas las ejecuciones
- Duración de cada una
- Logs completos
- Artefactos descargados

## 🎯 Verificación Final

Antes de considerar que todo está listo:

- ✅ El secret `OPENAI_API_KEY` existe en GitHub
- ✅ El workflow ejecutó al menos una vez sin errores
- ✅ Los archivos se generaron en `reports/`
- ✅ El contenido del briefing tiene sentido
- ✅ Puedes acceder al archivo vía URL

## 📞 Soporte

Si tienes problemas:

1. Revisa los logs en **Actions**
2. Verifica este documento de troubleshooting
3. Abre un issue en el repositorio

---

**¡Tu sistema está listo para generar briefings automáticamente!** 🎉
