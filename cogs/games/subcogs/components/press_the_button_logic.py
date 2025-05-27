import requests
from bs4 import BeautifulSoup



class PressTheButtonLogic():
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.base_url = "https://willyoupressthebutton.com/"

        self.question_url = ""
        self.benefit = ""
        self.drawback = ""

        self.pressed = bool()
        self.result_url = ""
        self.percent_yes = ""
        self.percent_no = ""

        self.get_random_dilemma()

    def request(self, url: str):
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"Failed to load page (HTTP {response.status_code})")
                return None
            return response.text
        except Exception as e:
            print(f"Error: {e}")
            return None

    def get_random_dilemma(self):
        response = self.request(self.base_url)
        if not response: return

        soup = BeautifulSoup(response, 'html.parser')

        dilemma_url = soup.find("meta", property="og:url")
        dilemma_benefit = soup.find(id="cond")
        dilemma_drawback = soup.find(id="res")

        if dilemma_url and dilemma_benefit and dilemma_drawback:
            self.question_url = dilemma_url.get("content")
            self.benefit = dilemma_benefit.get_text(strip=True)
            self.drawback = dilemma_drawback.get_text(strip=True)
        
    def get_dilemma_results(self):
        choice = "yes" if self.pressed else "no"
        self.result_url = f"{self.question_url}/{choice}"
        response = self.request(self.result_url)
        if not response: return
        
        soup = BeautifulSoup(response, "html.parser")

        left_stat = soup.find("span", class_="statsBarLeft")
        right_stat = soup.find("span", class_="statsBarRight")

        if left_stat and right_stat:
            self.percent_yes = left_stat.get_text(strip=True)
            self.percent_no = right_stat.get_text(strip=True)
        
    def press_button(self, pressed: bool = True):
        self.pressed = pressed
        self.get_dilemma_results()
