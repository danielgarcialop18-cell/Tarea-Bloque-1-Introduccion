from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
from typing import Optional, Dict, List, Union
import numpy as np  # <--- AÑADIDO

from src.plots.plots import plot_prices, plot_monte_carlo


@dataclass
class PriceSeries:
    """
    Representa la serie histórica normalizada de precios para UN activo.
    Usa un dataclass para guardar los datos de forma coherente.
    """
    
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
        """
        Esta función especial se ejecuta AUTOMÁTICAMENTE
        justo después del __init__ que ha creado el dataclass.
        
        """
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
        """Devuelve el número de registros (filas) del DataFrame."""
        return len(self.data)

    def get_summary(self) -> str: # <--- CAMBIO: Actualizado para mostrar estadísticas
        """Devuelve un resumen simple de la serie."""
        if self.data.empty:
            return f"Serie: {self.ticker} ({self.source}) - (Vacía)"
        else:
            # Formateamos las estadísticas para que se vean bien
            stats_str = ""
            if self.main_col:
                stats_str = f"| Col: {self.main_col} (Media: {self.mean_value:,.2f}, Std: {self.std_dev_value:,.2f})"

            return (f"Serie: {self.ticker} ({self.source}) | "
                    f"Rango: {self.start_date.date()} a {self.end_date.date()} | "
                    f"Registros: {len(self)} {stats_str}")

    # --- NUEVOS MÉTODOS ESTADÍSTICOS (OPCIONALES) ---

    def get_daily_returns(self, column: str = 'close'):
        """
        Calcula los retornos diarios (cambio porcentual) de una columna.
        Por defecto, usa la columna 'close'.
        """
        if column in self.data.columns:
            return self.data[column].pct_change()
        
        print(f"Advertencia: Columna '{column}' no encontrada para calcular retornos.")
        return None

    def calculate_sma(self, window_days: int = 20):
        """
        Calcula la Media Móvil Simple (SMA) de la columna principal.
        """
        if self.main_col and len(self.data) >= window_days:
            return self.data[self.main_col].rolling(window=window_days).mean()
        
        if not self.main_col:
            print("Advertencia: No hay columna principal (close/rsi) para calcular SMA.")
        else:
            print(f"Advertencia: No hay suficientes datos ({len(self)}) para la ventana SMA ({window_days}).")
        return None

    def get_min_max(self):
        """Devuelve el mínimo y máximo (precio y fecha) de la columna principal."""
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

    # --- ¡NUEVO MÉTODO! LÓGICA DE MONTE CARLO ---
    def run_monte_carlo(self, days: int, simulations: int) -> np.ndarray:
        """
        Ejecuta una simulación de Monte Carlo para esta serie.
        Utiliza el Movimiento Geométrico Browniano (GBM).
        """
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

    # --- ¡NUEVO MÉTODO! VISUALIZACIÓN ---
    def plot_simulation(self, paths: np.ndarray, title: str):
        """
        Llama a la función de ploteo para mostrar los resultados
        de la simulación de esta serie.
        """
        print(f"Mostrando gráfico para {self.ticker}...")
        plot_monte_carlo(paths, title)


@dataclass
class Portfolio:
    """
    Representa una cartera o colección de PriceSeries (activos).
    También es un dataclass.
    """
    name: str # El nombre de la cartera, ej: "Mi Cartera"
    
    assets: Dict[str, PriceSeries] = field(default_factory=dict)
    
    weights: Optional[Dict[str, float]] = None

    def add_series(self, series: PriceSeries):
        """
        Método para añadir un objeto PriceSeries a la cartera.
        """
        if not isinstance(series, PriceSeries):
            print(f"Error: Solo se pueden añadir objetos PriceSeries a la cartera.")
            return
            
        self.assets[series.ticker] = series
        print(f"Activo {series.ticker} añadido a la cartera '{self.name}'.")

    @property
    def tickers(self):
        """Devuelve la lista de tickers que hay en la cartera."""
        return list(self.assets.keys())

    def __len__(self):
        """Devuelve cuántos activos (series) hay en la cartera."""
        return len(self.assets)

    # --- ¡NUEVO MÉTODO! LÓGICA DE MONTE CARLO ---
    def run_monte_carlo(self, days: int, simulations: int) -> np.ndarray:
        """
        Ejecuta una simulación de Monte Carlo para la cartera completa,
        preservando la CORRELACIÓN entre activos.
        """
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

    # --- ¡NUEVO MÉTODO! VISUALIZACIÓN ---
    def plot_simulation(self, paths: np.ndarray, title: str):
        """
        Llama a la función de ploteo para mostrar los resultados
        de la simulación de la cartera.
        """
        print(f"Mostrando gráfico para Cartera '{self.name}'...")
        plot_monte_carlo(paths, title)