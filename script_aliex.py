from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json
import re

app = Flask(__name__)

def scrape_thepillowhome(url):
    """Scrapea título e imágenes principales de The Pillow Home"""
    playwright = None
    browser = None
    try:
        # Iniciar Playwright
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navegar a la página
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        page.wait_for_timeout(2000)
        
        # Obtener el HTML
        html_content = page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # EXTRAER TÍTULO (Shopify usa h1 con clase específica)
        titulo = ""
        title_tag = soup.find('h1', class_='product__title') or soup.find('h1')
        if title_tag:
            titulo = title_tag.get_text(strip=True)
        
        # EXTRAER IMÁGENES PRINCIPALES (Shopify usa un patrón específico)
        imagenes = []
        
        # Buscar en el contenedor de imágenes de Shopify
        img_containers = soup.find_all('div', class_='product__media')
        if not img_containers:
            img_containers = soup.find_all('div', class_='product-single__photos')
        
        for container in img_containers:
            imgs = container.find_all('img')
            for img in imgs:
                img_url = img.get('src') or img.get('data-src')
                if img_url:
                    # Normalizar URL
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = 'https://thepillowhome.com' + img_url
                    
                    # Evitar duplicados
                    if img_url not in imagenes:
                        imagenes.append(img_url)
        
        # Si no encontró imágenes, buscar de forma genérica
        if not imagenes:
            all_imgs = soup.find_all('img')
            for img in all_imgs[:10]:  # Limitar a las primeras 10
                img_url = img.get('src') or img.get('data-src')
                if img_url and 'product' in img_url.lower():
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = 'https://thepillowhome.com' + img_url
                    
                    if img_url not in imagenes:
                        imagenes.append(img_url)
        
        return {
            'success': True,
            'titulo': titulo,
            'imagenes': imagenes
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        if browser:
            browser.close()
        if playwright:
            playwright.stop()

def scrape_aliexpress(url):
    """Scrapea título e imágenes principales de AliExpress"""
    playwright = None
    browser = None
    try:
        # Iniciar Playwright
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navegar a la página
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        page.wait_for_timeout(2000)
        
        # Obtener el HTML
        html_content = page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # EXTRAER TÍTULO
        titulo = ""
        title_tag = soup.find('h1')
        if title_tag:
            titulo = title_tag.get_text(strip=True)
        
        # EXTRAER IMÁGENES PRINCIPALES del JSON embebido
        imagenes = []
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string and 'imagePathList' in script.string:
                try:
                    pattern = r'"imagePathList"\s*:\s*(\[[^\]]+\])'
                    match = re.search(pattern, script.string)
                    if match:
                        imagenes = json.loads(match.group(1))
                        # Normalizar URLs
                        imagenes = ['https:' + img if img.startswith('//') else img for img in imagenes]
                        break
                except:
                    pass
        
        return {
            'success': True,
            'titulo': titulo,
            'imagenes': imagenes
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        if browser:
            browser.close()
        if playwright:
            playwright.stop()

@app.route('/scrape', methods=['GET', 'POST'])
def scrape():
    if request.method == 'POST':
        data = request.get_json()
        url = data.get('url')
    else:
        url = request.args.get('url')
    
    if not url:
        return jsonify({
            'success': False,
            'error': 'Se requiere el parámetro "url"'
        }), 400
    
    # Detectar el dominio de la URL
    parsed_url = urlparse(url)
    dominio = parsed_url.netloc.lower()
    
    # Determinar qué función usar según el dominio
    if 'aliexpress.com' in dominio:
        result = scrape_aliexpress(url)
    elif 'thepillowhome.com' in dominio:
        result = scrape_thepillowhome(url)
    else:
        # Si no es un sitio soportado, devolver error
        result = {
            'success': False,
            'error': f'Sitio no soportado: {dominio}. Sitios disponibles: aliexpress.com, thepillowhome.com'
        }
    
    return jsonify(result)

@app.route('/')
def home():
    return jsonify({
        'message': 'Scraper multi-sitio activo',
        'sitios_soportados': ['aliexpress.com', 'thepillowhome.com'],
        'uso': 'GET o POST a /scrape con parámetro url',
        'ejemplo': {
            'url': 'https://www.aliexpress.com/item/1005008988478906.html'
        }
    })

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
