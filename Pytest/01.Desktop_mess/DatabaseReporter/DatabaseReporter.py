
import logging
import psycopg2
from psycopg2 import OperationalError


class DatabaseReporter:
    def __init__(self, host, port, user, password, dbname):
        self.connection_params = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "dbname": dbname
        }
        self.conn = None
        self.cursor = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            self.cursor = self.conn.cursor()
            logging.info("Подключение к БД успешно!")

        except OperationalError:
            logging.exception("Ошибка подключения к БД")
            raise

    def fetch_messages(self, query, params=None):
        if self.cursor is None:
            raise RuntimeError("Нет активного подключения к БД")

        try:
            self.cursor.execute(query, params or ())
            results = self.cursor.fetchall()
            return results

        except Exception:
            logging.exception("Ошибка выполнения SQL-запроса")
            raise

    def message_exists(self, results, message):
        if not results:
            return False

        return any(
            row[0] is not None and message in str(row[0])
            for row in results
        )

    def close(self):
        try:
            if self.cursor is not None:
                self.cursor.close()
                self.cursor = None

            if self.conn is not None:
                self.conn.close()
                self.conn = None

            logging.info("Соединение с БД закрыто")

        except Exception:
            logging.exception("Ошибка при закрытии соединения")
