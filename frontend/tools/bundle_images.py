"""Embed local product photographs without changing the existing Dockerfile.
Run from any directory. No dependencies beyond Python's standard library.
"""
import base64
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'assets/products/manifest.json').read_text())
images = {key: 'data:image/jpeg;base64,' + base64.b64encode((root / 'assets/products' / item['file']).read_bytes()).decode() for key, item in manifest.items()}
source = root / 'app.js'
text = source.read_text()
start, end = '/* PRODUCT_IMAGES_START */', '/* PRODUCT_IMAGES_END */'
before, rest = text.split(start, 1)
_, after = rest.split(end, 1)
source.write_text(before + start + '\nconst PRODUCT_IMAGES = Object.freeze(' + json.dumps(images, indent=2) + ');\n' + end + after)
print(f'Bundled {len(images)} local product photographs into app.js')
