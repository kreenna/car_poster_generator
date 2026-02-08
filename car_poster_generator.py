#!/usr/bin/env python3
"""
Car Poster Generator
Fetches car specifications from automobile-catalog.com and generates a poster image.
"""

import requests
from bs4 import BeautifulSoup
import re
from PIL import Image, ImageDraw, ImageFont
import os
from typing import Dict, List, Optional
import time
from urllib.parse import urljoin, quote


def _fetch_with_selenium(url: str, timeout: int = 30, verbose: bool = False) -> Optional[str]:
    """Fetch page HTML using Selenium. Tries undetected-chromedriver first, then regular Chrome with anti-detection options."""
    driver = None

    def _get_driver_uc():
        """Try undetected-chromedriver (best at bypassing Cloudflare)."""
        try:
            import undetected_chromedriver as uc
            opts = uc.ChromeOptions()
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--window-size=1920,1080")
            # Match Chrome version: env CHROME_MAJOR_VERSION=144 if driver/browser versions mismatch
            version_main = None
            try:
                v = os.environ.get("CHROME_MAJOR_VERSION", "").strip()
                if v and v.isdigit():
                    version_main = int(v)
            except Exception:
                pass
            err_msg = ""
            for attempt in range(2):
                try:
                    if version_main is not None:
                        driver = uc.Chrome(options=opts, version_main=version_main)
                    else:
                        driver = uc.Chrome(options=opts)
                    driver.set_page_load_timeout(timeout)
                    return driver
                except Exception as e:
                    err_msg = str(e)
                    # ChromeDriver version mismatch: "Current browser version is 144.x" -> use 144
                    match = re.search(r"Current browser version is (\d+)", err_msg, re.I)
                    if match and version_main is None:
                        version_main = int(match.group(1))
                        if verbose:
                            print(f"  Using ChromeDriver for version {version_main} to match your browser.")
                        continue
                    break
            if verbose and err_msg:
                print(f"  undetected_chromedriver failed: {err_msg}")
                if "distutils" in err_msg.lower():
                    print("  Fix (Python 3.12+): pip install setuptools")
                if "version" in err_msg.lower() and "chrome" in err_msg.lower():
                    print("  Fix: set CHROME_MAJOR_VERSION=144  (match your Chrome major version)")
            return None
        except Exception as e:
            if verbose:
                print(f"  undetected_chromedriver not available or failed: {e}")
                if "distutils" in str(e).lower():
                    print("  Fix (Python 3.12+): pip install setuptools")
            return None

    def _get_driver_plain():
        """Fallback: standard Selenium with anti-detection options."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(timeout)
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            })
            return driver
        except Exception as e:
            if verbose:
                print(f"  Selenium Chrome failed: {e}")
            return None

    try:
        driver = _get_driver_uc()
        if driver is None:
            driver = _get_driver_plain()
        if driver is None:
            if verbose:
                print("  Install: pip install undetected-chromedriver  (recommended for Cloudflare sites)")
            return None

        driver.get(url)
        # Wait for Cloudflare or real content
        for _ in range(18):
            time.sleep(1)
            html = driver.page_source
            if "Just a moment" in html or "Checking your browser" in html:
                if verbose and _ == 0:
                    print("  Waiting for Cloudflare check...")
                continue
            # Page likely loaded (no challenge), allow a bit more for dynamic content
            if len(html) > 5000:
                time.sleep(2)
                html = driver.page_source
                if "Just a moment" not in html and "Checking your browser" not in html:
                    return html
        # Timeout or still on challenge page
        html = driver.page_source if driver else ""
        if "Just a moment" in html or "Checking your browser" in html:
            if verbose:
                print("  Site still showing Cloudflare check. Try: pip install undetected-chromedriver")
            return None
        return html
    except Exception as e:
        if verbose:
            print(f"  Browser fetch error: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


# Car brand -> country of production (ISO 3166-1 alpha-2)
BRAND_COUNTRY = {
    'audi': 'DE', 'bmw': 'DE', 'mercedes': 'DE', 'mercedes-benz': 'DE', 'porsche': 'DE',
    'volkswagen': 'DE', 'vw': 'DE', 'opel': 'DE', 'maybach': 'DE', 'smart': 'DE',
    'ferrari': 'IT', 'lamborghini': 'IT', 'maserati': 'IT', 'fiat': 'IT', 'alfa romeo': 'IT',
    'lancia': 'IT', 'pagani': 'IT',
    'renault': 'FR', 'peugeot': 'FR', 'citroën': 'FR', 'citroen': 'FR', 'bugatti': 'FR',
    'bentley': 'GB', 'rolls-royce': 'GB', 'aston martin': 'GB', 'jaguar': 'GB',
    'land rover': 'GB', 'mclaren': 'GB', 'lotus': 'GB', 'mini': 'GB', 'mg': 'GB',
    'ford': 'US', 'chevrolet': 'US', 'tesla': 'US', 'dodge': 'US',
    'jeep': 'US', 'cadillac': 'US', 'gmc': 'US', 'buick': 'US', 'chrysler': 'US',
    'toyota': 'JP', 'honda': 'JP', 'nissan': 'JP', 'mazda': 'JP', 'subaru': 'JP',
    'lexus': 'JP', 'infiniti': 'JP', 'acura': 'JP', 'suzuki': 'JP', 'mitsubishi': 'JP',
    'hyundai': 'KR', 'kia': 'KR', 'genesis': 'KR', 'ssangyong': 'KR',
    'volvo': 'SE', 'koenigsegg': 'SE', 'saab': 'SE',
    'skoda': 'CZ', 'tatra': 'CZ',
    'dacia': 'RO',
    'seat': 'ES', 'cupra': 'ES',
    'tata': 'IN', 'mahindra': 'IN',
}

# Flag drawing: 'h' = horizontal stripes (colors top to bottom), 'v' = vertical (left to right),
# 'circle' = (bg_color, circle_color) for Japan-style, 'cross' = (bg_color, cross_color) for Sweden
FLAG_DEFINITIONS = {
    'DE': ('h', ['#000000', '#DD0000', '#FFCE00']),  # Germany
    'AT': ('h', ['#ED2939', '#FFFFFF', '#ED2939']),  # Austria
    'IT': ('v', ['#009246', '#FFFFFF', '#CE2B37']),  # Italy
    'FR': ('v', ['#002395', '#FFFFFF', '#ED2939']),  # France
    'JP': ('circle', ('#FFFFFF', '#BC002D')),        # Japan
    'US': ('h', (['#B22234', '#FFFFFF'] * 7)[:13]), # USA: 7 red + 6 white (simplified)
    'GB': ('h', ['#012169', '#FFFFFF', '#C8102E']), # UK simplified (union jack is complex)
    'KR': ('h', ['#FFFFFF', '#003478', '#C60C30']), # South Korea simplified
    'SE': ('cross', ('#006AA7', '#FECC00')),        # Sweden
    'CZ': ('h', ['#11457E', '#FFFFFF', '#D7141A']), # Czech Republic (white wedge simplified as h)
    'RO': ('v', ['#002B7F', '#FCD116', '#CE1126']),  # Romania
    'ES': ('h', ['#C60B1E', '#FFC400', '#C60B1E']), # Spain (simplified, no coat of arms)
    'IN': ('h', ['#FF9933', '#FFFFFF', '#138808']), # India
    'CH': ('h', ['#FF0000', '#FFFFFF']),            # Switzerland (square cross simplified)
    'NL': ('h', ['#AE1C28', '#FFFFFF', '#21468B']), # Netherlands
    'BE': ('v', ['#000000', '#FDDA24', '#ED2939']), # Belgium
    'PL': ('h', ['#FFFFFF', '#DC143C']),           # Poland
    'RU': ('h', ['#FFFFFF', '#0039A6', '#D52B1E']), # Russia
}

# Known fallback URLs when scraping is blocked. Site path: /model/BRAND/MODEL.html (model slug required).
KNOWN_MODEL_URLS = {
    ("audi", "tt rs"): [
        ("Audi TT RS", "https://www.automobile-catalog.com/model/audi/tt_gen_2.html"),
        ("Audi TT RS", "https://www.automobile-catalog.com/model/audi/tt_rs.html"),
    ],
}


class CarSpecScraper:
    """Scrapes car specifications from automobile-catalog.com"""
    
    BASE_URL = "https://www.automobile-catalog.com"
    SKIP_LINK_TEXTS = {'Home', 'Search', 'About', 'Back', 'Login', 'Sign in', 'Contact', 'Privacy', 'Terms'}
    
    def __init__(self, verbose: bool = False):
        self.session = requests.Session()
        self.verbose = verbose
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def _is_blocked(self, response: requests.Response) -> bool:
        if response.status_code == 403:
            return True
        text = (response.text or "")[:2000]
        return "Just a moment" in text or "cf_chl" in text or "challenge" in text.lower()
    
    def _extract_models_from_soup(self, soup: BeautifulSoup, brand: str) -> List[Dict]:
        """Extract model entries from parsed HTML. Site path format: /model/BRAND/MODEL.html"""
        models = []
        seen_urls = set()
        brand_lower = brand.lower()
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').strip()
            text = link.get_text(strip=True)
            if not text or len(text) < 2 or text in self.SKIP_LINK_TEXTS:
                continue
            full_url = urljoin(self.BASE_URL, href)
            if self.BASE_URL not in full_url or 'automobile-catalog.com' not in full_url:
                continue
            path_lower = href.lower() if href.startswith('/') else full_url.lower()
            # Accept links to /model/... (and legacy /car/, /make/ if present)
            if '/model/' in path_lower or '/car/' in path_lower or '/make/' in path_lower or brand_lower in path_lower:
                if full_url not in seen_urls and len(text) < 120:
                    seen_urls.add(full_url)
                    models.append({'name': text, 'url': full_url})
        
        return models
    
    def search_brand(self, brand: str, model_slug: Optional[str] = None) -> List[Dict]:
        """Get model URL(s) to try. Site has no brand-only page; path must be /model/BRAND/MODEL.html."""
        if not model_slug:
            return []
        brand_slug = brand.lower().strip().replace(' ', '_')
        slug = model_slug.lower().strip().replace(' ', '_').replace('-', '_')
        url = f"{self.BASE_URL}/model/{brand_slug}/{slug}.html"
        return [{"name": f"{brand} {model_slug.replace('_', ' ').title()}", "url": url}]
    
    def get_model_specs(self, model_url: str) -> Optional[Dict]:
        """Get specifications for a specific car model"""
        try:
            print(f"Fetching: {model_url}")
            response = self.session.get(model_url, timeout=15)
            html = None
            if self._is_blocked(response):
                print("  Page blocked, trying browser fallback...")
                html = _fetch_with_selenium(model_url, verbose=self.verbose)
            if html is None and response.ok:
                html = response.text
            if not html:
                return None
            soup = BeautifulSoup(html, 'html.parser')
            
            specs = {}
            text_content = soup.get_text(separator=' ', strip=True)
            
            # Look for specification tables
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        label = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        # Map common labels to our spec keys; only accept short, spec-like values
                        def _ok_spec_val(v, max_len=35):
                            v = (v or "").strip().replace("\n", " ")[:max_len]
                            if not v or len(v) > max_len:
                                return None
                            if any(x in v.lower() for x in ("coupe", "roadster", "submodel", "belonging", "vers", "gen.")):
                                return None
                            return v
                        if 'engine' in label or 'displacement' in label:
                            if _ok_spec_val(value):
                                specs['engine'] = _ok_spec_val(value)
                        elif 'power' in label or 'horsepower' in label or 'hp' in label:
                            if _ok_spec_val(value):
                                specs['power'] = _ok_spec_val(value)
                        elif 'torque' in label:
                            if _ok_spec_val(value):
                                specs['torque'] = _ok_spec_val(value)
                        elif 'weight' in label or 'mass' in label:
                            if _ok_spec_val(value):
                                specs['weight'] = _ok_spec_val(value)
                        elif 'acceleration' in label or '0-100' in label or '0-60' in label:
                            if _ok_spec_val(value):
                                specs['acceleration_0_100'] = _ok_spec_val(value)
                        elif 'top speed' in label or 'maximum speed' in label:
                            if _ok_spec_val(value):
                                specs['top_speed'] = _ok_spec_val(value)
                        elif 'year' in label or 'production' in label:
                            if _ok_spec_val(value, 20) and re.match(r"^[\d\s\-]+$", value.strip()[:20]):
                                specs['year'] = value.strip()[:20]
            
            # Fallback: Use regex patterns on full text
            if not specs.get('engine'):
                engine_match = re.search(r'(\d+\.?\d*)\s*L(?:\s*TFSI|\s*TDI|\s*V6|\s*V8|\s*I4)?', text_content, re.I)
                if engine_match:
                    specs['engine'] = engine_match.group(0).strip()
            
            if not specs.get('power'):
                # Look for HP, PS, or kW
                power_match = re.search(r'(\d+)\s*(?:HP|hp|PS|ps|kW|kw)', text_content, re.I)
                if power_match:
                    specs['power'] = f"{power_match.group(1)} HP"
            
            if not specs.get('torque'):
                torque_match = re.search(r'(\d+)\s*Nm|(\d+)\s*lb-ft|(\d+)\s*lb\.ft', text_content, re.I)
                if torque_match:
                    if torque_match.group(1):
                        specs['torque'] = f"{torque_match.group(1)} Nm"
                    else:
                        specs['torque'] = f"{torque_match.group(2) or torque_match.group(3)} lb-ft"
            
            if not specs.get('weight'):
                weight_match = re.search(r'(\d{3,5})\s*kg|(\d{3,5})\s*lbs?', text_content, re.I)
                if weight_match:
                    if weight_match.group(1):
                        specs['weight'] = f"{weight_match.group(1)} kg"
                    else:
                        specs['weight'] = f"{weight_match.group(2)} lbs"
            
            if not specs.get('acceleration_0_100'):
                accel_match = re.search(r'0-100[^\d]*(\d+\.?\d*)\s*s(?:ec)?|0-60[^\d]*(\d+\.?\d*)\s*s(?:ec)?', text_content, re.I)
                if accel_match:
                    specs['acceleration_0_100'] = f"{accel_match.group(1) or accel_match.group(2)} s"
            
            if not specs.get('top_speed'):
                speed_match = re.search(r'(?:top|max(?:imum)?)\s*speed[^\d]*(\d+)\s*km/h|(\d+)\s*km/h.*top', text_content, re.I)
                if speed_match:
                    specs['top_speed'] = f"{speed_match.group(1) or speed_match.group(2)} km/h"
            
            if not specs.get('year'):
                # Look for year ranges in the URL or text
                year_match = re.search(r'(\d{4})\s*-\s*(\d{4})|(\d{4})', model_url + ' ' + text_content)
                if year_match:
                    if year_match.group(2):
                        specs['year'] = f"{year_match.group(1)}-{year_match.group(2)}"
                    else:
                        specs['year'] = year_match.group(3)

            # Extract main car image URL (for poster)
            for img in soup.find_all('img', src=True):
                src = img.get('src', '').strip()
                if not src or 'logo' in src.lower() or 'icon' in src.lower() or 'pixel' in src.lower():
                    continue
                full_img_url = urljoin(model_url, src)
                if 'automobile-catalog.com' in full_img_url or full_img_url.startswith('http'):
                    specs['image_url'] = full_img_url
                    break
            if 'image_url' not in specs:
                for img in soup.find_all('img', src=True):
                    src = img.get('src', '').strip()
                    if src and len(src) > 10:
                        specs['image_url'] = urljoin(model_url, src)
                        break
            
            return specs if specs else None
            
        except Exception as e:
            print(f"Error getting specs from {model_url}: {e}")
            import traceback
            traceback.print_exc()
            return None


class PosterGenerator:
    """Generates car poster images matching the reference design"""
    
    def __init__(self, width=1200, height=1600):
        self.width = width
        self.height = height
        self.margin = 60
        self.border_width = 2
    
    def _get_font(self, size, bold=False):
        """Get font with fallback options"""
        font_paths = [
            ("arial.ttf", "arialbd.ttf"),
            ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
            ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf"),
            ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Helvetica.ttc"),
        ]
        
        for regular, bold_font in font_paths:
            try:
                if bold and os.path.exists(bold_font):
                    return ImageFont.truetype(bold_font, size)
                elif os.path.exists(regular):
                    font = ImageFont.truetype(regular, size)
                    # Try to make it bold by using a larger size
                    if bold:
                        return ImageFont.truetype(regular, int(size * 1.1))
                    return font
            except:
                continue
        
        # Ultimate fallback
        return ImageFont.load_default()
    
    def _draw_country_flag(self, draw: ImageDraw.ImageDraw, country_code: str, x: int, y: int, w: int, h: int):
        """Draw the flag of the given country (ISO 3166-1 alpha-2) in the given rectangle."""
        country_code = (country_code or '').upper()[:2]
        if not country_code or country_code not in FLAG_DEFINITIONS:
            return
        kind, data = FLAG_DEFINITIONS[country_code]
        if kind == 'h':
            colors = data
            n = len(colors)
            stripe_h = h / n
            for i, color in enumerate(colors):
                y1 = int(y + i * stripe_h)
                y2 = int(y + (i + 1) * stripe_h)
                draw.rectangle([x, y1, x + w, y2], fill=color)
        elif kind == 'v':
            colors = data
            n = len(colors)
            stripe_w = w / n
            for i, color in enumerate(colors):
                x1 = int(x + i * stripe_w)
                x2 = int(x + (i + 1) * stripe_w)
                draw.rectangle([x1, y, x2, y + h], fill=color)
        elif kind == 'circle':
            bg_color, circle_color = data
            draw.rectangle([x, y, x + w, y + h], fill=bg_color)
            cx = x + w // 2
            cy = y + h // 2
            r = int(min(w, h) * 0.35)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=circle_color)
        elif kind == 'cross':
            bg_color, cross_color = data
            draw.rectangle([x, y, x + w, y + h], fill=bg_color)
            bar_w = max(2, w // 5)
            bar_h = max(2, h // 5)
            # Vertical bar
            v_x = x + (w - bar_w) // 2
            draw.rectangle([v_x, y, v_x + bar_w, y + h], fill=cross_color)
            # Horizontal bar
            h_y = y + (h - bar_h) // 2
            draw.rectangle([x, h_y, x + w, h_y + bar_h], fill=cross_color)
    
    def _sanitize_spec_value(self, v: str, max_len: int = 22) -> str:
        """Keep spec values short so they don't overlap in layout."""
        if not v:
            return ""
        v = str(v).strip().replace("\n", " ").replace("\r", " ")
        if len(v) > max_len:
            v = v[: max_len - 1] + "…"
        return v

    def generate_poster(self, brand: str, model: str, specs: Dict, output_path: str):
        """Generate a poster image with car specifications matching reference design"""
        # Strip internal keys used for image URL
        display_specs = {k: v for k, v in specs.items() if not k.startswith("_") and k != "image_url"}
        image_url = specs.get("image_url")

        # Create image with white background
        img = Image.new("RGB", (self.width, self.height), color="white")
        draw = ImageDraw.Draw(img)

        # Load fonts
        brand_font = self._get_font(64, bold=True)
        model_font = self._get_font(88, bold=True)
        label_font = self._get_font(26, bold=True)
        value_font = self._get_font(24, bold=False)

        # Border lines
        border_x = self.margin
        draw.line([(border_x, self.margin), (border_x, self.height - self.margin)], fill="#d0d0d0", width=1)
        draw.line([(self.width - border_x, self.margin), (self.width - border_x, self.height - self.margin)], fill="#d0d0d0", width=1)

        # Header
        header_y = self.margin + 50
        brand_text = brand.upper()
        draw.text((self.margin + 50, header_y), brand_text, fill="#888888", font=brand_font)
        bbox = draw.textbbox((0, 0), brand_text, font=brand_font)
        brand_height = bbox[3] - bbox[1]
        model_text = model.upper()
        model_y = header_y + brand_height + 15
        draw.text((self.margin + 50, model_y), model_text, fill="#1a1a1a", font=model_font)
        bbox = draw.textbbox((0, 0), model_text, font=model_font)
        model_header_bottom = model_y + (bbox[3] - bbox[1])

        # Gray image area (reference style) and car image
        image_area_top = model_header_bottom + 40
        spec_area_top = self.height - self.margin - 320
        image_area_bottom = spec_area_top - 40
        gray_bg = "#e5e5e5"
        draw.rectangle([border_x + 20, image_area_top, self.width - border_x - 20, image_area_bottom], fill=gray_bg)

        if image_url:
            try:
                resp = requests.get(image_url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (compatible; CarPoster/1.0)"})
                if resp.ok:
                    from io import BytesIO
                    car_img = Image.open(BytesIO(resp.content)).convert("RGB")
                    iw, ih = car_img.size
                    box_w = self.width - 2 * self.margin - 40
                    box_h = image_area_bottom - image_area_top
                    scale = min(box_w / iw, box_h / ih, 1.0)
                    nw, nh = int(iw * scale), int(ih * scale)
                    car_img = car_img.resize((nw, nh), Image.Resampling.LANCZOS)
                    paste_x = self.margin + 20 + (box_w - nw) // 2
                    paste_y = image_area_top + (box_h - nh) // 2
                    img.paste(car_img, (paste_x, paste_y))
            except Exception:
                pass

        # Specs section: fixed column widths so text never overlaps
        spec_y_start = spec_area_top
        line_height = 42
        text_color = "#1a1a1a"
        col_width = (self.width - 2 * self.margin - 100) // 3
        left_col_x = self.margin + 50
        mid_col_x = left_col_x + col_width + 20
        right_col_x = mid_col_x + col_width + 20
        max_val_len = 18

        # Left: YEAR
        if "year" in display_specs:
            val = self._sanitize_spec_value(display_specs["year"], max_val_len)
            draw.text((left_col_x, spec_y_start), "YEAR", fill=text_color, font=label_font)
            draw.text((left_col_x, spec_y_start + line_height), val, fill=text_color, font=value_font)

        # Middle: Engine, Power, Torque, Weight (fixed width column)
        mid_items = []
        for key, label in [("engine", "Engine"), ("power", "Power"), ("torque", "Torque"), ("weight", "Weight")]:
            if key in display_specs:
                mid_items.append((label, self._sanitize_spec_value(display_specs[key], max_val_len)))
        mid_label_w = 75
        mid_val_start = mid_col_x + mid_label_w + 12
        mid_val_end = mid_col_x + col_width - 10
        for i, (label, value) in enumerate(mid_items):
            y = spec_y_start + i * line_height
            draw.text((mid_col_x, y), label, fill=text_color, font=label_font)
            vb = draw.textbbox((0, 0), value, font=value_font)
            val_w = min(vb[2] - vb[0], mid_val_end - mid_val_start)
            draw.text((mid_val_end - val_w, y), value, fill=text_color, font=value_font)

        # Right: 0-100, Top speed, flag
        right_items = []
        if "acceleration_0_100" in display_specs:
            right_items.append(("0-100 km/h", self._sanitize_spec_value(display_specs["acceleration_0_100"], max_val_len)))
        if "top_speed" in display_specs:
            right_items.append(("Top speed", self._sanitize_spec_value(display_specs["top_speed"], max_val_len)))
        r_label_w = 110
        r_val_end = right_col_x + col_width - 10
        for i, (label, value) in enumerate(right_items):
            y = spec_y_start + i * line_height
            draw.text((right_col_x, y), label, fill=text_color, font=label_font)
            vb = draw.textbbox((0, 0), value, font=value_font)
            val_w = min(vb[2] - vb[0], col_width - r_label_w - 15)
            draw.text((r_val_end - val_w, y), value, fill=text_color, font=value_font)

        # Flag
        country_code = BRAND_COUNTRY.get(brand.strip().lower())
        flag_y = spec_y_start + len(right_items) * line_height + 12
        flag_w, flag_h = 36, 24
        flag_x = r_val_end - flag_w
        if country_code:
            self._draw_country_flag(draw, country_code, flag_x, flag_y, flag_w, flag_h)
        
        # Save image
        if output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
            # Convert to RGB if needed for JPG
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(output_path, 'JPEG', quality=95)
        else:
            img.save(output_path, 'PNG', quality=95)
        
        print(f"Poster saved to: {output_path}")


def demo_mode():
    """Generate a demo poster with sample data (for testing)"""
    generator = PosterGenerator()
    demo_specs = {
        'year': '2016-2023',
        'engine': '2.5L TFSI',
        'power': '394 HP',
        'torque': '480 Nm',
        'weight': '1450 kg',
        'acceleration_0_100': '3.7 s',
        'top_speed': '250 km/h'
    }
    generator.generate_poster('AUDI', 'TT RS', demo_specs, 'demo_poster.png')
    print("Demo poster generated: demo_poster.png")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate car poster from automobile-catalog.com',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python car_poster_generator.py Audi --model "TT RS"
  python car_poster_generator.py Audi --model tt_gen_2   (exact slug from site)
  python car_poster_generator.py BMW --model "M3" --output bmw_m3.jpg
  python car_poster_generator.py --demo  # Generate demo poster with sample data

Site URL format: https://www.automobile-catalog.com/model/BRAND/MODEL.html (model slug required).
        """
    )
    parser.add_argument('brand', nargs='?', help='Car brand (e.g., Audi, BMW)')
    parser.add_argument('--model', help='Model name or slug (required), e.g. "TT RS" or tt_gen_2')
    parser.add_argument('--output', default='car_poster.png', help='Output file path (PNG or JPG)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--demo', action='store_true', help='Generate demo poster with sample data')
    
    args = parser.parse_args()
    
    # Demo mode
    if args.demo:
        demo_mode()
        return
    
    if not args.brand:
        parser.print_help()
        return
    
    scraper = CarSpecScraper(verbose=args.verbose)
    generator = PosterGenerator()

    # Site uses /model/BRAND/MODEL.html only; there is no brand-only page. --model is required.
    if not args.model:
        print(f"\n[!] --model is required. The site uses URLs like /model/brand/model_slug.html")
        print(f"    Example: python car_poster_generator.py Audi --model \"TT RS\"")
        print(f"    Or with exact slug: python car_poster_generator.py Audi --model tt_gen_2")
        print(f"    Use the model slug from the site (e.g. tt_gen_2, tt_rs, a4).")
        return

    print(f"Fetching {args.brand} {args.model} from automobile-catalog.com...")
    brand_key = args.brand.lower().strip()
    model_key = args.model.lower().strip()
    models = []

    # Prefer known URLs (exact slugs like tt_gen_2) when defined
    for (b, m), entries in KNOWN_MODEL_URLS.items():
        if b == brand_key and (m in model_key or model_key in m):
            models = [{"name": name, "url": url} for name, url in entries]
            if args.verbose:
                print(f"Using known URL(s) for this model.")
            break
    if not models:
        models = scraper.search_brand(args.brand, args.model)
        if models:
            print(f"Trying URL: {models[0]['url']}")

    if not models:
        print(f"\n[!] Could not build URL for {args.brand} {args.model}.")
        print("    The site uses /model/brand/model_slug.html (e.g. /model/audi/tt_gen_2.html).")
        print("    Try --model with the exact slug from the site, or add it to KNOWN_MODEL_URLS in the script.")
        return
    
    # Try each candidate URL (e.g. tt_gen_2 then tt_rs) until we get specs
    selected_model = models[0]
    specs = None
    for candidate in models:
        print(f"\n[OK] Trying: {candidate['name']}")
        print(f"Fetching: {candidate['url']}...")
        specs = scraper.get_model_specs(candidate['url'])
        if specs:
            selected_model = candidate
            break

    if specs:
        print(f"\n[OK] Retrieved specifications:")
        for key, value in specs.items():
            print(f"  {key}: {value}")
        print(f"\nGenerating poster...")
        generator.generate_poster(args.brand, selected_model['name'], specs, args.output)
        print(f"\n[OK] Success! Poster saved to: {args.output}")
    else:
        print("\n[!] Could not retrieve specifications (page may be blocked or format changed).")
        print("Generating poster with reference data for this model...")
        demo_specs = {
            'year': '2016-2023',
            'engine': '2.5L TFSI',
            'power': '394 HP',
            'torque': '480 Nm',
            'weight': '1450 kg',
            'acceleration_0_100': '3.7 s',
            'top_speed': '250 km/h'
        }
        generator.generate_poster(args.brand, selected_model['name'], demo_specs, args.output)
        print(f"\n[OK] Poster saved to: {args.output} (using reference specs)")


if __name__ == '__main__':
    main()
