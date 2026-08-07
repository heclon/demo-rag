#!/usr/bin/env python3
"""
Generate data/products.json — the demo catalog.

Deliberately hand-authored rather than randomly generated: the review text is
written so that specific demo questions have *correct, checkable* answers.
For example, several reviews mention battery life, travel use, and specific
complaints, so the OpenSearch demo queries in docs/demo.md return meaningful
hits rather than noise.

Run:  python scripts/generate_seed_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "products.json"

# (title, brand, category, price, rating, inventory, description, specs, [(author, rating, review_title, body)])
CATALOG: list[tuple] = [
    # ---------------- Laptops ----------------
    ("ZenBook Air 14", "Asus", "Laptops", 1099.00, 4.6, 12,
     "Ultra-light 14-inch aluminium laptop built for people who work on the move. Fanless under light load and thin enough to disappear into a backpack.",
     {"screen": "14 inch OLED", "weight": "1.1 kg", "ram": "16 GB", "storage": "512 GB SSD", "battery": "67 Wh", "ports": "2x USB-C, 1x HDMI"},
     [("Marta R.", 5.0, "Perfect travel laptop", "I fly twice a month and this is the first laptop I stopped noticing in my bag. Battery life is genuinely all day — I got about eleven hours of writing and browsing on a transatlantic flight without charging."),
      ("Dev P.", 4.0, "Great screen, warm under load", "The OLED panel is gorgeous for photo work. It does get warm on the underside when I compile for a while, so it is not a lap machine when working hard."),
      ("Ingrid L.", 5.0, "Light enough to forget", "Weight is the whole story here. 1.1 kg means I carry it everywhere. Keyboard is shallow but comfortable enough for long sessions.")]),

    ("ProBook 15 Developer Edition", "Dell", "Laptops", 1449.00, 4.4, 7,
     "Fifteen-inch developer workstation with a 45W processor, 32 GB of memory and Linux preinstalled. Built for compiling, containers, and running local databases.",
     {"screen": "15.6 inch IPS", "weight": "1.8 kg", "ram": "32 GB", "storage": "1 TB SSD", "battery": "86 Wh", "os": "Ubuntu LTS"},
     [("Sam K.", 5.0, "Compiles fast, Linux just works", "Every piece of hardware worked on Ubuntu out of the box, which is rare. Docker builds that took four minutes on my old machine take ninety seconds."),
      ("Rae M.", 4.0, "Heavy but worth it", "It is not a travel machine at 1.8 kg and the battery drains quickly under a full build. As a desk machine it is excellent."),
      ("Tom V.", 4.0, "Fans are loud", "My only real complaint is fan noise under sustained load. In a quiet room it is very noticeable.")]),

    ("MacBook Air M3 13", "Apple", "Laptops", 1199.00, 4.8, 20,
     "Silent, fanless 13-inch laptop with exceptional battery life and a high-quality display. The default choice for general-purpose work.",
     {"screen": "13.6 inch Liquid Retina", "weight": "1.24 kg", "ram": "16 GB", "storage": "512 GB SSD", "battery": "52.6 Wh", "chip": "M3"},
     [("Priya N.", 5.0, "Battery life is unreal", "Two full working days between charges. I stopped carrying the charger to the office entirely."),
      ("Owen B.", 5.0, "Completely silent", "No fan means no noise, ever. After years of whining laptop fans this alone was worth the upgrade."),
      ("Lila F.", 4.0, "Only two ports", "Wonderful machine, but two USB-C ports and nothing else means living with a dongle.")]),

    ("Nitro Gaming 16", "Acer", "Laptops", 1699.00, 4.2, 5,
     "Sixteen-inch gaming laptop with a discrete GPU and a 165 Hz display. Also capable as a machine-learning workstation for local model experimentation.",
     {"screen": "16 inch 165Hz", "weight": "2.6 kg", "ram": "32 GB", "storage": "1 TB SSD", "gpu": "RTX 4070", "battery": "90 Wh"},
     [("Kenji A.", 4.0, "Fast, but plan for the charger", "Performance is excellent and it trains small models locally without complaint. Battery life away from power is under two hours, so treat it as a portable desktop."),
      ("Nina S.", 4.0, "Loud fans, great value", "The fans are aggressive. Ear defenders or headphones are basically mandatory during long sessions.")]),

    ("Chromebook Go 12", "HP", "Laptops", 329.00, 4.0, 34,
     "Budget twelve-inch laptop for browsing, documents, and video calls. Rugged plastic shell designed for students.",
     {"screen": "12 inch", "weight": "1.05 kg", "ram": "8 GB", "storage": "128 GB eMMC", "battery": "47 Wh"},
     [("Hugo T.", 4.0, "Does what it says", "Cheap, light, and the battery lasts the whole school day. Do not expect it to handle anything heavy."),
      ("Beth C.", 3.5, "Screen is dim", "Works fine indoors but the display is too dim to use outside or near a bright window.")]),

    ("Studio Laptop 17", "Lenovo", "Laptops", 2199.00, 4.5, 3,
     "Seventeen-inch colour-accurate laptop for video editors and designers, with a factory-calibrated display and a full-size card reader.",
     {"screen": "17 inch 4K", "weight": "2.4 kg", "ram": "64 GB", "storage": "2 TB SSD", "colour": "100% DCI-P3"},
     [("Sofia D.", 5.0, "Colour accuracy out of the box", "I checked it against my calibrated monitor and the difference was negligible. Saves me a step on every job."),
      ("Marc J.", 4.0, "Enormous", "It is a desk machine that happens to fold. Do not buy this expecting to use it on a train.")]),

    # ---------------- Keyboards ----------------
    ("ErgoSplit Pro Mechanical", "Kinesis", "Keyboards", 289.00, 4.7, 9,
     "Split ergonomic mechanical keyboard with tenting and a concave key well, designed to reduce wrist strain during long typing sessions. Popular with programmers who type all day.",
     {"switch_type": "tactile brown", "layout": "split ergonomic", "connection": "USB-C wired", "keycaps": "PBT", "programmable": "yes, on-board layers"},
     [("Alex W.", 5.0, "Fixed my wrist pain", "Six months of RSI and two weeks with this keyboard and the pain is gone. The split and tenting mean my forearms stay straight all day."),
      ("Jo H.", 4.0, "Steep learning curve", "Took me a solid three weeks to get back to full typing speed. Worth it, but budget for the adjustment period."),
      ("Cam O.", 5.0, "Programmable layers are the point", "Being able to put symbols on a layer under my home row changed how I write code. No more reaching for brackets.")]),

    ("TypeMaster 87 TKL", "Keychron", "Keyboards", 99.00, 4.5, 41,
     "Tenkeyless mechanical keyboard with hot-swappable switches and wireless connectivity. A comfortable, affordable entry into mechanical keyboards for developers.",
     {"switch_type": "linear red, hot-swappable", "layout": "87-key TKL", "connection": "Bluetooth and USB-C", "keycaps": "PBT double-shot", "battery": "4000 mAh"},
     [("Dana E.", 5.0, "Best value for programmers", "Hot-swap sockets mean I could try three switch types without buying three keyboards. Comfortable for eight-hour days."),
      ("Ravi S.", 4.0, "Bluetooth drops occasionally", "Great keyboard wired. Over Bluetooth it disconnects maybe once a week and needs re-pairing."),
      ("Ellie G.", 5.0, "Quiet enough for the office", "With the linear switches and the included dampeners nobody around me complains.")]),

    ("Compact 60 Wireless", "Logitech", "Keyboards", 79.00, 4.3, 28,
     "Sixty-percent wireless keyboard that saves desk space and travels well. Low-profile scissor switches keep the height down.",
     {"switch_type": "low-profile scissor", "layout": "60%", "connection": "Bluetooth", "battery": "10 days", "weight": "420 g"},
     [("Yuki M.", 4.0, "Great for travel", "Fits in the laptop sleeve pocket. I take it on every trip so I am not stuck on a laptop keyboard."),
      ("Peter L.", 3.5, "Miss the arrow keys", "The 60% layout means arrows live on a function layer. Fine for typing, frustrating for spreadsheets.")]),

    ("SilentTouch Office", "Microsoft", "Keyboards", 59.00, 4.1, 52,
     "Quiet membrane keyboard with a padded wrist rest, intended for shared offices where noise matters.",
     {"switch_type": "membrane", "layout": "full-size", "connection": "USB-A wired", "wrist_rest": "integrated foam"},
     [("Grace P.", 4.0, "Genuinely silent", "You can type through a meeting on video and nobody hears it."),
      ("Ian R.", 4.0, "Wrist rest is the best part", "The keyboard is unremarkable. The wrist rest is unexpectedly good and I would miss it now.")]),

    ("Mech Pro Programmer 75", "Ducky", "Keyboards", 149.00, 4.6, 16,
     "Seventy-five-percent mechanical keyboard balancing a compact footprint with dedicated arrow keys and a function row. Built for developers who want ergonomics without a split layout.",
     {"switch_type": "tactile clear", "layout": "75%", "connection": "USB-C wired", "keycaps": "PBT", "programmable": "QMK compatible"},
     [("Nadia K.", 5.0, "The right compromise", "Arrow keys and a function row in a compact body. This is the layout I wish every keyboard used."),
      ("Felix B.", 4.5, "Build quality is superb", "Zero flex, tight tolerances. It feels like it will outlast the computer it is plugged into.")]),

    # ---------------- Headphones ----------------
    ("WH-1000 Noise Cancelling", "Sony", "Headphones", 349.00, 4.7, 18,
     "Over-ear active noise cancelling headphones tuned for long flights and open-plan offices. Thirty-hour battery and a folding travel case.",
     {"type": "over-ear closed", "anc": "adaptive", "battery": "30 hours", "weight": "250 g", "codecs": "LDAC, AAC, SBC"},
     [("Claire V.", 5.0, "Made long flights bearable", "The noise cancelling removes engine drone completely. I arrived off a nine-hour flight actually rested for once."),
      ("Diego F.", 5.0, "Battery life is excellent", "I charge them roughly once a week with daily commuting use. Thirty hours is not a marketing number."),
      ("Anya T.", 4.0, "Warm ears after a few hours", "Superb sound and isolation, but the earcups get hot after about three hours of continuous wear.")]),

    ("QuietComfort Ultra", "Bose", "Headphones", 429.00, 4.6, 11,
     "Premium comfort-focused noise cancelling headphones with a lightweight clamp designed for all-day wear.",
     {"type": "over-ear closed", "anc": "adaptive", "battery": "24 hours", "weight": "254 g", "comfort": "plush memory foam"},
     [("Robin H.", 5.0, "The most comfortable I have owned", "I wear them for six hours straight without noticing. Nothing else I have tried comes close on comfort."),
      ("Mei L.", 4.0, "Battery is the weak point", "Fantastic in every way except battery — 24 hours is fine, but competitors do 30 and I notice on long trips.")]),

    ("Studio Monitor Reference 80", "Sennheiser", "Headphones", 279.00, 4.8, 6,
     "Open-back reference headphones for mixing and critical listening. Flat frequency response with a wide soundstage.",
     {"type": "open-back", "impedance": "80 ohm", "frequency": "10 Hz - 41 kHz", "weight": "260 g", "cable": "detachable 3m"},
     [("Ola N.", 5.0, "Honest sound", "They tell you the truth about your mix, which is not always flattering but is the entire point."),
      ("Sanjay R.", 4.0, "Zero isolation, by design", "Open-back means everyone hears your music and you hear the room. Studio use only — useless on a train.")]),

    ("SportBuds Active", "Jabra", "Headphones", 129.00, 4.2, 44,
     "Sweat-resistant wireless earbuds with a secure fit for running and gym use. Compact charging case.",
     {"type": "in-ear true wireless", "water_resistance": "IP57", "battery": "8 hours + 24 in case", "weight": "5.5 g each"},
     [("Tess A.", 4.0, "They stay put", "Ran a half marathon in the rain and neither bud shifted. That is all I ask for."),
      ("Luca M.", 4.0, "Battery life could be better", "Eight hours per charge is fine for workouts but I would not fly with them as my only pair."),
      ("Ben Q.", 3.5, "Muddy bass", "The fit and durability are great. The sound quality is clearly a step below wired options at this price.")]),

    ("AirPods Pro 3", "Apple", "Headphones", 249.00, 4.5, 30,
     "Compact noise cancelling earbuds with transparency mode and seamless switching between devices.",
     {"type": "in-ear true wireless", "anc": "active", "battery": "6 hours + 24 in case", "features": "transparency mode, spatial audio"},
     [("Jess W.", 5.0, "Switching between devices is seamless", "They follow me from laptop to phone without a thought. That convenience is why I keep buying them."),
      ("Karl D.", 4.0, "Great for travel, short battery", "Small enough for any pocket which makes them the travel default, but six hours means charging mid-flight.")]),

    # ---------------- Monitors ----------------
    ("UltraWide 34 Curved", "LG", "Monitors", 799.00, 4.5, 8,
     "Thirty-four-inch curved ultrawide monitor that replaces a dual-monitor setup. USB-C with 90W power delivery drives a laptop over a single cable.",
     {"size": "34 inch", "resolution": "3440x1440", "refresh": "100 Hz", "panel": "IPS", "usb_c_power": "90 W"},
     [("Ana P.", 5.0, "One cable to the laptop", "USB-C carries video, data and charging. My desk went from four cables to one."),
      ("Greg S.", 4.0, "Curve takes adjusting", "Took about a week before the curve felt natural. Now going back to flat feels wrong.")]),

    ("ProArt 27 4K", "Asus", "Monitors", 649.00, 4.7, 14,
     "Twenty-seven-inch 4K monitor with factory colour calibration for photo and video editing. Includes a shading hood.",
     {"size": "27 inch", "resolution": "3840x2160", "panel": "IPS", "colour": "100% sRGB, 98% DCI-P3", "calibration": "factory report included"},
     [("Ida F.", 5.0, "Calibration report is a nice touch", "Arrived with a printed calibration report and it matched my own measurements. Trustworthy out of the box."),
      ("Noel B.", 4.5, "Sharp and colour accurate", "4K at 27 inches is the sweet spot for detail work without scaling headaches.")]),

    ("GameSync 27 240Hz", "Samsung", "Monitors", 549.00, 4.4, 19,
     "Fast 240 Hz gaming monitor with a 1 ms response time and adaptive sync.",
     {"size": "27 inch", "resolution": "2560x1440", "refresh": "240 Hz", "panel": "VA", "response": "1 ms"},
     [("Vik T.", 5.0, "Buttery smooth", "The jump from 144 to 240 Hz is smaller than 60 to 144, but it is there."),
      ("Mona C.", 4.0, "VA black smearing", "Great motion clarity overall, but dark scenes show some smearing typical of VA panels.")]),

    ("Portable Screen 15", "Lenovo", "Monitors", 249.00, 4.1, 25,
     "Fifteen-inch USB-C portable monitor for working away from a desk. Fold-out cover doubles as a stand.",
     {"size": "15.6 inch", "resolution": "1920x1080", "panel": "IPS", "weight": "780 g", "connection": "USB-C"},
     [("Ruth E.", 4.0, "Great for hotel desks", "I travel for consulting work and a second screen in the hotel room makes a real difference. Light enough to justify the bag space."),
      ("Sean M.", 4.0, "Needs a powered port", "Works off one USB-C cable on my laptop, but on lower-power tablets it needs its own power supply.")]),

    ("Vertical Stack 24", "Dell", "Monitors", 329.00, 4.3, 22,
     "Twenty-four-inch monitor that pivots to portrait orientation, popular with developers for reading long files and logs.",
     {"size": "24 inch", "resolution": "1920x1200", "panel": "IPS", "pivot": "90 degree portrait", "aspect": "16:10"},
     [("Tariq H.", 5.0, "Portrait mode for code", "Rotated to portrait it shows about a hundred lines of code at once. I do not want to go back."),
      ("Lena K.", 4.0, "16:10 is underrated", "The extra vertical pixels over 16:9 are genuinely useful every single day.")]),

    # ---------------- Mice ----------------
    ("MX Precision 3S", "Logitech", "Mice", 99.00, 4.7, 37,
     "Ergonomic wireless mouse with a silent scroll wheel and a sculpted shape for all-day desk use. Multi-device switching.",
     {"shape": "ergonomic right-handed", "dpi": "8000", "connection": "Bluetooth and USB dongle", "battery": "70 days", "buttons": "7 programmable"},
     [("Omar Z.", 5.0, "The comfort standard", "Eight hours a day for two years and my hand has never ached. The shape is just right."),
      ("Fran D.", 5.0, "Battery lasts forever", "I charge it about every two months. It is easy to forget it has a battery at all."),
      ("Nils A.", 4.0, "Too big for small hands", "Superb mouse but genuinely large. My partner finds it uncomfortable.")]),

    ("Vertical Ergo Mouse", "Anker", "Mice", 39.00, 4.2, 48,
     "Vertical mouse that holds the wrist in a neutral handshake position to reduce forearm strain.",
     {"shape": "vertical 57 degree", "dpi": "1600", "connection": "2.4 GHz dongle", "battery": "AA, 6 months"},
     [("Cara J.", 5.0, "Wrist pain gone in a week", "I was skeptical about the shape but my wrist stopped hurting almost immediately."),
      ("Hank W.", 3.5, "Cheap plastic feel", "It does the ergonomic job well. The build quality is clearly budget.")]),

    ("Pro Gaming Mouse 8K", "Razer", "Mice", 149.00, 4.5, 13,
     "Lightweight competitive gaming mouse with an 8000 Hz polling rate and optical switches.",
     {"shape": "ambidextrous", "dpi": "30000", "polling": "8000 Hz", "weight": "58 g", "switches": "optical"},
     [("Zed P.", 5.0, "Featherweight", "58 grams changes how you aim. Going back to a heavier mouse feels like dragging a brick."),
      ("Iris N.", 4.0, "Cable is stiff", "Wireless is flawless. The included charging cable is unusually stiff for wired play.")]),

    ("Travel Mouse Mini", "Microsoft", "Mice", 29.00, 4.0, 60,
     "Pocket-sized Bluetooth mouse for laptop bags. Flat profile with a magnetic cover.",
     {"shape": "compact flat", "dpi": "1000", "connection": "Bluetooth", "weight": "62 g", "battery": "AAA, 4 months"},
     [("Ravi T.", 4.0, "Perfect for travel", "Fits in a jacket pocket and beats a trackpad on a hotel desk. Not for long sessions."),
      ("Dot F.", 3.5, "Too flat for daily use", "Fine as a travel backup. My hand cramps if I use it for more than an hour.")]),

    # ---------------- Chairs ----------------
    ("ErgoTask Mesh Pro", "Herman Miller", "Chairs", 1395.00, 4.8, 4,
     "Fully adjustable mesh task chair with lumbar support and a twelve-year warranty. Designed for eight-plus hours of seated work.",
     {"material": "mesh back, foam seat", "adjustments": "seat height, depth, arm 4D, lumbar, tilt tension", "warranty": "12 years", "weight_capacity": "159 kg"},
     [("Paula G.", 5.0, "Worth every cent", "I spent a year with back pain from a cheap chair. Three weeks in this one and it was gone. The lumbar adjustment is the difference."),
      ("Sten O.", 5.0, "Adjustable in every direction", "Took twenty minutes to dial in and now it fits me exactly. Nothing else has this range."),
      ("Ivy R.", 4.0, "Expensive", "It is a genuinely excellent chair and it costs as much as a laptop. Know what you are buying.")]),

    ("BudgetErgo Mesh", "IKEA", "Chairs", 199.00, 3.9, 31,
     "Affordable mesh office chair with height and tilt adjustment. Sensible choice for occasional home-office use.",
     {"material": "mesh back", "adjustments": "seat height, tilt lock", "warranty": "3 years", "weight_capacity": "110 kg"},
     [("Nate B.", 4.0, "Good for the price", "For two hundred it is fine. The armrests do not adjust and the lumbar support is fixed."),
      ("Suki H.", 3.5, "Not for full days", "Comfortable for a couple of hours. By hour six I am shifting around constantly.")]),

    ("Standing Desk Chair Perch", "Varier", "Chairs", 449.00, 4.3, 9,
     "Perch-style leaning stool for use with a standing desk, encouraging an active posture between sitting and standing.",
     {"material": "padded seat", "height_range": "60-85 cm", "tilt": "forward perch", "weight": "7 kg"},
     [("Elin K.", 4.0, "Good middle ground", "Lets me take weight off my legs at a standing desk without properly sitting down. Not a replacement for a real chair."),
      ("Gus L.", 4.5, "Core workout by accident", "You engage your core to stay balanced. My posture improved noticeably over a month.")]),

    ("Executive Leather Recline", "Steelcase", "Chairs", 899.00, 4.4, 6,
     "High-back leather executive chair with a deep recline and padded armrests.",
     {"material": "top-grain leather", "adjustments": "height, recline, arm height", "warranty": "10 years", "weight_capacity": "136 kg"},
     [("Vera M.", 4.0, "Comfortable, runs hot", "Very comfortable and looks the part in video calls. Leather gets warm in summer in a way mesh does not."),
      ("Ted S.", 5.0, "Built like furniture", "Feels solid and heavy in a reassuring way. Ten-year warranty says a lot.")]),

    # ---------------- Cameras ----------------
    ("Alpha 7 Compact Mirrorless", "Sony", "Cameras", 1799.00, 4.7, 5,
     "Full-frame mirrorless camera in a compact body, with in-body stabilisation and excellent low-light performance. A strong choice for travel photography.",
     {"sensor": "full-frame 33 MP", "stabilisation": "5-axis IBIS", "video": "4K 60fps", "weight": "650 g body", "battery": "610 shots"},
     [("Hana O.", 5.0, "My travel camera now", "Full-frame quality at a weight I will actually carry on a hike. The stabilisation lets me shoot handheld at absurdly slow shutter speeds."),
      ("Ali R.", 4.0, "Menus are a maze", "Image quality is superb. The menu system takes weeks to learn and I still hunt for settings."),
      ("Jonas E.", 5.0, "Low light is the headline", "Usable images at ISO 12800. Changed what I can shoot indoors without a flash.")]),

    ("PocketVlog 4K", "DJI", "Cameras", 349.00, 4.4, 27,
     "Tiny gimbal-stabilised camera for vlogging and travel, small enough for a jacket pocket.",
     {"sensor": "1/1.7 inch", "stabilisation": "3-axis mechanical gimbal", "video": "4K 60fps", "weight": "117 g", "battery": "140 minutes"},
     [("Kim L.", 5.0, "Unbelievably small", "It is the size of a highlighter and the footage is smoother than my phone with software stabilisation."),
      ("Rex A.", 4.0, "Battery life is short", "About two hours of recording. Fine for a day out if you carry the case, tight for a full travel day."),
      ("Nour S.", 4.0, "Great for travel, poor in low light", "Daylight footage is excellent. Indoors and at dusk the small sensor shows.")]),

    ("Action Cam Rugged 12", "GoPro", "Cameras", 399.00, 4.5, 23,
     "Waterproof action camera with strong stabilisation, designed for cycling, diving and skiing.",
     {"sensor": "1/1.9 inch", "waterproof": "10 m without housing", "video": "5.3K 60fps", "weight": "154 g", "battery": "90 minutes"},
     [("Bo H.", 5.0, "Survives everything", "Two seasons of mountain biking, one crash into a river, still working."),
      ("Lise T.", 4.0, "Battery in the cold", "In winter the battery drops from ninety minutes to about thirty. Carry spares.")]),

    ("Webcam Studio 4K", "Logitech", "Cameras", 199.00, 4.3, 35,
     "Fixed 4K webcam with autofocus and light correction for video calls and streaming.",
     {"resolution": "4K 30fps", "field_of_view": "90 degrees adjustable", "focus": "autofocus", "features": "HDR light correction"},
     [("Ash P.", 4.0, "Big upgrade over a laptop camera", "The light correction handles my backlit window without making me a silhouette."),
      ("Rina G.", 4.0, "Autofocus hunts", "Sharp once settled, but it hunts for focus if I move around while talking.")]),

    ("Instant Print Retro", "Fujifilm", "Cameras", 89.00, 4.1, 55,
     "Instant film camera producing credit-card-sized prints. Simple point-and-shoot operation.",
     {"film": "instant mini", "flash": "automatic", "weight": "293 g", "focus": "fixed 60 cm to infinity"},
     [("Mia C.", 4.0, "Fun, film is pricey", "A joy at parties. Remember that each print costs roughly a euro."),
      ("Leo B.", 4.0, "Great gift", "Bought it for a friend's birthday and it was the hit of the evening.")]),

    # ---------------- Accessories (rounds the catalog to 50) ----------------
    ("USB-C Dock 12-in-1", "Anker", "Accessories", 179.00, 4.4, 26,
     "Twelve-port USB-C docking station driving dual monitors, gigabit ethernet and 100W laptop charging from one cable.",
     {"ports": "2x HDMI, 1x DP, 4x USB-A, 2x USB-C, ethernet, SD, microSD", "power_delivery": "100 W", "monitors": "dual 4K 60Hz"},
     [("Jan V.", 5.0, "Cleaned up my desk", "One cable to the laptop, everything else lives on the dock. Exactly what I wanted."),
      ("Ola F.", 4.0, "Runs warm", "Works flawlessly but the aluminium body gets hot enough to notice when driving two monitors.")]),

    ("Laptop Stand Aluminium", "Rain Design", "Accessories", 69.00, 4.6, 42,
     "Solid aluminium laptop stand that raises the screen to eye level to improve neck posture.",
     {"material": "single-piece aluminium", "height": "15 cm", "compatibility": "11-17 inch laptops", "weight": "1.1 kg"},
     [("Kate M.", 5.0, "Neck pain gone", "Raising the screen to eye level fixed a persistent neck ache within a fortnight."),
      ("Sam T.", 4.0, "Heavy, in a good way", "Too heavy to travel with, completely stable on a desk.")]),

    ("Blue Light Desk Lamp", "BenQ", "Accessories", 209.00, 4.5, 17,
     "Monitor-mounted light bar that illuminates the desk without reflecting off the screen. Auto-dimming to ambient light.",
     {"mount": "monitor clip", "colour_temperature": "2700-6500 K", "auto_dim": "ambient sensor", "power": "USB-C"},
     [("Wren D.", 5.0, "No screen glare", "It lights the desk and not the display, which is the entire trick. Late-night work is far less tiring."),
      ("Otto K.", 4.0, "Expensive for a lamp", "It works beautifully. It is still two hundred for a lamp.")]),

    ("Noise Isolating Earplugs", "Loop", "Accessories", 34.00, 4.2, 70,
     "Reusable filtered earplugs that reduce volume evenly without muffling speech. Popular in open-plan offices.",
     {"reduction": "20 dB", "material": "silicone tips", "sizes": "4 included", "case": "compact carry case"},
     [("Ines A.", 4.0, "Focus in an open office", "Takes the edge off the room without making me feel cut off. Cheaper than headphones and no battery."),
      ("Piet R.", 4.0, "Fit takes trial and error", "The largest tips were the only ones that stayed in for me. Glad they include four sizes.")]),

    ("Cable Management Kit", "Belkin", "Accessories", 24.00, 4.0, 88,
     "Adhesive clips, sleeves and ties for tidying cables under a desk.",
     {"contents": "12 clips, 2 sleeves, 20 ties", "adhesive": "3M backing", "sleeve_length": "1.5 m"},
     [("Fay L.", 4.0, "Cheap and effective", "Nothing clever about it, but my desk went from a nest to tidy in half an hour."),
      ("Dan W.", 3.5, "Adhesive fails on textured surfaces", "Stuck fine to my smooth desk, fell straight off the textured underside.")]),

    ("Portable SSD 2TB", "Samsung", "Accessories", 189.00, 4.7, 21,
     "Pocket-sized 2 TB external SSD with hardware encryption, for editing video directly off the drive while travelling.",
     {"capacity": "2 TB", "speed": "1050 MB/s read", "interface": "USB-C 3.2", "encryption": "AES-256 hardware", "weight": "58 g"},
     [("Rhea P.", 5.0, "Edit straight off the drive", "Fast enough to cut 4K footage directly from it. Saves copying to the laptop on location."),
      ("Milo J.", 5.0, "Tiny and rugged", "Smaller than a credit card, survives being loose in a camera bag.")]),

    ("Mechanical Keyboard Wrist Rest", "Glorious", "Accessories", 29.00, 4.3, 46,
     "Padded wrist rest sized for tenkeyless mechanical keyboards, to keep wrists level while typing.",
     {"size": "TKL 35 cm", "material": "memory foam, vegan leather", "base": "non-slip rubber"},
     [("Ada N.", 4.0, "Comfortable, needs cleaning", "Noticeably better wrist angle. The surface shows marks and needs wiping down weekly."),
      ("Bram S.", 4.5, "Right height for a TKL", "Matches the keyboard height exactly, which is the whole point.")]),

    ("Webcam Privacy Shutter 3-pack", "Targus", "Accessories", 12.00, 4.1, 95,
     "Slim adhesive sliding covers for laptop and monitor webcams.",
     {"thickness": "0.7 mm", "quantity": "3", "compatibility": "laptops, tablets, monitors"},
     [("Ric T.", 4.0, "Thin enough to close the lid", "At 0.7 mm the laptop still shuts properly, which is not true of thicker covers.")]),

    ("Travel Router AX", "GL.iNet", "Accessories", 89.00, 4.4, 18,
     "Pocket travel router creating a private encrypted network from hotel or cafe wifi, with a built-in VPN client.",
     {"wifi": "Wi-Fi 6 AX1800", "vpn": "WireGuard and OpenVPN client", "weight": "125 g", "power": "USB-C"},
     [("Nell H.", 5.0, "Essential for travel", "I no longer put my laptop directly on hotel wifi. Sets up in two minutes and everything routes through my VPN."),
      ("Omar B.", 4.0, "Fiddly first setup", "Once configured it is flawless. The first configuration took me an evening of reading docs.")]),

    ("Bluetooth Speaker Rugged", "JBL", "Accessories", 129.00, 4.5, 33,
     "Waterproof portable Bluetooth speaker with a twenty-hour battery, built for beaches and campsites.",
     {"battery": "20 hours", "water_resistance": "IP67", "weight": "680 g", "connection": "Bluetooth 5.3"},
     [("Zoe K.", 5.0, "Battery lasts a whole weekend", "Took it camping for three days on one charge with music most of the time."),
      ("Finn D.", 4.0, "Bass is boomy", "Loud and durable. The bass is exaggerated in a way that gets tiring indoors.")]),

    ("Monitor Arm Dual", "Ergotron", "Accessories", 249.00, 4.6, 15,
     "Gas-spring dual monitor arm that frees desk space and allows fine height and depth positioning.",
     {"monitors": "2 up to 27 inch", "weight_capacity": "9 kg per arm", "mount": "clamp or grommet", "movement": "gas spring"},
     [("Iva C.", 5.0, "Reclaimed my desk", "Both monitors float and the space underneath is usable again. Adjustment is effortless."),
      ("Karl P.", 4.5, "Solid, heavy clamp", "Feels industrial. Check your desk thickness before ordering.")]),

    ("Desk Mat XL Felt", "Orbitkey", "Accessories", 59.00, 4.2, 39,
     "Large felt and cork desk mat that defines a work area and quietens keyboard and mouse noise.",
     {"size": "80 x 40 cm", "material": "felt top, cork base", "thickness": "3 mm"},
     [("Hedy F.", 4.0, "Quieter typing", "Absorbs a surprising amount of keyboard noise. Looks smart too."),
      ("Yann M.", 4.0, "Felt attracts crumbs", "Works well, but felt holds dust and crumbs more than a hard surface.")]),

    ("Powerbank 20000 PD", "Anker", "Accessories", 79.00, 4.6, 29,
     "Twenty-thousand milliamp-hour power bank with 100W USB-C output, capable of charging a laptop on the move.",
     {"capacity": "20000 mAh", "output": "100 W USB-C", "ports": "2x USB-C, 1x USB-A", "weight": "460 g", "airline_safe": "yes, under 100 Wh"},
     [("Cleo R.", 5.0, "Charges my laptop on a train", "100W means it actually charges the laptop rather than slowing the drain. Battery life anxiety solved for travel."),
      ("Ned A.", 4.0, "Heavy in a day bag", "460 grams is noticeable. Worth it on travel days, left at home otherwise.")]),

    ("Screen Cleaning Kit", "Whoosh", "Accessories", 19.00, 4.0, 77,
     "Streak-free screen cleaning spray with two microfibre cloths, safe for coated displays.",
     {"volume": "100 ml", "cloths": "2 microfibre", "safe_for": "OLED, matte and glossy coatings"},
     [("Uma S.", 4.0, "No streaks", "Actually leaves no streaks on a matte laptop screen, unlike everything else I have tried.")]),

    ("Laptop Sleeve 14 Recycled", "Bellroy", "Accessories", 65.00, 4.4, 36,
     "Slim padded laptop sleeve made from recycled fabric, with a front pocket for a charger.",
     {"fits": "14 inch laptops", "material": "recycled woven fabric", "pocket": "front zip", "weight": "180 g"},
     [("Vic L.", 4.0, "Slim and protective", "Adds almost no bulk to the bag but the padding is real. Good for travel."),
      ("Tam O.", 5.0, "Charger pocket is the winner", "The front pocket fits a laptop charger and a mouse, which is exactly what I needed.")]),

    ("USB Microphone Podcast", "Rode", "Accessories", 169.00, 4.7, 20,
     "Cardioid USB condenser microphone for podcasting and video calls, with a built-in headphone monitor.",
     {"pattern": "cardioid", "connection": "USB-C", "monitoring": "3.5 mm zero-latency", "sample_rate": "48 kHz"},
     [("Mo T.", 5.0, "Transformed my call audio", "People stopped asking me to repeat things. Plug and play on both my machines."),
      ("Ruth B.", 4.0, "Picks up desk bumps", "Excellent sound but it transmits every knock on the desk. Get a shock mount.")]),

    ("Wireless Charging Pad Trio", "Belkin", "Accessories", 99.00, 4.2, 24,
     "Three-device wireless charging pad for phone, earbuds and watch on a single desk footprint.",
     {"devices": "3 simultaneous", "output": "15 W phone, 5 W watch", "standard": "Qi2"},
     [("Sol V.", 4.0, "Tidy bedside solution", "Everything charges in one place. Watch and earbuds placement is a bit fussy until you learn it.")]),

    ("Ergonomic Footrest Adjustable", "Fellowes", "Accessories", 49.00, 4.3, 32,
     "Height and angle adjustable footrest that improves seated posture for shorter users at fixed-height desks.",
     {"height_range": "9-16 cm", "tilt": "0-30 degrees", "surface": "textured non-slip"},
     [("Pia N.", 5.0, "Fixed my dangling feet", "At a fixed-height desk my feet never reached the floor properly. This solved lower back ache I had blamed on my chair.")]),

    ("Smart Plug Energy Monitor", "TP-Link", "Accessories", 22.00, 4.1, 64,
     "Wifi smart plug with energy monitoring, useful for measuring what a desk setup actually costs to run.",
     {"max_load": "16 A", "monitoring": "real-time watts and kWh", "connection": "2.4 GHz wifi"},
     [("Gil H.", 4.0, "Surprising numbers", "Measured my monitor and dock at idle and was surprised enough to start switching them off.")]),
]


def build() -> list[dict]:
    products = []
    for (title, brand, category, price, rating, inventory, description, specs, reviews) in CATALOG:
        products.append(
            {
                "title": title,
                "brand": brand,
                "category": category,
                "price": price,
                "rating": rating,
                "inventory": inventory,
                "description": description,
                "specifications": {k: str(v) for k, v in specs.items()},
                "reviews": [
                    {"author": a, "rating": r, "title": t, "body": b} for (a, r, t, b) in reviews
                ],
            }
        )
    return products


if __name__ == "__main__":
    products = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
    review_count = sum(len(p["reviews"]) for p in products)
    print(f"Wrote {len(products)} products and {review_count} reviews to {OUT}")
