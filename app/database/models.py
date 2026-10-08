import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="INR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    categories: Mapped[List["Category"]] = relationship(back_populates="store")
    products: Mapped[List["Product"]] = relationship(back_populates="store", foreign_keys="[Product.store_id]")
    customers: Mapped[List["Customer"]] = relationship(back_populates="store", foreign_keys="[Customer.store_id]")
    sales: Mapped[List["Sale"]] = relationship(back_populates="store", foreign_keys="[Sale.store_id]")
    suppliers: Mapped[List["Supplier"]] = relationship(back_populates="store", foreign_keys="[Supplier.store_id]")
    analysis_runs: Mapped[List["AnalysisRun"]] = relationship(back_populates="store")


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.stores.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    store: Mapped["Store"] = relationship(back_populates="categories")
    products: Mapped[List["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("selling_price >= 0", name="chk_products_selling_price"),
        CheckConstraint("cost_price >= 0", name="chk_products_cost_price"),
        CheckConstraint("reorder_level >= 0", name="chk_products_reorder_level"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.stores.id"), nullable=False)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("public.categories.id"), nullable=True)
    sku: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selling_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False, server_default="0")
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="10")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    store: Mapped["Store"] = relationship(back_populates="products", foreign_keys=[store_id])
    category: Mapped[Optional["Category"]] = relationship(back_populates="products")
    inventory: Mapped[Optional["Inventory"]] = relationship(back_populates="product", uselist=False)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.stores.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    store: Mapped["Store"] = relationship(back_populates="customers", foreign_keys=[store_id])
    sales: Mapped[List["Sale"]] = relationship(back_populates="customer", foreign_keys="[Sale.customer_id]")


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (
        CheckConstraint("quantity_on_hand >= 0", name="chk_inventory_quantity_on_hand"),
        {"schema": "public"},
    )

    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.stores.id"), primary_key=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.products.id"), primary_key=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="inventory")


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("status IN ('completed', 'voided')", name="chk_sales_status"),
        CheckConstraint("subtotal >= 0", name="chk_sales_subtotal"),
        CheckConstraint("discount >= 0", name="chk_sales_discount"),
        CheckConstraint("total_amount >= 0", name="chk_sales_total_amount"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.stores.id"), nullable=False)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("public.customers.id"), nullable=True)
    sale_number: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="completed")
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    subtotal: Mapped[Decimal] = mapped_column(Numeric, nullable=False, server_default="0")
    discount: Mapped[Decimal] = mapped_column(Numeric, nullable=False, server_default="0")
    total_amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False, server_default="0")

    # Relationships
    store: Mapped["Store"] = relationship(back_populates="sales", foreign_keys=[store_id])
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="sales", foreign_keys=[customer_id])
    items: Mapped[List["SaleItem"]] = relationship(back_populates="sale")


class SaleItem(Base):
    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_sale_items_quantity"),
        CheckConstraint("unit_price >= 0", name="chk_sale_items_unit_price"),
        CheckConstraint("line_total >= 0", name="chk_sale_items_line_total"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.sales.id"), nullable=False)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.stores.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric, nullable=False)

    # Relationships
    sale: Mapped["Sale"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('sale', 'purchase', 'return', 'adjustment', 'damage')",
            name="chk_inv_movement_type",
        ),
        CheckConstraint("quantity_change <> 0", name="chk_inv_movement_qty_change"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.stores.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.products.id"), nullable=False)
    sale_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("public.sales.id"), nullable=True)
    movement_type: Mapped[str] = mapped_column(String, nullable=False)
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    product: Mapped["Product"] = relationship()
    sale: Mapped[Optional["Sale"]] = relationship()


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.stores.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    store: Mapped["Store"] = relationship(back_populates="suppliers", foreign_keys=[store_id])
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship(back_populates="supplier")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'ordered', 'received', 'cancelled')",
            name="chk_po_status",
        ),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.stores.id"), nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.suppliers.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="draft")
    ordered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    supplier: Mapped["Supplier"] = relationship(back_populates="purchase_orders")
    items: Mapped[List["PurchaseOrderItem"]] = relationship(back_populates="purchase_order")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        CheckConstraint("quantity_ordered > 0", name="chk_poi_quantity_ordered"),
        CheckConstraint("unit_cost >= 0", name="chk_poi_unit_cost"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.purchase_orders.id"), nullable=False)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.stores.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.products.id"), nullable=False)
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    unit_cost: Mapped[Decimal] = mapped_column(Numeric, nullable=False)

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        CheckConstraint(
            "analysis_type IN ('market_basket', 'segmentation', 'forecast', 'recommendation')",
            name="chk_analysis_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="chk_analysis_status",
        ),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.stores.id"), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String, nullable=False)
    algorithm: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    data_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    store: Mapped["Store"] = relationship(back_populates="analysis_runs")


class AssociationRule(Base):
    __tablename__ = "association_rules"
    __table_args__ = (
        CheckConstraint("support >= 0 AND support <= 1", name="chk_ar_support"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="chk_ar_confidence"),
        CheckConstraint("lift >= 0", name="chk_ar_lift"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.analysis_runs.id"), nullable=False)
    antecedent_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.products.id"), nullable=False)
    consequent_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.products.id"), nullable=False)
    support: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    lift: Mapped[Decimal] = mapped_column(Numeric, nullable=False)

    # Relationships
    analysis_run: Mapped["AnalysisRun"] = relationship()
    antecedent_product: Mapped["Product"] = relationship(foreign_keys=[antecedent_product_id])
    consequent_product: Mapped["Product"] = relationship(foreign_keys=[consequent_product_id])


class CustomerSegment(Base):
    __tablename__ = "customer_segments"
    __table_args__ = (
        CheckConstraint("recency_days >= 0", name="chk_cs_recency_days"),
        CheckConstraint("frequency >= 0", name="chk_cs_frequency"),
        CheckConstraint("monetary >= 0", name="chk_cs_monetary"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.analysis_runs.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.customers.id"), nullable=False)
    recency_days: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    monetary: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    rfm_score: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    cluster_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    segment_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    analysis_run: Mapped["AnalysisRun"] = relationship()
    customer: Mapped["Customer"] = relationship()


class DemandForecast(Base):
    __tablename__ = "demand_forecasts"
    __table_args__ = (
        CheckConstraint("predicted_demand >= 0", name="chk_df_predicted_demand"),
        CheckConstraint("lower_bound IS NULL OR lower_bound >= 0", name="chk_df_lower_bound"),
        CheckConstraint("upper_bound IS NULL OR upper_bound >= 0", name="chk_df_upper_bound"),
        {"schema": "public"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.analysis_runs.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("public.products.id"), nullable=False)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    predicted_demand: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    lower_bound: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    upper_bound: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)

    # Relationships
    analysis_run: Mapped["AnalysisRun"] = relationship()
    product: Mapped["Product"] = relationship()