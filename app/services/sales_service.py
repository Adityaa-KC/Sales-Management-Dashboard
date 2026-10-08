import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    Customer,
    Inventory,
    Product,
    Sale,
    SaleItem,
)


def create_sale(
    session: Session,
    store_id,
    customer_id,
    items: list[dict],
):
    """
    Create a sale and update inventory atomically.

    items format:
    [
        {
            "product_id": product_uuid,
            "quantity": 2
        },
        ...
    ]

    Returns:
        Sale object

    Raises:
        ValueError for invalid sales or insufficient stock.
    """

    if not items:
        raise ValueError("Sale must contain at least one item.")

    # ---------------------------------------------------------
    # 1. Verify customer
    # ---------------------------------------------------------

    customer = session.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.store_id == store_id,
        )
    ).scalar_one_or_none()

    if customer is None:
        raise ValueError("Customer not found.")

    # ---------------------------------------------------------
    # 2. Prepare sale totals
    # ---------------------------------------------------------

    subtotal = Decimal("0.00")

    prepared_items = []

    # ---------------------------------------------------------
    # 3. Validate every product and inventory quantity
    # ---------------------------------------------------------

    for item in items:

        product_id = item["product_id"]
        quantity = int(item["quantity"])

        if quantity <= 0:
            raise ValueError(
                "Product quantity must be greater than zero."
            )

        # Lock inventory row during this transaction.
        inventory = session.execute(
            select(Inventory)
            .where(
                Inventory.product_id == product_id,
                Inventory.store_id == store_id,
            )
            .with_for_update()
        ).scalar_one_or_none()

        if inventory is None:
            raise ValueError(
                f"Inventory not found for product {product_id}."
            )

        # -----------------------------------------------------
        # 4. Check stock
        # -----------------------------------------------------

        if inventory.quantity_on_hand < quantity:
            raise ValueError(
                f"Insufficient stock. "
                f"Available: {inventory.quantity_on_hand}, "
                f"Requested: {quantity}."
            )

        # -----------------------------------------------------
        # 5. Get product
        # -----------------------------------------------------

        product = session.execute(
            select(Product).where(
                Product.id == product_id,
                Product.store_id == store_id,
                Product.is_active.is_(True),
            )
        ).scalar_one_or_none()

        if product is None:
            raise ValueError(
                f"Product {product_id} not found or inactive."
            )

        # -----------------------------------------------------
        # 6. Calculate line total
        # -----------------------------------------------------

        unit_price = Decimal(product.selling_price)
        line_total = unit_price * quantity

        subtotal += line_total

        prepared_items.append(
            {
                "product": product,
                "inventory": inventory,
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )

    # ---------------------------------------------------------
    # 7. Create Sale
    # ---------------------------------------------------------

    sale = Sale(
        store_id=store_id,
        customer_id=customer_id,
        sale_number=f"SALE-{uuid.uuid4().hex.upper()}",
        status="completed",
        subtotal=subtotal,
        discount=Decimal("0.00"),
        total_amount=subtotal,
    )

    session.add(sale)
    session.flush()

    # ---------------------------------------------------------
    # 8. Create SaleItems + update inventory
    # ---------------------------------------------------------

    for item in prepared_items:

        sale_item = SaleItem(
            sale_id=sale.id,
            store_id=store_id,
            product_id=item["product"].id,
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            line_total=item["line_total"],
        )

        session.add(sale_item)

        # Decrease inventory.
        item["inventory"].quantity_on_hand -= item["quantity"]

    # ---------------------------------------------------------
    # 9. Commit everything together
    # ---------------------------------------------------------

    session.commit()

    # Refresh the object from PostgreSQL.
    session.refresh(sale)

    return sale