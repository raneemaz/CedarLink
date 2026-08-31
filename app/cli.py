"""Custom Flask CLI commands.

These run with `flask <command>` and require server/database access, so they
are the safe place to perform privileged actions that must never be exposed
through a public HTTP endpoint (e.g. creating an administrator).
"""

import os
import uuid

import click
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import (
    Address,
    Category,
    Order,
    OrderItem,
    Product,
    ProductImage,
    Store,
    User,
)

VALID_VERIFICATION_METHODS = ("email", "sms", "whatsapp")
MIN_ADMIN_PASSWORD_LENGTH = 8


@click.command("create-admin")
@click.option("--email", required=True, prompt=True,
              help="Admin email address.")
@click.option(
    "--password",
    required=True,
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Admin password (min 8 characters).",
)
@click.option("--first-name", required=True, prompt="First name")
@click.option("--last-name", required=True, prompt="Last name")
@click.option("--phone", required=True,
              prompt=True, help="Admin phone number.")
@click.option(
    "--verification-method",
    default="email",
    show_default=True,
    type=click.Choice(VALID_VERIFICATION_METHODS),
    help="Channel used for the login verification code.",
)
@with_appcontext
def create_admin(
    email,
    password,
    first_name,
    last_name,
    phone,
    verification_method,
):
    """Create an administrator account.

    Administrators cannot be created through public registration. This command
    is the only supported way to bootstrap the first admin.
    """
    email = (email or "").strip().lower()

    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        raise click.ClickException(
            "Password must be at least "
            f"{MIN_ADMIN_PASSWORD_LENGTH} characters."
        )

    existing = User.query.filter_by(email=email).first()

    if existing:
        raise click.ClickException(
            f"A user with email {email} already exists "
            f"(id={existing.id}, role={existing.role})."
        )

    admin = User(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email,
        password=generate_password_hash(password),
        phone=phone.strip(),
        role="admin",
        # Admins are created out of band by a trusted operator, so the account
        # is verified immediately (no registration email challenge).
        is_verified=True,
        verification_method=verification_method,
    )

    db.session.add(admin)
    db.session.commit()

    click.echo(
        f"Admin account created: {admin.email} (id={admin.id}). "
        f"Login sends a verification code via '{verification_method}'."
    )


DEMO_PASSWORD = "Cedar!2026"
ADMIN_EMAIL = "admin@cedarlink.demo"

# Distinct fill colours for the generated placeholder images.
_IMAGE_COLORS = (
    (198, 40, 40),
    (2, 119, 189),
    (46, 125, 50),
    (245, 124, 0),
    (106, 27, 154),
    (0, 131, 143),
    (191, 54, 12),
    (69, 90, 100),
)

# Category names in the three interface languages (C.5).
_CATEGORY_SPECS = (
    ("Food", "طعام", "Alimentation"),
    ("Clothes", "ملابس", "Vêtements"),
    ("Electronics", "إلكترونيات", "Électronique"),
    ("Books", "كتب", "Livres"),
    ("Beauty", "تجميل", "Beauté"),
)


def _p(name_en, name_ar, name_fr, desc_en, desc_ar, desc_fr,
       price, stock, category):
    """One product spec, trilingual. Keyed by its English name elsewhere."""
    return {
        "name": {"en": name_en, "ar": name_ar, "fr": name_fr},
        "description": {"en": desc_en, "ar": desc_ar, "fr": desc_fr},
        "price": price,
        "stock": stock,
        "category": category,
    }


# Products grouped by store. English is the canonical name; Arabic and
# French are real translations so the demo catalogue is genuinely trilingual.
_STORE_SPECS = (
    {
        "vendor_email": "vendor.beirut@cedarlink.demo",
        "vendor_name": ("Nadia", "Khoury"),
        "phone": "+961 3 100 001",
        "store": "Hamra Grocery",
        "city": "Beirut",
        "description": "Pantry staples and Lebanese specialties in the "
        "heart of Hamra.",
        "inside_fee": 2.00,
        "outside_fee": 5.00,
        "active": True,
        "products": (
            _p("Zaatar Blend 200g",
               "خلطة زعتر ٢٠٠ غرام",
               "Mélange de zaatar 200 g",
               "House wild-thyme blend with sumac and sesame.",
               "خلطة الزعتر البري من إعدادنا مع السماق والسمسم.",
               "Mélange maison de thym sauvage au sumac et sésame.",
               3.50, 40, "Food"),
            _p("Lebanese Extra Virgin Olive Oil 1L",
               "زيت زيتون لبناني بكر ممتاز ١ لتر",
               "Huile d'olive vierge extra libanaise 1 L",
               "Cold-pressed, single-estate from the Koura hills.",
               "معصور على البارد، من بستان واحد في تلال الكورة.",
               "Pressée à froid, d'un seul domaine des collines du Koura.",
               12.00, 25, "Food"),
            _p("Baklava Assortment (12 pcs)",
               "تشكيلة بقلاوة (١٢ قطعة)",
               "Assortiment de baklava (12 pièces)",
               "Walnut and pistachio, layered and soaked in "
               "orange-blossom syrup.",
               "بالجوز والفستق، طبقات مشبعة بشراب ماء الزهر.",
               "Noix et pistache, en couches, imbibées de sirop à la "
               "fleur d'oranger.",
               9.00, 0, "Food"),
            _p("Arabic Coffee with Cardamom 250g",
               "قهوة عربية بالهيل ٢٥٠ غرام",
               "Café arabe à la cardamome 250 g",
               "Finely ground, medium roast.",
               "مطحونة ناعماً، تحميص متوسط.",
               "Mouture fine, torréfaction moyenne.",
               6.50, 30, "Food"),
            _p("Pomegranate Molasses 500ml",
               "دبس رمان ٥٠٠ مل",
               "Mélasse de grenade 500 ml",
               "Thick, tart, no added sugar.",
               "كثيف، حامض، دون سكر مضاف.",
               "Épaisse, acidulée, sans sucre ajouté.",
               4.25, 18, "Food"),
            _p("\"Beirut Nightingale\" - Poems",
               "«عندليب بيروت» - قصائد",
               "« Le Rossignol de Beyrouth » - Poèmes",
               "A bilingual pocket collection by a local press.",
               "مجموعة جيب ثنائية اللغة من دار نشر محلية.",
               "Un recueil de poche bilingue d'un éditeur local.",
               13.00, 20, "Books"),
        ),
    },
    {
        "vendor_email": "vendor.tripoli@cedarlink.demo",
        "vendor_name": ("Omar", "Baroudi"),
        "phone": "+961 3 100 002",
        "store": "Tripoli Threads",
        "city": "Tripoli",
        "description": "Hand-finished clothing and textiles from the old "
        "souks of Tripoli.",
        "inside_fee": 1.50,
        "outside_fee": 4.00,
        "active": True,
        "products": (
            _p("Hand-Embroidered Abaya",
               "عباءة مطرزة يدوياً",
               "Abaya brodée à la main",
               "Black crepe with tone-on-tone cuff embroidery.",
               "كريب أسود مع تطريز على الأساور بلون مطابق.",
               "Crêpe noir avec broderie ton sur ton aux poignets.",
               45.00, 12, "Clothes"),
            _p("Cotton Keffiyeh Scarf",
               "كوفية قطنية",
               "Keffieh en coton",
               "Classic weave, generous size.",
               "نسيج كلاسيكي، مقاس واسع.",
               "Tissage classique, grande taille.",
               8.00, 50, "Clothes"),
            _p("Linen Summer Shirt",
               "قميص كتان صيفي",
               "Chemise d'été en lin",
               "Breathable, relaxed fit, coconut buttons.",
               "قابل للتهوية، قصّة مريحة، أزرار من جوز الهند.",
               "Respirante, coupe décontractée, boutons en coco.",
               22.00, 20, "Clothes"),
            _p("Hand-Knit Wool Scarf",
               "وشاح صوف محبوك يدوياً",
               "Écharpe en laine tricotée à la main",
               "Undyed highland wool.",
               "صوف جبلي غير مصبوغ.",
               "Laine de montagne non teinte.",
               15.50, 0, "Clothes"),
            _p("Full-Grain Leather Belt",
               "حزام جلد طبيعي كامل الحبيبات",
               "Ceinture en cuir pleine fleur",
               "Vegetable-tanned, solid brass buckle.",
               "مدبوغ نباتياً، إبزيم من النحاس الصلب.",
               "Tannage végétal, boucle en laiton massif.",
               18.00, 15, "Clothes"),
        ),
    },
    {
        "vendor_email": "vendor.saida@cedarlink.demo",
        "vendor_name": ("Rami", "Haidar"),
        "phone": "+961 3 100 003",
        "store": "Saida Electronics",
        "city": "Saida",
        "description": "Everyday electronics and accessories, tested "
        "before they ship.",
        "inside_fee": 3.00,
        "outside_fee": 6.00,
        "active": True,
        "products": (
            _p("USB-C Fast Charger 30W",
               "شاحن سريع USB-C بقوة ٣٠ واط",
               "Chargeur rapide USB-C 30 W",
               "Compact GaN charger, foldable pins.",
               "شاحن GaN مدمج، أطراف قابلة للطي.",
               "Chargeur GaN compact, broches pliables.",
               14.99, 35, "Electronics"),
            _p("Wireless Earbuds (BT 5.3)",
               "سماعات لاسلكية (بلوتوث ٥٫٣)",
               "Écouteurs sans fil (BT 5.3)",
               "In-ear, USB-C case, ~6h per charge.",
               "داخل الأذن، علبة USB-C، نحو ٦ ساعات لكل شحنة.",
               "Intra-auriculaires, boîtier USB-C, ~6 h par charge.",
               29.90, 22, "Electronics"),
            _p("Power Bank 10000mAh",
               "بطارية متنقلة ١٠٠٠٠ مللي أمبير",
               "Batterie externe 10000 mAh",
               "Dual output, pass-through charging.",
               "مخرجان، شحن متزامن أثناء التوصيل.",
               "Double sortie, charge simultanée.",
               24.50, 16, "Electronics"),
            _p("LED Desk Lamp (Dimmable)",
               "مصباح مكتب LED (قابل لخفت الإضاءة)",
               "Lampe de bureau LED (variable)",
               "Three colour temperatures, USB port in the base.",
               "ثلاث درجات حرارة لونية، منفذ USB في القاعدة.",
               "Trois températures de couleur, port USB dans la base.",
               19.00, 10, "Electronics"),
            _p("Braided HDMI Cable 2m",
               "كابل HDMI مجدول ٢ متر",
               "Câble HDMI tressé 2 m",
               "4K/60Hz, gold-plated ends.",
               "دقة 4K‏/60 هرتز، أطراف مطلية بالذهب.",
               "4K/60 Hz, embouts plaqués or.",
               6.75, 40, "Electronics"),
            _p("\"Arabic Grammar Made Simple\"",
               "«قواعد اللغة العربية بيُسر»",
               "« La grammaire arabe simplifiée »",
               "A workbook for adult learners.",
               "كتاب تمارين للمتعلمين البالغين.",
               "Un cahier d'exercices pour apprenants adultes.",
               9.50, 25, "Books"),
        ),
    },
    {
        "vendor_email": "vendor.jounieh@cedarlink.demo",
        "vendor_name": ("Maya", "Rizk"),
        "phone": "+961 3 100 004",
        "store": "Jounieh Beauty Bar",
        "city": "Jounieh",
        "description": "Small-batch skincare and bath goods. (Store "
        "currently deactivated.)",
        "inside_fee": 2.50,
        "outside_fee": 5.50,
        "active": False,
        "products": (
            _p("Damascus Rose Water Toner 200ml",
               "تونر ماء ورد دمشقي ٢٠٠ مل",
               "Tonique à l'eau de rose de Damas 200 ml",
               "Single-ingredient, steam-distilled.",
               "مكوّن واحد، مقطّر بالبخار.",
               "Ingrédient unique, distillé à la vapeur.",
               7.50, 28, "Beauty"),
            _p("Pure Argan Hair Oil 100ml",
               "زيت أركان نقي للشعر ١٠٠ مل",
               "Huile d'argan pure pour cheveux 100 ml",
               "Cold-pressed, unscented.",
               "معصور على البارد، دون رائحة.",
               "Pressée à froid, sans parfum.",
               16.00, 14, "Beauty"),
            _p("Olive & Laurel Aleppo Soap",
               "صابون حلب بالزيتون والغار",
               "Savon d'Alep à l'olive et au laurier",
               "Traditional cure, ~20% laurel.",
               "تجفيف تقليدي، نحو ٢٠٪ من زيت الغار.",
               "Séchage traditionnel, ~20 % de laurier.",
               4.00, 45, "Beauty"),
        ),
    },
)

_CUSTOMER_SPECS = (
    {
        "email": "customer.rania@cedarlink.demo",
        "name": ("Rania", "Haddad"),
        "phone": "+961 3 200 001",
        "addresses": (
            ("Home", "Rue Gouraud, Gemmayzeh, Building 12", "Beirut", True),
            ("Work", "Charles Helou Ave, Office 4B", "Beirut", False),
        ),
    },
    {
        "email": "customer.karim@cedarlink.demo",
        "name": ("Karim", "Nassar"),
        "phone": "+961 3 200 002",
        "addresses": (
            ("Home", "Rue Mar Maroun, near the port", "Jounieh", True),
        ),
    },
    {
        "email": "customer.lina@cedarlink.demo",
        "name": ("Lina", "Fares"),
        "phone": "+961 3 200 003",
        "addresses": (
            ("Home", "Azmi Street, Building Andraos", "Tripoli", True),
        ),
    },
)

# customer index, store name, status, ((product name, qty), ...), days ago
_ORDER_SPECS = (
    (0, "Hamra Grocery", "delivered",
     (("Lebanese Extra Virgin Olive Oil 1L", 1), ("Zaatar Blend 200g", 2)),
     9),
    (0, "Saida Electronics", "pending",
     (("Wireless Earbuds (BT 5.3)", 1),), 0),
    (1, "Tripoli Threads", "processing",
     (("Linen Summer Shirt", 1), ("Full-Grain Leather Belt", 1)), 2),
    (1, "Hamra Grocery", "canceled",
     (("Arabic Coffee with Cardamom 250g", 1),), 5),
    (2, "Tripoli Threads", "delivered",
     (("Cotton Keffiyeh Scarf", 3),), 14),
    (2, "Saida Electronics", "processing",
     (("Power Bank 10000mAh", 1), ("Braided HDMI Cable 2m", 2)), 1),
)


def _refuse_in_production():
    if os.getenv("FLASK_CONFIG", "").strip().lower() == "production":
        raise click.ClickException(
            "`flask seed` is disabled when FLASK_CONFIG=production."
        )


def _get_or_create(model, defaults=None, **filters):
    instance = model.query.filter_by(**filters).first()

    if instance is not None:
        return instance, False

    params = dict(filters)
    params.update(defaults or {})

    instance = model(**params)
    db.session.add(instance)

    return instance, True


def _get_or_create_user(email, first_name, last_name, phone, role):
    user = User.query.filter_by(email=email).first()

    if user is not None:
        return user, False

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=generate_password_hash(DEMO_PASSWORD),
        phone=phone,
        role=role,
        is_verified=True,
        verification_method="email",
    )
    db.session.add(user)

    return user, True


def _placeholder_image(text, color):
    from PIL import Image, ImageDraw, ImageFont

    width, height = 800, 600
    image = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=44)

    lines = []
    line = ""

    for word in text.split():
        candidate = f"{line} {word}".strip()

        if draw.textlength(candidate, font=font) <= width - 80:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word

    if line:
        lines.append(line)

    line_height = 58
    start_y = (height - len(lines) * line_height) // 2

    for index, line in enumerate(lines):
        text_width = draw.textlength(line, font=font)
        draw.text(
            ((width - text_width) / 2, start_y + index * line_height),
            line,
            fill="white",
            font=font,
        )

    return image


def _save_product_image(product, color):
    filename = f"{uuid.uuid4().hex}.png"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

    _placeholder_image(product.name, color).save(path, format="PNG")

    db.session.add(
        ProductImage(image_url=filename, product_id=product.id)
    )


def _seed_order(customer, store, status, line_items, days_ago):
    from datetime import datetime, timedelta, timezone

    address = customer.addresses[0] if customer.addresses else None
    delivery_city = address.city if address else store.location
    delivery_address = (
        address.address_line if address else "Main Street"
    )

    subtotal = sum(
        float(product.price) * quantity
        for product, quantity in line_items
    )

    if delivery_city.strip().lower() == store.location.strip().lower():
        delivery_fee = float(store.inside_city_delivery_fee)
    else:
        delivery_fee = float(store.outside_city_delivery_fee)

    placed_at = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) - timedelta(days=days_ago)

    order = Order(
        user_id=customer.id,
        store_id=store.id,
        status=status,
        delivery_address=delivery_address,
        delivery_city=delivery_city,
        total_price=subtotal + delivery_fee,
        created_at=placed_at,
        updated_at=placed_at,
    )
    db.session.add(order)
    db.session.flush()

    for product, quantity in line_items:
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
            )
        )


@click.command("seed")
@with_appcontext
def seed():
    """Populate the database with a realistic demo marketplace.

    Idempotent — safe to run repeatedly; it fills in whatever is missing.
    Refuses to run when FLASK_CONFIG=production.
    """
    _refuse_in_production()

    # A demo admin so the admin console is reachable straight from the seed.
    # `_refuse_in_production` keeps this out of real deployments; admins there
    # are still CLI-only via `flask create-admin`.
    _get_or_create_user(
        ADMIN_EMAIL, "Site", "Admin", "+961 1 000 000", "admin"
    )
    db.session.flush()

    categories = {}
    for name_en, name_ar, name_fr in _CATEGORY_SPECS:
        category, _ = _get_or_create(
            Category,
            {
                "name_ar": name_ar,
                "name_fr": name_fr,
                "description": f"{name_en} from local Lebanese stores.",
            },
            name_en=name_en,
        )
        # Backfill translations onto a category that predates C.5.
        category.name_ar = category.name_ar or name_ar
        category.name_fr = category.name_fr or name_fr
        categories[name_en] = category

    db.session.flush()

    products = {}
    color_index = 0

    for spec in _STORE_SPECS:
        vendor, _ = _get_or_create_user(
            spec["vendor_email"],
            spec["vendor_name"][0],
            spec["vendor_name"][1],
            spec["phone"],
            "vendor",
        )
        db.session.flush()

        store, _ = _get_or_create(
            Store,
            {
                "description": spec["description"],
                "location": spec["city"],
                "contact_info": spec["vendor_email"],
                "is_active": spec["active"],
                # Demo stores skip the approval queue.
                "approval_status": "approved",
                "inside_city_delivery_fee": spec["inside_fee"],
                "outside_city_delivery_fee": spec["outside_fee"],
                "delivery_available": True,
            },
            owner_id=vendor.id,
            name=spec["store"],
        )
        db.session.flush()

        for item in spec["products"]:
            name = item["name"]
            description = item["description"]
            product, _ = _get_or_create(
                Product,
                {
                    "name_ar": name["ar"],
                    "name_fr": name["fr"],
                    "description_en": description["en"],
                    "description_ar": description["ar"],
                    "description_fr": description["fr"],
                    "price": item["price"],
                    "stock": item["stock"],
                    "category_id": categories[item["category"]].id,
                },
                store_id=store.id,
                name_en=name["en"],
            )
            # Backfill translations onto a product that predates C.5.
            product.name_ar = product.name_ar or name["ar"]
            product.name_fr = product.name_fr or name["fr"]
            product.description_ar = product.description_ar or description["ar"]
            product.description_fr = product.description_fr or description["fr"]
            products[name["en"]] = product

    db.session.flush()

    for product in products.values():
        if not product.images:
            _save_product_image(
                product,
                _IMAGE_COLORS[color_index % len(_IMAGE_COLORS)],
            )
            color_index += 1

    customers = []

    for spec in _CUSTOMER_SPECS:
        customer, _ = _get_or_create_user(
            spec["email"],
            spec["name"][0],
            spec["name"][1],
            spec["phone"],
            "customer",
        )
        db.session.flush()
        customers.append(customer)

        if not customer.addresses:
            for label, line, city, is_default in spec["addresses"]:
                db.session.add(
                    Address(
                        user_id=customer.id,
                        label=label,
                        recipient_name=(
                            f"{customer.first_name} {customer.last_name}"
                        ),
                        phone=customer.phone,
                        address_line=line,
                        city=city,
                        is_default=is_default,
                    )
                )

    db.session.flush()

    stores_by_name = {
        store.name: store for store in Store.query.all()
    }

    for (
        customer_index,
        store_name,
        status,
        line_item_specs,
        days_ago,
    ) in _ORDER_SPECS:
        customer = customers[customer_index]

        if customer.orders:
            continue

        line_items = [
            (products[name], quantity)
            for name, quantity in line_item_specs
        ]
        _seed_order(
            customer,
            stores_by_name[store_name],
            status,
            line_items,
            days_ago,
        )

    db.session.commit()

    click.echo("")
    click.echo("=" * 64)
    click.echo("CedarLink demo data is ready.")
    click.echo("")
    click.echo(f"Admin      (password: {DEMO_PASSWORD})")
    click.echo(f"  {ADMIN_EMAIL}")
    click.echo("")
    click.echo(f"Vendors    (password: {DEMO_PASSWORD})")
    for spec in _STORE_SPECS:
        flag = "" if spec["active"] else "  [store deactivated]"
        click.echo(
            f"  {spec['vendor_email']:<32} {spec['store']:<20} "
            f"{spec['city']}{flag}"
        )

    click.echo("")
    click.echo(f"Customers  (password: {DEMO_PASSWORD})")
    for spec in _CUSTOMER_SPECS:
        click.echo(
            f"  {spec['email']:<32} "
            f"{spec['name'][0]} {spec['name'][1]}"
        )

    click.echo("")
    click.echo(
        "Logging in sends a 6-digit code. With MAIL_SUPPRESS_SEND=true "
        "(the .env.example"
    )
    click.echo(
        "default) the code is printed to the Flask server console."
    )
    click.echo("=" * 64)


def register_cli(app):
    app.cli.add_command(create_admin)
    app.cli.add_command(seed)
