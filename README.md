# Car Poster Generator

A Python script that automatically fetches car specifications from [automobile-catalog.com](https://www.automobile-catalog.com) and generates professional car posters in PNG or JPG format.

## Features

- 🔍 Automatic car model discovery for any brand
- 📊 Extracts key specifications (engine, power, torque, weight, acceleration, top speed)
- 🎨 Generates clean, professional posters matching the reference design
- 💾 Saves output as PNG or JPG
- 🌐 Web scraping with robust error handling

## Installation

1. Install Python 3.7 or higher

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

List available models for a brand:
```bash
python car_poster_generator.py Audi
```

Generate a poster for a specific model:
```bash
python car_poster_generator.py Audi --model "TT RS"
```

Specify output file:
```bash
python car_poster_generator.py BMW --model "M3" --output bmw_m3.jpg
```

### Command Line Arguments

- `brand` (required): Car brand name (e.g., Audi, BMW, Mercedes)
- `--model`: Specific model name (optional, lists available models if not provided)
- `--output`: Output file path (default: `car_poster.png`)
- `--verbose` or `-v`: Enable verbose output

## Examples

```bash
# Generate poster for Audi TT RS
python car_poster_generator.py Audi --model "TT RS"

# Generate poster for BMW M3 as JPG
python car_poster_generator.py BMW --model "M3" --output bmw_m3.jpg

# List all Mercedes models
python car_poster_generator.py Mercedes
```

## Output

The script generates a poster image with:
- Brand and model name at the top
- Key specifications at the bottom:
  - Year (production years)
  - Engine displacement
  - Power (HP)
  - Torque (Nm)
  - Weight (kg)
  - 0-100 km/h acceleration
  - Top speed

## Notes

- The scraper may need adjustments if the website structure changes
- Some models may not have complete specifications available
- Network connectivity is required to fetch data from automobile-catalog.com
- The script uses respectful scraping with delays and proper headers

## Troubleshooting

**No models found:**
- Verify the brand name spelling on automobile-catalog.com
- Check your internet connection
- The website structure may have changed

**Specifications not retrieved:**
- The model page format may be different
- Try a different model variant
- Check the URL manually in a browser

## Requirements

- Python 3.7+
- requests
- beautifulsoup4
- Pillow (PIL)
- lxml
- Selenium

## License

This script is provided as-is for educational and personal use.
