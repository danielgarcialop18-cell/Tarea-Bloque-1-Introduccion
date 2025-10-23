# src/extractors/runner.py
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable, Dict
import pandas as pd


def fetch_many(
    symbols: Iterable[str],
    fetch_one: Callable[[str], dict],
    normalize_one: Callable[[dict, str], pd.DataFrame],
    max_workers: int = 8,
) -> Dict[str, pd.DataFrame]:
    """
    Descarga N símbolos en paralelo y devuelve un diccionario con los DataFrames normalizados.
    
    Parámetros:
    -----------
    symbols : Iterable[str]
        Lista de símbolos o tickers a descargar (por ejemplo: ["AAPL", "MSFT", "EURUSD=X"]).
    fetch_one : Callable[[str], dict]
        Función que recibe un símbolo y devuelve su JSON crudo desde la API.
        Ejemplo: lambda s: extractor.history(s, start, end)
    normalize_one : Callable[[dict, str], pd.DataFrame]
        Función que recibe (raw_json, symbol) y devuelve un DataFrame normalizado.
    max_workers : int, opcional
        Número máximo de hilos (descargas simultáneas). Por defecto 8.
    
    Devuelve:
    ----------
    Dict[str, pd.DataFrame]
        Diccionario donde cada clave es un símbolo y cada valor es un DataFrame ya normalizado.
    """

    results: Dict[str, pd.DataFrame] = {}

    # Creamos un "pool" de hilos para ejecutar tareas en paralelo
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Enviamos una tarea por símbolo y guardamos la relación Future -> símbolo
        futures = {executor.submit(fetch_one, s): s for s in symbols}

        # Iteramos sobre las tareas a medida que terminan
        for future in as_completed(futures):
            sym = futures[future]
            try:
                # Obtenemos el JSON crudo desde la API
                raw = future.result()
                # Lo normalizamos usando la función pasada
                df = normalize_one(raw, sym)
                # Guardamos el DataFrame en el diccionario de resultados
                results[sym] = df
                print(f"✅ {sym} descargado correctamente ({len(df)} filas).")
            except Exception as e:
                # Si hay error, seguimos sin romper el proceso completo
                results[sym] = pd.DataFrame()
                print(f"⚠️ Error al descargar {sym}: {e}")

    # Devolvemos todos los resultados (cada uno un DataFrame normalizado)
    return results
