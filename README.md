# 📊 Market Starter Project

Plantilla base para crear tu propio toolkit de análisis financiero.

### Estructura recomendada
- `src/extractors/` → Para conectarte a APIs y descargar datos
- `src/normalization/` → Para limpiar y estandarizar los datos
- `src/utils/` → Funciones auxiliares
- `src/reports/` → Generación de reportes
- `src/plots/` → Visualización de gráficos
- `src/cli.py` → Punto de entrada principal

### Primeros pasos
```bash
python -m venv venv
source venv/bin/activate   # o venv\Scripts\activate en Windows
pip install -r requirements.txt
python -m src.cli
```
