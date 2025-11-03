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

    results: Dict[str, pd.DataFrame] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_one, s): s for s in symbols}

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

    return results
