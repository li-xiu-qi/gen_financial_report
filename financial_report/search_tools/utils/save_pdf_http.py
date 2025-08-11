import requests
from pathlib import Path
from os import path


def save_pdf(url, to,headers:dict=None) -> bool:
    Path(to).parent.mkdir(parents=True, exist_ok=True)
    try:
        response = requests.get(url, headers=headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        })
    except requests.RequestException as e:
        print(f"Error downloading PDF: {e}")
        return False
    if response.status_code == 200:
        with open(to, 'wb') as f:
            f.write(response.content)
        return True
    else:
        print(f"Failed to download PDF. Status code: {response.status_code}")
        return False

