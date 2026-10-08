from decimal import Decimal
import sys
from sqlalchemy import select
from sqlalchemy.orm import Session
from pathlib import Path    

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.connection import get_engine
from app.database.models import (
    Store,
    Category,
    Product,
    Customer,
    Inventory,
)
from app.services.sales_service import create_sale


def main():

    print("=" * 60)
    print("SMART RETAIL - DEMO DATA SEED")
    print("=" * 60)

    engine = get_engine()

    with Session(engine) as session:

        # ------------------------------------------------------
        # 1. Store
        # ------------------------------------------------------

        store = session.execute(
            select(Store).where(
                Store.name == "SmartRetail Demo Store"
            )
        ).scalar_one_or_none()

        if store:
            print("Demo store already exists.")
            print("Delete it manually if you want a fresh dataset.")
            return

        store = Store(
            name="SmartRetail Demo Store",
            currency="INR",
        )

        session.add(store)
        session.flush()

        print("Created store.")

        # ------------------------------------------------------
        # 2. Category
        # ------------------------------------------------------

        category = Category(
            store_id=store.id,
            name="General Retail",
        )

        session.add(category)
        session.flush()

        # ------------------------------------------------------
        # 3. Products
        # ------------------------------------------------------

        products_data = [
            ("P001", "Laptop", 60000, 40000, 10, 35),
            ("P002", "Wireless Mouse", 800, 450, 20, 75),
            ("P003", "Keyboard", 1500, 900, 15, 42),
            ("P004", "USB Cable", 500, 250, 25, 12),
            ("P005", "Headphones", 2500, 1400, 10, 28),
        ]

        products = {}

        for sku, name, selling, cost, reorder, stock in products_data:

            product = Product(
                store_id=store.id,
                category_id=category.id,
                sku=sku,
                name=name,
                selling_price=Decimal(str(selling)),
                cost_price=Decimal(str(cost)),
                reorder_level=reorder,
                is_active=True,
            )

            session.add(product)
            session.flush()

            inventory = Inventory(
                store_id=store.id,
                product_id=product.id,
                quantity_on_hand=stock,
            )

            session.add(inventory)

            products[sku] = product

        # ------------------------------------------------------
        # 4. Customers
        # ------------------------------------------------------

        customers = []

        customer_data = [
            ("Rahul Sharma", "rahul@example.com"),
            ("Priya Singh", "priya@example.com"),
            ("Aman Verma", "aman@example.com"),
            ("Neha Gupta", "neha@example.com"),
            ("Rohit Kumar", "rohit@example.com"),
        ]

        for name, email in customer_data:

            customer = Customer(
                store_id=store.id,
                name=name,
                email=email,
            )

            session.add(customer)
            session.flush()

            customers.append(customer)

        session.commit()

        print("Created products and customers.")

        # ------------------------------------------------------
        # 5. Create sales
        # ------------------------------------------------------

        sales = [
            (customers[0], "P001", 1),
            (customers[0], "P002", 2),
            (customers[1], "P005", 2),
            (customers[1], "P002", 3),
            (customers[2], "P003", 2),
            (customers[2], "P004", 4),
            (customers[3], "P001", 1),
            (customers[4], "P005", 3),
            (customers[4], "P003", 1),
        ]

        for customer, sku, quantity in sales:

            sale = create_sale(
                session=session,
                store_id=store.id,
                customer_id=customer.id,
                items=[
                    {
                        "product_id": products[sku].id,
                        "quantity": quantity,
                    }
                ],
            )

            print(
                f"Sale created: "
                f"{customer.name} -> "
                f"{products[sku].name} x{quantity} "
                f"= ₹{sale.total_amount}"
            )

        print("\n" + "=" * 60)
        print("DEMO DATA CREATED SUCCESSFULLY")
        print("=" * 60)


if __name__ == "__main__":
    main()