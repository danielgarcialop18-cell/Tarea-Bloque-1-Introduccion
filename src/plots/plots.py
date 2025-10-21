# plots.py — Visualización
# ------------------------
# Aquí puedes crear gráficos con matplotlib o plotly.

import matplotlib.pyplot as plt

def plot_prices(df):
    plt.plot(df["date"], df["close"])
    plt.title("Evolución del precio")
    plt.show()
