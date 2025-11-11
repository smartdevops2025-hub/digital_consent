import os
import requests

def download_malayalam_fonts():
    """Download Malayalam fonts for better rendering"""
    fonts_dir = "fonts"
    os.makedirs(fonts_dir, exist_ok=True)
    
    font_urls = {
        "Manjari-Regular.ttf": "https://github.com/Manjari-Regular/Manjari/raw/master/fonts/ttf/Manjari-Regular.ttf",
        "NotoSansMalayalam-Regular.ttf": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansMalayalam/NotoSansMalayalam-Regular.ttf"
    }
    
    for font_name, url in font_urls.items():
        font_path = os.path.join(fonts_dir, font_name)
        if not os.path.exists(font_path):
            try:
                print(f"Downloading {font_name}...")
                response = requests.get(url)
                with open(font_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Downloaded {font_name}")
            except Exception as e:
                print(f"❌ Failed to download {font_name}: {e}")

if __name__ == "__main__":
    download_malayalam_fonts()