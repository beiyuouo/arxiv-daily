import requests
from xml.etree import ElementTree
# from tqdm import tqdm
import arxiv

def get_arxiv_metadata(arxiv_id):
    """
    ArXiv ID를 사용하여 논문 메타데이터(제목, 저자)를 가져옵니다.
    """
    base_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    response = requests.get(base_url)
    # API 호출 상태 확인
    if response.status_code != 200:
        print(f"ArXiv API 호출 실패: {response.status_code}")
        return {"title": "Unknown", "authors": []}
    try:
        # XML 파싱
        root = ElementTree.fromstring(response.content)
        # Entry 태그로 이동
        entry = root.find("{http://www.w3.org/2005/Atom}entry")
        if entry is None:
            print("논문 정보를 찾을 수 없습니다.")
            return {"title": "Unknown", "authors": []}
        # 논문 제목 추출
        title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip()
        # 저자 정보 추출
        authors = [
            author.find("{http://www.w3.org/2005/Atom}name").text.strip()
            for author in entry.findall("{http://www.w3.org/2005/Atom}author")
        ]
        return {"title": title, "authors": authors}
    except Exception as e:
        print(f"오류 발생: {e}")
        return {"title": "Unknown", "authors": []}
def get_paper_url_by_title(title):
    """
    논문 제목을 입력받아 해당 논문의 paper_url을 반환하는 함수.
    Args:
        title (str): 논문 제목
    Returns:
        str: 논문의 URL (찾지 못한 경우 None 반환)
    """
    try:
        # arxiv 검색 설정
        search = arxiv.Search(
            query=title,
            max_results=1,  # 제목으로 검색 시 첫 번째 결과만 반환
            sort_by=arxiv.SortCriterion.Relevance
        )
        # 검색 결과 처리
        for result in search.results():
            return result.entry_id  # 논문의 URL 반환
    except Exception as e:
        print(f"Error occurred: {e}")
    return None  # 논문을 찾지 못한 경우 None 반환
def fetch_huggingface_news(limit=10):
    """
    Hugging Face API에서 최신 소식 가져오기 + ArXiv 논문 저자 정보 추가
    """
    url = f"https://huggingface.co/api/models?limit={limit}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"API 호출 실패: {response.status_code}")
        return []
    models = response.json()
    news_data = []
    for model in models:
        # 'arxiv' 태그 추출
        arxiv_links = [tag.split(":")[1] for tag in model.get("tags", []) if tag.startswith("arxiv:")]
        # ArXiv 저자 정보 가져오기
        arxiv_authors = []
        for arxiv_id in arxiv_links:
            metadata = get_arxiv_metadata(arxiv_id)
            arxiv_authors.append({"id": arxiv_id, "title": metadata["title"], "authors": metadata["authors"]})
        # 'license' 정보 추출
        license_info = next((tag.split(":")[1] for tag in model.get("tags", []) if tag.startswith("license:")), "Unknown license")
        # ArXiv 정보 추가
        if arxiv_authors:
            arxiv_info = arxiv_authors[0]  # 첫 번째 논문 정보만 사용
            arxiv_title = arxiv_info["title"]
            arxiv_authors_list = arxiv_info["authors"]
        else:
            arxiv_title = "NULL"
            arxiv_authors_list = []
        # GitHub URL: Hugging Face 모델 페이지 URL로 구성
        github_url = f"https://huggingface.co/{model.get('modelId')}"
        
        print(arxiv_title)
        arxiv_title = get_paper_url_by_title(arxiv_title)
        # 데이터 추가
        print(arxiv_title)
        news_data.append({
            "title": model.get("modelId"),
            "github_url": github_url,
            "category": model.get("pipeline_tag"),
            "arxiv_links": arxiv_title,
            "authors": arxiv_authors_list,
            "license": license_info
        })
    return news_data