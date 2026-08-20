"""初始化 documind 数据库 + 商品演示表 + 示例数据。

运行（在项目根目录 DocuMind 下）：
    conda activate NLP
    python scripts/setup_mysql.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymysql

from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB


def main() -> None:
    # 1) 先连不带库名的连接，创建数据库（幂等）
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
        password=MYSQL_PASSWORD, ssl_disabled=True, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB} "
                "DEFAULT CHARACTER SET utf8mb4"
            )
        conn.commit()
    finally:
        conn.close()

    # 2) 再连到 documind 库，建表 + 插数据
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
        password=MYSQL_PASSWORD, database=MYSQL_DB, ssl_disabled=True, charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS products")
            cur.execute(
                """
                CREATE TABLE products (
                    id       INT AUTO_INCREMENT PRIMARY KEY,
                    name     VARCHAR(64)  NOT NULL,
                    category VARCHAR(32)  NOT NULL,
                    price    DECIMAL(10,2) NOT NULL,
                    stock    INT          NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cur.executemany(
                "INSERT INTO products (name, category, price, stock) VALUES (%s, %s, %s, %s)",
                [
                    ("iPhone 15 Pro", "数码", 7999.00, 12),
                    ("小米 14", "数码", 3999.00, 30),
                    ("AirPods Pro 2", "数码", 1899.00, 5),
                    ("机械键盘", "数码", 499.00, 15),
                    ("《三体》全集", "图书", 99.00, 50),
                    ("《活着》", "图书", 39.80, 100),
                    ("《算法导论》", "图书", 128.00, 8),
                    ("保温杯", "日用品", 59.90, 200),
                ],
            )
        conn.commit()
        print(f"数据库 {MYSQL_DB} 就绪：products 表已建，插入 8 行演示数据。")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
