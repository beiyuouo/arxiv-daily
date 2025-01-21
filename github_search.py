import requests
import base64

class GitHubRepoAnalyzer:
    def __init__(self, repo_url, token=None):
        self.base_url = self.convert_to_api_url(repo_url)
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {token}" if token else None
        }
        self.framework_keywords = {
            "pytorch": ["torch", "torchvision"],
            "tensorflow": ["tensorflow", "tf.keras"],
        }
        self.code_extensions = {".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go", ".html", ".css", ".sh", ".rb", ".php", ".ipynb"}

    def convert_to_api_url(self, repo_url):
        """Convert a standard GitHub URL to a GitHub API URL."""
        if repo_url.startswith("https://github.com/"):
            parts = repo_url.replace("https://github.com/", "").split("/")
            if len(parts) >= 2:
                owner, repo = parts[:2]
                return f"https://api.github.com/repos/{owner}/{repo}/contents"
        raise ValueError("Invalid GitHub URL format")

    def get_file_content(self, file_url):
        """Get the content of a file from GitHub."""
        response = requests.get(file_url, headers=self.headers)
        if response.status_code == 200:
            content = base64.b64decode(response.json()["content"]).decode("utf-8")
            return content
        return ""

    def detect_framework_in_content(self, content):
        """Detect the framework from a file's content."""
        for framework, keywords in self.framework_keywords.items():
            if any(keyword in content for keyword in keywords):
                return framework
        return None

    def analyze_directory(self, url):
        """Analyze a directory recursively for code files and frameworks."""
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return {"is_empty": True, "framework": None}

        files = response.json()
        has_code_file = False
        detected_framework = None

        for file in files:
            if file["type"] == "file" and file["name"].endswith(tuple(self.code_extensions)):
                has_code_file = True
                content = self.get_file_content(file["url"])
                framework = self.detect_framework_in_content(content)
                if framework:
                    detected_framework = framework
                    break  # Stop searching once a framework is detected
            elif file["type"] == "dir":
                # Recursively analyze subdirectories
                result = self.analyze_directory(file["url"])
                if result["is_empty"] == False:
                    has_code_file = True
                if result["framework"]:
                    detected_framework = result["framework"]
                    break

        return {"is_empty": not has_code_file, "framework": detected_framework}

    def analyze_repo(self):
        """Analyze the GitHub repository from the base URL."""
        result = self.analyze_directory(self.base_url)
        if result["is_empty"]:
            return "레포지토리에 코드가 없습니다."
        elif result["framework"]:
            return f"코드를 발견했습니다. 사용된 프레임워크: {result['framework']}"
        else:
            return "코드를 발견했지만, 특정 프레임워크는 감지되지 않았습니다."



# 사용 예시
base_url = "https://github.com/songxf1024/gims"
analyzer = GitHubRepoAnalyzer(base_url, token="my Token")
print(analyzer.analyze_repo())
