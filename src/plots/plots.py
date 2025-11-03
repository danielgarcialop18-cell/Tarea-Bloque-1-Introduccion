import matplotlib.pyplot as plt
import numpy as np  
import pandas as pd  
import seaborn as sns

def plot_prices(df):
    plt.plot(df["date"], df["close"])
    plt.title("Evolución del precio")
    plt.show()


def plot_monte_carlo(simulation_paths: np.ndarray, title: str):
    if simulation_paths is None or simulation_paths.size == 0:
        print("No hay datos que graficar.")
        return

    plt.figure(figsize=(12, 7))
    
    # Grafica todas las simulaciones (con transparencia)
    plt.plot(simulation_paths, color='blue', alpha=0.05)
    
    # Calcula y grafica la media y los percentiles
    mean_path = np.mean(simulation_paths, axis=1)
    median_path = np.median(simulation_paths, axis=1)
    p5_path = np.percentile(simulation_paths, 5, axis=1)
    p95_path = np.percentile(simulation_paths, 95, axis=1)

    plt.plot(mean_path, color='red', linewidth=2, label='Media')
    plt.plot(median_path, color='orange', linestyle='--', linewidth=2, label='Mediana (P50)')
    plt.plot(p5_path, color='grey', linestyle=':', label='Percentil 5')
    plt.plot(p95_path, color='grey', linestyle=':', label='Percentil 95')
    
    # Rellenar el área de confianza
    plt.fill_between(range(len(mean_path)), p5_path, p95_path, color='grey', alpha=0.2, label='Rango 90% Confianza')

    plt.title(f"Simulación Monte Carlo: {title}")
    plt.xlabel("Días a futuro")
    plt.ylabel("Valor / Precio Simulado")
    plt.legend()
    plt.grid(True)
    
    print(f"Mostrando gráfico: {title}...")
    plt.show()


def plot_normalized_prices(df_closes_common: pd.DataFrame):
   
    if df_closes_common.empty:
        print("No hay datos para el gráfico de rendimiento normalizado.")
        return

    print("Mostrando gráfico: Rendimiento Normalizado (Base 100)...")
    
    # Normalizar: (precio_actual / precio_inicial) * 100
    normalized_df = (df_closes_common / df_closes_common.iloc[0]) * 100
    
    plt.figure(figsize=(12, 7))
    plt.plot(normalized_df)
    
    plt.title("Rendimiento Normalizado (Base 100)")
    plt.xlabel(f"Fecha (Desde {df_closes_common.index.min().date()})")
    plt.ylabel("Rendimiento (Base 100)")
    plt.legend(normalized_df.columns)
    plt.grid(True)
    plt.show()


def plot_correlation_heatmap(corr_matrix: pd.DataFrame):
  
    if corr_matrix.empty:
        print("No hay datos para el mapa de calor de correlación.")
        return
        
    print("Mostrando gráfico: Mapa de Calor de Correlación...")
    
    plt.figure(figsize=(10, 7))
    sns.heatmap(
        corr_matrix, 
        annot=True,     
        cmap='coolwarm',  
        fmt=".2f",        
        linewidths=.5     
    )
    plt.title("Mapa de Calor de Correlación (Retornos Logarítmicos)")
    plt.show()


def plot_weights_pie_chart(weights: dict, title: str):
    if not weights:
        print("No hay pesos definidos para el gráfico de tarta.")
        return
        
    print(f"Mostrando gráfico: {title}...")

    labels = weights.keys()
    sizes = weights.values()
    
    plt.figure(figsize=(8, 8))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, pctdistance=0.85)
    
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    
    plt.title(title)
    plt.axis('equal') 
    plt.show()