import argparse
import os
import sys
import pandas as pd
import numpy as np 

from .extractors.alphavantage_extractor import AlphaVantageExtractor
from .extractors.marketstack_extractor import MarketStackExtractor
from .extractors.twelvedata_extractor import TwelveDataExtractor
from .extractors.runner import fetch_many
from .normalization.normalizer import Normalizer
from .models.series import PriceSeries, Portfolio


def _get_extractor(provider: str, apikey: str):
    if provider == "alpha":
        return AlphaVantageExtractor(apikey)
    elif provider == "marketstack":
        return MarketStackExtractor(apikey)
    elif provider == "twelvedata":
        return TwelveDataExtractor(apikey)
    else:
        raise SystemExit(f"Proveedor no soportado: {provider}")


def _resolve_api_key(provider: str, apikey_arg: str | None) -> str:
    if apikey_arg:
        return apikey_arg
    env_map = {
        "alpha": "ALPHAVANTAGE_API_KEY",
        "marketstack": "MARKETSTACK_API_KEY",
        "twelvedata": "TWELVEDATA_API_KEY",
    }
    key = os.getenv(env_map[provider])
    if not key:
        raise SystemExit(f"Falta API key. Pasa --apikey o define {env_map[provider]}.")
    return key


def _concat_or_single(dfs: list[pd.DataFrame]) -> pd.DataFrame:
    dfs = [df for df in dfs if df is not None and not df.empty]
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs).sort_index()


# --- FUNCIÓN PARA IMPRIMIR RESULTADOS DE MONTE CARLO ---
def _print_mc_results(paths: np.ndarray, name: str):
    """Imprime estadísticas de un resultado de Monte Carlo."""
    if paths is None or paths.size == 0:
        print(f"   -> {name}: No hay resultados.")
        return
    
    ultimo_precio_real = paths[0, 0] 
    precios_finales = paths[-1, :]   
    
    media_final = np.mean(precios_finales)
    mediana_final = np.median(precios_finales)
    percentil_5 = np.percentile(precios_finales, 5)
    percentil_95 = np.percentile(precios_finales, 95)
    
    retorno_medio_pct = (media_final / ultimo_precio_real - 1) * 100

    print("\n" + "--- Resultados Monte Carlo para: " f"{name}" " ---")
    print(f"   Precio/Valor Inicial: {ultimo_precio_real:12.2f}")
    print(f"   Valor Final (Media):    {media_final:12.2f} (Retorno: {retorno_medio_pct:+.2f}%)")
    print(f"   Valor Final (Mediana):  {mediana_final:12.2f}")
    print(f"   Rango 90%% (P5 - P95):  {percentil_5:12.2f} - {percentil_95:12.2f}")


def main():
    p = argparse.ArgumentParser(description="Extractor multi-API de OHLCV y RSI (formato estandarizado)")
    
    # --- ARGUMENTOS INICIALES ---
    p.add_argument("--provider", choices=["alpha","marketstack","twelvedata"], required=True,
                   help="Proveedor de datos")
    p.add_argument("--symbols", required=True,
                   help="Símbolos separados por comas (ej. AAPL,MSFT o índices como ^GSPC, EUR/USD en TwelveData)")
    p.add_argument("--datatype", choices=["history","indicator"], default="history",
                   help="Tipo de dato: histórico OHLCV o indicador")
    p.add_argument("--indicator", choices=["rsi"], default="rsi",
                   help="Indicador (si datatype=indicator)")
    p.add_argument("--time_period", type=int, default=14,
                   help="Periodo del indicador (por defecto 14)")
    p.add_argument("--start", default=None, help="YYYY-MM-DD (si la API lo soporta)")
    p.add_argument("--end", default=None, help="YYYY-MM-DD (si la API lo soporta)")
    p.add_argument("--apikey", default=None, help="API key (si no, se leerá de variable de entorno)")
    p.add_argument("--to-csv", default=None, help="Ruta de salida CSV (opcional)")
    p.add_argument("--to-json", default=None, help="Ruta de salida JSON (opcional)")
    p.add_argument("--max-workers", type=int, default=4,
                   help="Nº de descargas simultáneas (1 = secuencial)")
    
    # --- ARGUMENTOS DE ESTADÍSTICAS ---
    p.add_argument("--show-stats", action="store_true", 
                   help="Muestra estadísticas adicionales (min/max, retorno medio)")
    p.add_argument("--sma", type=int, default=None, 
                   help="Calcula y muestra la SMA de N días (ej. 20 o 50)")

    # --- ARGUMENTOS MONTE CARLO ---
    p.add_argument("--monte-carlo", type=int, default=None, 
                   metavar="N_SIM",
                   help="Nº de simulaciones Monte Carlo a ejecutar (ej. 1000)")
    p.add_argument("--mc-days", type=int, default=252, 
                   help="Días a futuro para la simulación (def: 252, 1 año bursátil)")
    p.add_argument("--mc-portfolio", action="store_true", 
                   help="Ejecutar simulación sobre la cartera completa (requiere --monte-carlo y datos 'history')")
    p.add_argument("--mc-weights", type=str, default=None, 
                   metavar="W1,W2,..",
                   help="Pesos de cartera '0.6,0.4' (auto-normaliza, si no, pesos iguales)")
    p.add_argument("--mc-plot", action="store_true", 
                   help="Mostrar un gráfico de la simulación (requiere matplotlib)")

    # --- ARGUMENTOS LIMPIEZA ---
    p.add_argument("--clean-na", action="store_true", 
                   help="Aplica limpieza de NaNs (rellena con 'ffill')")
    p.add_argument("--resample-daily", action="store_true", 
                   help="Re-muestrea la serie a frecuencia diaria (rellena fines de semana)")
    p.add_argument("--negative-prices", action="store_true",
                   help="Elimina precios <= 0 reemplazando con NaN (Recomendado)")
    
    # --- ARGUMENTO DE REPORTE ---
    p.add_argument("--report", action="store_true", 
                   help="Genera y muestra un informe detallado de la cartera en Markdown")

    # --- ARGUMENTO DE GRÁFICOS ---
    p.add_argument("--show-plots", action="store_true", 
                   help="Genera y muestra gráficos de análisis de la cartera")
    
    args = p.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    apikey = _resolve_api_key(args.provider, args.apikey)
    ex = _get_extractor(args.provider, apikey)
    norm = Normalizer()
    
    out_by_symbol: dict[str, pd.DataFrame] = {} 

    # --- PRECIOS (OHLCV) ---
    if args.datatype == "history":
        fetch_one = lambda s: ex.history(s, start=args.start, end=args.end)
        if args.provider == "alpha":
            normalize_one = lambda raw, s: norm.normalize_alphavantage_daily(raw, s)
        elif args.provider == "marketstack":
            normalize_one = lambda raw, s: norm.normalize_marketstack_eod(raw)
        else:  
            normalize_one = lambda raw, s: norm.normalize_twelvedata_timeseries(raw, s)

        if args.max_workers == 1:
            for sym in symbols:
                try:
                    raw = fetch_one(sym)
                    out_by_symbol[sym] = normalize_one(raw, sym)
                except Exception as e:
                    print(f"⚠️ Error con {sym}: {e}", file=sys.stderr)
                    out_by_symbol[sym] = pd.DataFrame()
        else:
            out_by_symbol = fetch_many(symbols, fetch_one, normalize_one, max_workers=args.max_workers)

    # --- INDICADORES (RSI) ---
    else:
        if args.indicator != "rsi":
            raise SystemExit("Por ahora solo se implementa RSI en modo indicador.")
        if args.provider == "alpha":
            fetch_one = lambda s: ex.rsi(s, time_period=args.time_period, interval="daily", series_type="close")
            normalize_one = lambda raw, s: norm.normalize_alphavantage_rsi(raw, s)
        elif args.provider == "twelvedata":
            fetch_one = lambda s: ex.rsi(s, time_period=args.time_period, interval="1day")
            normalize_one = lambda raw, s: norm.normalize_twelvedata_rsi(raw, s)
        else:
            print(" MarketStack no ofrece RSI gratuito.", file=sys.stderr)
            fetch_one = lambda s: {}
            normalize_one = lambda raw, s: pd.DataFrame()

        if args.max_workers == 1:
            for sym in symbols:
                try:
                    raw = fetch_one(sym)
                    out_by_symbol[sym] = normalize_one(raw, sym)
                except Exception as e:
                    print(f"⚠️ Error con {sym}: {e}", file=sys.stderr)
                    out_by_symbol[sym] = pd.DataFrame()
        else:
            out_by_symbol = fetch_many(symbols, fetch_one, normalize_one, max_workers=args.max_workers)
    
    
    # --- Portfolio y PriceSeries --- 
    portfolio_name = f"Cartera CLI ({args.provider} - {args.datatype})"
    cartera = Portfolio(name=portfolio_name)
    
    for sym, df in out_by_symbol.items():
        if df is not None and not df.empty:
            source = df['source'].iloc[0] if 'source' in df.columns else args.provider
            serie = PriceSeries(ticker=sym, source=source, data=df)

            if args.negative_prices:
                serie.negative_prices()

            if args.clean_na:
                serie.fillna() # Llama al método que usa 'ffill' por defecto
            
            if args.resample_daily:
                serie.resample_daily() # Llama al método que re-muestrea y usa 'ffill'

            cartera.add_series(serie)

    out = _concat_or_single(list(out_by_symbol.values()))


    # --- Salida por pantalla --- 
    if not cartera.assets: 
        print("\n No hay datos para mostrar.")
    else:
        print("\n" + "="*40)
        print(f"📊 Resumen de la Cartera: '{cartera.name}'")
        print(f"Total de activos: {len(cartera)}")
        print("="*40)

        for ticker, series in cartera.assets.items():
            print(f"\n  -> {series.get_summary()}")
            if args.sma:
                sma = series.calculate_sma(args.sma)
                if sma is not None and not sma.empty:
                    print(f"     SMA({args.sma}d): {sma.iloc[-1]:.2f}") 
            if args.show_stats:
                stats = series.get_min_max()
                returns = series.get_daily_returns()
                if stats:
                    print(f"     Mín: {stats['min_value']:.2f} (el {stats['min_date'].date()})")
                    print(f"     Máx: {stats['max_value']:.2f} (el {stats['max_date'].date()})")
                if returns is not None:
                    print(f"     Retorno Diario Medio: {returns.mean() * 100:.4f}%")
        print("\n" + "="*40)


    # --- SOLUCIÓN PARA EL GRÁFICO DE TARTA ---
    
    if args.mc_weights and cartera.assets:
        pesos_cartera = None
        tickers_cartera = cartera.tickers
        try:
            pesos_lista = [float(p.strip()) for p in args.mc_weights.split(',')]
            if len(pesos_lista) != len(cartera):
                raise ValueError(f"Número de pesos ({len(pesos_lista)}) no coincide con número de activos ({len(cartera)})")
            s = sum(pesos_lista)
            if not np.isclose(s, 1.0) and s > 0:
                print(f"Advertencia: Los pesos suman {s:.2f}, se normalizarán.")
                pesos_lista = [p / s for p in pesos_lista]
            pesos_cartera = {ticker: peso for ticker, peso in zip(tickers_cartera, pesos_lista)}
        except Exception as e:
            print(f"⚠️ Error al parsear pesos: {e}. Usando pesos iguales.")
        
        if pesos_cartera is None:
            print(f"Usando pesos iguales (1/{len(cartera)}) para {len(cartera)} activos.")
            peso_igual = 1.0 / len(cartera)
            pesos_cartera = {ticker: peso_igual for ticker in tickers_cartera}
        
        cartera.weights = pesos_cartera
        print(f"Pesos de cartera asignados: {cartera.weights}")
    

    # --- SIMULACIÓN MONTE CARLO ---
    
    if args.monte_carlo and args.monte_carlo > 0:
        print("\n" + "="*40)
        print(f"🔬 Ejecutando Simulación Monte Carlo")
        print(f"   Simulaciones: {args.monte_carlo} | Días a futuro: {args.mc_days}")
        print("="*40)
        
        # --- SIMULACIÓN DE LA CARTERA ---
        if args.mc_portfolio:
            if not cartera.assets:
                print("⛔ No hay activos en la cartera para simular.")
            elif not cartera.weights:
                print("⛔ No se pueden simular pesos de cartera porque no se definieron (usa --mc-weights).")
            else:
                print(f"Simulando cartera completa. Pesos: {cartera.weights}")
                try:
                    paths = cartera.run_monte_carlo(args.mc_days, args.monte_carlo)
                    _print_mc_results(paths, f"Cartera '{cartera.name}'")
                    
                    if args.mc_plot:
                        cartera.plot_simulation(paths, f"Simulación Monte Carlo - Cartera '{cartera.name}'")
                        
                except Exception as e:
                    print(f"⚠️ Error fatal en simulación de cartera: {e}")

        # --- SIMULACIÓN DE ACTIVOS INDIVIDUALMENTE ---
        else:
            print("Simulando activos individuales...")
            for ticker, series in cartera.assets.items():
                if series.main_col != 'close' or series.data.empty:
                    print(f"\n   -> Omitiendo {ticker} (no es 'close' o está vacío)")
                    continue
                
                try:
                    paths = series.run_monte_carlo(args.mc_days, args.monte_carlo)
                    _print_mc_results(paths, ticker)
                    
                    if args.mc_plot:
                        series.plot_simulation(paths, f"Simulación Monte Carlo - {ticker}")
                        
                except Exception as e:
                    print(f"⚠️ Error en simulación de {ticker}: {e}")
        
        print("\n" + "="*40)

    # --- REPORTE ---
    if args.report:
        print("\n" + "="*50)
        print(" GENERANDO REPORTE DE CARTERA ".center(50, "="))
        print("="*50 + "\n")
        
        try:
            informe_md = cartera.report()
            print(informe_md)
        except Exception as e:
            print(f"⚠️ Error al generar el informe: {e}")
            import traceback
            traceback.print_exc() 
        
        print("\n" + "="*50)
        print(" FIN DEL REPORTE ".center(50, "="))
        print("="*50)

    # --- GRÁFICOS ---
    if args.show_plots:
        print("\n" + "="*50)
        print(" GENERANDO GRÁFICOS DE CARTERA ".center(50, "="))
        print("="*50 + "\n")
        
        try:
            cartera.plots_report()
        except Exception as e:
            print(f"⚠️ Error al generar los gráficos: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*50)
        print(" FIN DE LOS GRÁFICOS ".center(50, "="))
        print("="*50)


    if args.to_csv:
        out.to_csv(args.to_csv, index=True)
        print(f"💾 Guardado CSV combinado en: {args.to_csv}")
    if args.to_json:
        out.to_json(args.to_json, orient="records", date_format="iso")
        print(f"💾 Guardado JSON combinado en: {args.to_json}")


if __name__ == "__main__":
    main()