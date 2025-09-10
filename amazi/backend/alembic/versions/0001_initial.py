"""initial tables

Revision ID: 0001_initial
Revises: 
Create Date: 2025-09-10

"""
from alembic import op
import sqlalchemy as sa


revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('timezone', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_table(
        'employees',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=128)),
        sa.Column('email', sa.String(length=255)),
        sa.Column('phone', sa.String(length=64)),
        sa.Column('wage', sa.Float()),
        sa.Column('min_hours', sa.Float()),
        sa.Column('max_hours', sa.Float()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_table(
        'timesheet_uploads',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_url', sa.String(length=1024), nullable=False),
        sa.Column('file_type', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_table(
        'extraction_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('upload_id', sa.Integer(), sa.ForeignKey('timesheet_uploads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('result_json', sa.JSON(), nullable=False),
        sa.Column('confidence_summary', sa.JSON()),
        sa.Column('needs_review', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_table(
        'shifts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('org_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.id', ondelete='SET NULL')),
        sa.Column('role', sa.String(length=128)),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('unpaid_break_min', sa.Integer()),
        sa.Column('status', sa.String(length=64)),
        sa.Column('evidence', sa.JSON()),
    )


def downgrade() -> None:
    op.drop_table('shifts')
    op.drop_table('extraction_runs')
    op.drop_table('timesheet_uploads')
    op.drop_table('employees')
    op.drop_table('organizations')

