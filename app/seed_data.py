"""Demo marketplace content for ``flask seed``.

Data only — no database access, no logic. ``cli.py`` walks these tables and
writes them through the ordinary services, so aggregates like
``rating_avg`` and ``used_count`` come out of the same code paths a real
write uses.

Everything here is invented. The people, addresses and phone numbers are
not real, and no real business is named. The goods, prices and
neighbourhoods are plausible for a Lebanese marketplace because a demo
that reads as filler is a demo nobody trusts.

Prices are USD, which is what CedarLink charges in; the LBP figures on
screen are converted for display.
"""

# Categories, in the three interface languages (C.5).
CATEGORY_SPECS = (
    ("Food", "طعام", "Alimentation"),
    ("Clothes", "ملابس", "Vêtements"),
    ("Electronics", "إلكترونيات", "Électronique"),
    ("Books", "كتب", "Livres"),
    ("Beauty", "تجميل", "Beauté"),
    ("Home", "منزل", "Maison"),
)


def p(name_en, name_ar, name_fr, desc_en, desc_ar, desc_fr,
      price, stock, category):
    """One product spec, trilingual. Keyed by its English name elsewhere."""
    return {
        "name": {"en": name_en, "ar": name_ar, "fr": name_fr},
        "description": {"en": desc_en, "ar": desc_ar, "fr": desc_fr},
        "price": price,
        "stock": stock,
        "category": category,
    }


# Weekly schedules. Monday = 0. A day may appear twice for a split shift;
# closes_at at or before opens_at means the interval crosses midnight.
def _week(opens, closes, skip=()):
    return [
        {"day_of_week": d, "opens_at": opens, "closes_at": closes}
        for d in range(7)
        if d not in skip
    ]


def _split_week(morning, afternoon, skip=()):
    """The classic Lebanese shop pattern: shut for the afternoon rest."""
    entries = []
    for d in range(7):
        if d in skip:
            continue
        entries.append(
            {"day_of_week": d, "opens_at": morning[0], "closes_at": morning[1]}
        )
        entries.append(
            {
                "day_of_week": d,
                "opens_at": afternoon[0],
                "closes_at": afternoon[1],
            }
        )
    return entries


HOURS_STANDARD = _week("09:00", "21:00")
HOURS_CLOSED_SUNDAY = _week("09:00", "20:00", skip=(6,))
HOURS_SPLIT = _split_week(("09:00", "14:00"), ("16:00", "20:00"), skip=(6,))
# Opens in the evening and shuts at two in the morning.
HOURS_LATE = _week("20:00", "02:00")


STORE_SPECS = (
    # ------------------------------------------------------------------ #
    {
        "vendor_email": "vendor.hamra@cedarlink.demo",
        "vendor_name": ("Nadia", "Khoury"),
        "phone": "+961 3 100 001",
        "store": "Hamra Grocery",
        "city": "Beirut",
        # Real neighbourhood coordinates, so the distance search returns a
        # meaningful spread instead of eight identical results.
        "lat": 33.896800, "lng": 35.479700,          # Hamra
        "description": "Pantry staples and Lebanese specialties in the "
                       "heart of Hamra.",
        "inside_fee": 2.00, "outside_fee": 5.00,
        "active": True,
        "approval": "approved",
        "hours": HOURS_STANDARD,
        "announcements": (
            {"title": "New olive-oil pressing just arrived",
             "body": "This season's cold-pressed oil from the Koura hills "
                     "is in stock. Limited quantity.",
             "when": "live"},
            {"title": "Ramadan opening hours",
             "body": "From the first of the month we open at noon and "
                     "close at midnight.",
             "when": "scheduled"},
            {"title": "Eid weekend closure",
             "body": "We were closed for the holiday and are now back to "
                     "our usual hours.",
             "when": "expired"},
        ),
        "products": (
            p("Zaatar Blend 200g", "خلطة زعتر ٢٠٠ غرام",
              "Mélange de zaatar 200 g",
              "House wild-thyme blend with sumac and sesame.",
              "خلطة الزعتر البري من إعدادنا مع السماق والسمسم.",
              "Mélange maison de thym sauvage au sumac et sésame.",
              3.50, 40, "Food"),
            p("Lebanese Extra Virgin Olive Oil 1L",
              "زيت زيتون لبناني بكر ممتاز ١ لتر",
              "Huile d'olive vierge extra libanaise 1 L",
              "Cold-pressed, single-estate from the Koura hills.",
              "معصور على البارد، من بستان واحد في تلال الكورة.",
              "Pressée à froid, d'un seul domaine des collines du Koura.",
              12.00, 25, "Food"),
            p("Baklava Assortment (12 pcs)", "تشكيلة بقلاوة (١٢ قطعة)",
              "Assortiment de baklava (12 pièces)",
              "Walnut and pistachio, layered and soaked in orange-blossom "
              "syrup.",
              "بالجوز والفستق، طبقات مشبعة بشراب ماء الزهر.",
              "Noix et pistache, en couches, imbibées de sirop à la fleur "
              "d'oranger.",
              9.00, 0, "Food"),
            p("Arabic Coffee with Cardamom 250g",
              "قهوة عربية بالهيل ٢٥٠ غرام",
              "Café arabe à la cardamome 250 g",
              "Finely ground, medium roast.",
              "مطحونة ناعماً، تحميص متوسط.",
              "Mouture fine, torréfaction moyenne.",
              6.50, 30, "Food"),
            p("Pomegranate Molasses 500ml", "دبس رمان ٥٠٠ مل",
              "Mélasse de grenade 500 ml",
              "Thick and sharp, pressed from sour pomegranates.",
              "كثيف وحامض، معصور من الرمان الحامض.",
              "Épaisse et acidulée, pressée de grenades acides.",
              5.00, 18, "Food"),
            p("Orange Blossom Water 300ml", "ماء زهر ٣٠٠ مل",
              "Eau de fleur d'oranger 300 ml",
              "Distilled from bitter-orange blossom.",
              "مقطر من زهر النارنج.",
              "Distillée à partir de fleurs de bigaradier.",
              4.00, 3, "Food"),
            p("Tahini 400g", "طحينة ٤٠٠ غرام", "Tahini 400 g",
              "Stone-ground hulled sesame, nothing added.",
              "سمسم مقشور مطحون بالحجر، بلا إضافات.",
              "Sésame décortiqué moulu à la meule, sans additifs.",
              5.50, 22, "Food"),
            p("Mixed Nuts Roasted 500g", "مكسرات مشكلة محمصة ٥٠٠ غرام",
              "Noix mélangées grillées 500 g",
              "Almonds, cashews and pistachios, roasted daily.",
              "لوز وكاجو وفستق، محمصة يومياً.",
              "Amandes, noix de cajou et pistaches, grillées chaque jour.",
              14.00, 16, "Food"),
        ),
    },
    # ------------------------------------------------------------------ #
    {
        "vendor_email": "vendor.achrafieh@cedarlink.demo",
        "vendor_name": ("Georges", "Haddad"),
        "phone": "+961 3 100 002",
        "store": "Achrafieh Pantry",
        "city": "Beirut",
        "lat": 33.886900, "lng": 35.517100,          # Achrafieh
        "description": "A small corner shop on Sassine, open since the "
                       "morning bread arrives.",
        "inside_fee": 2.50, "outside_fee": 6.00,
        "active": True,
        "approval": "approved",
        # Shuts for the afternoon and reopens — the split-day screenshot.
        "hours": HOURS_SPLIT,
        "announcements": (
            {"title": "Fresh manoushe every morning",
             "body": "The oven is on from seven. Zaatar, cheese and "
                     "kishk until we run out.",
             "when": "live"},
        ),
        "products": (
            p("Kishk 400g", "كشك ٤٠٠ غرام", "Kishk 400 g",
              "Fermented wheat and yoghurt, dried and milled.",
              "قمح مخمر مع اللبن، مجفف ومطحون.",
              "Blé fermenté et yaourt, séché et moulu.",
              7.00, 14, "Food"),
            p("Village Labneh 500g", "لبنة بلدية ٥٠٠ غرام",
              "Labneh de village 500 g",
              "Strained for three days, salted lightly.",
              "مصفاة ثلاثة أيام، مملحة قليلاً.",
              "Égouttée trois jours, légèrement salée.",
              6.00, 20, "Food"),
            p("Makdous in Olive Oil 750g", "مكدوس بزيت الزيتون ٧٥٠ غرام",
              "Makdous à l'huile d'olive 750 g",
              "Baby aubergines stuffed with walnut and pepper.",
              "باذنجان صغير محشو بالجوز والفليفلة.",
              "Petites aubergines farcies aux noix et au poivron.",
              11.00, 9, "Food"),
            p("Mountain Honey 500g", "عسل جبلي ٥٠٠ غرام",
              "Miel de montagne 500 g",
              "Raw, from hives above Bcharre.",
              "خام، من خلايا فوق بشري.",
              "Brut, de ruches situées au-dessus de Bcharré.",
              18.00, 7, "Food"),
            p("Green Freekeh 1kg", "فريكة خضراء ١ كيلو",
              "Freekeh verte 1 kg",
              "Young wheat, fire-roasted and cracked.",
              "قمح أخضر، محمص على النار ومجروش.",
              "Blé vert, grillé au feu et concassé.",
              6.50, 25, "Food"),
            p("Rose Jam 450g", "مربى الورد ٤٥٠ غرام",
              "Confiture de roses 450 g",
              "Damask rose petals in a light syrup.",
              "بتلات الورد الجوري في شراب خفيف.",
              "Pétales de rose de Damas dans un sirop léger.",
              8.00, 2, "Food"),
            p("Sumac 200g", "سماق ٢٠٠ غرام", "Sumac 200 g",
              "Coarse ground, deep red, sharp.",
              "مطحون خشن، أحمر غامق، حامض.",
              "Mouture grossière, rouge foncé, acidulé.",
              4.50, 30, "Food"),
            p("Bulgur Coarse 1kg", "برغل خشن ١ كيلو",
              "Boulgour gros 1 kg",
              "For kibbeh and tabbouleh.",
              "للكبة والتبولة.",
              "Pour le kibbé et le taboulé.",
              4.00, 35, "Food"),
        ),
    },
    # ------------------------------------------------------------------ #
    {
        "vendor_email": "vendor.marmikhael@cedarlink.demo",
        "vendor_name": ("Rita", "Feghali"),
        "phone": "+961 3 100 003",
        "store": "Mar Mikhael Books",
        "city": "Beirut",
        "lat": 33.897600, "lng": 35.523300,          # Mar Mikhael
        "description": "Second-hand and new, Arabic, French and English. "
                       "Open late.",
        "inside_fee": 3.00, "outside_fee": 7.00,
        "active": True,
        "approval": "approved",
        # Evening trade that runs past midnight — the wrap-around case.
        "hours": HOURS_LATE,
        "announcements": (
            {"title": "Poetry night, every second Thursday",
             "body": "Readings start at nine. The shop stays open until "
                     "two.",
             "when": "live"},
            {"title": "Summer stocktake",
             "body": "We will be shut for two days at the end of the "
                     "month while we count.",
             "when": "scheduled"},
        ),
        "products": (
            p("Beirut Fragments", "شظايا بيروت", "Fragments de Beyrouth",
              "A wartime memoir of the city, in English.",
              "مذكرات من زمن الحرب عن المدينة، بالإنكليزية.",
              "Mémoire de guerre sur la ville, en anglais.",
              15.00, 6, "Books"),
            p("Arabic Grammar for Beginners",
              "قواعد اللغة العربية للمبتدئين",
              "Grammaire arabe pour débutants",
              "Clear tables, exercises and answer key.",
              "جداول واضحة وتمارين مع الحلول.",
              "Tableaux clairs, exercices et corrigés.",
              22.00, 11, "Books"),
            p("Anthology of Levantine Poetry", "مختارات من الشعر الشامي",
              "Anthologie de la poésie levantine",
              "Facing-page Arabic and English.",
              "النص العربي والإنكليزي وجهاً لوجه.",
              "Arabe et anglais en regard.",
              19.00, 4, "Books"),
            p("Lebanese Cookery, Illustrated", "المطبخ اللبناني، مصوّر",
              "Cuisine libanaise, illustrée",
              "Two hundred household recipes, photographed.",
              "مئتا وصفة منزلية، مع الصور.",
              "Deux cents recettes de famille, photographiées.",
              28.00, 8, "Books"),
            p("Cedars: A Natural History", "الأرز: تاريخ طبيعي",
              "Les cèdres : une histoire naturelle",
              "The forests of the Lebanon range, past and present.",
              "غابات جبل لبنان، ماضيها وحاضرها.",
              "Les forêts du mont Liban, hier et aujourd'hui.",
              24.00, 0, "Books"),
            p("Pocket French-Arabic Dictionary",
              "قاموس جيب فرنسي-عربي",
              "Dictionnaire de poche français-arabe",
              "Twelve thousand entries, both directions.",
              "اثنا عشر ألف مدخل، في الاتجاهين.",
              "Douze mille entrées, dans les deux sens.",
              13.00, 17, "Books"),
            p("Notebook, Stitched Cloth Cover", "دفتر بغلاف قماشي مخيط",
              "Carnet à couverture en tissu cousue",
              "A5, unlined, ninety-six leaves.",
              "قياس A5، بلا خطوط، ستة وتسعون ورقة.",
              "A5, sans lignes, quatre-vingt-seize feuillets.",
              9.00, 3, "Books"),
            p("Reading Lamp, Brass Finish", "مصباح قراءة بلمسة نحاسية",
              "Lampe de lecture, finition laiton",
              "Clamps to a shelf or a headboard.",
              "يثبت على الرف أو على طرف السرير.",
              "Se fixe à une étagère ou une tête de lit.",
              26.00, 5, "Home"),
        ),
    },
    # ------------------------------------------------------------------ #
    {
        "vendor_email": "vendor.tripoli@cedarlink.demo",
        "vendor_name": ("Samir", "Osman"),
        "phone": "+961 3 100 004",
        "store": "Tripoli Threads",
        "city": "Tripoli",
        "lat": 34.436700, "lng": 35.849400,
        "description": "Hand-finished clothing from the old souks of "
                       "Tripoli.",
        "inside_fee": 1.50, "outside_fee": 4.00,
        "active": True,
        "approval": "approved",
        # Shut on Sundays — the closed-day screenshot.
        "hours": HOURS_CLOSED_SUNDAY,
        "announcements": (
            {"title": "Winter stock is in",
             "body": "Wool and heavier cottons on the shelves from this "
                     "week.",
             "when": "live"},
        ),
        "products": (
            p("Embroidered Cotton Shirt", "قميص قطني مطرز",
              "Chemise en coton brodée",
              "Hand-stitched cuffs, unbleached cotton.",
              "أساور مخيطة يدوياً، قطن غير مبيض.",
              "Poignets cousus main, coton écru.",
              32.00, 12, "Clothes"),
            p("Wool Winter Scarf", "وشاح صوف شتوي",
              "Écharpe d'hiver en laine",
              "Loom-woven, undyed mountain wool.",
              "منسوج على النول، صوف جبلي غير مصبوغ.",
              "Tissée au métier, laine de montagne non teinte.",
              18.00, 20, "Clothes"),
            p("Linen Summer Dress", "فستان كتان صيفي",
              "Robe d'été en lin",
              "Loose cut, side pockets, washed linen.",
              "قصة واسعة، جيوب جانبية، كتان مغسول.",
              "Coupe ample, poches latérales, lin lavé.",
              45.00, 6, "Clothes"),
            p("Kufiya, Black and White", "كوفية بيضاء وسوداء",
              "Keffieh noir et blanc",
              "Full size, hand-knotted fringe.",
              "قياس كامل، أهداب معقودة يدوياً.",
              "Taille complète, franges nouées main.",
              14.00, 25, "Clothes"),
            p("Leather Belt, Hand-Tooled", "حزام جلد منقوش يدوياً",
              "Ceinture en cuir travaillée main",
              "Vegetable-tanned, solid brass buckle.",
              "مدبوغ نباتياً، إبزيم نحاس صلب.",
              "Tannage végétal, boucle en laiton massif.",
              28.00, 9, "Clothes"),
            p("Wool Felt Slippers", "خف من اللباد الصوفي",
              "Chaussons en feutre de laine",
              "Soft sole, made for indoors.",
              "نعل طري، للاستعمال داخل المنزل.",
              "Semelle souple, pour l'intérieur.",
              22.00, 2, "Clothes"),
            p("Cotton Table Runner", "مفرش طاولة قطني",
              "Chemin de table en coton",
              "Two metres, striped in madder red.",
              "مترين، مخطط بالأحمر الفوّي.",
              "Deux mètres, rayé de rouge garance.",
              26.00, 11, "Home"),
            p("Hand-Loomed Cushion Cover", "غطاء وسادة منسوج يدوياً",
              "Housse de coussin tissée main",
              "45 cm square, hidden zip.",
              "٤٥ سم مربع، سحاب مخفي.",
              "45 cm de côté, fermeture invisible.",
              20.00, 0, "Home"),
        ),
    },
    # ------------------------------------------------------------------ #
    {
        "vendor_email": "vendor.saida@cedarlink.demo",
        "vendor_name": ("Hassan", "Zaatar"),
        "phone": "+961 3 100 005",
        "store": "Saida Electronics",
        "city": "Saida",
        "lat": 33.557200, "lng": 35.372800,
        "description": "Everyday electronics and accessories, tested "
                       "before they leave the counter.",
        "inside_fee": 3.00, "outside_fee": 6.00,
        "active": True,
        "approval": "approved",
        "hours": HOURS_STANDARD,
        # The screenshot: shut right now, and the reason everyone in
        # Lebanon recognises.
        "override": {"status": "closed", "reason": "Power outage",
                     "hours_ahead": 5},
        "announcements": (
            {"title": "Generator hours",
             "body": "We run on the generator between noon and six. Card "
                     "payments may be slow.",
             "when": "live"},
        ),
        "products": (
            p("Solar Power Bank 20000mAh", "بطارية متنقلة شمسية ٢٠٠٠٠",
              "Batterie externe solaire 20000 mAh",
              "Two USB outputs, panel for a slow top-up.",
              "مخرجان USB، لوح للشحن البطيء.",
              "Deux sorties USB, panneau pour recharge lente.",
              38.00, 15, "Electronics"),
            p("LED Rechargeable Lantern", "فانوس LED قابل للشحن",
              "Lanterne LED rechargeable",
              "Eight hours on full, three brightness steps.",
              "ثماني ساعات بشحن كامل، ثلاث درجات إضاءة.",
              "Huit heures en pleine charge, trois niveaux.",
              16.00, 30, "Electronics"),
            p("USB-C Fast Charger 45W", "شاحن USB-C سريع ٤٥ واط",
              "Chargeur USB-C rapide 45 W",
              "Charges a laptop and a phone together.",
              "يشحن حاسوباً وهاتفاً معاً.",
              "Recharge un portable et un téléphone ensemble.",
              24.00, 22, "Electronics"),
            p("Bluetooth Speaker, Water Resistant",
              "مكبر صوت بلوتوث مقاوم للماء",
              "Enceinte Bluetooth résistante à l'eau",
              "Twelve hours, pairs in stereo with a second unit.",
              "اثنتا عشرة ساعة، يقترن ستيريو مع وحدة ثانية.",
              "Douze heures, appairage stéréo avec une seconde.",
              45.00, 8, "Electronics"),
            p("Voltage Stabiliser 1000VA", "منظم جهد ١٠٠٠ فولت أمبير",
              "Régulateur de tension 1000 VA",
              "Protects a fridge or a television from surges.",
              "يحمي البراد أو التلفزيون من التذبذب.",
              "Protège un réfrigérateur ou un téléviseur.",
              75.00, 4, "Electronics"),
            p("Wired Earphones with Microphone",
              "سماعات سلكية مع ميكروفون",
              "Écouteurs filaires avec micro",
              "3.5 mm, braided cable, inline control.",
              "٣.٥ ملم، سلك مجدول، تحكم على السلك.",
              "3,5 mm, câble tressé, commande en ligne.",
              9.00, 40, "Electronics"),
            p("Extension Lead, 5 Sockets", "وصلة كهرباء بخمسة مآخذ",
              "Multiprise 5 prises",
              "Three metres, individually switched.",
              "ثلاثة أمتار، مفتاح لكل مأخذ.",
              "Trois mètres, interrupteur par prise.",
              12.00, 3, "Electronics"),
            p("LED Bulb 9W, Warm White", "لمبة LED ٩ واط أبيض دافئ",
              "Ampoule LED 9 W blanc chaud",
              "E27 fitting, pack of four.",
              "قاعدة E27، عبوة من أربع.",
              "Culot E27, lot de quatre.",
              8.00, 50, "Electronics"),
        ),
    },
    # ------------------------------------------------------------------ #
    {
        "vendor_email": "vendor.jounieh@cedarlink.demo",
        "vendor_name": ("Maya", "Sfeir"),
        "phone": "+961 3 100 006",
        "store": "Jounieh Beauty Bar",
        "city": "Jounieh",
        "lat": 33.980800, "lng": 35.617800,
        "description": "Small-batch soap and skincare made along the bay.",
        "inside_fee": 2.00, "outside_fee": 5.50,
        # Deactivated by its owner — the storefront hides it, the vendor
        # console still shows it.
        "active": False,
        "approval": "approved",
        "hours": HOURS_STANDARD,
        "announcements": (
            {"title": "Back in the spring",
             "body": "The shop is closed while we move to a larger "
                     "workroom.",
             "when": "live"},
        ),
        "products": (
            p("Olive Oil Soap, Aleppo Style", "صابون زيت زيتون حلبي",
              "Savon à l'huile d'olive, style d'Alep",
              "Cured nine months, laurel berry oil.",
              "معتق تسعة أشهر، بزيت الغار.",
              "Affiné neuf mois, à l'huile de baies de laurier.",
              5.00, 40, "Beauty"),
            p("Rose Water Toner 200ml", "تونر ماء الورد ٢٠٠ مل",
              "Lotion tonique à l'eau de rose 200 ml",
              "Single-distilled Damask rose, nothing else.",
              "ورد جوري مقطر مرة واحدة، لا شيء غيره.",
              "Rose de Damas distillée une fois, rien d'autre.",
              12.00, 18, "Beauty"),
            p("Argan Hair Oil 100ml", "زيت أركان للشعر ١٠٠ مل",
              "Huile capillaire d'argan 100 ml",
              "Cold-pressed, unscented.",
              "معصور على البارد، بلا عطر.",
              "Pressée à froid, sans parfum.",
              20.00, 12, "Beauty"),
            p("Black Seed Face Cream 50ml",
              "كريم الوجه بالحبة السوداء ٥٠ مل",
              "Crème visage à la nigelle 50 ml",
              "Light, for daily use.",
              "خفيف، للاستعمال اليومي.",
              "Légère, pour un usage quotidien.",
              16.00, 9, "Beauty"),
            p("Bath Salts with Laurel 600g", "ملح استحمام بالغار ٦٠٠ غرام",
              "Sels de bain au laurier 600 g",
              "Dead Sea salt, laurel and rosemary.",
              "ملح البحر الميت مع الغار وإكليل الجبل.",
              "Sel de la mer Morte, laurier et romarin.",
              14.00, 15, "Beauty"),
            p("Beeswax Lip Balm", "مرطب شفاه بشمع النحل",
              "Baume à lèvres à la cire d'abeille",
              "Beeswax and olive oil, three in a tin.",
              "شمع نحل وزيت زيتون، ثلاثة في علبة.",
              "Cire d'abeille et huile d'olive, trois par boîte.",
              7.00, 26, "Beauty"),
            p("Clay Face Mask 120g", "قناع طيني للوجه ١٢٠ غرام",
              "Masque visage à l'argile 120 g",
              "Green clay from the Bekaa, powdered.",
              "طين أخضر من البقاع، مطحون.",
              "Argile verte de la Bekaa, en poudre.",
              11.00, 0, "Beauty"),
            p("Cotton Wash Cloth, Pack of Three",
              "منشفة وجه قطنية، ثلاث قطع",
              "Gant de toilette en coton, lot de trois",
              "Waffle weave, unbleached.",
              "نسيج وافل، غير مبيض.",
              "Tissage nid d'abeille, écru.",
              9.00, 20, "Home"),
        ),
    },
    # ------------------------------------------------------------------ #
    {
        "vendor_email": "vendor.cedarloom@cedarlink.demo",
        "vendor_name": ("Rami", "Btaddini"),
        "phone": "+961 3 100 007",
        "store": "Cedar Loom",
        "city": "Beirut",
        # Online only: no shopfront, so no coordinates and never in a
        # distance result.
        "online_only": True,
        "lat": None, "lng": None,
        "description": "Handwoven throws and cushions, made to order and "
                       "shipped from the workshop.",
        "inside_fee": 0.00, "outside_fee": 3.50,
        "active": True,
        "approval": "approved",
        "hours": HOURS_STANDARD,
        "announcements": (
            {"title": "Made to order, two weeks",
             "body": "Every piece is woven after you order it. Allow two "
                     "weeks before dispatch.",
             "when": "live"},
        ),
        "products": (
            p("Handwoven Wool Throw", "بطانية صوف منسوجة يدوياً",
              "Plaid en laine tissé main",
              "150 × 200 cm, undyed wool, hand-knotted fringe.",
              "١٥٠ × ٢٠٠ سم، صوف غير مصبوغ، أهداب يدوية.",
              "150 × 200 cm, laine non teinte, franges nouées main.",
              85.00, 5, "Home"),
            p("Cushion Cover, Cedar Motif", "غطاء وسادة بنقشة الأرزة",
              "Housse de coussin, motif cèdre",
              "45 cm square, woven in two greens.",
              "٤٥ سم مربع، منسوج بلونين أخضرين.",
              "45 cm de côté, tissé en deux verts.",
              30.00, 14, "Home"),
            p("Wool Floor Runner", "سجادة أرضية صوفية",
              "Tapis de couloir en laine",
              "70 × 200 cm, flat weave, reversible.",
              "٧٠ × ٢٠٠ سم، نسيج مسطح، وجهان.",
              "70 × 200 cm, tissage plat, réversible.",
              120.00, 3, "Home"),
            p("Linen Tea Towel, Pair", "منشفة مطبخ كتان، زوج",
              "Torchon en lin, la paire",
              "Stone-washed, hanging loop.",
              "مغسول بالحجر، مع حلقة للتعليق.",
              "Lavé à la pierre, avec passant.",
              16.00, 22, "Home"),
            p("Woven Storage Basket", "سلة تخزين منسوجة",
              "Panier de rangement tissé",
              "Rush and cotton cord, 35 cm across.",
              "أسل وحبل قطني، قطر ٣٥ سم.",
              "Jonc et corde de coton, 35 cm de diamètre.",
              28.00, 8, "Home"),
            p("Wool Blanket, Single Bed", "بطانية صوف لسرير مفرد",
              "Couverture en laine, lit simple",
              "160 × 220 cm, herringbone.",
              "١٦٠ × ٢٢٠ سم، نقشة عظم السمكة.",
              "160 × 220 cm, chevrons.",
              140.00, 2, "Home"),
            p("Table Mats, Set of Four", "مفارش طاولة، أربع قطع",
              "Sets de table, lot de quatre",
              "Cotton, wipe clean, natural and clay.",
              "قطن، سهل التنظيف، لون طبيعي وطيني.",
              "Coton, nettoyage facile, naturel et argile.",
              24.00, 0, "Home"),
            p("Loom-Woven Scarf, Fine Wool", "وشاح منسوج بصوف ناعم",
              "Écharpe tissée, laine fine",
              "Merino, 180 × 35 cm.",
              "ميرينو، ١٨٠ × ٣٥ سم.",
              "Mérinos, 180 × 35 cm.",
              48.00, 10, "Clothes"),
        ),
    },
    # ------------------------------------------------------------------ #
    {
        "vendor_email": "vendor.badaro@cedarlink.demo",
        "vendor_name": ("Karim", "Chalhoub"),
        "phone": "+961 3 100 008",
        "store": "Badaro Home",
        "city": "Beirut",
        "lat": 33.877800, "lng": 35.512500,          # Badaro
        "description": "Kitchen and household goods, chosen to last.",
        "inside_fee": 2.50, "outside_fee": 6.00,
        "active": True,
        # Waiting on an admin — this is what fills the approval queue.
        "approval": "pending",
        "hours": HOURS_STANDARD,
        "announcements": (),
        "products": (
            p("Cezve Coffee Pot, Copper", "ركوة قهوة نحاسية",
              "Cafetière cezve en cuivre",
              "Tinned inside, wooden handle, three cups.",
              "مبطنة بالقصدير، مقبض خشبي، ثلاثة فناجين.",
              "Étamée, manche en bois, trois tasses.",
              22.00, 12, "Home"),
            p("Mortar and Pestle, Marble", "جرن ومدقة من الرخام",
              "Mortier et pilon en marbre",
              "Heavy, 14 cm, for garlic and spice.",
              "ثقيل، ١٤ سم، للثوم والبهار.",
              "Lourd, 14 cm, pour l'ail et les épices.",
              26.00, 7, "Home"),
            p("Kibbeh Tray, Tinned Copper", "صينية كبة من النحاس المقصدر",
              "Plat à kibbé en cuivre étamé",
              "36 cm, oven and table.",
              "٣٦ سم، للفرن والمائدة.",
              "36 cm, four et table.",
              34.00, 5, "Home"),
            p("Glass Tea Set, Six Cups", "طقم شاي زجاجي، ستة أكواب",
              "Service à thé en verre, six tasses",
              "Slim waisted glasses with saucers.",
              "أكواب مخصرة مع صحون.",
              "Verres à taille fine avec soucoupes.",
              19.00, 16, "Home"),
            p("Olive Wood Serving Board", "لوح تقديم من خشب الزيتون",
              "Planche de service en bois d'olivier",
              "40 cm, oiled, each grain different.",
              "٤٠ سم، مزيت، كل قطعة بعروق مختلفة.",
              "40 cm, huilée, veinage unique.",
              32.00, 9, "Home"),
            p("Enamel Stock Pot 8L", "قدر مطلي بالمينا ٨ ليتر",
              "Marmite émaillée 8 L",
              "For mloukhieh and large batches.",
              "للملوخية والطبخات الكبيرة.",
              "Pour la mouloukhieh et les grandes quantités.",
              42.00, 4, "Home"),
            p("Cotton Apron, Adjustable", "مريول قطني قابل للتعديل",
              "Tablier en coton ajustable",
              "Heavy cotton, two front pockets.",
              "قطن سميك، جيبان أماميان.",
              "Coton épais, deux poches devant.",
              15.00, 1, "Home"),
            p("Storage Jars, Set of Three", "برطمانات تخزين، ثلاث قطع",
              "Bocaux de conservation, lot de trois",
              "Clip lid, rubber seal, one litre each.",
              "غطاء بمشبك، حشوة مطاطية، ليتر لكل واحد.",
              "Couvercle à clip, joint caoutchouc, un litre.",
              21.00, 11, "Home"),
        ),
    },
)


CUSTOMER_SPECS = (
    {
        "email": "customer.rania@cedarlink.demo",
        "name": ("Rania", "Abou Zeid"),
        "phone": "+961 3 200 001",
        # Both saved addresses carry a map pin, so the "search near a
        # saved address" chips on /stores have something to offer.
        "addresses": (
            ("Home", "14 Rue Souraty, Hamra", "Beirut", True,
             33.897200, 35.480600),
            ("Work", "Sassine Square, 3rd floor", "Beirut", False,
             33.886400, 35.518000),
        ),
        # A customer who has said what she cares about.
        "interests": ("Food", "Home", "Books"),
        "hide_out_of_stock": False,
    },
    {
        "email": "customer.karim@cedarlink.demo",
        "name": ("Karim", "Mansour"),
        "phone": "+961 3 200 002",
        "addresses": (
            ("Home", "Rue Mar Maroun, Jounieh", "Jounieh", True,
             33.981500, 35.618900),
        ),
        # Chose nothing — the default home order is what he sees.
        "interests": (),
        "hide_out_of_stock": True,
    },
    {
        "email": "customer.lina@cedarlink.demo",
        "name": ("Lina", "Daher"),
        "phone": "+961 3 200 003",
        "addresses": (
            ("Home", "Rue Azmi, near the clock tower", "Tripoli", True,
             None, None),
        ),
        "interests": ("Clothes", "Beauty"),
        "hide_out_of_stock": False,
    },
    {
        "email": "customer.omar@cedarlink.demo",
        "name": ("Omar", "Fakhoury"),
        "phone": "+961 3 200 004",
        "addresses": (
            ("Home", "Rue Badaro, opposite the park", "Beirut", True,
             33.878200, 35.513100),
            ("Other", "Riad El Solh, office block C", "Beirut", False,
             None, None),
        ),
        "interests": ("Electronics",),
        "hide_out_of_stock": False,
    },
)


# code, type, value, extras — one per badge state on the coupon screens.
COUPON_SPECS = (
    {"code": "CEDAR10", "discount_type": "percentage", "value": 10,
     "min_order_total": 20, "usage_limit": 100, "per_user_limit": 2,
     "store": None, "state": "active"},
    {"code": "WELCOME5", "discount_type": "fixed", "value": 5,
     "min_order_total": 15, "usage_limit": 50, "per_user_limit": 1,
     "store": None, "state": "active"},
    {"code": "SUMMER25", "discount_type": "percentage", "value": 25,
     "min_order_total": None, "usage_limit": None, "per_user_limit": None,
     "store": None, "state": "expired"},
    # usage_limit 1, and it is spent once during seeding — so "Limit
    # reached" is a state the coupon arrived at, not one that was typed in.
    {"code": "FIRST50", "discount_type": "percentage", "value": 50,
     "min_order_total": None, "usage_limit": 1, "per_user_limit": 1,
     "store": None, "state": "exhausted"},
    {"code": "HAMRA15", "discount_type": "percentage", "value": 15,
     "min_order_total": 10, "usage_limit": 30, "per_user_limit": 3,
     "store": "Hamra Grocery", "state": "active"},
    {"code": "SPRING20", "discount_type": "percentage", "value": 20,
     "min_order_total": None, "usage_limit": None, "per_user_limit": None,
     "store": None, "state": "scheduled"},
)


# (customer index, store, status, [(product, qty)], days ago)
ORDER_SPECS = (
    (0, "Hamra Grocery", "delivered",
     (("Lebanese Extra Virgin Olive Oil 1L", 2),
      ("Zaatar Blend 200g", 3)), 24),
    (0, "Mar Mikhael Books", "delivered",
     (("Lebanese Cookery, Illustrated", 1),), 17),
    (0, "Cedar Loom", "processing",
     (("Cushion Cover, Cedar Motif", 2),), 3),
    (1, "Saida Electronics", "delivered",
     (("Solar Power Bank 20000mAh", 1),
      ("LED Rechargeable Lantern", 2)), 30),
    (1, "Tripoli Threads", "canceled",
     (("Wool Winter Scarf", 1),), 12),
    (2, "Tripoli Threads", "delivered",
     (("Embroidered Cotton Shirt", 1),
      ("Kufiya, Black and White", 2)), 21),
    (2, "Jounieh Beauty Bar", "delivered",
     (("Olive Oil Soap, Aleppo Style", 4),), 15),
    (3, "Achrafieh Pantry", "processing",
     (("Mountain Honey 500g", 1), ("Village Labneh 500g", 2)), 2),
    (3, "Badaro Home", "pending",
     (("Cezve Coffee Pot, Copper", 1),), 1),
)

# The order that runs through a real checkout with a coupon, so the
# discount line and the redemption row are genuine.
COUPON_ORDER = {
    "customer": 0,
    "coupon": "CEDAR10",
    "items": (("Mixed Nuts Roasted 500g", 1), ("Tahini 400g", 2)),
    "city": "Beirut",
}

# A cart spanning two stores, checked out for real so it becomes two
# linked orders the way a customer's would.
MULTI_STORE_ORDER = {
    "customer": 3,
    "items": (("USB-C Fast Charger 45W", 1), ("Sumac 200g", 2)),
    "city": "Beirut",
}


# (customer index, (kind, name), rating, title, body)
# Ratings are deliberately spread: a demo where everything is 5.0 shows
# nothing about how ratings render.
REVIEW_SPECS = (
    (0, ("product", "Lebanese Extra Virgin Olive Oil 1L"), 5,
     "Worth the price",
     "Peppery and green, the way good oil should be. I went back for a "
     "second bottle."),
    (0, ("product", "Zaatar Blend 200g"), 4,
     "Good, a little heavy on the sumac",
     "Fresh and fragrant. I would like slightly less sumac but that is "
     "personal taste."),
    (0, ("store", "Hamra Grocery"), 5,
     "My regular shop now",
     "Ordered three times. Everything has arrived on the day they said."),
    (0, ("product", "Lebanese Cookery, Illustrated"), 4,
     "Beautiful book, heavy",
     "The photographs are lovely. It does not sit open on a counter "
     "easily."),
    (1, ("product", "Solar Power Bank 20000mAh"), 3,
     "Does the job, solar panel is slow",
     "Holds its charge well. The panel is close to useless — treat it as "
     "a normal power bank."),
    (1, ("product", "LED Rechargeable Lantern"), 5,
     "Two outages and still going",
     "Bright enough for a whole room on the middle setting."),
    (1, ("store", "Saida Electronics"), 4,
     "Knew what they were talking about",
     "Asked three questions before buying and got straight answers."),
    (2, ("product", "Embroidered Cotton Shirt"), 5,
     "The stitching is real",
     "You can see it is hand-finished. Washed twice, no change."),
    (2, ("product", "Kufiya, Black and White"), 2,
     "Thinner than I expected",
     "The weave is looser than the one I have from before. Fine for "
     "summer, not for wind."),
    (2, ("store", "Tripoli Threads"), 4,
     "Careful packing",
     "Wrapped in paper and tied. Arrived two days later than the "
     "estimate."),
    (2, ("product", "Olive Oil Soap, Aleppo Style"), 5,
     "Lasts for weeks",
     "One bar has outlasted three of the supermarket kind."),
)

# The review a customer reports, and the one an admin then removes, so
# both moderation states have content on the admin queue.
FLAGGED_REVIEW = ("product", "Kufiya, Black and White")
FLAG_REASON = "The reviewer is comparing it to a different product."

REMOVED_REVIEW = ("product", "Zaatar Blend 200g")
REMOVE_REASON = "Duplicate of a review the same customer left earlier."
