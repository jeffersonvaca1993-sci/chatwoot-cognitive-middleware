# src/database/connector.py
from sqlalchemy import text
from src.database.session import engine

class DatabaseConnector:
    """
    Wrapper simple sobre SQLAlchemy para ejecutar SQL crudo
    y devolver diccionarios, satisfaciendo la interfaz esperada por ExpropiadorDeDatos.
    """
    def __init__(self):
        self.engine = engine

    def ejecutar_escritura(self, sql: str, parametros: tuple) -> dict:
        """
        Ejecuta un INSERT/UPDATE y devuelve el resultado (usualmente RETURNING id).
        """
        with self.engine.connect() as conn:
            # Convertimos los parámetros posicionales (%s) a estilo SQLAlchemy (:p1, :p2...)
            # Ojo: El código del usuario usa %s (estilo psycopg2 directo).
            # SQLAlchemy usa :param.
            # Para mantener compatibilidad con el código del usuario que usa %s,
            # lo ideal sería usar el cursor crudo de psycopg2 o adaptar la query.
            # Aquí optaremos por usar `conn.connection.cursor()` para tener comportamiento raw.
            
            # Acceso al driver raw (psycopg2/pg8000)
            # Esto asume que estamos usando psycopg2 como driver subyacente
            raw_conn = conn.connection
            cursor = raw_conn.cursor()
            try:
                cursor.execute(sql, parametros)
                if cursor.description:
                    # Si hay resultados (RETURNING)
                    columns = [desc[0] for desc in cursor.description]
                    row = cursor.fetchone()
                    raw_conn.commit()
                    if row:
                        return dict(zip(columns, row))
                    return {}
                else:
                    raw_conn.commit()
                    return {}
            except Exception as e:
                raw_conn.rollback()
                raise e
            finally:
                cursor.close()
