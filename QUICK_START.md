# ⚡ Quick Start: 3 Pasos para Empezar

## Paso 1️⃣: Crear OpenAI API Key (2 min)

1. Ve a: **https://platform.openai.com/api-keys**
2. Click en **+ Create new secret key**
3. Dale nombre: "USD-COP Daily Briefing"
4. **COPIA la clave** (aparece solo una vez) ✅

---

## Paso 2️⃣: Agregar Secret en GitHub (2 min)

1. Ve a tu repositorio en **GitHub.com**
2. **Settings → Secrets and variables → Actions**
3. Click en **New repository secret**
4. Rellena:
   - **Name**: `OPENAI_API_KEY`
   - **Secret**: Pega la clave que copiaste
5. Click en **Add secret** ✅

---

## Paso 3️⃣: Ejecutar el Pipeline (1 min)

### Opción A: Automático (recomendado)
- El sistema se ejecuta **automáticamente cada día a las 7:00 AM UTC**
- Los briefings aparecerán en `reports/briefings/briefing_llm_*.txt`

### Opción B: Manual (para probar ahora)
1. Ve a tu repo en GitHub
2. Pestaña **Actions**
3. Click en **Daily Briefing Generation**
4. Botón azul **Run workflow**
5. Espera 2-3 minutos ⏳

---

## ✅ ¡Listo!

Tu sistema está generando briefings automáticamente cada día.

**El archivo principal es:**
```
reports/briefings/briefing_llm_YYYY-MM-DD.txt
```

---

## 📖 Documentación

- **`README.md`** - Documentación completa
- **`DEPLOY.md`** - Guía detallada de despliegue
- **`SETUP_COMPLETE.md`** - Lo que se implementó

---

## 🌐 Integrar en tu Website

```javascript
// Obtener el briefing del día
const today = new Date().toISOString().split('T')[0];
const url = `https://raw.githubusercontent.com/TU-USUARIO/TU-REPO/main/reports/briefings/briefing_llm_${today}.txt`;

fetch(url)
  .then(response => response.text())
  .then(briefing => {
    document.querySelector('#briefing-container').textContent = briefing;
  })
  .catch(() => {
    console.log('Briefing no disponible para hoy');
  });
```

---

## 🚀 ¡Listo para producción!

Tu sistema de análisis USD/COP está 100% operativo y generando briefings profesionales cada día automáticamente.
