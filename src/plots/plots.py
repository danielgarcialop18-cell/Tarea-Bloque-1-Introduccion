import matplotlib.pyplot as plt
import numpy as np  
def plot_prices(df):
    plt.plot(df["date"], df["close"])
    plt.title("Evolución del precio")
    plt.show()

# --- AÑADE TODA ESTA NUEVA FUNCIÓN ---

def plot_monte_carlo(simulation_paths: np.ndarray, title: str):
    """
    Grafica las trayectorias de una simulación Monte Carlo.
    
    Parámetros:
    simulation_paths: Array de (días, simulaciones)
    """
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