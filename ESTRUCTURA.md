```mermaid
classDiagram
    direction LR

    %% --- Clases de Extractores y Herencia ---
    class BaseExtractor {
        <<Abstract>>
        +history(ticker, start, end)*
    }
    class AlphaVantageExtractor {
        +history(ticker, start, end)
        +rsi(symbol)
    }
    class MarketStackExtractor {
        +history(ticker, start, end)
    }
    class TwelveDataExtractor {
        +history(ticker, start, end)
        +rsi(symbol)
    }

    BaseExtractor <|-- AlphaVantageExtractor : hereda
    BaseExtractor <|-- MarketStackExtractor : hereda
    BaseExtractor <|-- TwelveDataExtractor : hereda


    %% --- Clases de Modelos y Contención ---
    class PriceSeries {
        +ticker: str
        +data: DataFrame
        +run_monte_carlo()
        +plot_simulation()
    }

    class Portfolio {
        +name: str
        +assets: Dict
        +add_series(PriceSeries)
        +run_monte_carlo()
        +report()
        +plots_report()
    }

    %% Portfolio "contiene" múltiples PriceSeries
    Portfolio "1" o-- "*" PriceSeries : Contiene


    %% --- Clases de Soporte ---
    class Normalizer {
         +normalize_alphavantage_daily(raw, ticker)
         +normalize_marketstack_eod(raw)
         +normalize_twelvedata_timeseries(raw)
    }

    
    %% --- Módulos de Utilidad (Funciones) ---
    component runner_py {
        <<Utilidad>>
        +fetch_many()
    }

    component plots_py {
         <<Utilidad>>
         +plot_monte_carlo()
         +plot_correlation_heatmap()
         +plot_normalized_prices()
    }


    %% --- Punto de Entrada y Dependencias ---
    component cli_main {
        <<Punto de Entrada>>
        +main()
    }

    cli_main ..> Portfolio : Crea y usa
    cli_main ..> PriceSeries : Crea y usa
    cli_main ..> Normalizer : Usa
    cli_main ..> BaseExtractor : Usa (a través de _get_extractor)
    cli_main ..> runner_py : Usa (para fetch_many)

    PriceSeries ..> plots_py : Usa (para plot_simulation)
    Portfolio ..> plots_py : Usa (para plots_report)
```