"""restrict saved payment methods to cards

Revision ID: e1b9c4d2f7a6
Revises: b5fe5631dafe
Create Date: 2026-08-22 12:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "e1b9c4d2f7a6"
down_revision = "b5fe5631dafe"
branch_labels = None
depends_on = None


def upgrade():
    # Remove every non-card saved method. Keep historical payments, but
    # detach them from the saved methods being removed.
    op.execute(
        """
        UPDATE payments
        SET payment_method_id = NULL
        WHERE payment_method_id IN (
            SELECT id FROM payment_methods WHERE type <> 'card'
        )
        """
    )
    op.execute("DELETE FROM payment_methods WHERE type <> 'card'")


def downgrade():
    # The removed saved methods contain user data and cannot be restored.
    pass
