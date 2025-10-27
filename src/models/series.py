# src/models/series.py

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
from typing import Optional, Dict, List, Union # <--- CAMBIO: Añadido Union

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
    
    # 2. CAMPOS CALCULADOS (que no pasamos al crearla)
    start_date: Optional[datetime] = field(init=False)
    end_date: Optional[datetime] = field(init=False)
    
    # --- NUEVOS CAMPOS ESTADÍSTICOS AUTOMÁTICOS ---
    # Se calcularán en __post_init__
    main_col: Optional[str] = field(init=False, default=None) # Columna principal (close o rsi)
    mean_value: Optional[float] = field(init=False, default=float('nan'))
    std_dev_value: Optional[float] = field(init=False, default=float('nan'))

    def __post_init__(self):
        """
        Esta función especial se ejecuta AUTOMÁTICAMENTE
        justo después del __init__ que ha creado el dataclass.
        
        Es el lugar perfecto para calcular nuestros campos.
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