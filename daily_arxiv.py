#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File    :   daily_arxiv.py
@Time    :   2021-10-29 22:34:09
@Author  :   Bingjie Yan
@Email   :   bj.yan.pa@qq.com
@License :   Apache License 2.0
"""


import datetime
import requests
import json
import arxiv
import os
import shutil
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"


def get_authors(authors, first_author=False):
    output = str()
    if first_author == False:
        output = ", ".join(str(author) for author in authors)
    else:
        output = authors[0]
    return output


def sort_papers(papers):
    output = dict()
    keys = list(papers.keys())
    keys.sort(reverse=True)
    for key in keys:
        output[key] = papers[key]
    return output


def get_yaml_data(yaml_file: str):
    fs = open(yaml_file)
    data = yaml.load(fs, Loader=Loader)
    print(data)
    return data


def get_daily_papers(topic: str, query: str = "slam", max_results=2):
    # output
    content = dict()

    # content
    output = dict()

    search_engine = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    cnt = 0

    for result in search_engine.results():

        paper_id = result.get_short_id()
        paper_title = result.title
        paper_url = result.entry_id

        code_url = base_url + paper_id
        paper_abstract = result.summary.replace("\n", " ")
        paper_authors = get_authors(result.authors)
        paper_first_author = get_authors(result.authors, first_author=True)
        primary_category = result.primary_category

        publish_time = result.published.date()

        print("Time = ", publish_time,
              " title = ", paper_title,
              " author = ", paper_first_author)

        # eg: 2108.09112v1 -> 2108.09112
        ver_pos = paper_id.find('v')
        if ver_pos == -1:
            paper_key = paper_id
        else:
            paper_key = paper_id[0:ver_pos]

        try:
            r = requests.get(code_url).json()
            # source code link
            if "official" in r and r["official"]:
                cnt += 1
                repo_url = r["official"]["url"]
                content[
                    paper_key] = f"|**{publish_time}**|**{paper_title}**|{paper_first_author} et.al.|[{paper_id}]({paper_url})|**[link]({repo_url})**|\n"
            else:
                content[
                    paper_key] = f"|**{publish_time}**|**{paper_title}**|{paper_first_author} et.al.|[{paper_id}]({paper_url})|null|\n"

        except Exception as e:
            print(f"exception: {e} with id: {paper_key}")

    data = {topic: content}
    return data


def update_json_file(filename, data):
    with open(filename, "r") as f:
        content = f.read()
        if not content:
            m = {}
        else:
            m = json.loads(content)

    json_data = m.copy()

    # update papers in each keywords
    for topic in data.keys():
        if not topic in json_data.keys():
            json_data[topic] = {}
        for subtopic in data[topic].keys():
            papers = data[topic][subtopic]

            if subtopic in json_data[topic].keys():
                json_data[topic][subtopic].update(papers)
            else:
                json_data[topic][subtopic] = papers

    with open(filename, "w") as f:
        json.dump(json_data, f)


def json_to_md(filename, to_web=False):
    """
    @param filename: str
    @return None
    """

    DateNow = datetime.date.today()
    DateNow = str(DateNow)
    DateNow = DateNow.replace('-', '.')

    with open(filename, "r") as f:
        content = f.read()
        if not content:
            data = {}
        else:
            data = json.loads(content)

    if to_web == False:
        md_filename = "README.md"
        # clean README.md if daily already exist else create it
        with open(md_filename, "w+") as f:
            pass

        # write data into README.md
        with open(md_filename, "a+") as f:

            f.write("## Updated on " + DateNow + "\n\n")

            for topic in data.keys():
                f.write("## " + topic + "\n\n")
                for subtopic in data[topic].keys():
                    day_content = data[topic][subtopic]
                    if not day_content:
                        continue
                    # the head of each part
                    f.write(f"### {subtopic}\n\n")

                    f.write("|Publish Date|Title|Authors|PDF|Code|\n" +
                            "|---|---|---|---|---|\n")

                    # sort papers by date
                    day_content = sort_papers(day_content)

                    for _, v in day_content.items():
                        if v is not None:
                            f.write(v)

                    f.write(f"\n")
    else:
        if os.path.exists('docs'):
            shutil.rmtree('docs')
        if not os.path.isdir('docs'):
            os.mkdir('docs')

        shutil.copyfile('README.md', os.path.join('docs', 'index.md'))

        for topic in data.keys():
            os.makedirs(os.path.join('docs', topic), exist_ok=True)
            md_indexname = os.path.join('docs', topic, "index.md")
            with open(md_indexname, "w+") as f:
                f.write(f"# {topic}\n\n")

            # print(f'web {topic}')

            for subtopic in data[topic].keys():
                md_filename = os.path.join('docs', topic, f"{subtopic}.md")
                # print(f'web {subtopic}')

                # clean README.md if daily already exist else create it
                with open(md_filename, "w+") as f:
                    pass

                with open(md_filename, "a+") as f:
                    day_content = data[topic][subtopic]
                    if not day_content:
                        continue
                    # the head of each part
                    f.write(f"# {subtopic}\n\n")
                    f.write("| Publish Date | Title | Authors | PDF | Code |\n")
                    f.write(
                        "|:---------|:-----------------------|:---------|:------|:------|\n")

                    # sort papers by date
                    day_content = sort_papers(day_content)

                    for _, v in day_content.items():
                        if v is not None:
                            f.write(v)

                    f.write(f"\n")

                with open(md_indexname, "a+") as f:
                    day_content = data[topic][subtopic]
                    if not day_content:
                        continue
                    # the head of each part
                    f.write(f"## {subtopic}\n\n")
                    f.write("| Publish Date | Title | Authors | PDF | Code |\n")
                    f.write(
                        "|:---------|:-----------------------|:---------|:------|:------|\n")

                    # sort papers by date
                    day_content = sort_papers(day_content)

                    for _, v in day_content.items():
                        if v is not None:
                            f.write(v)

                    f.write(f"\n")

    print("finished")


if __name__ == "__main__":

    data_collector = dict()

    yaml_path = os.path.join(".", "topic.yml")
    yaml_data = get_yaml_data(yaml_path)

    # print(yaml_data)

    keywords = dict(yaml_data)

    for topic in keywords.keys():
        for subtopic, keyword in dict(keywords[topic]).items():

            # topic = keyword.replace("\"","")
            print("Keyword: " + subtopic)

            data = get_daily_papers(
                subtopic, query=keyword, max_results=2)

            if not topic in data_collector.keys():
                data_collector[topic] = {}
            data_collector[topic].update(data)

            print(data)
            # print(data_collector)

            print("\n")

    print(data_collector)
    # update README.md file
    json_file = "arxiv-daily.json"
#     if ~os.path.exists(json_file):
#         with open(json_file,'w')as a:
#             print("create " + json_file)

    # update json data
    update_json_file(json_file, data_collector)
    # json data to markdown
    json_to_md(json_file)

    # json data to markdown
    json_to_md(json_file, to_web=True)
