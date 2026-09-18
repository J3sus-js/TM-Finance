from datetime import datetime
from contextlib import contextmanager
import sqlite3
import csv
import shutil
import os

DB_NAME = "control_gastos.db"

def hacer_copia_seguridad():
    """Genera una copia de respaldo automática de la base de datos al iniciar."""
    if os.path.exists(DB_NAME):
        os.makedirs("backups", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = os.path.join("backups", f"control_gastos_backup_{timestamp}.db")
        try:
            shutil.copy2(DB_NAME, backup_name)
            print(f"[Backup] Copia de seguridad creada: {backup_name}")
        except Exception as e:
            print(f"[Backup] Error al crear la copia de seguridad: {e}")

@contextmanager
def obtener_conexion():
    """Gestor de contexto para manejar conexiones y cierres automáticamente."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def inicializar_bd():
    """Crea las tablas necesarias si no existen con optimizaciones de SQLite."""
    with obtener_conexion() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute('''
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL DEFAULT (date('now')),
                categoria TEXT NOT NULL,
                descripcion TEXT DEFAULT '',
                monto REAL NOT NULL CHECK(monto > 0),
                metodo_pago TEXT NOT NULL DEFAULT 'Efectivo'
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS presupuestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT UNIQUE NOT NULL,
                limite REAL NOT NULL CHECK(limite > 0)
            )
        ''')

def definir_presupuesto(categoria: str, limite: float):
    """Establece o actualiza un presupuesto mensual por categoría."""
    if limite <= 0:
        raise ValueError("El límite debe ser mayor a cero.")
    with obtener_conexion() as conn:
        conn.execute('''
            INSERT INTO presupuestos (categoria, limite) VALUES (?, ?)
            ON CONFLICT(categoria) DO UPDATE SET limite = ?
        ''', (categoria.strip(), limite, limite))

def obtener_presupuestos() -> list:
    """Obtiene todos los presupuestos configurados."""
    with obtener_conexion() as conn:
        cursor = conn.execute("SELECT categoria, limite FROM presupuestos")
        return [dict(fila) for fila in cursor.fetchall()]

def verificar_presupuesto_al_gastar(categoria: str, monto_nuevo: float, fecha_gasto: str):
    """Verifica si el gasto excede o se acerca al presupuesto de la categoría en ese mes."""
    try:
        anio, mes, _ = fecha_gasto.split("-")
        mes_str = f"{anio}-{mes}"
    except ValueError:
        return

    with obtener_conexion() as conn:
        cursor_p = conn.execute("SELECT limite FROM presupuestos WHERE categoria = ?", (categoria.strip(),))
        res_p = cursor_p.fetchone()
        if not res_p:
            return
        
        limite = res_p["limite"]
        cursor_g = conn.execute('''
            SELECT SUM(monto) AS total FROM gastos 
            WHERE categoria = ? AND strftime('%Y-%m', fecha) = ?
        ''', (categoria.strip(), mes_str))
        res_g = cursor_g.fetchone()
        gastado_actual = res_g["total"] if res_g and res_g["total"] is not None else 0.0

        total_proyectado = gastado_actual + monto_nuevo
        print(f"\n[AVISO DE PRESUPUESTO] Categoría '{categoria}':")
        print(f" • Límite mensual: ${limite:.2f}")
        print(f" • Gastado hasta ahora + este gasto: ${total_proyectado:.2f}")
        
        if total_proyectado > limite:
            print(f" ⚠️ ¡ALERTA! Este gasto hace que SUPÈRES el presupuesto por ${total_proyectado - limite:.2f}.")
        elif total_proyectado >= (limite * 0.8):
            print(" ⚠️ ¡Cuidado! Estás cerca de alcanzar o superar el 80% de tu presupuesto.")

def agregar_gasto(categoria: str, monto: float, descripcion: str = "", fecha: str = None, metodo_pago: str = "Efectivo"):
    """Registra un nuevo gasto validando montos y fechas."""
    if monto <= 0:
        raise ValueError("El monto del gasto debe ser mayor a cero.")
    
    if not fecha:
        fecha = datetime.now().strftime("%Y-%m-%d")
    else:
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            raise ValueError("La fecha debe tener el formato YYYY-MM-DD.")

    verificar_presupuesto_al_gastar(categoria, monto, fecha)

    with obtener_conexion() as conn:
        conn.execute('''
            INSERT INTO gastos (fecha, categoria, descripcion, monto, metodo_pago)
            VALUES (?, ?, ?, ?, ?)
        ''', (fecha, categoria.strip(), descripcion.strip(), monto, metodo_pago.strip()))

def listar_gastos(limite: int = 15, offset: int = 0) -> list:
    """Obtiene una lista de los gastos más recientes con paginación."""
    with obtener_conexion() as conn:
        cursor = conn.execute('''
            SELECT id, fecha, categoria, descripcion, monto, metodo_pago 
            FROM gastos 
            ORDER BY fecha DESC, id DESC 
            LIMIT ? OFFSET ?
        ''', (limite, offset))
        return [dict(fila) for fila in cursor.fetchall()]

def listar_gastos_avanzado(fecha_inicio: str = None, fecha_fin: str = None, categoria: str = None, metodo_pago: str = None) -> list:
    """Filtra los gastos de forma avanzada utilizando múltiples criterios opcionales."""
    query = "SELECT id, fecha, categoria, descripcion, monto, metodo_pago FROM gastos WHERE 1=1"
    parametros = []

    if fecha_inicio and fecha_fin:
        query += " AND fecha BETWEEN ? AND ?"
        parametros.extend([fecha_inicio, fecha_fin])
    elif fecha_inicio:
        query += " AND fecha >= ?"
        parametros.append(fecha_inicio)
    elif fecha_fin:
        query += " AND fecha <= ?"
        parametros.append(fecha_fin)

    if categoria:
        query += " AND categoria COLLATE NOCASE = ?"
        parametros.append(categoria.strip())

    if metodo_pago:
        query += " AND metodo_pago COLLATE NOCASE = ?"
        parametros.append(metodo_pago.strip())

    query += " ORDER BY fecha DESC"

    with obtener_conexion() as conn:
        cursor = conn.execute(query, parametros)
        return [dict(fila) for fila in cursor.fetchall()]

def actualizar_gasto(gasto_id: int, categoria: str = None, monto: float = None, descripcion: str = None, fecha: str = None, metodo_pago: str = None):
    """Actualiza los campos de un gasto existente de forma dinámica."""
    campos = []
    valores = []
    
    if categoria:
        campos.append("categoria = ?")
        valores.append(categoria.strip())
    if monto is not None:
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a cero.")
        campos.append("monto = ?")
        valores.append(monto)
    if descripcion is not None:
        campos.append("descripcion = ?")
        valores.append(descripcion.strip())
    if fecha:
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            raise ValueError("La fecha debe tener el formato YYYY-MM-DD.")
        campos.append("fecha = ?")
        valores.append(fecha)
    if metodo_pago:
        campos.append("metodo_pago = ?")
        valores.append(metodo_pago.strip())
        
    if not campos:
        return
        
    valores.append(gasto_id)
    query = f"UPDATE gastos SET {', '.join(campos)} WHERE id = ?"
    
    with obtener_conexion() as conn:
        cursor = conn.execute(query, valores)
        if cursor.rowcount == 0:
            raise ValueError(f"No se encontró ningún gasto con el ID {gasto_id}.")

def eliminar_gasto(gasto_id: int):
    """Elimina un gasto por su ID."""
    with obtener_conexion() as conn:
        cursor = conn.execute("DELETE FROM gastos WHERE id = ?", (gasto_id,))
        if cursor.rowcount == 0:
            raise ValueError(f"No se encontró ningún gasto con el ID {gasto_id}.")

def obtener_total_gastos() -> float:
    """Retorna la suma total de los gastos registrados."""
    with obtener_conexion() as conn:
        cursor = conn.execute("SELECT SUM(monto) AS total FROM gastos")
        resultado = cursor.fetchone()
        return resultado["total"] if resultado["total"] is not None else 0.0

def gastos_por_categoria() -> list:
    """Agrupa y suma los gastos por categoría."""
    with obtener_conexion() as conn:
        cursor = conn.execute('''
            SELECT categoria, SUM(monto) AS total_categoria
            FROM gastos
            GROUP BY categoria
            ORDER BY total_categoria DESC
        ''')
        return [dict(fila) for fila in cursor.fetchall()]

def resumen_mensual(anio: int, mes: int) -> dict:
    """Devuelve el total gastado y desglose para un año y mes específicos."""
    mes_str = f"{anio:04d}-{mes:02d}"
    with obtener_conexion() as conn:
        cursor_total = conn.execute('''
            SELECT SUM(monto) AS total FROM gastos 
            WHERE strftime('%Y-%m', fecha) = ?
        ''', (mes_str,))
        total = cursor_total.fetchone()["total"] or 0.0
        
        cursor_cat = conn.execute('''
            SELECT categoria, SUM(monto) AS total_categoria 
            FROM gastos 
            WHERE strftime('%Y-%m', fecha) = ?
            GROUP BY categoria
        ''', (mes_str,))
        categorias = [dict(row) for row in cursor_cat.fetchall()]
        
        return {"mes": mes_str, "total_mes": total, "desglose": categorias}

def resumen_anual(anio: int) -> dict:
    """Agrupa y calcula el comportamiento financiero mes a mes para un año específico."""
    anio_str = f"{anio:04d}"
    with obtener_conexion() as conn:
        cursor_total = conn.execute('''
            SELECT SUM(monto) AS total FROM gastos 
            WHERE strftime('%Y', fecha) = ?
        ''', (anio_str,))
        total_anual = cursor_total.fetchone()["total"] or 0.0
        
        cursor_meses = conn.execute('''
            SELECT strftime('%m', fecha) AS mes, SUM(monto) AS total_mes
            FROM gastos
            WHERE strftime('%Y', fecha) = ?
            GROUP BY mes
            ORDER BY mes ASC
        ''', (anio_str,))
        meses_data = [dict(row) for row in cursor_meses.fetchall()]
        
        return {"anio": anio_str, "total_anual": total_anual, "desglose_meses": meses_data}

def exportar_a_csv(nombre_archivo: str = "reporte_gastos.csv"):
    """Exporta todos los registros de gastos a un archivo CSV."""
    with obtener_conexion() as conn:
        cursor = conn.execute("SELECT id, fecha, categoria, descripcion, monto, metodo_pago FROM gastos ORDER BY fecha DESC")
        registros = cursor.fetchall()
        
    with open(nombre_archivo, mode="w", newline="", encoding="utf-8") as archivo:
        writer = csv.writer(archivo)
        writer.writerow(["ID", "Fecha", "Categoría", "Descripción", "Monto", "Método de Pago"])
        for fila in registros:
            writer.writerow([fila["id"], fila["fecha"], fila["categoria"], fila["descripcion"], fila["monto"], fila["metodo_pago"]])

def mostrar_barra_progreso(actual: float, total: float, ancho: int = 20):
    """Genera una barra de progreso basada en texto."""
    if total <= 0:
        porcentaje = 0
    else:
        porcentaje = min(actual / total, 1.0)
    completado = int(ancho * porcentaje)
    barra = "█" * completado + "-" * (ancho - completado)
    return f"[{barra}] {porcentaje * 100:.1f}%"


# ==============================================================================
# MENÚ INTERACTIVO EN CONSOLA (BLOQUE COMPLETO)
# ==============================================================================
def mostrar_menu():
    print("\n" + "="*45)
    print("      SISTEMA AVANZADO DE CONTROL DE GASTOS     ")
    print("="*45)
    print(" 1. Registrar un nuevo gasto")
    print(" 2. Listar gastos recientes")
    print(" 3. Filtros avanzados de gastos (Fecha, Categoría, Pago)")
    print(" 4. Ver balance general y gráficos por categoría")
    print(" 5. Ver resumen por mes")
    print(" 6. Ver resumen anual")
    print(" 7. Definir o actualizar presupuesto mensual")
    print(" 8. Exportar datos a CSV")
    print(" 9. Actualizar un gasto existente")
    print(" 10. Eliminar un gasto")
    print(" 11. Salir")
    print("="*45)

if __name__ == "__main__":
    hacer_copia_seguridad()
    inicializar_bd()
    
    while True:
        mostrar_menu()
        opcion = input("Selecciona una opción (1-11): ").strip()
        
        if opcion == "1":
            print("\n--- Registrar Gasto ---")
            cat = input("Categoría (ej. Comida, Transporte): ").strip()
            try:
                monto = float(input("Monto ($): ").strip())
                desc = input("Descripción (opcional): ").strip()
                fecha_input = input("Fecha (YYYY-MM-DD) [Enter para hoy]: ").strip()
                fecha = fecha_input if fecha_input else None
                
                print("Métodos de pago comunes: Efectivo, Tarjeta, Transferencia")
                metodo = input("Método de pago [Efectivo]: ").strip()
                metodo_pago = metodo if metodo else "Efectivo"
                
                agregar_gasto(cat, monto, desc, fecha, metodo_pago)
                print("\n¡Gasto registrado con éxito!")
            except ValueError as e:
                print(f"Error: {e}. Asegúrate de ingresar datos válidos.")
                
        elif opcion == "2":
            print("\n--- Gastos Recientes ---")
            gastos = listar_gastos(limite=15)
            if not gastos:
                print("No hay gastos registrados todavía.")
            else:
                for g in gastos:
                    print(f"ID [{g['id']}] | {g['fecha']} | {g['categoria']}: ${g['monto']:.2f} [{g['metodo_pago']}] -- {g['descripcion']}")

        elif opcion == "3":
            print("\n--- Filtros Avanzados de Gastos ---")
            print("Deja el campo en blanco si no deseas aplicarlo.")
            f_inicio = input("Fecha de inicio (YYYY-MM-DD): ").strip() or None
            f_fin = input("Fecha de fin (YYYY-MM-DD): ").strip() or None
            cat_filtro = input("Categoría específica: ").strip() or None
            metodo_filtro = input("Método de pago específico (ej. Tarjeta): ").strip() or None
            
            try:
                gastos = listar_gastos_avanzado(fecha_inicio=f_inicio, fecha_fin=f_fin, categoria=cat_filtro, metodo_pago=metodo_filtro)
                if not gastos:
                    print("No se encontraron gastos con los filtros indicados.")
                else:
                    print(f"\nResultados encontrados ({len(gastos)} registros):")
                    total_filtrado = sum(g['monto'] for g in gastos)
                    for g in gastos:
                        print(f"ID [{g['id']}] | {g['fecha']} | {g['categoria']}: ${g['monto']:.2f} [{g['metodo_pago']}] -- {g['descripcion']}")
                    print(f"\nTotal en este filtrado: ${total_filtrado:.2f}")
            except Exception as e:
                print(f"Error al filtrar los datos: {e}")
                
        elif opcion == "4":
            print("\n--- Balance General y Gráficos ---")
            total_hist = obtener_total_gastos()
            print(f"Gasto Total Histórico: ${total_hist:.2f}")
            print("\nDesglose por categoría y proporciones:")
            cats = gastos_por_categoria()
            if not cats:
                print("No hay datos para mostrar.")
            else:
                for row in cats:
                    barra = mostrar_barra_progreso(row['total_categoria'], total_hist)
                    print(f" • {row['categoria']}: ${row['total_categoria']:.2f}  {barra}")

        elif opcion == "5":
            print("\n--- Resumen Mensual ---")
            try:
                anio = int(input("Ingresa el año (ej. 2026): ").strip())
                mes = int(input("Ingresa el mes (1-12): ").strip())
                resumen = resumen_mensual(anio, mes)
                print(f"\nResumen para: {resumen['mes']}")
                print(f"Total del mes: ${resumen['total_mes']:.2f}")
                print("Desglose:")
                for item in resumen['desglose']:
                    barra = mostrar_barra_progreso(item['total_categoria'], resumen['total_mes'])
                    print(f" - {item['categoria']}: ${item['total_categoria']:.2f}  {barra}")
            except ValueError:
                print("Por favor, ingresa números válidos para el año y el mes.")

        elif opcion == "6":
            print("\n--- Resumen Anual ---")
            try:
                anio = int(input("Ingresa el año a consultar (ej. 2026): ").strip())
                resumen_an = resumen_anual(anio)
                print(f"\nComportamiento Financiero del Año {resumen_an['anio']}")
                print(f"Gasto Total Anual: ${resumen_an['total_anual']:.2f}")
                print("\nDesglose por Meses:")
                if not resumen_an['desglose_meses']:
                    print("No hay registros para este año.")
                else:
                    nombres_meses = {
                        "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
                        "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
                        "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"
                    }
                    for m_data in resumen_an['desglose_meses']:
                        mes_num = m_data['mes']
                        nombre_mes = nombres_meses.get(mes_num, mes_num)
                        total_m = m_data['total_mes']
                        barra = mostrar_barra_progreso(total_m, resumen_an['total_anual'])
                        print(f" • {nombre_mes}: ${total_m:.2f}  {barra}")
            except ValueError:
                print("Por favor, ingresa un año válido.")

        elif opcion == "7":
            print("\n--- Definir / Actualizar Presupuesto ---")
            cat = input("Categoría a presupuestar (ej. Comida): ").strip()
            try:
                limite = float(input("Límite mensual ($): ").strip())
                definir_presupuesto(cat, limite)
                print("¡Presupuesto guardado con éxito!")
            except ValueError as e:
                print(f"Error: {e}")

        elif opcion == "8":
            print("\n--- Exportar Datos ---")
            nombre_archivo = input("Nombre del archivo CSV [reporte_gastos.csv]: ").strip()
            if not nombre_archivo:
                nombre_archivo = "reporte_gastos.csv"
            try:
                exportar_a_csv(nombre_archivo)
                print(f"¡Datos exportados exitosamente a '{nombre_archivo}'!")
            except Exception as e:
                print(f"Error al exportar: {e}")
                
        elif opcion == "9":
            print("\n--- Actualizar Gasto ---")
            try:
                g_id = int(input("ID del gasto que deseas modificar: ").strip())
                print("Deja el campo en blanco si no deseas cambiarlo.")
                cat = input("Nueva categoría: ").strip() or None
                monto_str = input("Nuevo monto: ").strip()
                monto = float(monto_str) if monto_str else None
                desc = input("Nueva descripción: ").strip() or None
                fecha = input("Nueva fecha (YYYY-MM-DD): ").strip() or None
                metodo = input("Nuevo método de pago: ").strip() or None
                
                actualizar_gasto(g_id, categoria=cat, monto=monto, descripcion=desc, fecha=fecha, metodo_pago=metodo)
                print("¡Gasto actualizado correctamente!")
            except ValueError as e:
                print(f"Error: {e}")
                
        elif opcion == "10":
            print("\n--- Eliminar Gasto ---")
            try:
                g_id = int(input("ID del gasto a eliminar: ").strip())
                confirmar = input(f"¿Estás seguro de borrar el ID {g_id}? (s/n): ").strip().lower()
                if confirmar == 's':
                    eliminar_gasto(g_id)
                    print("Gasto eliminado.")
                else:
                    print("Operación cancelada.")
            except ValueError as e:
                print(f"Error: {e}")
                
        elif opcion == "11":
            print("\n¡Hasta luego! Saliendo del sistema de gastos.")
            break
        else:
            print("\nOpción no válida. Por favor, elige un número del 1 al 11.")
            
