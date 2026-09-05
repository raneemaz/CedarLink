"""Assigning a driver to an order, and moving that delivery forward.

Everything the delivery routes used to do inline lives here, so that the
seed — and anything else that needs a delivery without going through HTTP —
runs the same rules a vendor's request does: one assignment per order, the
`assigned → picked_up → delivered` walk with no skipping, the delivered
timestamp, and the customer notification on every step.

The one rule worth naming is :func:`may_disclose_phone`. The driver's number
belongs to a third party, so it is released to the customer only while the
delivery is still in progress and withdrawn once it is done; the vendor, who
is the driver's employer, keeps it. See ADR 0019.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.models.delivery_assignment import DeliveryAssignment
from app.services.notification_service import notify_delivery_update


# The only forward moves. A status with no entry here is terminal.
DELIVERY_STATUS_TRANSITIONS = {
    "assigned": "picked_up",
    "picked_up": "delivered",
}


class DeliveryError(Exception):
    """A delivery operation that failed a business rule.

    Carries the HTTP status and the JSON body the route returns verbatim,
    the same way ``OrderError`` does.
    """

    def __init__(self, message, status_code=400, **extra):
        super().__init__(message)
        self.status_code = status_code
        self.payload = {"error": message, **extra}


def _utcnow():
    """Naive UTC, matching the columns on ``DeliveryAssignment``."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def may_disclose_phone(assignment, *, is_vendor):
    """Whether this caller may be shown the driver's phone number (ADR 0019).

    The vendor always may. The customer may while the delivery is in
    progress, and not once it has been delivered — the number was released
    to solve a problem that no longer exists.
    """
    return is_vendor or assignment.status != "delivered"


def assign_driver(order, driver_name, driver_phone):
    """Put a named driver on an order. One assignment per order, ever."""
    driver_name = str(driver_name or "").strip()
    driver_phone = str(driver_phone or "").strip()

    if not driver_name:
        raise DeliveryError("driver_name is required")

    if not driver_phone:
        raise DeliveryError("driver_phone is required")

    existing = DeliveryAssignment.query.filter_by(order_id=order.id).first()

    if existing is not None:
        raise DeliveryError(
            "Delivery assignment already exists for this order",
            status_code=409,
        )

    assignment = DeliveryAssignment(
        order_id=order.id,
        driver_name=driver_name,
        driver_phone=driver_phone,
        status="assigned",
        assigned_at=_utcnow(),
    )

    db.session.add(assignment)
    db.session.commit()

    # After the commit, never before: a failed notification must not undo
    # the assignment.
    notify_delivery_update(order, "assigned")

    return assignment


def advance_status(assignment, order, new_status):
    """Move a delivery one step along, or refuse."""
    expected = DELIVERY_STATUS_TRANSITIONS.get(assignment.status)

    if expected is None:
        raise DeliveryError(
            f"Delivery with status '{assignment.status}' cannot be updated"
        )

    if new_status != expected:
        raise DeliveryError(
            "Invalid delivery status transition",
            current_status=assignment.status,
            allowed_next_status=expected,
        )

    assignment.status = new_status

    if new_status == "delivered":
        assignment.delivered_at = _utcnow()

    db.session.commit()

    notify_delivery_update(order, assignment.status)

    return assignment
