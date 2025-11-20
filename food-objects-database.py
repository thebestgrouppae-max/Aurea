import pandas as pd
import difflib
import os

def main():
    # === 1. Cargar archivo Excel (segunda fila como cabecera) ===
    base_dir = os.path.dirname(__file__)
    excel_path = os.path.join(base_dir, "database.xlsx")
    df = pd.read_excel(excel_path, header=1)
    df.columns = df.columns.str.strip()  # limpiar espacios

    # === 2. Separar datos de alimentos y productos ===
    df_food = df[["ingredientes", "Carbon savings per kg in kg"]].dropna(subset=["ingredientes"])
    df_prod = df[["categoría superior", "Subcategoría", "Carbon savings per item in kg"]].dropna(subset=["Subcategoría"])

    # === 3. Preguntar el tipo ===
    tipo = input("¿Quieres calcular para 'alimentos' o 'productos'? ").strip().lower()

    # === 4. Alimentos ===
    if tipo.startswith("a"):
        num = int(input("¿Cuántos ingredientes quieres añadir? "))
        total_ahorro = 0
        total_coste_destruccion = 0
        total_emisiones_residuos = 0
        coste_por_kg = 0.30       # € por kg (coste de destrucción)
        emision_por_kg = 0.5      # kg CO₂ por kg eliminado

        for i in range(num):
            print(f"\nIngrediente {i+1}:")
            ingrediente_input = input("Nombre del ingrediente: ").strip().lower()
            cantidad_kg = float(input("Cantidad en kg: ").replace(",", "."))

            match = df_food[df_food["ingredientes"].str.lower() == ingrediente_input]

            if match.empty:
                todos = df_food["ingredientes"].str.lower().tolist()
                similares = difflib.get_close_matches(ingrediente_input, todos, n=1, cutoff=0.6)
                if similares:
                    sugerencia = similares[0]
                    print(f"🤔 '{ingrediente_input}' no se encuentra. ¿Quizás quisiste decir '{sugerencia}'?")
                    confirmar = input("¿Usar esta sugerencia? (s/n): ").strip().lower()
                    if confirmar == "s":
                        match = df_food[df_food["ingredientes"].str.lower() == sugerencia]
                    else:
                        print("❌ Ingrediente saltado.")
                        continue
                else:
                    print(f"⚠️ No se encontró ningún ingrediente similar a '{ingrediente_input}'.")
                    continue

            co2_por_kg = match.iloc[0]["Carbon savings per kg in kg"]
            ahorro = co2_por_kg * cantidad_kg
            coste_destruccion = cantidad_kg * coste_por_kg
            emisiones_residuos = cantidad_kg * emision_por_kg

            total_ahorro += ahorro
            total_coste_destruccion += coste_destruccion
            total_emisiones_residuos += emisiones_residuos

            print(f"✅ {ingrediente_input.capitalize()}: {cantidad_kg} kg → {ahorro:.2f} kg CO₂ ahorrados | 💥 Coste de destrucción: {coste_destruccion:.2f} € | 🗑️ Emisiones eliminación: {emisiones_residuos:.2f} kg CO₂")

        balance_neto = total_ahorro + total_emisiones_residuos

        print(f"\n🌍 Ahorro total de CO₂ (alimentos): {total_ahorro:.2f} kg CO₂")
        print(f"🗑️ Emisiones totales por eliminación (alimentos): {total_emisiones_residuos:.2f} kg CO₂")
        print(f"💶 Coste total de destrucción (alimentos): {total_coste_destruccion:.2f} €")
        print(f"⚖️ Total de CO₂: {balance_neto:.2f} kg CO₂")

    # === 5. Productos ===
    elif tipo.startswith("p"):
        num = int(input("¿Cuántos productos quieres añadir? "))
        total_ahorro = 0
        total_coste_destruccion = 0
        total_emisiones_residuos = 0
        coste_por_unidad = 0.40   # € por unidad (coste de destrucción)
        emision_por_unidad = 0.9  # kg CO₂ por unidad eliminada

        # Listas únicas de categorías (para sugerencias)
        categorias_sup = df_prod["categoría superior"].dropna().str.lower().unique().tolist()
        subcategorias_all = df_prod["Subcategoría"].dropna().str.lower().unique().tolist()

        for i in range(num):
            print(f"\nProducto {i+1}:")
            categoria_sup = input("Categoría superior: ").strip().lower()

            # Verificar si la categoría superior existe
            if categoria_sup not in categorias_sup:
                similar_sup = difflib.get_close_matches(categoria_sup, categorias_sup, n=1, cutoff=0.6)
                if similar_sup:
                    sugerencia_sup = similar_sup[0]
                    print(f"🤔 '{categoria_sup}' no se encuentra. ¿Quizás quisiste decir '{sugerencia_sup}'?")
                    confirmar_sup = input("¿Usar esta sugerencia? (s/n): ").strip().lower()
                    if confirmar_sup == "s":
                        categoria_sup = sugerencia_sup
                    else:
                        print("❌ Categoría saltada.")
                        continue
                else:
                    print(f"⚠️ No se encontró ninguna categoría similar a '{categoria_sup}'.")
                    continue

            # Filtrar subcategorías disponibles para esa categoría
            subcats_cat = df_prod[df_prod["categoría superior"].str.lower() == categoria_sup]["Subcategoría"].str.lower().unique().tolist()

            subcategoria = input("Subcategoría: ").strip().lower()

            if subcategoria not in subcats_cat:
                similar_sub = difflib.get_close_matches(subcategoria, subcats_cat, n=1, cutoff=0.6)
                if similar_sub:
                    sugerencia_sub = similar_sub[0]
                    print(f"🤔 '{subcategoria}' no se encuentra. ¿Quizás quisiste decir '{sugerencia_sub}'?")
                    confirmar_sub = input("¿Usar esta sugerencia? (s/n): ").strip().lower()
                    if confirmar_sub == "s":
                        subcategoria = sugerencia_sub
                    else:
                        print("❌ Subcategoría saltada.")
                        continue
                else:
                    print(f"⚠️ No se encontró ninguna subcategoría similar a '{subcategoria}'.")
                    continue

            cantidad = int(input("Cantidad (número de unidades): "))

            match = df_prod[
                (df_prod["categoría superior"].str.lower() == categoria_sup) &
                (df_prod["Subcategoría"].str.lower() == subcategoria)
            ]

            if match.empty:
                print(f"⚠️ No se encontró coincidencia para {categoria_sup} / {subcategoria}.")
                continue

            co2_por_item = match.iloc[0]["Carbon savings per item in kg"]
            ahorro = co2_por_item * cantidad
            coste_destruccion = cantidad * coste_por_unidad
            emisiones_residuos = cantidad * emision_por_unidad

            total_ahorro += ahorro
            total_coste_destruccion += coste_destruccion
            total_emisiones_residuos += emisiones_residuos

            print(f"✅ {categoria_sup} – {subcategoria}: {cantidad} unidades → {ahorro:.2f} kg CO₂ ahorrados | 💥 Coste de destrucción: {coste_destruccion:.2f} € | 🗑️ Emisiones eliminación: {emisiones_residuos:.2f} kg CO₂")

        balance_neto = total_ahorro + total_emisiones_residuos

        print(f"\n🌍 Ahorro total de CO₂ (productos): {total_ahorro:.2f} kg CO₂")
        print(f"🗑️ Emisiones totales por eliminación (productos): {total_emisiones_residuos:.2f} kg CO₂")
        print(f"💶 Coste total de destrucción (productos): {total_coste_destruccion:.2f} €")
        print(f"⚖️ Total de CO₂: {balance_neto:.2f} kg CO₂")

    else:
        print("⚠️ Opción no válida. Escribe 'alimentos' o 'productos'.")

if __name__ == "__main__":
    main()
