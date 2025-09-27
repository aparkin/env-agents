import time, requests
class HttpClient:
    def __init__(self, user_agent: str="env-agents/0.1.0", timeout: int=60):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.timeout = timeout
    def get(self, url: str, params: dict | None = None, retries: int = 3):
        backoff = 1.0
        for _ in range(retries+1):
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code in (429,500,502,503,504):
                ra = resp.headers.get("Retry-After")
                sleep = float(ra) if ra else backoff
                time.sleep(sleep)
                backoff *= 2
                continue
            resp.raise_for_status()
            return resp
        return resp
