
## Información General del Proyecto

Este proyecto utiliza dos librerías principales para la obtención de datos financieros:

- **yfinance**: Para descargar datos históricos de precios de activos desde Yahoo Finance

## YFinance - Documentación Técnica

### Instalación

```bash
pip install yfinance
```

### Descripción General

`yfinance` es una librería Python que ofrece una interfaz Pythonica para obtener datos financieros y de mercado desde la API no oficial de Yahoo Finance. Proporciona herramientas para descargar datos históricos, información fundamental, opciones y más.

### Funcionalidades Principales

#### 1. Descarga de Datos Históricos

La función principal es `yf.download()` para obtener datos históricos de precios:

```python
import yfinance as yf

# Descarga básica
data = yf.download('AAPL', start='2023-01-01', end='2023-12-31')

# Múltiples tickers
data = yf.download(['AAPL', 'MSFT'], period='1y', interval='1d')

# Parámetros principales:
# - tickers: símbolo(s) del activo
# - start/end: fechas de inicio y fin
# - period: período predefinido ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
# - interval: intervalo de datos ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
```

#### 2. Información de Activos Individuales

```python
import yfinance as yf

ticker = yf.Ticker("COP=X")  # USD/COP

# Información general
info = ticker.info

# Datos históricos específicos
history = ticker.history(period="5y", interval="1d")

# Información rápida (más eficiente)
fast_info = ticker.fast_info
```

### Símbolos Relevantes para el Proyecto

Según la documentación de Yahoo Finance y símbolos disponibles:

- **USD/COP**: `COP=X` (par de divisas USD/COP)
- **Brent Crude Oil**: `BZ=F` (futuros de Brent)
- **US Dollar Index (DXY)**: `DX-Y.NYB` (�ndice del d�lar estadounidense)
- **VIX (Volatilidad)**: `^VIX` (�ndice de volatilidad del mercado)
- **Bonos EM en USD**: `EMB`
- **Bonos EM moneda local**: `EMLC`, `LEMB`, `FEMB`
- **Riesgo Colombia (acciones)**: `ICOL`, `GXG`, `CIB`
- **Tasas base globales**: `^TNX`
- **Commodities de exportaci�n**: `KC=F` (caf�), `MTF=F` (carb�n)
- **Activos refugio**: `GC=F` (oro)
- **FX regional**: `USDCLP=X`, `USDMXN=X`

### Características Técnicas

#### Datos de Salida
- **Formato**: pandas DataFrame con columnas: Open, High, Low, Close, Adj Close, Volume
- **Índice de tiempo**: DatetimeIndex con zona horaria
- **Frecuencia**: Desde 1 minuto hasta mensual

#### Manejo de Errores
- La librería maneja errores de red y timeouts automáticamente
- Reintentos automáticos en caso de fallos temporales
- Logging disponible con `yf.enable_debug_mode()`

#### Limitaciones
- **Rate Limiting**: Yahoo Finance tiene límites de requests por IP
- **Disponibilidad**: Algunos símbolos pueden no estar disponibles en ciertas regiones
- **Datos históricos**: Limitaciones en profundidad histórica para algunos activos


### Instalación

```bash
```

### Descripción General


### Funcionalidades Principales

#### 1. Búsqueda de Activos

```python

# Buscar activos por nombre o símbolo
results = search_assets(
    query="Colombia 5Y Bond",
    limit=10,
    type="Bond",
    exchange="Colombia"
)

# El resultado incluye el 'ticker' (ID de Investing.com)
investing_id = int(results[0]["ticker"])
```

#### 2. Descarga de Datos Históricos

```python

# Datos históricos usando el ID de Investing.com
data = historical_data(
    investing_id=investing_id,
    from_date="01/01/2020",
    to_date="12/31/2024"
)

# Parámetros:
# - investing_id: ID único del activo en Investing.com
# - from_date/to_date: formato "MM/DD/YYYY"
# - interval: '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1wk', '1mo'
```

### Obtención de IDs de Bonos Colombianos

Para obtener los `instrument_id` de los bonos colombianos:

1. **Búsqueda inicial**:
```python

# Buscar bonos Colombia 5Y
results_5y = search_assets(
    query="Colombia 5Y",
    limit=5,
    type="Bond"
)

# Buscar bonos Colombia 10Y
results_10y = search_assets(
    query="Colombia 10Y",
    limit=5,
    type="Bond"
)
```

2. **Verificación de resultados**:
```python
# Revisar resultados para encontrar el bono correcto
for result in results_5y:
    print(f"Nombre: {result['name']}, País: {result['country']}, ID: {result['ticker']}")
```

### Características Técnicas

#### Datos de Salida
- **Formato**: Lista de diccionarios JSON
- **Campos**: date, open, high, low, close, volume
- **Sin índice de fecha**: Los datos vienen sin índice de tiempo (necesario post-procesamiento)

#### Ventajas sobre investpy
- �
 Datos intradiarios disponibles
- �
 Más rápido y ligero
- �
 Más fácil de usar
- ❌ Sin datos de dividendos
- ❌ Sin calendario económico
- ❌ Sin indicadores técnicos

#### Limitaciones
- Requiere obtener el `investing_id` correcto para cada activo
- Formato de fecha específico (MM/DD/YYYY)
- No incluye información fundamental adicional

## Implementación Técnica para el Proyecto

### Flujo de Datos - YFinance

```python
import yfinance as yf
import pandas as pd

def descargar_datos_yfinance():
    # Símbolos del proyecto
    symbols = {
        "COP=X": "USD/COP",
        "BZ=F": "Brent",
        "DX-Y.NYB": "DXY",
        "^VIX": "VIX"
    }

    # Descargar datos históricos (5 años)
    data_frames = []
    for symbol, nombre in symbols.items():
        try:
            df = yf.download(
                symbol,
                period="5y",
                interval="1d",
                progress=False
            )
            df['ticker'] = nombre
            df['symbol'] = symbol
            data_frames.append(df)
        except Exception as e:
            print(f"Error descargando {symbol}: {e}")

    # Combinar todos los datos
    if data_frames:
        combined_df = pd.concat(data_frames)
        combined_df = combined_df.reset_index()
        combined_df = combined_df.rename(columns={
            'Date': 'date',
            'Close': 'close',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Volume': 'volume'
        })
        return combined_df
    return None
```


```python
import pandas as pd

def obtener_bonos_colombia():
    # Buscar bonos Colombia
    search_5y = search_assets(query="Colombia 5Y", limit=10, type="Bond")
    search_10y = search_assets(query="Colombia 10Y", limit=10, type="Bond")

    # Encontrar IDs correctos (requiere verificación manual)
    # Estos IDs deben verificarse y actualizarse según disponibilidad
    bonos = {
        "COL_5Y": None,   # ID a determinar
        "COL_10Y": None   # ID a determinar
    }

    # Buscar y asignar IDs
    for result in search_5y + search_10y:
        nombre = result['name'].upper()
        if '5' in nombre and 'COL_5Y' not in locals():
            bonos['COL_5Y'] = int(result['ticker'])
        elif '10' in nombre and 'COL_10Y' not in locals():
            bonos['COL_10Y'] = int(result['ticker'])

    return bonos

def descargar_datos_bonos(bonos_ids):
    datos_bonos = []

    for nombre, inv_id in bonos_ids.items():
        if inv_id:
            try:
                data = historical_data(
                    investing_id=inv_id,
                    from_date="01/01/2020",
                    to_date="12/31/2024"
                )

                # Convertir a DataFrame
                df = pd.DataFrame(data)
                df['ticker'] = nombre
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                datos_bonos.append(df)

            except Exception as e:
                print(f"Error descargando {nombre}: {e}")

    return datos_bonos
```

## Consideraciones de Producción

### YFinance
- **Rate Limiting**: Implementar delays entre requests
- **Fallbacks**: Manejar símbolos no disponibles
- **Cache**: Considerar almacenamiento local para evitar requests frecuentes
- **Validación**: Verificar disponibilidad de símbolos antes del deployment

- **IDs dinámicos**: Los `investing_id` pueden cambiar, requerir monitoreo
- **Búsqueda robusta**: Implementar lógica para encontrar IDs correctos
- **Post-procesamiento**: Convertir datos a formato estándar (con índice de fecha)

### Mejores Prácticas
1. **Respetar términos de servicio** de ambas plataformas
2. **Implementar manejo de errores robusto**
3. **Usar configuración externa** para símbolos e IDs
4. **Logging detallado** para debugging y monitoreo
5. **Validación de datos** antes del procesamiento posterior
