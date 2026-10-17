import tempfile
import unittest
from datetime import date
from pathlib import Path

import database as db


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.temp_dir.name) / "test.db")
        db.initialize_database()

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def crear_usuario(self, username):
        return db.crear_usuario(username, f"{username}@example.com", "test-hash")

    def registrar(self, usuario_id, fecha, tipo, monto, categoria="Comida"):
        db.registrar_transaccion(
            usuario_id, tipo, date.fromisoformat(fecha), categoria, "Prueba", monto
        )

    def test_transacciones_y_presupuestos_rechazan_montos_no_validos(self):
        usuario = self.crear_usuario("ana")
        gasto = db.registrar_gasto
        monto_invalido = (0, -1, float("nan"), float("inf"), float("-inf"), True)

        for monto in monto_invalido:
            with self.subTest(monto=monto):
                with self.assertRaises(ValueError):
                    self.registrar(usuario["id"], "2026-10-01", "Gasto", monto)
                with self.assertRaises(ValueError):
                    gasto(date(2026, 10, 1), "Comida", "Prueba", monto)
                with self.assertRaises(ValueError):
                    db.guardar_presupuesto_usuario(usuario["id"], "Comida", monto)
                with self.assertRaises(ValueError):
                    db.guardar_presupuesto("Comida", monto)

        self.registrar(usuario["id"], "2026-10-01", "Gasto", 12)
        db.registrar_gasto(date(2026, 10, 1), "Comida", "Prueba", 12)
        legacy_gasto = db.listar_gastos()[0]
        transaction = db.listar_transacciones(usuario["id"])[0]
        for monto in monto_invalido:
            with self.subTest(monto_actualizado=monto):
                with self.assertRaises(ValueError):
                    db.actualizar_transaccion(
                        usuario["id"], transaction["id"], date(2026, 10, 1),
                        "Comida", "Prueba", monto, "Efectivo",
                    )
                with self.assertRaises(ValueError):
                    db.actualizar_gasto(
                        legacy_gasto["id"], date(2026, 10, 1), "Comida",
                        "Prueba", monto, "Efectivo",
                    )

    def test_limite_cero_devuelve_cero_y_limites_invalidos_se_rechazan(self):
        usuario = self.crear_usuario("luis")
        self.registrar(usuario["id"], "2026-10-01", "Gasto", 12)

        self.assertEqual(db.listar_transacciones(usuario["id"], limite=0), [])
        for limite in (-1, 1.5, True):
            with self.subTest(limite=limite):
                with self.assertRaises(ValueError):
                    db.listar_transacciones(usuario["id"], limite=limite)

    def test_movimientos_y_presupuestos_se_aislan_por_usuario_y_mes(self):
        ana = self.crear_usuario("ana")
        luis = self.crear_usuario("luis")
        self.registrar(ana["id"], "2026-09-30", "Gasto", 50)
        self.registrar(ana["id"], "2026-10-01", "Gasto", 20)
        self.registrar(ana["id"], "2026-10-02", "Ingreso", 100)
        self.registrar(luis["id"], "2026-10-02", "Gasto", 999)
        db.guardar_presupuesto_usuario(ana["id"], "Comida", 200)

        resumen = db.obtener_resumen_financiero(
            ana["id"], date(2026, 10, 1), date(2026, 11, 1)
        )
        presupuesto = db.listar_presupuestos_usuario(
            ana["id"], date(2026, 10, 1), date(2026, 11, 1)
        )

        self.assertEqual(resumen["gastos"], 70)
        self.assertEqual(resumen["ingresos"], 100)
        self.assertEqual(resumen["balance"], 30)
        self.assertEqual(resumen["gastos_mes"], 20)
        self.assertEqual(presupuesto[0]["gastado"], 20)
        self.assertEqual(
            [fila["monto"] for fila in db.listar_transacciones(luis["id"])],
            [999],
        )

    def test_google_crea_o_reutiliza_cuenta_verificada_y_nombre_unico(self):
        first = db.obtener_o_crear_usuario_google(
            "antonio@example.com", "Antonio Monroy", "google-hash"
        )
        repeated = db.obtener_o_crear_usuario_google(
            "ANTONIO@example.com", "Antonio Monroy", "unused-hash"
        )
        second = db.obtener_o_crear_usuario_google(
            "ana@example.com", "Antonio Monroy", "another-hash"
        )

        self.assertEqual(first["id"], repeated["id"])
        self.assertEqual(first["email"], "antonio@example.com")
        self.assertEqual(first["username"], "Antonio Monroy")
        self.assertEqual(second["username"], "Antonio Monroy 2")
        self.assertEqual(db.contar_usuarios(), 2)


if __name__ == "__main__":
    unittest.main()
