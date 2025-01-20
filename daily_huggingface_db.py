from bs4 import BeautifulSoup
import requests 
from huggingface_script.fetch_hf_news import get_arxiv_metadata, fetch_huggingface_news
import sqlite3
from huggingface_script.insert_data import insert_model, insert_hf_news
import datetime 

def initialize_database(db_path="db/database.db"):
    """
    데이터베이스 초기화 및 필요한 테이블 생성
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 테이블 생성 (만약 테이블이 존재하지 않으면)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS hf_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            paper TEXT,
            github_url TEXT,
            license TEXT,
            category TEXT
        )
    """)
    
    # 변경사항 저장
    conn.commit()
    return conn 

def get_huggingface_models(base_url="https://huggingface.co/models"):
    """
    크롤링하여 Hugging Face 모델 메타데이터를 가져옵니다.
    
    Returns:
        dict: 모델 이름을 키로 하는 메타데이터 딕셔너리.
    """
    response = requests.get(base_url)
    if response.status_code != 200:
        print(f"Failed to fetch Hugging Face models: {response.status_code}")
        return {}

    soup = BeautifulSoup(response.content, "html.parser")
    models = {}

    # 모델 카드 데이터 추출
    for card in soup.find_all("div", class_="model-card"):
        try:
            # 모델 이름 추출
            model_name_element = card.find("a", class_="model-name")
            model_name = model_name_element.text.strip() if model_name_element else "Unknown Model"

            # 태그 추출
            tags = [tag.text.strip() for tag in card.find_all("span", class_="tag")]

            # 저자 정보 추출
            author_element = card.find("a", class_="author")
            author_name = author_element.text.strip() if author_element else "Unknown Author"

            # 논문 링크 추출
            paper_link_element = card.find("a", class_="paper-link")
            paper_url = paper_link_element["href"].strip() if paper_link_element else None

            # 메타데이터 정리
            model_data = {
                "model_name": model_name,
                "author": author_name,
                "tags": ", ".join(tags),
                "paper_url": paper_url,
            }

            # 모델 이름을 키로 추가
            models[model_name] = model_data
        except Exception as e:
            print(f"Error parsing model card: {e}")

    return models

def save_huggingface_to_db(conn, data):
    """
    Hugging Face 모델 데이터를 SQLite 데이터베이스에 저장합니다.

    Parameters:
        conn (sqlite3.Connection): SQLite 데이터베이스 연결 객체
        data (dict): Hugging Face 모델 메타데이터 딕셔너리
    """
    cursor = conn.cursor()

    # Hugging Face 데이터를 저장할 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS huggingface_models (
            model_name TEXT PRIMARY KEY,
            author TEXT,
            tags TEXT,
            paper_url TEXT
        )
    """)

    for model_name, model_data in data.items():
        cursor.execute("""
            INSERT OR IGNORE INTO huggingface_models
            (model_name, author, tags, paper_url)
            VALUES (?, ?, ?, ?)
        """, (model_name, model_data["author"], model_data["tags"], model_data["paper_url"]))

    conn.commit()

def db_to_md(conn, md_filename="./database/db_markdown/huggface_readme.md"):
    """
    SQLite DB 데이터를 읽어 Markdown 파일 생성
    """
    cursor = conn.cursor()
    # Markdown 파일 초기화
    with open(md_filename, "w") as f:
        # Header 작성
        f.write("# Hugging Face News\n")
        f.write(f"Updated on {datetime.date.today().strftime('%Y-%m-%d')}\n\n")
        f.write("> Generated from the Hugging Face database.\n\n")

        # 데이터 가져오기
        cursor.execute("SELECT title, paper, github_url, license, category FROM hf_news")
        rows = cursor.fetchall()

        f.write("| Title | Paper | GitHub URL | License | Category |\n")
        f.write("|:------|:------|:-----------|:--------|:---------|\n")

        for row in rows:
            title, paper, github_url, license, category = row
            print(row)
            # paper_link = f"[Link]({paper})" if paper != "NULL" else "NULL"
            title = title if title != [] else "NULL"
            paper_link = paper if paper != "NULL" else "NULL"
            github_link = f"[Link]({github_url})" if github_url else "NULL"
            f.write(f"| {title} | {paper_link} | {github_link} | {license} | {category} |\n")

    print(f"Markdown file '{md_filename}' generated successfully.")



if __name__ == "__main__":
    db_path = './database/huggingface_model.db'
    conn = initialize_database(db_path)
    hf_news = fetch_huggingface_news(limit=100)


    insert_hf_news(hf_news, db_path) 
    db_to_md(conn)







    
