# 📊 Tarea Bloque 1 Introducción - Daniel García López

La estructura que va a seguir este proyecto es la siguiente.

### Estructura recomendada
- `src/extractors/` → Para conectarte a APIs y descargar datos
- `src/normalization/` → Para limpiar y estandarizar los datos
- `src/utils/` → Funciones auxiliares
- `src/reports/` → Generación de reportes
- `src/plots/` → Visualización de gráficos
- `src/cli.py` → Punto de entrada principal

# 📦 Extractors.py
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

A continuación, se van a mostrar los parámetros que hay que usar a la hora de llamar a la API desde el código, estos se especifican en la documentación de cada API.

**Parámetros principales (sacados de la documentación oficial):**
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

**Parámetros principales (sacados de la documentación oficial):**
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

## 📊 Clase TwelveDataExtractor
- URL: https://api.twelvedata.com/time_series

**Parámetros principales (sacados de la documentación oficial):**
- `symbol`: código del activo
- `interval`: "1day", "1h", "15min", etc.
- `outputsize`: número máximo de datos (por defecto 5000)
- `start_date / end_date`: fechas opcionales
- `apikey`: clave de acceso

TwelveData es una API flexible que permite obtener tanto datos diarios como intradía.
En este proyecto se usa el intervalo `1day` para mantener consistencia con las otras fuentes.
En este caso el contenido JSON llega bajo la clave `values`.

El JSON recibido tiene esta forma:

```bash
{
  "meta": {"symbol": "AAPL", "interval": "1day", "currency": "USD"},
  "values": [
    {"datetime": "2024-01-01", "open": "190.00", "high": "192.30", "low": "189.50", "close": "191.80", "volume": "12345678"},
    ...
  ]
}
```

# 🧮 Normalization.py

## 🎯 Objetivo
Dado que las APIs financieras (AlphaVantage, MarketStack y TwelveData) devuelven la información en formatos JSON distintos, con diferentes nombres de campos y estructuras; se crea el módulo `normalizer.py`, cuya función es convertir cualquier tipo de estructura JSON dada por las distintas APIs en un formato estándar para cada una de ellas.

## 🧩 Problema que resuelve
Cada API habla un idioma distinto, siendo:

| API              | Estructura principal                                    | Nombres de campos              | Formato de fecha             |
| ---------------- | ------------------------------------------------------- | ------------------------------ | ---------------------------- |
| **AlphaVantage** | `"Time Series (Daily)" → { fecha: { "1. open": ... } }` | `"1. open"`, `"2. high"`, etc. | `"YYYY-MM-DD"`               |
| **MarketStack**  | `"data" → [ { "open": ..., "close": ... } ]`            | `"open"`, `"close"`, etc.      | `"YYYY-MM-DDT00:00:00+0000"` |
| **TwelveData**   | `"values" → [ { "open": ..., "close": ... } ]`          | `"open"`, `"close"`, etc.      | `"YYYY-MM-DD HH:MM:SS"`      |

Como puede observarse, el **normalizador traduce todos estos formatos a un mismo estándar** de columnas y tipos de datos (`date`, `open`, `high`, `low`, `close`, `volume`, `ticker`, `source`).

## 📊 Formato de salida
El formato de salida que se espera conseguir es el siguiente: 

| Columna | Descripción | Ejemplo |
|----------|--------------|----------|
| `date`   | Fecha del registro (convertida a tipo `datetime` y usada como índice) | `2025-10-22` |
| `open`   | Precio de apertura del día | `255.30` |
| `high`   | Precio máximo del día | `260.00` |
| `low`    | Precio mínimo del día | `252.50` |
| `close`  | Precio de cierre del día | `258.70` |
| `volume` | Volumen de negociación | `48900200` |
| `ticker` | Símbolo del activo | `AAPL` |
| `source` | API de origen de los datos | `alphavantage` |

---
Por lo que la estructura que se espera recibir será algo así:
```bash
              open    high     low   close     volume ticker        source
date
2025-10-14  246.60  248.84  244.70  247.77  35477986.0   AAPL  alphavantage
2025-10-15  249.48  251.82  247.47  249.34  33893611.0   AAPL  alphavantage

```

## Clase Normalizer
Contiene todos los métodos encargados de transformar el JSON bruto que devuelven las APIs en un formato común.
Se crea el atributo global que define las columnas estándar que toda serie ha de tener:
```bash
STANDARD_COLS = ["date","open","high","low","close","volume","ticker","source"]

```
En esta clase se han creado una serie de métodos internos que realizan las funciones pertinentes.

### 🕓 Método datetime `_dt(self, s)`
Convierte cualquier valor de fecha (`str`, `datetime`, etc.) a un objeto `datetime` sin zona horaria. Unificando así el formato temporal de las tres APIs.
```bash
def _dt(self, s):
    if isinstance(s, datetime):
        return s
    dt = parser.isoparse(s)
    return dt.replace(tzinfo=None) if dt.tzinfo else dt

```

### 📦 Método OHLCV `_finalize_ohlcv(self, rows)`
Recibe una lista de diccionarios y devuelve un `DataFrame` limpio y ordenado por fecha.
```bash
df = pd.DataFrame(sorted(rows, key=lambda x: x["date"]))
df["date"] = pd.to_datetime(df["date"])
return df.set_index("date")

```
Centraliza los pasos finales comunes: ordenación, conversión de tipos y asignación del índice.

## 💲 Normalizadores de precios (OHLCV) 
Son los normalizadores para cada una de las APIs para obtener los datos OHLCV, también dentro de las clase normalizer.

### 🧩 Método AlphaVantage `normalize_alphavantage_daily(self, raw, ticker)`
Convierte el JSON de AlphaVantage a formato estándar.
```bash
for k in raw.keys():
    if "Time Series" in k:
        ts = raw[k]; break

```
AlphaVantage usa nombres como `"1. open"` o `"2. high"`, así que el método los renombra como se estableció al principio:
```bash
for d, row in ts.items():
    out.append({
        "date": self._dt(d),
        "open": float(row.get("1. open")),
        "high": float(row.get("2. high")),
        ...
    })

```
Sustituyen los nombres numéricos que da AlphaVantage por `open`, `high`, `low`, etc, y añade las columnas `ticker` y `source`.

### 📈 Método MarketStack `normalize_marketstack_eod(self, raw)`
MarketStack ya usa nombres simples (`open`, `close`, etc.) y devuelve los datos en una lista bajo la clave `"data"`.
```bash
data = raw.get("data", [])
for r in data:
    out.append({
        "date": self._dt(r.get("date")),
        "open": float(r["open"]) if r.get("open") else float("nan"),
        ...
    })

```
En este caso no se necestin traducir datos, sin embargo, algunas APIs como MarketStack a veces devuelven campos sin datos (como un día sin volumen o sin cierre), este `null` se convierte en `None`, y si se intenta hacer `float(None)` da error. Es por eso que si se detecta un `None`, se cambia por `Nan`, que es el valor numérico vacío que entiende pandas.

### 💰 Método TwelveData `normalize_twelvedata_timeseries(self, raw, ticker)`
TwelveData devuelve los datos bajo `"values"`. Su estructura es similar a MarketStack pero con campo `"datetime"`.
```bash
vals = raw.get("values", [])
for r in vals:
    out.append({
        "date": self._dt(r.get("datetime")),
        "open": float(r["open"]),
        ...
    })

```

## 📉 Normalizador de otra tipología de datos (RSI)
Este normalizador va a estar únicamente para las APIs AlphaVantage y TwelveData, ya que el indicador que quería usar era el RSI y en estas dos son las únicas APIs en las que se puede usar sin tener la versión de pago.

### 🔵 Método AlphaVantage RSI `normalize_alphavantage_rsi(self, raw, ticker)`
Extrae el RSI del bloque `"Technical Analysis: RSI"` de AlphaVantage.
```bash
block = raw.get("Technical Analysis: RSI", {})
for d, obj in block.items():
    val = float(obj.get("RSI", "nan"))
    rows.append({"date": self._dt(d), "rsi": val, "ticker": ticker, "source": "alphavantage"})

```
Devuelve un DataFrame con columnas `rsi`, `ticker`, `source`, e `índice date`.

### 🔵 Método TwelveData RSI `normalize_twelvedata_rsi(self, raw, ticker)`
En TwelveData, el RSI llega en `"values"` con pares `{ "datetime": ..., "rsi": ... }`.
```bash
vals = raw.get("values", [])
for r in vals:
    rows.append({
        "date": self._dt(r.get("datetime")),
        "rsi": float(r.get("rsi", "nan")),
        "ticker": ticker,
        "source": "twelvedata"
    })

```
Obteniendo una salida con igual formato al obtenido en AlphaVantage.

# 📦 models.py
Hasta ahora, la información normalizada de cada activo se devolvía como un `pd.DataFrame` genérico. Aunque es útil y se pueden ver los datos, esta forma no captura la identidad de la serie (que activo es y de donde proviene).

Para inyectar coherencia y cohesión de datos en el proyecto, se encapsula el `DataFrame` normalizado y sus metadatos (`ticker`, `source`) dentro de un objeto de dominio que representa este concepto.

Siguiendo el enunciado, se utilizan dataclasses de Python para crear estos objetos, ya que nos permiten definir "contenedores" de datos de forma limpia y concisa. Estos nuevos modelos residirán en `src/models/series.py`.

## 📈 Clase PriceSeries
Se define la `PriceSeries` como un `@dataclass` que representa la serie temporal de un único activo. Es la "ficha" individual de cada activo.

Sus atributos principales son:
- `ticker: str`: El símbolo del activo (ej. "AAPL").
- `source: str`: La API de origen (ej. "alphavantage").
- `data: pd.DataFrame`: El DataFrame normalizado con los datos (OHLCV o RSI).
```bash
# src/models/series.py

@dataclass
class PriceSeries:
    ticker: str
    source: str
    data: pd.DataFrame
    start_date: Optional[datetime] = field(init=False)
    end_date: Optional[datetime] = field(init=False)

    def __post_init__(self):
        # ... (lógica para calcular start_date y end_date)
```

La clase utiliza `__post_init__` para calcular automáticamente las fechas de inicio y fin a partir del DataFrame.

De esta manera solucionamos varios problemas:
- Los datos (`data`) y sus metadatos (`ticker`, `source`) viajan siempre solos en un mismo paquete.
- En lugar de un dataframe genérico, ahora tenemos una `dataclass` que es `PriceSeries`, que es un objeto con significado dentro del dominio de nuestro proyecto.
- Esto nos permite añadir métodos útiles a la clase y sin ensuciar el `dataframe`, como los siguientes.

### 📏 Método `__len__(self)`
Este método nos permite saber el número de filas del `dataframe`. De esta forma nos permite escribir `len(mi_serie)` en lugar de `len(mi_serie.data)`.
```bash
def __len__(self) -> int:
        return len(self.data)
```

### 📚 Método get_summary(self)
Es un método que he creado para mostrar rápidamente la información del objeto sin necesidad de imprimir el `dataframe` entero.
```bash
def get_summary(self) -> str:
        """Devuelve un resumen simple de la serie."""
        if self.data.empty:
            return f"Serie: {self.ticker} ({self.source}) - (Vacía)"
        else:
            return (f"Serie: {self.ticker} ({self.source}) | "
                    f"Rango: {self.start_date.date()} a {self.end_date.date()} | "
                    f"Registros: {len(self)}")
```
