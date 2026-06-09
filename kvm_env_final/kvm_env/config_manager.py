# kvm_env/config_manager.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class ConfigManager:
    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        """Подключение к PostgreSQL с параметрами из .env"""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('PGHOST', 'localhost'),
                port=os.getenv('PGPORT', '5432'),
                database=os.getenv('PGDATABASE', 'kvm_env'),
                user=os.getenv('PGUSER'),
                password=os.getenv('PGPASSWORD')
            )
            self.conn.autocommit = False
        except Exception as e:
            print(f"❌ Ошибка подключения к PostgreSQL: {e}")
            print("   Убедитесь, что PostgreSQL запущен и настроен.")
            raise

    def init_db(self):
        """Создание таблиц, если их нет"""
        with self.conn.cursor() as cur:
            # Таблица vms
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vms (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    vcpus INTEGER NOT NULL,
                    memory_mb INTEGER NOT NULL,
                    disk_path TEXT NOT NULL,
                    state VARCHAR(20) DEFAULT 'stopped',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Таблица images
            cur.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id SERIAL PRIMARY KEY,
                    image_path TEXT NOT NULL,
                    build_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    packer_log TEXT
                )
            """)
            # Таблица operation_log
            cur.execute("""
                CREATE TABLE IF NOT EXISTS operation_log (
                    id SERIAL PRIMARY KEY,
                    action VARCHAR(50),
                    vm_id INTEGER REFERENCES vms(id) ON DELETE SET NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN
                )
            """)
            self.conn.commit()
            print("✅ База данных инициализирована")

    def add_vm(self, name, description, vcpus, memory_mb, disk_path, state='stopped'):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO vms (name, description, vcpus, memory_mb, disk_path, state)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (name, description, vcpus, memory_mb, disk_path, state))
            vm_id = cur.fetchone()[0]
            self.conn.commit()
            return vm_id

    def update_vm(self, name, vcpus=None, memory_mb=None, description=None, state=None):
        updates = []
        params = []
        if vcpus is not None:
            updates.append("vcpus = %s")
            params.append(vcpus)
        if memory_mb is not None:
            updates.append("memory_mb = %s")
            params.append(memory_mb)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if state is not None:
            updates.append("state = %s")
            params.append(state)
        if not updates:
            return
        params.append(name)
        query = f"UPDATE vms SET {', '.join(updates)} WHERE name = %s"
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            self.conn.commit()

    def delete_vm(self, name):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM vms WHERE name = %s RETURNING id", (name,))
            vm_id = cur.fetchone()
            if vm_id:
                self.conn.commit()
                return vm_id[0]
            return None

    def get_vm(self, name):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM vms WHERE name = %s", (name,))
            return cur.fetchone()

    def get_all_vms(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM vms ORDER BY name")
            return cur.fetchall()

    def log_operation(self, action, vm_id, success):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO operation_log (action, vm_id, success)
                VALUES (%s, %s, %s)
            """, (action, vm_id, success))
            self.conn.commit()

    def save_image(self, image_path, packer_log=""):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO images (image_path, packer_log)
                VALUES (%s, %s)
            """, (image_path, packer_log))
            self.conn.commit()

    def get_current_image(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT image_path FROM images ORDER BY build_date DESC LIMIT 1")
            return cur.fetchone()