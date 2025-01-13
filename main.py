#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   daily_arxiv.py
@Time    :   2021-10-29 22:34:09
@Author  :   Bingjie Yan
@Email   :   bj.yan.pa@qq.com
@License :   Apache License 2.0
"""

import json.decoder
import os.path
import shutil

from gevent import monkey

monkey.patch_all()
import gevent
from gevent.queue import Queue
from datetime import datetime
import requests
import arxiv
import yaml

from fire import Fire

from config import (
    SERVER_PATH_TOPIC,
    SERVER_DIR_STORAGE,
    SERVER_PATH_README,
    SERVER_PATH_DOCS,
    SERVER_DIR_HISTORY,
    SERVER_PATH_STORAGE_MD,
    TIME_ZONE_KR,
    logger,
)


class ToolBox:
    @staticmethod
    def log_date(mode="log"):
        if mode == "log":
            return str(datetime.now(TIME_ZONE_KR)).split(".")[0]
        elif mode == "file":
            return str(datetime.now(TIME_ZONE_KR)).split(" ")[0]

    @staticmethod
    def get_yaml_data() -> dict:
        with open(SERVER_PATH_TOPIC, "r", encoding="utf8") as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
        print(data)
        return data

    @staticmethod
    def handle_html(url: str):
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.44"
        }
        proxies = {"http": None, "https": None}
        session = requests.session()
        response = session.get(url, headers=headers, proxies=proxies)
        try:
            data_ = response.json()
            return data_
        except json.decoder.JSONDecodeError as e:
            logger.error(e)

    @staticmethod
    def get_repository_list(config_path: str = "database/awesome_repos.yml") -> list:
        """
        Load repository URLs from a YAML configuration file.

        Args:
            config_path (str): Path to the YAML configuration file.

        Returns:
            list: A list of repository URLs.
        """
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found: {config_path}")
            return []

        with open(config_path, "r", encoding="utf8") as f:
            try:
                data = yaml.load(f, Loader=yaml.SafeLoader)
                return data.get("repositories", [])
            except Exception as e:
                logger.error(f"Failed to read configuration file {config_path}: {e}")
                return []

    @staticmethod
    # Awesome github pages 업데이트 동기화 함수
    def update_readme(repo_url: str, repo_dir: str, target_path: str):
        """
        Clone the repo if not exists, or pull the latest changes, and copy README.md to the target path.

        Args:
            repo_url (str): URL of the repository to pull updates from.
            repo_dir (str): Local directory where the repository is cloned.
            target_path (str): Path to copy the updated README.md file.
        """
        if not os.path.exists(repo_dir):
            # Clone the repository if it doesn't exist
            os.system(f"git clone {repo_url} {repo_dir}")
            logger.info(f"Cloned repository: {repo_url}")
        else:
            # Pull the latest changes if repository exists
            try:
                os.system(f"git -C {repo_dir} pull")
                logger.info(f"Pulled latest changes for {repo_dir}")
            except Exception as e:
                logger.error(f"Failed to pull latest changes for {repo_dir}: {e}")

        # Copy the README.md file to the target path
        readme_path = os.path.join(repo_dir, "README.md")
        if os.path.exists(readme_path):
            shutil.copyfile(readme_path, target_path)
            logger.info(f"Updated README.md copied to {target_path}")
        else:
            logger.warning(f"README.md not found in {repo_dir}")

class CoroutineSpeedup:
    """轻量化的协程控件"""

    def __init__(
        self,
        work_q: Queue = None,
        task_docker=None,
    ):
        # 任务容器：queue
        self.worker = work_q if work_q else Queue()
        self.channel = Queue()
        # 任务容器：迭代器
        self.task_docker = task_docker
        # 协程数
        self.power = 32
        # 任务队列满载时刻长度
        self.max_queue_size = 0

        self.cache_space = []

        self.max_results = 30

    def _adaptor(self):
        while not self.worker.empty():
            task: dict = self.worker.get_nowait()
            if task.get("pending"):
                self.runtime(context=task.get("pending"))
            elif task.get("response"):
                self.parse(context=task)

    def _progress(self):
        p = self.max_queue_size - self.worker.qsize() - self.power
        p = 0 if p < 1 else p
        return p

    def runtime(self, context: dict):
        keyword_ = context.get("keyword")

        res = arxiv.Search(
            query=keyword_,
            max_results=self.max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
        ).results()

        context.update({"response": res, "hook": context})
        self.worker.put_nowait(context)

    def parse(self, context):
        base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"
        _paper = {}
        arxiv_res = context.get("response")
        for result in arxiv_res:
            paper_id = result.get_short_id()
            paper_title = result.title
            paper_url = result.entry_id

            code_url = base_url + paper_id
            paper_first_author = result.authors[0]

            publish_time = result.published.date()

            ver_pos = paper_id.find("v")
            paper_key = paper_id if ver_pos == -1 else paper_id[0:ver_pos]

            # 尝试获取仓库代码
            # ----------------------------------------------------------------------------------
            # Origin(r)
            # ----------------------------------------------------------------------------------
            # {
            #   'paper_url': 'https://',
            #   'official': {'url': 'https://github.com/nyu-wireless/mmwRobotNav'},
            #   'all_official': [{'url': 'https://github.com/nyu-wireless/mmwRobotNav'}],
            #   'unofficial_count': 0,
            #   'frameworks': [],
            #   'status': 'OK'
            # }
            # ----------------------------------------------------------------------------------
            # None(r)
            # ----------------------------------------------------------------------------------
            # {
            #   'paper_url': 'https://',
            #   'official': None,
            #   'all_official': [],
            #   'unofficial_count': 0,
            #   'frameworks': [],
            #   'status': 'OK'
            # }
            response = ToolBox.handle_html(code_url)
            official_ = response.get("official")
            repo_url = official_.get("url", "null") if official_ else "null"
            # ----------------------------------------------------------------------------------
            # 编排模型
            # ----------------------------------------------------------------------------------
            # IF repo
            #   |publish_time|paper_title|paper_first_author|[paper_id](paper_url)|`[link](url)`
            # ELSE
            #   |publish_time|paper_title|paper_first_author|[paper_id](paper_url)|`null`
            _paper.update(
                {
                    paper_key: {
                        "publish_time": publish_time,
                        "title": paper_title,
                        "authors": f"{paper_first_author} et.al.",
                        "id": paper_id,
                        "paper_url": paper_url,
                        "repo": repo_url,
                    },
                }
            )
        self.channel.put_nowait(
            {
                "paper": _paper,
                "topic": context["hook"]["topic"],
                "subtopic": context["hook"]["subtopic"],
                "fields": ["Publish Date", "Title", "Authors", "PDF", "Code"],
            }
        )
        logger.success(
            f"handle [{self.channel.qsize()}/{self.max_queue_size}]"
            f" | topic=`{context['topic']}` subtopic=`{context['hook']['subtopic']}`"
        )

    def offload_tasks(self):
        if self.task_docker:
            for task in self.task_docker:
                self.worker.put_nowait({"pending": task})
        self.max_queue_size = self.worker.qsize()

    def overload_tasks(self):
        ot = _OverloadTasks()
        file_obj: dict = {}
        while not self.channel.empty():
            # 将上下文替换成 Markdown 语法文本
            context: dict = self.channel.get()
            md_obj: dict = ot.to_markdown(context)

            # 子主题分流
            if not file_obj.get(md_obj["hook"]):
                file_obj[md_obj["hook"]] = md_obj["hook"]
            file_obj[md_obj["hook"]] += md_obj["content"]

            # 生成 mkdocs 所需文件
            os.makedirs(
                os.path.join(SERVER_PATH_DOCS, f'{context["topic"]}'), exist_ok=True
            )
            with open(
                os.path.join(
                    SERVER_PATH_DOCS, f'{context["topic"]}', f'{context["subtopic"]}.md'
                ),
                "w",
            ) as f:
                f.write(md_obj["content"])

        # 生成 Markdown 模板文件
        template_ = ot.generate_markdown_template(
            content="".join(list(file_obj.values()))
        )
        # 存储 Markdown 模板文件
        ot.storage(template_, obj_="database")

        return template_

    def go(self, power: int):
        # 任务重载
        self.offload_tasks()
        # 配置弹性采集功率
        if self.max_queue_size != 0:
            self.power = self.max_queue_size if power > self.max_queue_size else power
        # 任务启动
        task_list = []
        for _ in range(self.power):
            task = gevent.spawn(self._adaptor)
            task_list.append(task)
        gevent.joinall(task_list)


class _OverloadTasks:
    def __init__(self):
        self._build()

        # yyyy-mm-dd
        self.update_time = ToolBox.log_date(mode="log")

        self.storage_path_by_date = SERVER_PATH_STORAGE_MD.format(
            ToolBox.log_date("file")
        )
        self.storage_path_readme = SERVER_PATH_README
        self.storage_path_docs = SERVER_PATH_DOCS

    # -------------------
    # Private API
    # -------------------
    @staticmethod
    def _build():
        if not os.path.exists(SERVER_DIR_STORAGE):
            os.mkdir(SERVER_DIR_STORAGE)

    @staticmethod
    def _set_markdown_hyperlink(text, link):
        return f"[{text}]({link})"

    def _generate_markdown_table_content(self, paper: dict):
        paper["publish_time"] = f"**{paper['publish_time']}**"
        paper["title"] = f"**{paper['title']}**"
        _pdf = self._set_markdown_hyperlink(text=paper["id"], link=paper["paper_url"])
        _repo = (
            self._set_markdown_hyperlink(text="link", link=paper["repo"])
            if "http" in paper["repo"]
            else "null"
        )

        line = (
            f"|{paper['publish_time']}"
            f"|{paper['title']}"
            f"|{paper['authors']}"
            f"|{_pdf}"
            f"|{_repo}|\n"
        )

        return line

    @staticmethod
    def _set_style_to(style: str = "center"):
        return " :---: " if style == "center" else " --- "

    # -------------------
    # Public API
    # -------------------
    def storage(self, template: str, obj_: str = "database"):
        """
        将 Markdown 模板存档
        @param template:
        @param obj_: database:将 Markdown 模板存档至 database/store 中。其他值，替换根目录下的 README
        @return:
        """
        path_factory = {
            "database": self.storage_path_by_date,
            "readme": self.storage_path_readme,
            "docs": self.storage_path_docs,
        }
        if obj_ not in path_factory.keys():
            path_ = path_factory["readme"]
        else:
            path_ = path_factory[obj_]
        with open(path_, "w", encoding="utf8") as f:
            for i in template:
                f.write(i)

    def generate_markdown_template(self, content: str):
        _project = f"# arxiv-daily\n"
        _pin = f" Automated deployment @ {self.update_time} Asia/Seoul\n"
        _tos = (
            "> Welcome to contribute! Add your topics and keywords in "
            "[`topic.yml`](https://github.com/chimdungs/arxiv-daily/blob/feature/branch-name/database/topic.yml).\n"
        )
        _tos += (
            "> You can also view historical data through the "
            "[storage](https://github.com/chimdungs/arxiv-daily/blob/feature/branch-name/database/storage).\n"
        )

        _form = _project + _pin + _tos + content

        return _form

    def to_markdown(self, context: dict) -> dict:
        _fields = context["fields"]
        _topic = context["topic"]
        _subtopic = context["subtopic"]
        _paper_obj = context["paper"]

        _topic_md = f"\n## {_topic}\n"
        _subtopic_md = f"\n### {_subtopic}\n"
        _fields_md = f"|{'|'.join(_fields)}|\n"
        _style_md = f"|{'|'.join([self._set_style_to('center') for _ in range(len(_fields))])}|\n"
        table_lines = "".join(
            [
                self._generate_markdown_table_content(paper)
                for paper in _paper_obj.values()
            ]
        )

        _content_md = _subtopic_md + _fields_md + _style_md + table_lines

        return {"hook": _topic_md, "content": _content_md}


class Scaffold:
    def __init__(self):
        pass

    @staticmethod
    @logger.catch()
    def run(env: str = "development", power: int = 16):
        """
        Start the test sample.

        Usage: python daily_arxiv.py run
        or: python daily_arxiv.py run --env=production  生产环境下运行

        @param power:  synergy power. The recommended value interval is [2,16].The default value is 37.
        @param env: Optional with [development production]
        @return:
        """
        # Get tasks
        context = ToolBox.get_yaml_data()

        # Set tasks
        pending_atomic = [
            {"subtopic": subtopic, "keyword": keyword.replace('"', ""), "topic": topic}
            for topic, subtopics in context.items()
            for subtopic, keyword in subtopics.items()
        ]

        # Offload tasks
        booster = CoroutineSpeedup(task_docker=pending_atomic)
        booster.go(power=power)

        # Overload tasks
        template_ = booster.overload_tasks()
        

        # Replace project README file.
        if env == "production":
            with open(SERVER_PATH_README, "w", encoding="utf8") as f:
                for i in template_:
                    f.write(i)

            shutil.copyfile(
                SERVER_PATH_README, os.path.join(SERVER_PATH_DOCS, "index.md")
            )
            # make history directory and copy files in SERVER_DIR_STORAGE to history directory
            if not os.path.exists(SERVER_DIR_HISTORY):
                os.mkdir(SERVER_DIR_HISTORY)
            logger.info(f"{SERVER_DIR_HISTORY} is created.")
            for file in os.listdir(SERVER_DIR_STORAGE):
                file_format = os.path.basename(file).split("_")[-1]
                shutil.copyfile(
                    os.path.join(SERVER_DIR_STORAGE, file),
                    os.path.join(SERVER_DIR_HISTORY, file_format),
                )
                logger.info(f"{file} is copied to {SERVER_DIR_HISTORY}.")

        # Load repository URLs from configuration
        repo_list = ToolBox.get_repository_list(config_path="database/awesome_repos.yml")

        # Iterate over each repository and update
        for repo_url in repo_list:
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            repo_dir = os.path.join(SERVER_PATH_DOCS, "🔥Awesome_Pages", repo_name)
            target_readme_path = os.path.join(repo_dir, f"{repo_name}_README.md")

            # Clone or update the repository and copy README.md
            ToolBox.update_readme(repo_url=repo_url, repo_dir=repo_dir, target_path=target_readme_path)

        logger.info("All awesome repositories updated successfully.")


if __name__ == "__main__":
    Fire(Scaffold)