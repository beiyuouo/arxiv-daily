import os
from os.path import dirname, join, abspath
from sys import platform

import pytz
from loguru import logger


# 定位项目根目录
SERVER_DIR_PROJECT = dirname(__file__) if "win" in platform else abspath("./")

#SERVER_PATH_README = join(SERVER_DIR_PROJECT, "README.md")                                  # default

SERVER_PATH_README = "./database/db_markdown/readme.md"    # DB용 markdown 
SERVER_PATH_DOCS = join(SERVER_DIR_PROJECT, "docs")

os.makedirs(SERVER_PATH_DOCS, exist_ok=True)

# 文件数据库 目录根
SERVER_DIR_DATABASE = join(SERVER_DIR_PROJECT, "database")

SERVER_DIR_STORAGE = join(SERVER_DIR_DATABASE, "storage")

SERVER_DIR_HISTORY = join(SERVER_PATH_DOCS, "history")

SERVER_PATH_STORAGE_MD = join(SERVER_DIR_STORAGE, "storage_{}.md")

SERVER_PATH_TOPIC = join(SERVER_DIR_DATABASE, "topic.yml")

# 服务器日志文件路径
SERVER_DIR_DATABASE_LOG = join(SERVER_DIR_DATABASE, "logs")
logger.add(
    join(SERVER_DIR_DATABASE_LOG, "runtime.log"),
    level="DEBUG",
    rotation="1 day",
    retention="20 days",
    encoding="utf8",
)
logger.add(
    join(SERVER_DIR_DATABASE_LOG, "error.log"),
    level="ERROR",
    rotation="1 week",
    encoding="utf8",
)

# 时区
TIME_ZONE_CN = pytz.timezone("Asia/Shanghai")
TIME_ZONE_KR = pytz.timezone("Asia/Seoul")          # 새로 추가
TIME_ZONE_NY = pytz.timezone("America/New_York")
