"""Sistema simplificado de análisis de relaciones para USD/COP.

Este módulo implementa la nueva lógica simplificada para encontrar relaciones
entre variables financieras y el COP (peso colombiano).
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from typing import Dict, Tuple, List


def run_relations(prices_path: str, output_path: str) -> pd.DataFrame:
    """Ejecuta el análisis completo de relaciones.

    Args:
        prices_path: Ruta al archivo parquet con datos de precios
        output_path: Ruta donde guardar el resultado CSV

    Returns:
        DataFrame con los resultados del análisis
    """
    # Cargar datos
    df = pd.read_parquet(prices_path)

    # Construir variables base
    variables = construir_variables_base(df)

    # Calcular retornos y lags
    retornos = calcular_retornos(variables)

    # Estandarizar variables
    estandarizadas = estandarizar_variables(retornos)

    # Elegir variable local (GXG o ICOL)
    local_ticker = elegir_riesgo_local(estandarizadas)

    # Crear factores regionales y locales
    factores = crear_factores(estandarizadas, local_ticker)

    # Calcular regresiones
    modelos = calcular_regresiones(factores)

    # Calcular contribuciones
    contribuciones = calcular_contribuciones(factores, modelos)

    # Crear tablas de resultados separadas para 1d y 5d
    tablas = crear_tabla_resultado(contribuciones, factores, modelos)

    # Generar one-liner para News Teller
    texto_news = generar_texto_news(contribuciones, factores, modelos)

    # Crear DataFrame combinado para compatibilidad hacia atrás
    # Agregar encabezados descriptivos
    if not tablas['1d'].empty:
        tablas['1d'].insert(0, 'periodo', '1d')
    if not tablas['5d'].empty:
        tablas['5d'].insert(0, 'periodo', '5d')

    resultado_combinado = pd.concat([
        tablas['1d'],
        tablas['5d']
    ], ignore_index=True) if not tablas['1d'].empty and not tablas['5d'].empty else (
        tablas['1d'] if not tablas['1d'].empty else tablas['5d']
    )

    # Guardar resultados
    resultado_combinado.to_csv(output_path, index=False)

    # Agregar texto como comentario
    with open(output_path, 'a') as f:
        f.write(f"\n# News Teller Summary:\n{texto_news}\n")

    return resultado_combinado


def construir_variables_base(df: pd.DataFrame) -> pd.DataFrame:
    """Construye las variables base necesarias."""
    # Pivotar datos para tener tickers como columnas
    df_pivot = df.pivot(index='date', columns='ticker', values='pct_change')

    # Rellenar valores faltantes hacia adelante (hasta 5 días)
    df_pivot = df_pivot.ffill(limit=5)

    return df_pivot


def calcular_retornos(variables: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Calcula retornos 1d y 5d con lags apropiados."""

    retornos = {}

    # Retornos 1d (sin cambios)
    retornos['1d'] = variables.copy()

    # Retornos 5d (rolling 5 días)
    retornos['5d'] = (1 + variables).rolling(5).apply(
        lambda x: (x + 1).prod() - 1 if len(x.dropna()) >= 3 else 0,
        raw=False
    )

    return retornos


def estandarizar_variables(retornos: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Estandariza variables con ventana rolling de 90 días."""

    def estandarizar_ventana(x):
        """Función auxiliar para estandarizar una ventana."""
        if len(x) < 10:  # Mínimo de observaciones
            return pd.Series([0] * len(x), index=x.index)

        # Remover NaN
        x_clean = x.dropna()
        if len(x_clean) < 10:
            return pd.Series([0] * len(x), index=x.index)

        mean_val = x_clean.mean()
        std_val = x_clean.std()

        if std_val > 0:
            return (x - mean_val) / std_val
        else:
            return pd.Series([0] * len(x), index=x.index)

    estandarizadas = {}

    for periodo, df in retornos.items():
        # Aplicar estandarización columna por columna
        df_estandarizada = pd.DataFrame(index=df.index, columns=df.columns)

        for col in df.columns:
            df_estandarizada[col] = df[col].rolling(90).apply(
                lambda x: estandarizar_ventana(x).iloc[-1] if len(x) > 0 else 0,
                raw=False
            )

        df_estandarizada = df_estandarizada.fillna(0)
        estandarizadas[periodo] = df_estandarizada

    return estandarizadas


def elegir_riesgo_local(estandarizadas: Dict[str, pd.DataFrame]) -> str:
    """Elige entre GXG o ICOL basado en estabilidad."""

    # Usar datos 5d para evaluación
    df_5d = estandarizadas['5d']

    # Calcular estabilidad para cada variable local
    estabilidad = {}

    for ticker in ['GXG', 'ICOL']:
        if ticker in df_5d.columns:
            # Calcular correlación rolling con COP
            corr_rolling = df_5d[ticker].rolling(90).corr(df_5d['COP=X'])

            # Calcular estabilidad como 1 / (std de betas + epsilon)
            estabilidad[ticker] = 1 / (corr_rolling.std() + 1e-6)

    # Elegir el más estable
    if estabilidad:
        return max(estabilidad, key=estabilidad.get)

    return 'GXG'  # Default


def crear_factores(estandarizadas: Dict[str, pd.DataFrame], local_ticker: str) -> Dict[str, pd.DataFrame]:
    """Crea los factores finales para cada período."""

    factores = {}

    for periodo in ['1d', '5d']:
        df = estandarizadas[periodo].copy()

        # Crear LA_USD (promedio estandarizado de USDMXN y USDCLP)
        fx_regional = ['USDMXN=X', 'USDCLP=X']
        disponibles = [t for t in fx_regional if t in df.columns]

        if len(disponibles) >= 1:
            df['LA_USD'] = df[disponibles].mean(axis=1)
        else:
            df['LA_USD'] = 0

        # Crear factor local solo para 5d
        if periodo == '5d':
            df['Local5d'] = df[local_ticker] if local_ticker in df.columns else 0
        else:
            df['Local5d'] = 0

        # Aplicar lags
        if periodo == '1d':
            # DXY_L1 y BZ_lag1
            df['DXY_L1'] = df['DX-Y.NYB'].shift(1)
            df['BZ_lag1'] = df['BZ=F'].shift(1)
        else:
            # Sin lags para 5d
            df['DXY_L1'] = df['DX-Y.NYB']
            df['BZ_lag1'] = df['BZ=F']

        factores[periodo] = df

    return factores


def calcular_regresiones(factores: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
    """Calcula regresiones OLS con ventana rolling de 90 días."""

    modelos = {}

    for periodo in ['1d', '5d']:
        df = factores[periodo]

        # Variables independientes para cada modelo
        if periodo == '1d':
            x_cols = ['DXY_L1', 'LA_USD', 'BZ_lag1']  # Sin Local5d para 1d
        else:
            x_cols = ['DXY_L1', 'LA_USD', 'BZ_lag1', 'Local5d']  # Con Local5d para 5d

        # Crear matriz X e y
        X = df[x_cols].fillna(0)
        y = df['COP=X'].fillna(0)

        # Crear matriz para regresión rolling
        X = sm.add_constant(X)

        # Inicializar arrays para resultados
        betas = pd.DataFrame(index=df.index, columns=['const'] + x_cols)
        r2_scores = pd.Series(index=df.index, dtype=float)

        # Calcular regresiones rolling ventana 90 días
        for i in range(90, len(df)):
            # Ventana de datos
            X_window = X.iloc[i-90:i]
            y_window = y.iloc[i-90:i]

            # Solo usar ventanas con suficientes datos no nulos
            valid_mask = ~(X_window.isna().any(axis=1) | y_window.isna())
            if valid_mask.sum() >= 30:  # Mínimo 30 observaciones
                X_valid = X_window[valid_mask]
                y_valid = y_window[valid_mask]

                try:
                    model = sm.OLS(y_valid, X_valid).fit()

                    # Guardar betas del último día de la ventana
                    betas.iloc[i] = model.params.values

                    # Calcular R2 para el día actual (simplificado)
                    X_current = X.iloc[i:i+1]
                    y_current = y.iloc[i]

                    if not X_current.isna().any().any() and not pd.isna(y_current):
                        y_pred = model.predict(X_current)
                        ss_res = ((y_current - y_pred.iloc[0]) ** 2)

                        # Usar ventana más amplia para ss_tot
                        y_recent = y.iloc[max(0, i-252):i]  # Último año
                        if len(y_recent.dropna()) > 10:
                            ss_tot = ((y_current - y_recent.mean()) ** 2)
                            r2_scores.iloc[i] = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
                        else:
                            r2_scores.iloc[i] = 0.0

                except Exception as e:
                    # Si hay error, usar betas promedio históricos
                    if i > 0:
                        betas_historicas = betas.iloc[:i].mean()
                        betas.iloc[i] = betas_historicas.values if not betas_historicas.isna().any() else 0
                    continue

        modelos[periodo] = {
            'betas': betas,
            'r2': r2_scores
        }

    return modelos


def calcular_contribuciones(factores: Dict[str, pd.DataFrame], modelos: Dict[str, Dict]) -> Dict[str, pd.DataFrame]:
    """Calcula contribuciones del día y residual con capping."""

    contribuciones = {}

    for periodo in ['1d', '5d']:
        df = factores[periodo]
        betas = modelos[periodo]['betas']

        # Variables para calcular contribuciones
        if periodo == '1d':
            x_cols = ['DXY_L1', 'LA_USD', 'BZ_lag1']  # Sin Local5d para 1d
        else:
            x_cols = ['DXY_L1', 'LA_USD', 'BZ_lag1', 'Local5d']  # Con Local5d para 5d

        # Calcular contribuciones
        contribs = pd.DataFrame(index=df.index, columns=x_cols + ['residual'])

        for i in range(len(df)):
            if i >= 90 and not betas.iloc[i].isna().any():
                # Contribuciones de factores
                cop_actual = df['COP=X'].iloc[i]
                cop_abs = abs(cop_actual)

                for col in x_cols:
                    factor_actual = df[col].iloc[i]
                    beta_factor = betas[col].iloc[i]
                    contrib_raw = float(beta_factor * factor_actual)

                    # Aplicar capping: |contribucion_factor| <= 0.8 * |retorno_COP_hoy|
                    contrib_cap = max(-0.8 * cop_abs, min(0.8 * cop_abs, contrib_raw))
                    contribs.loc[df.index[i], col] = contrib_cap

                # Residual (usando contribuciones cappeadas)
                contrib_total = contribs.loc[df.index[i], x_cols].sum()
                residual_value = float(cop_actual - contrib_total)
                contribs.loc[df.index[i], 'residual'] = residual_value

        # Llenar valores faltantes con 0
        contribs = contribs.fillna(0).infer_objects(copy=False)
        contribuciones[periodo] = contribs

    return contribuciones


def crear_tabla_resultado(contribuciones: Dict[str, pd.DataFrame], factores: Dict[str, pd.DataFrame], modelos: Dict[str, Dict]) -> Dict[str, pd.DataFrame]:
    """Crea tablas mínimas separadas para 1d y 5d con columna note."""

    tablas = {}

    for periodo in ['1d', '5d']:
        # Usar datos del día más reciente
        ultimo_dia = factores[periodo].index.max()

        # Obtener datos del día más reciente
        factores_periodo = factores[periodo]
        contribuciones_periodo = contribuciones[periodo]
        betas_periodo = modelos[periodo]['betas']

        if ultimo_dia not in factores_periodo.index:
            tablas[periodo] = pd.DataFrame()  # Sin datos para el día más reciente
            continue

        # Variables para calcular
        if periodo == '1d':
            x_cols = ['DXY_L1', 'LA_USD', 'BZ_lag1']  # Sin Local5d para 1d
        else:
            x_cols = ['DXY_L1', 'LA_USD', 'BZ_lag1', 'Local5d']  # Con Local5d para 5d

        # Crear tabla resultado
        resultado = []

        for col in x_cols:
            beta_actual = float(betas_periodo[col].loc[ultimo_dia]) if ultimo_dia in betas_periodo.index and not pd.isna(betas_periodo[col].loc[ultimo_dia]) else 0.0

            # Verificar si fue cappeado
            cop_actual = factores_periodo['COP=X'].loc[ultimo_dia]
            contrib_actual = contribuciones_periodo[col].loc[ultimo_dia]
            contrib_raw = beta_actual * factores_periodo[col].loc[ultimo_dia]

            note = ""
            if abs(contrib_actual) < abs(contrib_raw) and abs(contrib_raw) > 0.001:
                note = "capped"

            fila = {
                'factor': col,
                'retorno_hoy': float(factores_periodo[col].loc[ultimo_dia]) if ultimo_dia in factores_periodo.index and not pd.isna(factores_periodo[col].loc[ultimo_dia]) else 0.0,
                'beta_rolling': beta_actual,
                'contribucion': float(contribuciones_periodo[col].loc[ultimo_dia]) if ultimo_dia in contribuciones_periodo.index and not pd.isna(contribuciones_periodo[col].loc[ultimo_dia]) else 0.0,
                'corr_5d_rolling': 0.0,  # Se calculará después
                'score_factor': 0.0,  # Se calculará después
                'note': note
            }
            resultado.append(fila)

        # Agregar residual
        resultado.append({
            'factor': 'residual',
            'retorno_hoy': 0.0,
            'beta_rolling': 0.0,
            'contribucion': float(contribuciones_periodo['residual'].loc[ultimo_dia]) if ultimo_dia in contribuciones_periodo.index and not pd.isna(contribuciones_periodo['residual'].loc[ultimo_dia]) else 0.0,
            'corr_5d_rolling': 0.0,
            'score_factor': 0.0,
            'note': ""
        })

        resultado_df = pd.DataFrame(resultado)

        # Calcular métricas adicionales (corr_5d_rolling, score_factor)
        resultado_df = calcular_metricas_adicionales(resultado_df, factores_periodo, ultimo_dia)

        tablas[periodo] = resultado_df

    return tablas


def calcular_metricas_adicionales(df: pd.DataFrame, factores_5d: pd.DataFrame, ultimo_dia: pd.Timestamp) -> pd.DataFrame:
    """Calcula métricas adicionales como correlaciones y scores."""

    # Calcular correlaciones rolling 5d
    ventana_datos = factores_5d.loc[:ultimo_dia]

    for i, row in df.iterrows():
        if row['factor'] != 'residual':
            factor_col = row['factor']

            # Correlación 5d rolling
            corr_rolling = ventana_datos[factor_col].rolling(5).corr(ventana_datos['COP=X'])
            corr_value = float(corr_rolling.loc[ultimo_dia]) if ultimo_dia in corr_rolling.index and not pd.isna(corr_rolling.loc[ultimo_dia]) else 0.0
            df.loc[i, 'corr_5d_rolling'] = corr_value

    # Calcular scores
    df = calcular_scores(df)

    return df


def calcular_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula scores para desempate según la regla especificada."""

    # Calcular estabilidad = 1 / (sd_rolling_beta + 1e-6) reescalado 0 a 1
    estabilidades = []
    for i, row in df.iterrows():
        if row['factor'] != 'residual':
            # Simular cálculo de estabilidad (en implementación real usar betas históricos)
            estabilidad = 0.5  # Placeholder
            estabilidades.append(estabilidad)

    if estabilidades:
        estabilidad_min = min(estabilidades)
        estabilidad_max = max(estabilidades)

        for i, row in df.iterrows():
            if row['factor'] != 'residual':
                estabilidad = estabilidades[i] if i < len(estabilidades) else 0.5

                # Reescalar a 0-1
                estabilidad_norm = (estabilidad - estabilidad_min) / (estabilidad_max - estabilidad_min) if estabilidad_max > estabilidad_min else 0.5

                # Calcular score_factor = 0.6 * |corr_5d_rolling| + 0.4 * estabilidad
                corr_abs = abs(row['corr_5d_rolling'])
                score = float(0.6 * corr_abs + 0.4 * estabilidad_norm)

                df.loc[i, 'score_factor'] = score

    return df


def generar_texto_news(contribuciones: Dict[str, pd.DataFrame], factores: Dict[str, pd.DataFrame], modelos: Dict[str, Dict]) -> str:
    """Genera el texto condicionado por R2 y residual para el News Teller."""

    # Usar datos del día más reciente
    ultimo_dia = factores['5d'].index.max()

    if ultimo_dia not in factores['5d'].index:
        return "No hay datos disponibles para generar el texto."

    # Obtener datos necesarios
    cop_actual = factores['5d']['COP=X'].loc[ultimo_dia]
    contribuciones_5d = contribuciones['5d'].loc[ultimo_dia]
    r2_1d = modelos['1d']['r2'].loc[ultimo_dia] if ultimo_dia in modelos['1d']['r2'].index else 0

    # Ordenar factores por magnitud de contribución (top 2)
    x_cols = ['DXY_L1', 'LA_USD', 'BZ_lag1', 'Local5d']
    contrib_ordenadas = []

    for col in x_cols:
        contrib = contribuciones_5d[col]
        if not pd.isna(contrib) and abs(contrib) > 0.001:  # Filtrar contribuciones pequeñas
            contrib_ordenadas.append((col, contrib))

    # Ordenar por magnitud absoluta
    contrib_ordenadas.sort(key=lambda x: abs(x[1]), reverse=True)

    # Línea 1: Movimiento del COP y principales drivers
    movimiento_cop = f"{cop_actual:.3f}" if not pd.isna(cop_actual) else "desconocido"

    if len(contrib_ordenadas) >= 2:
        factor_a, contrib_a = contrib_ordenadas[0]
        factor_b, contrib_b = contrib_ordenadas[1]

        contrib_a_pct = f"{contrib_a:.1f}" if not pd.isna(contrib_a) else "0.0"
        contrib_b_pct = f"{contrib_b:.1f}" if not pd.isna(contrib_b) else "0.0"

        # Condicionar texto por R2
        if r2_1d < 0.10:
            verbo = "parece haber sido impulsado por"
        else:
            verbo = "fue por"

        linea_1 = f"El COP se movió {movimiento_cop}%. Driver 1 {factor_a} {contrib_a_pct}%, Driver 2 {factor_b} {contrib_b_pct}%."
    else:
        linea_1 = f"El COP se movió {movimiento_cop}%."

    # Línea 2: Condicionales por residual y risk_on
    residual = contribuciones_5d['residual']
    residual_pct = abs(residual) if not pd.isna(residual) else 0
    mov_abs = abs(cop_actual) if not pd.isna(cop_actual) else 0

    # Calcular risk_on (VIX > percentil 80 de últimos 12 meses)
    vix_data = factores['5d']['^VIX'].dropna()
    if len(vix_data) >= 252:  # Aproximadamente 1 año de datos
        percentil_80 = vix_data.quantile(0.8)
        vix_actual = vix_data.loc[ultimo_dia] if ultimo_dia in vix_data.index else np.nan
        risk_on = 1 if not pd.isna(vix_actual) and vix_actual > percentil_80 else 0
    else:
        risk_on = 0

    # Construir línea 2
    condiciones = []

    if residual_pct > 0.30 * mov_abs:
        condiciones.append("resto residual, probable ruido local.")

    if risk_on == 1:
        condiciones.append("sesgo de riesgo global.")

    if condiciones:
        linea_2 = " ".join(condiciones)
    else:
        linea_2 = ""

    return f"{linea_1}\n{linea_2}".strip()
