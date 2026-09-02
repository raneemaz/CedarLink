"""reviews table + product/store rating aggregates (C.3)

Generated with ``flask db migrate``, then trimmed to this feature: the
autogenerate run also surfaced pre-existing drift (composite notification
indexes replaced by simple ones in the model without a migration;
``payments.provider`` NOT NULL) that is not part of this change and is left
for its own fix.

New ``reviews`` table — a verified-purchase rating of exactly one product OR
one store, enforced by a CHECK. Two unique constraints, not one, because
``NULL != NULL`` hides same-order store-review duplicates from the
product-keyed index and vice versa. Indexes on ``product_id`` / ``store_id``
(every product and store page reads by them) and ``user_id``.

``products`` and ``stores`` each gain ``rating_avg`` (Numeric(3,2), nullable)
and ``rating_count`` (Integer, default 0), recomputed by ``review_service``.

See docs/decisions/0015-review-rating-aggregates.md.

Revision ID: a128e4a1eead
Revises: a1b2c3d4e5f6
Create Date: 2026-09-02 17:37:54.879452

"""
from alembic import op
import sqlalchemy as sa


revision = 'a128e4a1eead'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('store_id', sa.Integer(), nullable=True),
        sa.Column('rating', sa.SmallInteger(), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.String(length=20),
            server_default='published',
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            '(product_id IS NOT NULL AND store_id IS NULL) OR '
            '(product_id IS NULL AND store_id IS NOT NULL)',
            name='ck_reviews_exactly_one_target',
        ),
        sa.CheckConstraint(
            'rating >= 1 AND rating <= 5',
            name='ck_reviews_rating_range',
        ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.ForeignKeyConstraint(['store_id'], ['stores.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'order_id', 'product_id',
            name='uq_reviews_user_order_product',
        ),
        sa.UniqueConstraint(
            'user_id', 'order_id', 'store_id',
            name='uq_reviews_user_order_store',
        ),
    )
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.create_index(
            'ix_reviews_product_id', ['product_id'], unique=False
        )
        batch_op.create_index(
            'ix_reviews_store_id', ['store_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_reviews_user_id'), ['user_id'], unique=False
        )

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'rating_avg', sa.Numeric(precision=3, scale=2), nullable=True
        ))
        batch_op.add_column(sa.Column(
            'rating_count', sa.Integer(), server_default='0', nullable=False
        ))

    with op.batch_alter_table('stores', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'rating_avg', sa.Numeric(precision=3, scale=2), nullable=True
        ))
        batch_op.add_column(sa.Column(
            'rating_count', sa.Integer(), server_default='0', nullable=False
        ))


def downgrade():
    with op.batch_alter_table('stores', schema=None) as batch_op:
        batch_op.drop_column('rating_count')
        batch_op.drop_column('rating_avg')

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('rating_count')
        batch_op.drop_column('rating_avg')

    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reviews_user_id'))
        batch_op.drop_index('ix_reviews_store_id')
        batch_op.drop_index('ix_reviews_product_id')

    op.drop_table('reviews')
