"""
MySQL数据库管理器
提供MySQL数据库连接池管理和常用CRUD操作
"""

import pymysql
from pymysql.cursors import DictCursor
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
import logging

# 导入配置
from config import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MySQLManager:
    """MySQL数据库管理器"""

    _instance = None
    _pool = None

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, 
                 host: str = None,
                 port: int = None,
                 user: str = None,
                 password: str = None,
                 database: str = None,
                 charset: str = None,
                 pool_size: int = None,
                 max_overflow: int = None):
        """
        初始化MySQL连接池

        Args:
            host: MySQL服务器地址，默认从配置文件读取
            port: MySQL服务器端口，默认从配置文件读取
            user: 数据库用户名，默认从配置文件读取
            password: 数据库密码，默认从配置文件读取
            database: 数据库名称，默认从配置文件读取
            charset: 字符集，默认从配置文件读取
            pool_size: 连接池大小，默认从配置文件读取
            max_overflow: 最大溢出连接数，默认从配置文件读取
        """
        if self._pool is None:
            # 使用配置文件中的值作为默认值
            self.config = {
                'host': host or settings.DB_HOST,
                'port': port or settings.DB_PORT,
                'user': user or settings.DB_USER,
                'password': password or settings.DB_PASSWORD,
                'database': database or settings.DB_NAME,
                'charset': charset or settings.DB_CHARSET,
                'cursorclass': DictCursor,
                'autocommit': False
            }
            self.pool_size = pool_size or settings.DB_POOL_SIZE
            self.max_overflow = max_overflow or settings.DB_MAX_OVERFLOW
            self._init_pool()

    def _init_pool(self):
        """初始化连接池"""
        try:
            # 这里使用简单的连接管理，实际项目中可以使用DBUtils等连接池库
            self._pool = []
            logger.info(f"MySQL连接池初始化成功，连接池大小: {self.pool_size}")
        except Exception as e:
            logger.error(f"MySQL连接池初始化失败: {str(e)}")
            raise

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器

        Yields:
            数据库连接对象
        """
        conn = None
        try:
            conn = pymysql.connect(**self.config)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库连接错误: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(self, sql: str, params: tuple = None) -> List[Dict]:
        """
        执行查询SQL

        Args:
            sql: SQL查询语句
            params: SQL参数

        Returns:
            查询结果列表
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    result = cursor.fetchall()
                    logger.info(f"执行查询成功: {sql}")
                    return result
        except Exception as e:
            logger.error(f"查询执行失败: {str(e)}")
            raise

    def execute_query_one(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """
        执行查询SQL，返回单条记录

        Args:
            sql: SQL查询语句
            params: SQL参数

        Returns:
            查询结果字典或None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    result = cursor.fetchone()
                    logger.info(f"执行单条查询成功: {sql}")
                    return result
        except Exception as e:
            logger.error(f"单条查询执行失败: {str(e)}")
            raise

    def execute_insert(self, sql: str, params: tuple = None) -> int:
        """
        执行插入SQL

        Args:
            sql: SQL插入语句
            params: SQL参数

        Returns:
            插入记录的ID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    insert_id = cursor.lastrowid
                    logger.info(f"执行插入成功，ID: {insert_id}")
                    return insert_id
        except Exception as e:
            logger.error(f"插入执行失败: {str(e)}")
            raise

    def execute_update(self, sql: str, params: tuple = None) -> int:
        """
        执行更新SQL

        Args:
            sql: SQL更新语句
            params: SQL参数

        Returns:
            影响的行数
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    affected_rows = cursor.execute(sql, params)
                    conn.commit()
                    logger.info(f"执行更新成功，影响行数: {affected_rows}")
                    return affected_rows
        except Exception as e:
            logger.error(f"更新执行失败: {str(e)}")
            raise

    def execute_delete(self, sql: str, params: tuple = None) -> int:
        """
        执行删除SQL

        Args:
            sql: SQL删除语句
            params: SQL参数

        Returns:
            影响的行数
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    affected_rows = cursor.execute(sql, params)
                    conn.commit()
                    logger.info(f"执行删除成功，影响行数: {affected_rows}")
                    return affected_rows
        except Exception as e:
            logger.error(f"删除执行失败: {str(e)}")
            raise

    def execute_batch(self, sql: str, params_list: List[tuple]) -> int:
        """
        批量执行SQL

        Args:
            sql: SQL语句
            params_list: 参数列表

        Returns:
            影响的总行数
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    affected_rows = cursor.executemany(sql, params_list)
                    conn.commit()
                    logger.info(f"批量执行成功，影响行数: {affected_rows}")
                    return affected_rows
        except Exception as e:
            logger.error(f"批量执行失败: {str(e)}")
            raise

    def execute_transaction(self, sql_list: List[Tuple[str, tuple]]) -> bool:
        """
        执行事务

        Args:
            sql_list: SQL语句和参数的元组列表

        Returns:
            是否执行成功
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    try:
                        for sql, params in sql_list:
                            cursor.execute(sql, params)
                        conn.commit()
                        logger.info(f"事务执行成功，共{len(sql_list)}条SQL")
                        return True
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"事务执行失败，已回滚: {str(e)}")
                        return False
        except Exception as e:
            logger.error(f"事务执行失败: {str(e)}")
            raise

    def close(self):
        """关闭连接池"""
        if self._pool:
            self._pool.clear()
            logger.info("MySQL连接池已关闭")


# 创建全局MySQL管理器实例
mysql_manager = MySQLManager()


def get_mysql_manager() -> MySQLManager:
    """
    获取MySQL管理器实例

    Returns:
        MySQL管理器实例
    """
    return mysql_manager
