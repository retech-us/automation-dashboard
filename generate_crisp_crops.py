import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs("assets/img/realogram_crops", exist_ok=True)

products = [
    {
        "filename": "crop_identify_1.jpg",
        "name": "BURT'S BEES",
        "sub": "POMEGRANATE",
        "desc": "Moisturizing Lip Balm",
        "accent": (185, 28, 28),     # Pomegranate ruby
        "cap": (153, 27, 27),
        "upc": "070561111018",
    },
    {
        "filename": "crop_identify_2.jpg",
        "name": "BURT'S BEES",
        "sub": "BEESWAX",
        "desc": "With Vitamin E & Peppermint",
        "accent": (217, 119, 6),     # Classic gold/red
        "cap": (245, 158, 11),
        "upc": "070561111025",
    },
    {
        "filename": "crop_identify_3.jpg",
        "name": "BURT'S BEES",
        "sub": "VANILLA BEAN",
        "desc": "All Natural Lip Balm",
        "accent": (180, 83, 9),      # Warm vanilla amber
        "cap": (254, 240, 138),
        "upc": "070561111032",
    },
    {
        "filename": "crop_identify_4.jpg",
        "name": "BURT'S BEES",
        "sub": "MANGO",
        "desc": "Nourishing Lip Balm",
        "accent": (234, 88, 12),     # Juicy mango orange
        "cap": (249, 115, 22),
        "upc": "070561111049",
    },
    {
        "filename": "crop_identify_5.jpg",
        "name": "BURT'S BEES",
        "sub": "HONEY",
        "desc": "With Honey Extract",
        "accent": (161, 98, 7),      # Golden honey
        "cap": (217, 119, 6),
        "upc": "070561111056",
    },
]

W, H = 480, 580

for p in products:
    im = Image.new("RGB", (W, H), (248, 250, 252))
    draw = ImageDraw.Draw(im)

    # Background card / blister pack
    card_margin = 24
    card_box = (card_margin, card_margin, W - card_margin, H - card_margin)
    draw.rounded_rectangle(card_box, radius=16, fill=(254, 252, 232), outline=(226, 232, 240), width=2)

    # Peg hole at top
    peg_cx, peg_cy = W // 2, card_margin + 28
    draw.ellipse((peg_cx - 24, peg_cy - 8, peg_cx + 24, peg_cy + 8), fill=(241, 245, 249), outline=(203, 213, 225), width=2)
    draw.ellipse((peg_cx - 10, peg_cy - 16, peg_cx + 10, peg_cy), fill=(241, 245, 249), outline=(203, 213, 225), width=2)

    # Brand header
    draw.text((W // 2, card_margin + 55), "BURT'S BEES®", fill=(78, 48, 26), anchor="mm", font_size=28)
    draw.text((W // 2, card_margin + 80), "100% NATURAL ORIGIN", fill=(146, 64, 14), anchor="mm", font_size=13)

    # Accent color banner
    banner_y1 = card_margin + 98
    banner_y2 = card_margin + 130
    draw.rectangle((card_margin + 8, banner_y1, W - card_margin - 8, banner_y2), fill=p["accent"])
    draw.text((W // 2, (banner_y1 + banner_y2) // 2), p["sub"], fill=(255, 255, 255), anchor="mm", font_size=18)

    # Lip balm tube rendering in center
    tube_w, tube_h = 130, 300
    tube_x = (W - tube_w) // 2
    tube_y = card_margin + 150

    # Tube cap (top 70px)
    cap_h = 75
    draw.rounded_rectangle((tube_x, tube_y, tube_x + tube_w, tube_y + cap_h), radius=10, fill=p["cap"], outline=(120, 53, 15), width=2)
    # Cap ridges
    for ry in range(tube_y + 12, tube_y + cap_h - 10, 8):
        draw.line((tube_x + 8, ry, tube_x + tube_w - 8, ry), fill=(255, 255, 255, 120), width=1)

    # Tube body
    body_y = tube_y + cap_h
    body_h = tube_h - cap_h
    draw.rounded_rectangle((tube_x, body_y, tube_x + tube_w, tube_y + tube_h), radius=8, fill=(254, 240, 138), outline=(120, 53, 15), width=2)

    # Tube label details
    draw.text((W // 2, body_y + 30), "BURT'S BEES", fill=(69, 26, 3), anchor="mm", font_size=16)
    draw.rectangle((tube_x + 10, body_y + 55, tube_x + tube_w - 10, body_y + 85), fill=p["accent"])
    draw.text((W // 2, body_y + 70), p["sub"], fill=(255, 255, 255), anchor="mm", font_size=13)
    draw.text((W // 2, body_y + 110), p["desc"], fill=(120, 53, 15), anchor="mm", font_size=11)
    draw.text((W // 2, body_y + 140), "NET WT. 0.15 oz / 4.25 g", fill=(146, 64, 14), anchor="mm", font_size=9)

    # Barcode & UPC at bottom of card
    bc_y = H - card_margin - 50
    draw.text((W // 2, bc_y - 12), f"UPC {p['upc']}", fill=(71, 85, 105), anchor="mm", font_size=11)
    # Barcode lines
    bc_left = W // 2 - 80
    for i in range(40):
        bx = bc_left + i * 4
        bw = 2 if (i % 3 == 0 or i % 5 == 0) else 1
        draw.line((bx, bc_y, bx, bc_y + 24), fill=(30, 41, 59), width=bw)

    # Save high quality
    out_path = os.path.join("assets/img/realogram_crops", p["filename"])
    im.save(out_path, "JPEG", quality=95)
    print(f"Saved {out_path} ({W}x{H})")
