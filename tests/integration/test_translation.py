"""Product / category translation (C.5).

- a customer searching in Arabic finds a product whose Arabic name matches,
  whatever the interface language
- a product with no French translation falls back to English, never blank
- the vendor and admin write paths accept name_en/ar/fr
"""

from app.extensions import db
from app.models.category import Category
from app.models.product import Product


# --------------------------------------------------------------------------- #
# Search across every language column
# --------------------------------------------------------------------------- #

def test_search_finds_product_by_its_arabic_name(
    client, make_store, make_product
):
    store = make_store()
    make_product(
        store=store,
        name="Zaatar Blend",
        name_ar="خلطة زعتر بري",
    )
    make_product(store=store, name="Olive Oil", name_ar="زيت زيتون")

    resp = client.get("/api/products", query_string={"keyword": "خلطة زعتر"})

    assert resp.status_code == 200
    products = resp.get_json()["products"]
    assert [p["name_en"] for p in products] == ["Zaatar Blend"]
    assert products[0]["name_ar"] == "خلطة زعتر بري"


def test_search_matches_the_french_description(
    client, make_store, make_product
):
    store = make_store()
    make_product(
        store=store,
        name="Rose Water",
        description_fr="Distillé à la vapeur, un seul ingrédient.",
    )
    make_product(store=store, name="Argan Oil")

    resp = client.get("/api/products", query_string={"keyword": "vapeur"})

    names = [p["name_en"] for p in resp.get_json()["products"]]
    assert names == ["Rose Water"]


# --------------------------------------------------------------------------- #
# Fallback — never blank
# --------------------------------------------------------------------------- #

def test_product_without_french_falls_back_to_english(
    client, make_store, make_product
):
    store = make_store()
    product = make_product(store=store, name="Keffiyeh Scarf", name_ar="كوفية")

    # The list serializer exposes every translation; French is simply absent.
    listing = client.get("/api/products").get_json()["products"]
    row = next(p for p in listing if p["id"] == product.id)
    assert row["name_en"] == "Keffiyeh Scarf"
    assert row["name_fr"] is None
    assert row["name_ar"] == "كوفية"
    # `name` is the English-canonical alias — never blank.
    assert row["name"] == "Keffiyeh Scarf"

    # The model helper resolves a missing translation to English.
    assert product.localized_name("fr") == "Keffiyeh Scarf"
    assert product.localized_name("ar") == "كوفية"
    # A blank string counts as missing, not as a valid empty name.
    product.name_fr = "   "
    assert product.localized_name("fr") == "Keffiyeh Scarf"


def test_detail_endpoint_returns_all_translations(
    client, make_store, make_product
):
    store = make_store()
    product = make_product(
        store=store,
        name="Coffee 250g",
        name_ar="قهوة ٢٥٠ غرام",
        name_fr="Café 250 g",
        description_ar="تحميص متوسط.",
    )

    body = client.get(f"/api/products/{product.id}").get_json()

    assert body["name_en"] == "Coffee 250g"
    assert body["name_ar"] == "قهوة ٢٥٠ غرام"
    assert body["name_fr"] == "Café 250 g"
    assert body["description_ar"] == "تحميص متوسط."
    assert body["description_fr"] is None


# --------------------------------------------------------------------------- #
# Write paths accept translations
# --------------------------------------------------------------------------- #

def test_vendor_creates_and_edits_a_trilingual_product(
    client, auth, vendor, make_store, category
):
    store = make_store(owner=vendor)

    created = client.post(
        "/api/products",
        json={
            "name_en": "Pomegranate Molasses",
            "name_ar": "دبس رمان",
            "name_fr": "Mélasse de grenade",
            "description_en": "Thick, tart.",
            "price": 4.25,
            "stock": 10,
            "store_id": store.id,
            "category_id": category.id,
        },
        headers=auth(vendor),
    )
    assert created.status_code == 201
    product_id = created.get_json()["id"]

    stored = db.session.get(Product, product_id)
    assert stored.name_ar == "دبس رمان"
    assert stored.name_fr == "Mélasse de grenade"

    edited = client.put(
        f"/api/products/{product_id}",
        json={"name_fr": "Mélasse de grenade 500 ml", "name_ar": ""},
        headers=auth(vendor),
    )
    assert edited.status_code == 200

    stored = db.session.get(Product, product_id)
    assert stored.name_fr == "Mélasse de grenade 500 ml"
    assert stored.name_ar is None  # a blank value clears the translation
    assert stored.name_en == "Pomegranate Molasses"  # untouched


def test_vendor_cannot_create_a_product_without_an_english_name(
    client, auth, vendor, make_store, category
):
    store = make_store(owner=vendor)

    resp = client.post(
        "/api/products",
        json={
            "name_ar": "دبس رمان",
            "price": 4.25,
            "stock": 10,
            "store_id": store.id,
            "category_id": category.id,
        },
        headers=auth(vendor),
    )

    assert resp.status_code == 400


def test_admin_creates_a_trilingual_category(client, auth, admin):
    resp = client.post(
        "/api/categories",
        json={
            "name_en": "Food",
            "name_ar": "طعام",
            "name_fr": "Alimentation",
        },
        headers=auth(admin),
    )
    assert resp.status_code == 201

    listing = client.get("/api/categories").get_json()
    row = next(c for c in listing if c["name_en"] == "Food")
    assert row["name_ar"] == "طعام"
    assert row["name_fr"] == "Alimentation"

    stored = db.session.get(Category, row["id"])
    assert stored.localized_name("ar") == "طعام"
    assert stored.localized_name("fr") == "Alimentation"


def test_admin_category_name_clash_is_on_the_english_name(
    client, auth, admin, make_category
):
    make_category(name="Books")

    resp = client.post(
        "/api/categories",
        json={"name_en": "Books", "name_ar": "كتب"},
        headers=auth(admin),
    )

    assert resp.status_code == 400
