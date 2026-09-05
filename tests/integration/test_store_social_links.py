"""Store social and contact links.

The stored value is an href on a public page, so the two things worth
guarding are that it is built from the vendor's input rather than being it
(normalisation), and that no scheme a browser would execute can ever reach
the column (validation). Both live in ``store_service``, not in the form:
the form is bypassed by calling the endpoint.
"""

import pytest

from app.models.store_social_link import StoreSocialLink
from app.services import store_service
from app.services.store_service import SocialLinkError


def _put(client, auth, store, links, user=None):
    return client.put(
        f"/api/stores/{store.id}/social-links",
        json={"social_links": links},
        headers=auth(user or store.owner),
    )


def _link(platform, value):
    return {"platform": platform, "value": value}


# --------------------------------------------------------------------------- #
# Normalisation — every way a vendor might type it lands on one value
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "platform,expected,variants",
    [
        (
            "instagram",
            "https://www.instagram.com/hamragrocery",
            (
                "hamragrocery",
                "@hamragrocery",
                "  @hamragrocery  ",
                "instagram.com/hamragrocery",
                "www.instagram.com/hamragrocery",
                "https://instagram.com/hamragrocery",
                "https://www.instagram.com/hamragrocery/",
                "https://www.instagram.com/hamragrocery?igshid=Zm9vYmFy",
            ),
        ),
        (
            "facebook",
            "https://www.facebook.com/HamraGrocery",
            (
                "HamraGrocery",
                "@HamraGrocery",
                "facebook.com/HamraGrocery",
                "https://www.facebook.com/HamraGrocery/",
                "https://fb.com/HamraGrocery",
                "https://m.facebook.com/HamraGrocery",
            ),
        ),
        (
            "tiktok",
            "https://www.tiktok.com/@hamra.grocery",
            (
                "hamra.grocery",
                "@hamra.grocery",
                "tiktok.com/@hamra.grocery",
                "www.tiktok.com/@hamra.grocery",
                "https://www.tiktok.com/@hamra.grocery",
                "https://www.tiktok.com/@hamra.grocery/",
            ),
        ),
        (
            "whatsapp",
            "https://wa.me/9613100001",
            (
                "+961 3 100 001",
                "+961-3-100-001",
                "961 3 100 001",
                "00961 3 100 001",
                "9613100001",
                "(961) 3 100 001",
            ),
        ),
        (
            "website",
            "https://hamragrocery.com/",
            (
                "hamragrocery.com",
                "  hamragrocery.com ",
                "https://hamragrocery.com",
                "https://hamragrocery.com/",
                "HTTPS://HamraGrocery.com",
            ),
        ),
        (
            "email",
            "mailto:hello@hamragrocery.com",
            (
                "hello@hamragrocery.com",
                "  hello@hamragrocery.com",
                "mailto:hello@hamragrocery.com",
            ),
        ),
        (
            "phone",
            "tel:+9611340000",
            (
                "+961 1 340 000",
                "961 1 340 000",
                "00961 1 340 000",
                "+961-1-340-000",
            ),
        ),
    ],
)
def test_every_input_variant_normalises_to_the_same_value(
    platform, expected, variants
):
    produced = {
        store_service.normalize_social_value(platform, variant)
        for variant in variants
    }

    assert produced == {expected}


def test_an_http_website_is_not_silently_upgraded_to_https():
    """Preserved, not rewritten — a vendor's site may have no certificate."""
    assert store_service.normalize_social_value(
        "website", "http://hamragrocery.com"
    ) == "http://hamragrocery.com/"


def test_a_facebook_url_is_not_accepted_as_an_instagram_handle():
    with pytest.raises(SocialLinkError):
        store_service.normalize_social_value(
            "instagram", "https://www.facebook.com/HamraGrocery"
        )


@pytest.mark.parametrize(
    "value",
    ["03 100 001", "0961 3 100 001"],
)
def test_a_national_number_without_a_country_code_is_refused(value):
    with pytest.raises(SocialLinkError) as exc:
        store_service.normalize_social_value("whatsapp", value)

    assert "country code" in str(exc.value)


# --------------------------------------------------------------------------- #
# Scheme validation — the stored-XSS guard
# --------------------------------------------------------------------------- #

DANGEROUS = (
    "javascript:alert(1)",
    "JavaScript:alert(1)",
    "  javascript:alert(1)",
    "java\tscript:alert(1)",
    "data:text/html;base64,PHNjcmlwdD4=",
    "file:///etc/passwd",
    "vbscript:msgbox(1)",
)


@pytest.mark.parametrize("value", DANGEROUS)
@pytest.mark.parametrize(
    "platform",
    ["instagram", "facebook", "tiktok", "whatsapp", "website", "email",
     "phone"],
)
def test_a_dangerous_scheme_never_normalises(platform, value):
    with pytest.raises(SocialLinkError):
        store_service.normalize_social_value(platform, value)


@pytest.mark.parametrize("value", DANGEROUS)
def test_a_dangerous_scheme_is_rejected_with_400_and_stores_nothing(
    client, auth, make_store, value
):
    store = make_store()

    response = _put(client, auth, store, [_link("website", value)])

    assert response.status_code == 400
    assert StoreSocialLink.query.filter_by(store_id=store.id).count() == 0


def test_a_rejected_submission_does_not_disturb_the_existing_set(
    client, auth, make_store
):
    store = make_store()
    _put(client, auth, store, [_link("instagram", "@hamragrocery")])

    response = _put(
        client,
        auth,
        store,
        [
            _link("instagram", "@newhandle"),
            _link("website", "javascript:alert(1)"),
        ],
    )

    assert response.status_code == 400

    links = client.get(
        f"/api/stores/{store.id}/social-links"
    ).get_json()["social_links"]

    assert [link["value"] for link in links] == [
        "https://www.instagram.com/hamragrocery"
    ]


# --------------------------------------------------------------------------- #
# The endpoints
# --------------------------------------------------------------------------- #

def test_the_public_payload_carries_the_normalised_values(
    client, auth, make_store
):
    store = make_store()

    _put(
        client,
        auth,
        store,
        [
            _link("instagram", "@hamragrocery"),
            _link("whatsapp", "+961 3 100 001"),
            _link("email", "hello@hamragrocery.com"),
        ],
    )

    response = client.get(f"/api/stores/{store.id}/social-links")

    assert response.status_code == 200
    assert {
        link["platform"]: link["value"]
        for link in response.get_json()["social_links"]
    } == {
        "instagram": "https://www.instagram.com/hamragrocery",
        "whatsapp": "https://wa.me/9613100001",
        "email": "mailto:hello@hamragrocery.com",
    }


def test_the_public_payload_is_in_the_interface_order(
    client, auth, make_store
):
    store = make_store()

    _put(
        client,
        auth,
        store,
        [
            _link("phone", "+961 1 340 000"),
            _link("instagram", "@hamragrocery"),
            _link("website", "hamragrocery.com"),
        ],
    )

    links = client.get(
        f"/api/stores/{store.id}/social-links"
    ).get_json()["social_links"]

    assert [link["platform"] for link in links] == [
        "instagram",
        "website",
        "phone",
    ]


def test_a_non_owner_cannot_write(client, auth, make_store, make_user):
    store = make_store()
    intruder = make_user("vendor")

    response = _put(
        client,
        auth,
        store,
        [_link("instagram", "@notmine")],
        user=intruder,
    )

    assert response.status_code == 403
    assert StoreSocialLink.query.filter_by(store_id=store.id).count() == 0


def test_a_customer_cannot_write(client, auth, make_store, make_user):
    store = make_store()

    response = _put(
        client,
        auth,
        store,
        [_link("instagram", "@notmine")],
        user=make_user("customer"),
    )

    assert response.status_code == 403


def test_the_same_platform_twice_in_one_request_is_refused(
    client, auth, make_store
):
    store = make_store()

    response = _put(
        client,
        auth,
        store,
        [
            _link("instagram", "@one"),
            _link("instagram", "@two"),
        ],
    )

    assert response.status_code == 400
    assert StoreSocialLink.query.filter_by(store_id=store.id).count() == 0


def test_two_stores_may_each_have_the_same_platform(
    client, auth, make_store
):
    """The unique constraint is per store, not global."""
    first = make_store()
    second = make_store()

    assert _put(
        client, auth, first, [_link("instagram", "@first")]
    ).status_code == 200
    assert _put(
        client, auth, second, [_link("instagram", "@second")]
    ).status_code == 200


def test_replacing_an_overlapping_set_does_not_raise_an_integrity_error(
    client, auth, make_store
):
    """The bug that broke ``set_interests``: INSERT is flushed before DELETE,
    so re-sending a platform the store already has collides with a row that
    is still there. The service diffs instead of clearing and recreating."""
    store = make_store()

    first = _put(
        client,
        auth,
        store,
        [
            _link("instagram", "@hamragrocery"),
            _link("facebook", "HamraGrocery"),
            _link("phone", "+961 1 340 000"),
        ],
    )
    assert first.status_code == 200

    # Instagram unchanged, facebook changed, phone dropped, website added.
    second = _put(
        client,
        auth,
        store,
        [
            _link("instagram", "@hamragrocery"),
            _link("facebook", "HamraGrocer"),
            _link("website", "hamragrocery.com"),
        ],
    )
    assert second.status_code == 200

    assert {
        link["platform"]: link["value"]
        for link in second.get_json()["social_links"]
    } == {
        "instagram": "https://www.instagram.com/hamragrocery",
        "facebook": "https://www.facebook.com/HamraGrocer",
        "website": "https://hamragrocery.com/",
    }


def test_an_untouched_link_keeps_its_row(client, auth, make_store):
    """Diffed, not recreated — so created_at stays honest."""
    store = make_store()

    _put(client, auth, store, [_link("instagram", "@hamragrocery")])
    original = StoreSocialLink.query.filter_by(
        store_id=store.id, platform="instagram"
    ).one()
    original_id, original_created = original.id, original.created_at

    _put(
        client,
        auth,
        store,
        [
            _link("instagram", "@hamragrocery"),
            _link("website", "hamragrocery.com"),
        ],
    )

    kept = StoreSocialLink.query.filter_by(
        store_id=store.id, platform="instagram"
    ).one()

    assert kept.id == original_id
    assert kept.created_at == original_created


def test_a_blank_value_clears_that_platform(client, auth, make_store):
    """How the vendor form deletes a link: it empties the field."""
    store = make_store()
    _put(client, auth, store, [_link("instagram", "@hamragrocery")])

    response = _put(client, auth, store, [_link("instagram", "   ")])

    assert response.status_code == 200
    assert response.get_json()["social_links"] == []


def test_an_empty_list_clears_everything(client, auth, make_store):
    store = make_store()
    _put(
        client,
        auth,
        store,
        [_link("instagram", "@x"), _link("phone", "+961 1 340 000")],
    )

    assert _put(client, auth, store, []).get_json()["social_links"] == []
    assert StoreSocialLink.query.filter_by(store_id=store.id).count() == 0


def test_an_unknown_platform_is_refused(client, auth, make_store):
    store = make_store()

    response = _put(client, auth, store, [_link("linkedin", "cedarlink")])

    assert response.status_code == 400


def test_links_are_not_public_for_a_store_customers_cannot_see(
    client, auth, make_store
):
    store = make_store(approval_status="pending")

    assert client.get(
        f"/api/stores/{store.id}/social-links"
    ).status_code == 404
