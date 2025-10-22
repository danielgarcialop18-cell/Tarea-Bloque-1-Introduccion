# 📊 Tarea Bloque 1 Introducción - Daniel García López

La estructura que va a seguir este proyecto es la siguiente.

### Estructura recomendada
- `src/extractors/` → Para conectarte a APIs y descargar datos
- `src/normalization/` → Para limpiar y estandarizar los datos
- `src/utils/` → Funciones auxiliares
- `src/reports/` → Generación de reportes
- `src/plots/` → Visualización de gráficos
- `src/cli.py` → Punto de entrada principal

# 📦 Extractors
En este módulo se establece la conexión entre el proyecto y las distintas APIs a usar, que en este caso van a ser AlphaVantage, MarketStack y TwelveData.

En este módulo se extraerá la información de distintas acciones, índices o divisas de las APIs en formato JSON y teniendo en cuenta como entregan los datos cada una de estas plataformas.

## 🎯 Objetivo general del diseño
Pese a que las APIs financieras ofrezcan información similar, utilizan nomenclaturas, parámetros y formatos distintos.
Para unificar el acceso y mantener el código ordenado, se ha diseñado un sistema basado en clases independientes para cada una de las APIs que heredan de una clase común.
```bash
BaseExtractor
│
├── AlphaVantageExtractor
├── MarketStackExtractor
└── TwelveDataExtractor
```
De esta forma todos los extractores:
- Comparten la misma interfaz (history(symbol, start, end))
- Se comportan igual desde fuera
- Cada uno se comunica con su API correspondiente

## 🧱 Clase base: BaseExtractor
Esta clase define cual debe ser la base de la que hereden las clases de cada API.
```bash
class BaseExtractor:
    def history(self, symbol: str, start: str | None = None, end: str | None = None):
        raise NotImplementedError
```
No implementa ninguna lógica concreta.
Simplemente obliga a las subclases a definir su propio método history() con la misma firma.
Esto garantiza coherencia y facilita la escalabilidad del proyecto: si en el futuro se añade una nueva API, bastará con crear una clase que herede de BaseExtractor e implemente ese método.

## 🌍 Clase AlphaVantageExtractor
- URL: https://www.alphavantage.co/query

**Parámetros principales:**
- `symbol`: código del activo
- `interval`: intervalo de tiempo (por ejemplo, `"1day"`)
- `outputsize`: número máximo de registros
- `apikey`: clave de acceso

La API de AlphaVantage devuelve los datos históricos dentro de una clave llamada `Time Series (Daily)`.
A diferencia de otras APIs, no permite filtrar por fechas desde la URL; por tanto, el extractor descarga el histórico completo o los últimos 100 días y el filtrado temporal se realiza posteriormente (por ejemplo, con pandas). 

El JSON recibido tiene esta forma:
```bash
{
  "Meta Data": {...},
  "Time Series (Daily)": {
    "2024-01-01": {"1. open": "150.00", "2. high": "151.20", "3. low": "149.80", "4. close": "150.75", "5. volume": "35477986"},
    ...
  }
}
```

## 💼 Clase MarketStackExtractor
- URL: http://api.marketstack.com/v1/eod

**Parámetros principales:**
- `access_key`: APIkey
- `symbols`: código del activo
- `date_from / date_to`: rango de fechas
- `limit`: cantidad máxima de registros a devolver

A diferencia de AlphaVantage, MarketStack sí permite filtrar por fechas directamente en la solicitud.
Los datos se devuelven bajo la clave `data` y ya incluyen información diaria (EOD — End Of Day).

El JSON recibido tiene esta forma:

```bash
{
  "pagination": {...},
  "data": [
    {"date": "2024-01-01", "symbol": "AAPL", "open": 190.00, "high": 192.30, "low": 189.50, "close": 191.80, "volume": 10234500},
    ...
  ]
}
```