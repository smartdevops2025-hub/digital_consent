#!/usr/bin/env python3
"""
Script to download and install Malayalam fonts for the consent system
"""

import os
import requests
import zipfile
import io

def download_fonts():
    """Download and install Malayalam fonts"""
    print("📥 Downloading Malayalam fonts...")
    
    # Create fonts directory
    fonts_dir = 'static/fonts'
    os.makedirs(fonts_dir, exist_ok=True)
    
    # Font URLs (direct download links)
    font_urls = {
        'NotoSansMalayalam-Regular.ttf': 'https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansMalayalam/NotoSansMalayalam-Regular.ttf',
    }
    
    for font_filename, font_url in font_urls.items():
        font_path = os.path.join(fonts_dir, font_filename)
        
        if not os.path.exists(font_path):
            try:
                print(f"⬇️ Downloading {font_filename}...")
                response = requests.get(font_url)
                response.raise_for_status()
                
                with open(font_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ Downloaded {font_filename}")
            except Exception as e:
                print(f"❌ Failed to download {font_filename}: {e}")
        else:
            print(f"✅ {font_filename} already exists")
    
    print("🎯 Font installation complete!")

if __name__ == "__main__":
    download_fonts()