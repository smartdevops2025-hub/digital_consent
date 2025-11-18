import os
import requests

def download_malayalam_font():
    """Download Noto Sans Malayalam font"""
    font_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansMalayalam/NotoSansMalayalam-Regular.ttf"
    font_dir = "static/fonts"
    font_path = os.path.join(font_dir, "NotoSansMalayalam-Regular.ttf")
    
    # Create directory if it doesn't exist
    os.makedirs(font_dir, exist_ok=True)
    
    if not os.path.exists(font_path):
        print("📥 Downloading Malayalam font...")
        try:
            response = requests.get(font_url)
            response.raise_for_status()
            with open(font_path, 'wb') as f:
                f.write(response.content)
            print(f"✅ Malayalam font downloaded to: {font_path}")
            return True
        except Exception as e:
            print(f"❌ Error downloading font: {e}")
            return False
    else:
        print(f"✅ Malayalam font already exists: {font_path}")
        return True

if __name__ == "__main__":
    download_malayalam_font()