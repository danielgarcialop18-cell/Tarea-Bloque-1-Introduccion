from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
from typing import Optional, Dict, List, Union
import numpy as np 
from tabulate import tabulate

from src.plots.plots import (
    plot_prices, 
    plot_monte_carlo,
    plot_normalized_prices,      
    plot_correlation_heatmap,    
    plot_weights_pie_chart      
)


@dataclass
class PriceSeries:
    
    # 1. CAMPOS QUE PASAMOS AL CREARLA
    ticker: str
    source: str
    data: pd.DataFrame
    
    # 2. CAMPOS CALCULADOS (no se pasan al crearla)
    start_date: Optional[datetime] = field(init=False)
    end_date: Optional[datetime] = field(init=False)
    
    # --- CAMPOS ESTADÍSTICOS AUTOMÁTICOS ---
    # Se calcularán en __post_init__
    main_col: Optional[str] = field(init=False, default=None) # (close o rsi)
    mean_value: Optional[float] = field(init=False, default=float('nan'))
    std_dev_value: Optional[float] = field(init=False, default=float('nan'))

    def __post_init__(self):
        if not self.data.empty:
            # --- Cálculo de fechas (existente) ---
            self.start_date = self.data.index.min()
            self.end_date = self.data.index.max()
            
            # --- Cálculo de estadísticas automáticas ---
            # 1. Determinar sobre qué columna calcular (close o rsi)
            if 'close' in self.data.columns:
                self.main_col = 'close'
            elif 'rsi' in self.data.columns:
                self.main_col = 'rsi'
            
            # 2. Calcular media y desviación si tenemos una columna principal
            if self.main_col:
                self.mean_value = self.data[self.main_col].mean()
                self.std_dev_value = self.data[self.main_col].std()
            else:
                self.mean_value = float('nan')
                self.std_dev_value = float('nan')
        else:
            # --- Caso de DataFrame vacío (existente) ---
            self.start_date = None
            self.end_date = None
            self.mean_value = float('nan')
            self.std_dev_value = float('nan')
            self.main_col = None

    def __len__(self) -> int:
        return len(self.data)

    def get_summary(self) -> str: 
        if self.data.empty:
            return f"Serie: {self.ticker} ({self.source}) - (Vacía)"
        else:
            stats_str = ""
            if self.main_col:
                stats_str = f"| Col: {self.main_col} (Media: {self.mean_value:,.2f}, Std: {self.std_dev_value:,.2f})"

            return (f"Serie: {self.ticker} ({self.source}) | "
                    f"Rango: {self.start_date.date()} a {self.end_date.date()} | "
                    f"Registros: {len(self)} {stats_str}")

    # --- NUEVOS MÉTODOS ESTADÍSTICOS ---

    def get_daily_returns(self, column: str = 'close'):
        if column in self.data.columns:
            return self.data[column].pct_change()
        
        print(f"Advertencia: Columna '{column}' no encontrada para calcular retornos.")
        return None

    def calculate_sma(self, window_days: int = 20):
        if self.main_col and len(self.data) >= window_days:
            return self.data[self.main_col].rolling(window=window_days).mean()
        
        if not self.main_col:
            print("Advertencia: No hay columna principal (close/rsi) para calcular SMA.")
        else:
            print(f"Advertencia: No hay suficientes datos ({len(self)}) para la ventana SMA ({window_days}).")
        return None

    def get_min_max(self):
        if self.main_col:
            min_val = self.data[self.main_col].min()
            min_date = self.data[self.main_col].idxmin()
            max_val = self.data[self.main_col].max()
            max_date = self.data[self.main_col].idxmax()
            return {
                "min_value": min_val,
                "min_date": min_date,
                "max_value": max_val,
                "max_date": max_date,
            }
        return None

    # --- MÉTODO DE MONTE CARLO PARA ACTIVOS ---
    def run_monte_carlo(self, days: int, simulations: int):
        if self.main_col != 'close' or self.data.empty:
            raise ValueError(f"Simulación solo aplicable a series 'close' con datos. (Activo: {self.ticker})")

        # 1. Calcular rentabilidades
        log_returns = np.log(1 + self.data[self.main_col].pct_change()).dropna()

        if log_returns.empty:
             raise ValueError(f"No hay suficientes datos históricos. (Activo: {self.ticker})")

        # 2. Calcular estadísticas
        mu = log_returns.mean()
        sigma = log_returns.std()
        
        # 3. Preparar simulación
        last_price = self.data[self.main_col].iloc[-1]
        simulation_paths = np.zeros((days + 1, simulations))
        simulation_paths[0] = last_price

        # 4. Ejecutar simulaciones
        for i in range(simulations):
            shock = np.random.normal(0, 1, days)
            drift = mu - 0.5 * sigma**2
            daily_returns = np.exp(drift + sigma * shock)
            
            path = np.zeros(days + 1)
            path[0] = last_price
            for t in range(1, days + 1):
                path[t] = path[t - 1] * daily_returns[t - 1]
            
            simulation_paths[:, i] = path

        return simulation_paths

    # --- VISUALIZACIÓN ---
    def plot_simulation(self, paths: np.ndarray, title: str):
        """
        Llama a la función de ploteo para mostrar los resultados
        de la simulación de esta serie.
        """
        print(f"Mostrando gráfico para {self.ticker}...")
        plot_monte_carlo(paths, title)

# --- METODO DE LIMPIEZA 1: RELLENA LOS NaN CON ffill ---
    def fillna(self, method: str = 'ffill'):
        if not self.data.empty:
            self.data.fillna(method=method, inplace=True)
            print(f"[{self.ticker}] Datos NaN rellenados con método '{method}'.")
        return self
    
# --- METODO DE LIMPIEZA 2: RELLENA LOS NaN CON ffill ---
    def resample_daily(self, fill_method: str = 'ffill'):
        if not self.data.empty:
            self.data.index = pd.to_datetime(self.data.index) # me aseguro de que el indice sea un datetime
            self.data = self.data.resample('D').fillna(method=fill_method)
            self.__post_init__() 
            print(f"[{self.ticker}] Serie re-muestreada a diario ('D') con método '{fill_method}'.")
        return self

# --- METODO DE LIMPIEZA 3: ELIMINA LOS VALORES NEGATIVOS Y NULOS ---
    def negative_prices(self):
        if not self.data.empty:
            price_cols = ['open', 'high', 'low', 'close']
            count = 0
            for col in price_cols:
                if col in self.data.columns:
                    non_positive_mask = self.data[col] <= 0
                    count += non_positive_mask.sum()
                    self.data.loc[non_positive_mask, col] = np.nan
            if count > 0:
                print(f"[{self.ticker}] Encontrados y eliminados {count} precios no positivos (<= 0)")
        return self 

@dataclass
class Portfolio: # Es una cartera, es decir, una coleccion de activos (PriceSeries)
    name: str # El nombre de la cartera
    
    assets: Dict[str, PriceSeries] = field(default_factory=dict)
    
    weights: Optional[Dict[str, float]] = None

    def add_series(self, series: PriceSeries):
        if not isinstance(series, PriceSeries):
            print(f"Error: Solo se pueden añadir objetos PriceSeries a la cartera.")
            return
            
        self.assets[series.ticker] = series
        print(f"Activo {series.ticker} añadido a la cartera '{self.name}'.")

    @property
    def tickers(self):
        return list(self.assets.keys()) # me devuelve una lista de los tickers que hay en la cartera

    def __len__(self):
        return len(self.assets) # me dice el numeron de activos de la cartera

    # --- MONTE CARLO PARA CARTERAS ---
    def run_monte_carlo(self, days: int, simulations: int):
        if not self.assets:
            raise ValueError("La cartera no tiene activos.")
        if self.weights is None:
            raise ValueError("La cartera no tiene pesos (weights) definidos.")

        tickers = self.tickers
        weights = np.array([self.weights[t] for t in tickers])
        
        # 1. Crear DataFrame
        close_prices = {}
        for ticker, series in self.assets.items():
            if series.main_col == 'close' and not series.data.empty:
                close_prices[ticker] = series.data['close']
            else:
                raise ValueError(f"Activo {ticker} no tiene datos 'close' para simulación.")
                
        df_closes = pd.concat(close_prices, axis=1, keys=close_prices.keys()).fillna(method='ffill').dropna()

        # 2. Calcular rentabilidades y estadísticas
        log_returns = np.log(1 + df_closes.pct_change()).dropna()
        
        if log_returns.empty:
            raise ValueError("No hay suficientes datos históricos para la simulación.")

        mean_returns = log_returns.mean().values
        cov_matrix = log_returns.cov().values
        last_prices = df_closes.iloc[-1].values
        
        # 3. Descomposición de Cholesky
        try:
            L = np.linalg.cholesky(cov_matrix)
        except np.linalg.LinAlgError:
            raise ValueError("Error: La matriz de covarianza no es positiva definida.")

        # 4. Preparar simulación
        all_asset_paths = np.zeros((days + 1, len(tickers), simulations))
        all_asset_paths[0, :, :] = last_prices.reshape(-1, 1)
        portfolio_paths = np.zeros((days + 1, simulations))
        portfolio_paths[0, :] = (last_prices * weights).sum()

        # 5. Ejecutar simulaciones
        drift = mean_returns - 0.5 * np.diag(cov_matrix)

        for i in range(simulations):
            Z = np.random.normal(0, 1, size=(days, len(tickers)))
            daily_shocks = Z @ L.T
            daily_returns = np.exp(drift + daily_shocks)
            
            current_prices = last_prices.copy()
            for t in range(1, days + 1):
                current_prices = current_prices * daily_returns[t-1, :]
                all_asset_paths[t, :, i] = current_prices
            
            portfolio_paths[:, i] = all_asset_paths[:, :, i] @ weights

        return portfolio_paths

    # --- VISUALIZACIÓN ---
    def plot_simulation(self, paths: np.ndarray, title: str):
        """
        Llama a la función de ploteo para mostrar los resultados
        de la simulación de la cartera.
        """
        print(f"Mostrando gráfico para Cartera '{self.name}'...")
        plot_monte_carlo(paths, title)

    # --- REPORTE ---
    def report(self):
    
        if not self.assets:
            return "# Reporte de Cartera\n\nCartera vacía."

        md = []
        
        # --- 1. Título y Resumen ---
        md.append(f"# Nombre de la Cartera: {self.name}")
        md.append(f"Activos Totales: {len(self)}")
        
        # --- 2. Pesos (Weights) ---
        md.append("\n## Pesos de la Cartera")
        if self.weights:
            weights_data = [[ticker, f"{weight*100:.2f}%"] for ticker, weight in self.weights.items()]
            md.append(tabulate(weights_data, headers=["Activo", "Peso"], tablefmt="pipe"))
        else:
            md.append("\n> ⚠️ Advertencia: No se han definido pesos ('weights') para esta cartera. \n> El análisis de riesgo/retorno de cartera (ej. Monte Carlo de cartera) no está disponible.")

        # --- 3. Resumen de Activos y Advertencias de Fechas ---
        md.append("\n## 📊 Resumen de Activos Individuales")
        
        table_data = []
        all_start_dates = []
        all_end_dates = []
        
        for ticker, series in self.assets.items():
            if series.data.empty:
                table_data.append([ticker, "N/A", 0, "N/A", "N/A", "N/A", "N/A"])
                continue
                
            all_start_dates.append(series.start_date)
            all_end_dates.append(series.end_date)
            table_data.append([
                series.ticker,
                series.main_col,
                len(series),
                series.start_date.date(),
                series.end_date.date(),
                f"{series.mean_value:,.2f}",
                f"{series.std_dev_value:,.2f}"
            ])
            
        md.append(tabulate(table_data, headers=["Ticker", "Col. Principal", "Registros", "Desde", "Hasta", "Media", "Volatilidad (Std)"], tablefmt="pipe"))
        
        # Advertencias de fechas
        if all_start_dates and all_end_dates:
            min_start = min(all_start_dates)
            max_start = max(all_start_dates)
            min_end = min(all_end_dates)
            max_end = max(all_end_dates)
            
            md.append("\n### ⚠️ Advertencias sobre Rango de Fechas")
            if max_start > min_start:
                md.append(f"- Disparidad de Inicio: Los activos no comienzan en la misma fecha (rango: {min_start.date()} a {max_start.date()}).")
            if min_end < max_end:
                md.append(f"- Disparidad de Fin: Los activos no terminan en la misma fecha (rango: {min_end.date()} a {max_end.date()}).")
            
            common_start = max_start
            common_end = min_end
            
            if common_start >= common_end:
                 md.append(f"- ¡IMPOSIBLE! No existe un rango de fechas común para todos los activos (Inicio común: {common_start.date()}, Fin común: {common_end.date()}). El análisis de correlación fallará.")
            else:
                md.append(f"- Rango Común Efectivo: El período válido para análisis de correlación es de **{common_start.date()}** a **{common_end.date()}**.")


        # --- 4. Análisis de Correlación (solo para 'close') ---
        md.append("\n## Análisis de Correlación (Histórica)")
        
        price_assets = [s for s in self.assets.values() if s.main_col == 'close' and not s.data.empty]
        
        if len(price_assets) < 2:
            md.append("\n_No hay suficientes activos de precios ('close') con datos para calcular la correlación._")
        else:
            try:
                # 1. Crear DataFrame de precios de cierre
                close_prices = {}
                for series in price_assets:
                    close_prices[series.ticker] = series.data['close']
                df_closes = pd.concat(close_prices, axis=1, keys=close_prices.keys())
                
                # 2. Rellenar y calcular retornos (respetando el rango común)
                # Nos aseguramos de que solo usamos el rango común para el cálculo
                common_start = max(s.start_date for s in price_assets)
                common_end = min(s.end_date for s in price_assets)
                
                df_closes_common = df_closes.loc[common_start:common_end].fillna(method='ffill').dropna(axis=0) 

                if df_closes_common.empty:
                     raise ValueError("El DataFrame de rango común está vacío tras limpiar los NaN.")

                # 3. Calcular retornos logarítmicos
                log_returns = np.log(1 + df_closes_common.pct_change()).dropna()
                
                if log_returns.empty:
                    md.append("\n> ⚠️ Advertencia: No se pudo calcular la correlación (datos insuficientes tras procesar retornos en el rango común).")
                else:
                    # 4. Calcular y mostrar matriz de correlación
                    corr_matrix = log_returns.corr()
                    md.append("\nMatriz de Correlación de Retornos Logarítmicos (sobre rango común):")
                    md.append(f"\n{tabulate(corr_matrix, headers='keys', tablefmt='pipe', floatfmt='.3f')}\n")
                    
                    # 5. Insights de Correlación
                    corr_pairs = corr_matrix.unstack().sort_values(ascending=False)
                    corr_pairs = corr_pairs[corr_pairs < 1.0] # Quitar las correlaciones perfectas (activo consigo mismo)
                    
                    if not corr_pairs.empty:
                        md.append("#### Observaciones Clave:")
                        
                        max_corr = corr_pairs.idxmax()
                        md.append(f"- Máxima Correlación: `{max_corr[0]}` y `{max_corr[1]}` ({corr_pairs.max():.3f}). Tienden a moverse juntos.")
                        
                        min_corr = corr_pairs.idxmin()
                        md.append(f"- Mínima Correlación (o Inversa): `{min_corr[0]}` y `{min_corr[1]}` ({corr_pairs.min():.3f}). Ofrecen la mayor diversificación.")
                    
            except Exception as e:
                md.append(f"\n> ⚠️ Error Inesperado: No se pudo generar el análisis de correlación: {e}")

        return "\n".join(md)
    

    def plots_report(self):
        """
        Genera y muestra una serie de gráficos útiles para
        analizar la cartera.
        """
        print("Generando gráficos de análisis de cartera...")
        
        if not self.assets:
            print("⛔ Cartera vacía. No se pueden generar gráficos.")
            return

        # --- Gráfico 1: Tarta de Pesos ---
        if self.weights:
            plot_weights_pie_chart(self.weights, f"Composición de la Cartera '{self.name}'")
        else:
            print("ℹ️ No hay pesos definidos, omitiendo gráfico de composición de cartera.")

        # --- Preparación para gráficos de precios/correlación ---
        price_assets = [s for s in self.assets.values() if s.main_col == 'close' and not s.data.empty]
        
        if len(price_assets) < 1:
            print("⛔ No hay activos de precios ('close') con datos para los gráficos de rendimiento o correlación.")
            return

        # 1. Crear DataFrame de precios de cierre
        try:
            close_prices = {}
            for series in price_assets:
                close_prices[series.ticker] = series.data['close']
            df_closes = pd.concat(close_prices, axis=1, keys=close_prices.keys())

            # 2. Encontrar rango común
            common_start = max(s.start_date for s in price_assets)
            common_end = min(s.end_date for s in price_assets)
            
            if common_start >= common_end:
                 print(f"⚠️ ¡Advertencia! No existe un rango común para los activos. No se pueden generar gráficos de rendimiento o correlación.")
                 return
            
            # --- ¡¡ARREGLO DE ADVERTENCIA!! ---
            # df_closes_common = df_closes.loc[common_start:common_end].fillna(method='ffill').dropna(axis=0) # <-- Línea antigua
            df_closes_common = df_closes.loc[common_start:common_end].ffill().dropna(axis=0) # <-- Línea nueva

            if df_closes_common.empty:
                print("⚠️ ¡Advertencia! El DataFrame de rango común está vacío. Omitiendo gráficos.")
                return

            # --- Gráfico 2: Rendimiento Normalizado ---
            plot_normalized_prices(df_closes_common)
            
            # --- Gráfico 3: Mapa de Correlación ---
            if len(price_assets) >= 2:
                log_returns = np.log(1 + df_closes_common.pct_change()).dropna()
                if not log_returns.empty:
                    corr_matrix = log_returns.corr()
                    plot_correlation_heatmap(corr_matrix)
                else:
                    print("ℹ️ Datos insuficientes para calcular la matriz de correlación.")
            else:
                print("ℹ️ Se necesitan al menos 2 activos para un mapa de correlación.")

        except Exception as e:
            print(f"⚠️ Error Inesperado al generar gráficos de precios: {e}")