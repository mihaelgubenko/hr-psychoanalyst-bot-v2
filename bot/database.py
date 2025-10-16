"""
Менеджер базы данных с улучшенной архитектурой и типизацией
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class AnalysisRecord:
    """Запись анализа с типизацией"""
    id: int
    telegram_id: int
    name: str
    analysis_type: str
    analysis_data: Dict[str, Any]
    payment_status: str
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return asdict(self)
    
    @classmethod
    def from_row(cls, row: tuple) -> 'AnalysisRecord':
        """Создание из строки БД"""
        return cls(
            id=row[0],
            telegram_id=row[1],
            name=row[2],
            analysis_type=row[3],
            analysis_data=json.loads(row[4]) if row[4] else {},
            payment_status=row[5],
            created_at=datetime.fromisoformat(row[6])
        )

@dataclass
class PromptVariant:
    """Вариант промпта для A/B тестирования"""
    id: str
    type: str
    name: str
    template: str
    description: str
    active: bool = True
    created_at: Optional[datetime] = None

@dataclass
class ABTestResult:
    """Результат A/B теста"""
    id: int
    user_id: int
    prompt_variant_id: str
    prompt_type: str
    user_feedback: Optional[float] = None
    response_quality: Optional[float] = None
    user_engagement: Optional[float] = None
    conversion: bool = False
    timestamp: Optional[datetime] = None

class DatabaseManager:
    """Менеджер базы данных с типизацией и улучшенной архитектурой"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = Path(config.database_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Создаем подключение с настройками
        self.connection_params = {
            'timeout': 30,
            'isolation_level': None,  # Автокоммит
            'check_same_thread': False
        }
    
    async def init_database(self) -> bool:
        """Инициализация базы данных с проверкой ошибок"""
        try:
            with sqlite3.connect(self.db_path, **self.connection_params) as conn:
                conn.execute('PRAGMA journal_mode=WAL')  # WAL режим для производительности
                conn.execute('PRAGMA synchronous=NORMAL')
                conn.execute('PRAGMA cache_size=10000')
                conn.execute('PRAGMA temp_store=MEMORY')
                
                cursor = conn.cursor()
                
                # Таблица клиентов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS clients (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        analysis_type TEXT NOT NULL,
                        analysis_data TEXT NOT NULL,
                        payment_status TEXT DEFAULT 'free',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Индексы для производительности
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_telegram_id ON clients(telegram_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_analysis_type ON clients(analysis_type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_clients_created_at ON clients(created_at)')
                
                # Таблица для A/B тестирования промптов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS prompt_variants (
                        id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        name TEXT NOT NULL,
                        template TEXT NOT NULL,
                        description TEXT,
                        active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица результатов A/B тестов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ab_test_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        prompt_variant_id TEXT NOT NULL,
                        prompt_type TEXT NOT NULL,
                        user_feedback REAL,
                        response_quality REAL,
                        user_engagement REAL,
                        conversion BOOLEAN DEFAULT FALSE,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (prompt_variant_id) REFERENCES prompt_variants (id)
                    )
                ''')
                
                # Индексы для A/B тестов
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ab_tests_user_id ON ab_test_results(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ab_tests_variant_id ON ab_test_results(prompt_variant_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ab_tests_timestamp ON ab_test_results(timestamp)')
                
                # Таблица назначений пользователей к вариантам
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_variant_assignments (
                        user_id INTEGER,
                        prompt_type TEXT,
                        variant_id TEXT,
                        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, prompt_type),
                        FOREIGN KEY (variant_id) REFERENCES prompt_variants (id)
                    )
                ''')
                
                # Таблица статистики использования
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS usage_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        date DATE NOT NULL,
                        requests_count INTEGER DEFAULT 0,
                        tokens_used INTEGER DEFAULT 0,
                        cache_hits INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, date)
                    )
                ''')
                
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_stats_user_date ON usage_stats(user_id, date)')
                
                conn.commit()
                logger.info("База данных инициализирована успешно")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            return False
    
    async def save_analysis(
        self, 
        telegram_id: int, 
        name: str, 
        analysis_type: str, 
        analysis_data: Dict[str, Any], 
        payment_status: str = 'free'
    ) -> Optional[int]:
        """Сохранение анализа с улучшенной обработкой ошибок"""
        try:
            with sqlite3.connect(self.db_path, **self.connection_params) as conn:
                cursor = conn.cursor()
                
                # Проверяем существование записи
                cursor.execute(
                    'SELECT id FROM clients WHERE telegram_id = ? AND analysis_type = ?',
                    (telegram_id, analysis_type)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Обновляем существующую запись
                    cursor.execute('''
                        UPDATE clients 
                        SET name = ?, analysis_data = ?, payment_status = ?, updated_at = ?
                        WHERE telegram_id = ? AND analysis_type = ?
                    ''', (
                        name, 
                        json.dumps(analysis_data, ensure_ascii=False), 
                        payment_status, 
                        datetime.now(),
                        telegram_id, 
                        analysis_type
                    ))
                    analysis_id = existing[0]
                else:
                    # Создаем новую запись
                    cursor.execute('''
                        INSERT INTO clients 
                        (telegram_id, name, analysis_type, analysis_data, payment_status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        telegram_id, 
                        name, 
                        analysis_type, 
                        json.dumps(analysis_data, ensure_ascii=False), 
                        payment_status, 
                        datetime.now(),
                        datetime.now()
                    ))
                    analysis_id = cursor.lastrowid
                
                conn.commit()
                logger.info(f"Анализ сохранен: ID {analysis_id}, пользователь {telegram_id}")
                return analysis_id
                
        except Exception as e:
            logger.error(f"Ошибка сохранения анализа: {e}")
            return None
    
    async def get_user_analyses(self, telegram_id: int) -> List[AnalysisRecord]:
        """Получение анализов пользователя с типизацией"""
        try:
            with sqlite3.connect(self.db_path, **self.connection_params) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    'SELECT * FROM clients WHERE telegram_id = ? ORDER BY created_at DESC', 
                    (telegram_id,)
                )
                
                rows = cursor.fetchall()
                return [AnalysisRecord.from_row(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Ошибка получения анализов: {e}")
            return []
    
    async def get_analysis_by_id(self, analysis_id: int) -> Optional[AnalysisRecord]:
        """Получение анализа по ID"""
        try:
            with sqlite3.connect(self.db_path, **self.connection_params) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM clients WHERE id = ?', (analysis_id,))
                row = cursor.fetchone()
                
                return AnalysisRecord.from_row(row) if row else None
                
        except Exception as e:
            logger.error(f"Ошибка получения анализа по ID: {e}")
            return None
    
    async def clear_user_data(self, telegram_id: int) -> bool:
        """Очистка данных пользователя"""
        try:
            with sqlite3.connect(self.db_path, **self.connection_params) as conn:
                cursor = conn.cursor()
                
                # Удаляем данные пользователя из всех таблиц
                cursor.execute('DELETE FROM clients WHERE telegram_id = ?', (telegram_id,))
                cursor.execute('DELETE FROM ab_test_results WHERE user_id = ?', (telegram_id,))
                cursor.execute('DELETE FROM user_variant_assignments WHERE user_id = ?', (telegram_id,))
                cursor.execute('DELETE FROM usage_stats WHERE user_id = ?', (telegram_id,))
                
                conn.commit()
                logger.info(f"Данные пользователя {telegram_id} очищены")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка очистки данных пользователя: {e}")
            return False
    
    async def clear_all_data(self) -> bool:
        """Очистка всех данных"""
        try:
            with sqlite3.connect(self.db_path, **self.connection_params) as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM clients')
                cursor.execute('DELETE FROM ab_test_results')
                cursor.execute('DELETE FROM user_variant_assignments')
                cursor.execute('DELETE FROM usage_stats')
                
                conn.commit()
                logger.info("Все данные очищены")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка очистки всех данных: {e}")
            return False
    
    async def get_usage_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Получение статистики использования"""
        try:
            with sqlite3.connect(self.db_path, **self.connection_params) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        SUM(requests_count) as total_requests,
                        SUM(tokens_used) as total_tokens,
                        SUM(cache_hits) as total_cache_hits,
                        AVG(requests_count) as avg_requests_per_day
                    FROM usage_stats 
                    WHERE user_id = ? AND date >= date('now', '-{} days')
                '''.format(days), (user_id,))
                
                result = cursor.fetchone()
                
                return {
                    'total_requests': result[0] or 0,
                    'total_tokens': result[1] or 0,
                    'total_cache_hits': result[2] or 0,
                    'avg_requests_per_day': result[3] or 0,
                    'period_days': days
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Получение статуса здоровья базы данных"""
        try:
            with sqlite3.connect(self.db_path, **self.connection_params) as conn:
                cursor = conn.cursor()
                
                # Подсчет записей
                cursor.execute('SELECT COUNT(*) FROM clients')
                total_clients = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM ab_test_results')
                total_tests = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM usage_stats')
                total_stats = cursor.fetchone()[0]
                
                # Проверка целостности
                cursor.execute('PRAGMA integrity_check')
                integrity_check = cursor.fetchone()[0]
                
                # Размер базы данных
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                return {
                    'status': 'healthy' if integrity_check == 'ok' else 'unhealthy',
                    'total_clients': total_clients,
                    'total_tests': total_tests,
                    'total_stats': total_stats,
                    'integrity_check': integrity_check,
                    'database_size_bytes': db_size,
                    'database_path': str(self.db_path)
                }
                
        except Exception as e:
            logger.error(f"Ошибка проверки здоровья БД: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def close(self):
        """Закрытие соединений (для асинхронного контекста)"""
        # SQLite автоматически закрывает соединения
        pass