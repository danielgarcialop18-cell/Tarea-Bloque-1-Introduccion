# src/models/series.py

from __future__ import annotations
from dataclasses import dataclass, field # Importamos dataclass y field
from datetime import datetime
import pandas as pd
from typing import Optional, Dict, List # Para "pistas de tipo" (str, List, etc.)

@dataclass
class PriceSeries:
    """
    Representa la serie histórica normalizada de precios para UN activo.
    Usa un dataclass para guardar los datos de forma coherente.
    """
    
    # 1. CAMPOS QUE PASAMOS AL CREARLA
    # ---------------------------------
    # Estos son los datos "de entrada". 
    # El @dataclass crea el __init__(self, ticker, source, data) por nosotros.
    
    ticker: str
    source: str
    data: pd.DataFrame
    
    # 2. CAMPOS CALCULADOS (que no pasamos al crearla)
    # -----------------------------------------------
    # Queremos que la propia serie sepa su fecha de inicio y fin,
    # pero no queremos pasárselo, queremos que lo calcule sola.
    # 'init=False' significa: "este campo no se pide en el __init__".
    
    start_date: Optional[datetime] = field(init=False)
    end_date: Optional[datetime] = field(init=False)

    def __post_init__(self):
        """
        Esta función especial se ejecuta AUTOMÁTICAMENTE
        justo después del __init__ que ha creado el dataclass.
        
        Es el lugar perfecto para calcular nuestros campos.
        """
        if not self.data.empty:
            # Calculamos las fechas y las guardamos en las variables
            self.start_date = self.data.index.min()
            self.end_date = self.data.index.max()
        else:
            self.start_date = None
            self.end_date = None

    def __len__(self) -> int:
        """Devuelve el número de registros (filas) del DataFrame."""
        return len(self.data)

    def get_summary(self) -> str:
        """Devuelve un resumen simple de la serie."""
        if self.data.empty:
            return f"Serie: {self.ticker} ({self.source}) - (Vacía)"
        else:
            return (f"Serie: {self.ticker} ({self.source}) | "
                    f"Rango: {self.start_date.date()} a {self.end_date.date()} | "
                    f"Registros: {len(self)}")


@dataclass
class Portfolio:
    """
    Representa una cartera o colección de PriceSeries (activos).
    También es un dataclass.
    """
    name: str # El nombre de la cartera, ej: "Mi Cartera"
    
    # Un diccionario para guardar los objetos PriceSeries.
    # Usamos 'default_factory' para asegurarnos de que crea un 
    # diccionario vacío nuevo cada vez que creamos una cartera.
    assets: Dict[str, PriceSeries] = field(default_factory=dict)
    
    # Un diccionario opcional para los pesos, ej: {"AAPL": 0.6, "MSFT": 0.4}
    weights: Optional[Dict[str, float]] = None

    def add_series(self, series: PriceSeries):
        """
        Método para añadir un objeto PriceSeries a la cartera.
        """
        # Comprobamos que lo que nos pasan es un PriceSeries
        if not isinstance(series, PriceSeries):
            print(f"Error: Solo se pueden añadir objetos PriceSeries a la cartera.")
            return
            
        # Lo guardamos en el diccionario, usando el ticker como clave
        self.assets[series.ticker] = series
        print(f"Activo {series.ticker} añadido a la cartera '{self.name}'.")

    @property
    def tickers(self) -> List[str]:
        """Devuelve la lista de tickers que hay en la cartera."""
        return list(self.assets.keys())

    def __len__(self) -> int:
        """Devuelve cuántos activos (series) hay en la cartera."""
        return len(self.assets)