import sqlite3
import datetime
import requests
import json
import arxiv
import os
import yaml
import time
import random
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"

# SQLite DB 초기화
def init_db(db_name="arxiv.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            topic TEXT,
            subtopic TEXT,
            publish_date TEXT,
            title TEXT,
            authors TEXT,
            first_author TEXT,
            pdf_url TEXT,
            code_url TEXT
        )
    """)
    conn.commit()
    return conn

def save_to_db(conn, data):
    cursor = conn.cursor()
    for topic, subtopics in data.items():
        for subtopic, papers in subtopics.items():
            for paper_id, paper_data in papers.items():
                # Parse paper_data to extract fields
                fields = paper_data.split('|')
                publish_date = fields[1].strip("**")
                title = fields[2].strip("**")
                authors = fields[3]
                first_author = authors.split(",")[0]
                pdf_url = fields[4].split("(")[-1].strip(")")
                code_url = fields[5].split("(")[-1].strip(")") if "link" in fields[5] else None
                # Insert into database
                cursor.execute("""
                    INSERT OR IGNORE INTO papers
                    (id, topic, subtopic, publish_date, title, authors, first_author, pdf_url, code_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (paper_id, topic, subtopic, publish_date, title, authors, first_author, pdf_url, code_url))
    conn.commit()

def get_authors(authors, first_author=False):
    return ", ".join(str(author) for author in authors) if not first_author else authors[0]

def sort_papers(papers):
    return {key: papers[key] for key in sorted(papers.keys(), reverse=True)}

def get_yaml_data(yaml_file: str):
    with open(yaml_file) as fs:
        data = yaml.load(fs, Loader=Loader)
    return data

def get_daily_papers(topic: str, query: str = "slam", max_results=2):
    content = dict()
    search_engine = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    for result in search_engine.results():
        paper_id = result.get_short_id()
        paper_title = result.title
        paper_url = result.entry_id
        code_url = base_url + paper_id
        paper_authors = get_authors(result.authors)
        paper_first_author = get_authors(result.authors, first_author=True)
        publish_time = result.published.date()
    
        try:
            r = requests.get(code_url).json()
            if "official" in r and r["official"]:
                repo_url = r["official"]["url"]
                content[paper_id] = f"|**{publish_time}**|**{paper_title}**|{paper_authors} et.al.|[{paper_id}]({paper_url})|**[link]({repo_url})**|\n"
            else: # OCR 
                content[paper_id] = f"|**{publish_time}**|**{paper_title}**|{paper_authors} et.al.|[{paper_id}]({paper_url})|null|\n"
        except Exception as e:
            print(f"Exception: {e} with id: {paper_id}")
    return {topic: content}

    
def db_to_md(conn, md_filename="README.md"):
    """
    SQLite DB 데이터를 읽어 Markdown 파일 생성
    """
    cursor = conn.cursor()
    # Markdown 파일 초기화
    with open(md_filename, "w") as f:
        # Header 작성
        f.write("# arxiv-daily\n")
        f.write(f"Updated on {datetime.date.today().strftime('%Y-%m-%d')}\n\n")
        f.write("> Welcome to contribute! Add your topics and keywords in [`topic.yml`](https://github.com/your-repo).\n\n")
        # 각 토픽별 데이터 가져오기
        cursor.execute("SELECT DISTINCT topic FROM papers")
        topics = cursor.fetchall()
        for topic in topics:
            topic_name = topic[0]
            f.write(f"## {topic_name}\n\n")
            cursor.execute("SELECT DISTINCT subtopic FROM papers WHERE topic=?", (topic_name,))
            subtopics = cursor.fetchall()
            for subtopic in subtopics:
                subtopic_name = subtopic[0]
                f.write(f"### {subtopic_name}\n\n")
                f.write("|Publish Date|Title|Authors|PDF|Code|\n")
                f.write("|:-----------|:-----|:------|:---|:---|\n")
                cursor.execute("""
                    SELECT publish_date, title, authors, pdf_url, code_url
                    FROM papers
                    WHERE topic=? AND subtopic=?
                    ORDER BY publish_date DESC
                """, (topic_name, subtopic_name))
                papers = cursor.fetchall()
                for paper in papers:
                    publish_date, title, authors, pdf_url, code_url = paper
                    code_link = f"[link]({code_url})" if code_url else "null"
                    f.write(f"|{publish_date}|**{title}**|{authors}|[PDF]({pdf_url})|{code_link}|\n")
                f.write("\n")
    print(f"Markdown file '{md_filename}' generated successfully.")

if __name__ == "__main__":
    # Initialize database
    conn = init_db('./database/arxiv.db')
    yaml_path = os.path.join("./database", "topic.yml")
    yaml_data = get_yaml_data(yaml_path)
    data_collector = dict()
    for topic in yaml_data.keys():
        for subtopic, keyword in yaml_data[topic].items():
            print("Processing Keyword:", subtopic)
            try:
                data = get_daily_papers(subtopic, query=keyword, max_results=10)
            except Exception as e:
                print(f"Error processing {subtopic}: {e}")
                data = None
            if not topic in data_collector:
                data_collector[topic] = {}
            if data:
                data_collector[topic].update(data)

    # Save collected data to SQLite database
    save_to_db(conn, data_collector)
    
    # Generate Markdown file from database
    db_to_md(conn, 'database/db_markdown/readme.md')
    conn.close()
    
    print("Data saved to SQLite database and Markdown file generated.")