# Product photography sources

Retrieved 4 November 2026. All photos are locally bundled JPEGs sourced from Unsplash. License: https://unsplash.com/license. Images illustrate the existing generic demo products; they are not claims about a specific branded SKU. No photographer or brand endorsement is implied.

The Unsplash license permits downloading and redistribution as part of an application. Do not resell the unmodified photos or compile a competing image service. Product trademarks remain with their owners.

| Stable ID | Product | Local file | Photographer | Source |
|---|---|---|---|---|
| p1 | Gaming Laptop | `p1.jpg` | Alienware | [Photo](https://unsplash.com/photos/kofhL_cfyR4) |
| p2 | Wireless Headphones | `p2.jpg` | Andrey Matveev | [Photo](https://unsplash.com/photos/OnUG2D_cWpg) |
| p3 | Mechanical Keyboard | `p3.jpg` | Hannes Köttner | [Photo](https://unsplash.com/photos/QpTZcTlk08g) |
| p4 | Smartphone | `p4.jpg` | 2H Media | [Photo](https://unsplash.com/photos/i8maBIp6yxg) |
| p5 | Running Shoes | `p5.jpg` | mostafa mahmoudi | [Photo](https://unsplash.com/photos/W_uDEmTq0po) |
| p6 | Gym Backpack | `p6.jpg` | Not recorded (original CDN source retained) | [Photo](https://images.unsplash.com/photo-1553062407-98eeb64c6a62) |
| p7 | Protein Shaker | `p7.jpg` | alexandr Kornienko | [Photo](https://unsplash.com/photos/iHqzvk7C3eM) |
| p8 | Dumbbell Set | `p8.jpg` | Greg Rosenke | [Photo](https://unsplash.com/photos/0zkJ1EsH9dY) |
| p9 | Desk Lamp | `p9.jpg` | swabdesign | [Photo](https://unsplash.com/photos/oh3vAmgBgkw) |
| p10 | Office Chair | `p10.jpg` | EFFYDESK | [Photo](https://unsplash.com/photos/7mfNpV5eJH0) |
| p11 | Coffee Maker | `p11.jpg` | Ronan Furuta | [Photo](https://unsplash.com/photos/AjcABUQ7WuA) |
| p12 | Travel Backpack | `p12.jpg` | Wiser by the Mile | [Photo](https://unsplash.com/photos/3o-X8WJOP5E) |

See `manifest.json` for exact source CDN URLs and IDs. The selected photographs were visually inspected; unsuitable initial candidates (including a mislabeled pizza bag and a kettle) were replaced before packaging. Some photos use studio or room settings rather than identical isolated backdrops. Cards provide consistent aspect ratio, pale surfaces and `object-fit: contain` without cutting off the object further.

The generic gym backpack is illustrated by a compact fabric backpack. The shaker is an unbranded shaker bottle. The photographs illustrate product types, not promised product specifications.

## Packaging without Docker changes

`python frontend/tools/bundle_images.py` reads this directory and the manifest, then regenerates only the marked `PRODUCT_IMAGES` block in `frontend/app.js`. The existing Dockerfile already copies `app.js`; therefore the photos work in the Docker image without a new COPY instruction or remote image requests. The separate JPEGs remain the editable source assets. This trades about 1.4 MB of script content for compatibility with the unchanged Docker configuration.

Both catalogue and recommendation cards call the same image renderer, keyed by stable backend product ID. A failed image is replaced by product-specific text, never an unrelated photo or permanent generic icon.
