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
    Sale,
    SaleItem,
)


def main():

    print("=" * 70)
    print("SMART RETAIL - SQLALCHEMY ORM TEST")
    print("=" * 70)

    engine = get_engine()

    with Session(engine) as session:

        try:

            # ==========================================================
            # 1. CREATE TEST STORE
            # ==========================================================

            print("\n[1] Creating test store...")

            store = Store(
                name="ORM Test Store",
                currency="INR",
            )

            session.add(store)
            session.flush()

            print(f"SUCCESS: Store created")
            print(f"Store ID: {store.id}")

            # ==========================================================
            # 2. CREATE CATEGORY
            # ==========================================================

            print("\n[2] Creating test category...")

            category = Category(
                store_id=store.id,
                name="ORM Test Category",
            )

            session.add(category)
            session.flush()

            print(f"SUCCESS: Category created")
            print(f"Category ID: {category.id}")

            # ==========================================================
            # 3. CREATE PRODUCT
            # ==========================================================

            print("\n[3] Creating test product...")

            product = Product(
                store_id=store.id,
                category_id=category.id,
                sku="ORM-TEST-001",
                name="ORM Test Product",
                description="Temporary product for ORM testing",
                selling_price=Decimal("100.00"),
                cost_price=Decimal("60.00"),
                reorder_level=10,
                is_active=True,
            )

            session.add(product)
            session.flush()

            print("SUCCESS: Product created")
            print(f"Product ID: {product.id}")
            print(f"Product name: {product.name}")

            # ==========================================================
            # 4. CREATE CUSTOMER
            # ==========================================================

            print("\n[4] Creating test customer...")

            customer = Customer(
                store_id=store.id,
                name="ORM Test Customer",
                email="orm-test@example.com",
                phone="9999999999",
            )

            session.add(customer)
            session.flush()

            print("SUCCESS: Customer created")
            print(f"Customer ID: {customer.id}")

            # ==========================================================
            # 5. CREATE INVENTORY
            # ==========================================================

            print("\n[5] Creating inventory record...")

            inventory = Inventory(
                store_id=store.id,
                product_id=product.id,
                quantity_on_hand=50,
            )

            session.add(inventory)
            session.flush()

            print("SUCCESS: Inventory created")
            print(f"Initial stock: {inventory.quantity_on_hand}")

            # ==========================================================
            # 6. CREATE SALE
            # ==========================================================

            print("\n[6] Creating sale...")

            sale = Sale(
                store_id=store.id,
                customer_id=customer.id,
                sale_number="ORM-TEST-SALE-001",
                status="completed",
                subtotal=Decimal("200.00"),
                discount=Decimal("0.00"),
                total_amount=Decimal("200.00"),
            )

            session.add(sale)
            session.flush()

            print("SUCCESS: Sale created")
            print(f"Sale ID: {sale.id}")
            print(f"Sale number: {sale.sale_number}")

            # ==========================================================
            # 7. CREATE SALE ITEM
            # ==========================================================

            print("\n[7] Creating sale item...")

            sale_item = SaleItem(
                sale_id=sale.id,
                store_id=store.id,
                product_id=product.id,
                quantity=2,
                unit_price=Decimal("100.00"),
                line_total=Decimal("200.00"),
            )

            session.add(sale_item)
            session.flush()

            print("SUCCESS: Sale item created")
            print(f"Quantity: {sale_item.quantity}")
            print(f"Unit price: {sale_item.unit_price}")
            print(f"Line total: {sale_item.line_total}")

            # ==========================================================
            # 8. TEST RELATIONSHIPS
            # ==========================================================

            print("\n[8] Testing ORM relationships...")

            # Sale → Customer
            if sale.customer is not None:
                print(
                    f"SUCCESS: Sale → Customer → "
                    f"{sale.customer.name}"
                )
            else:
                raise Exception("Sale → Customer relationship failed")

            # Sale → Store
            if sale.store is not None:
                print(
                    f"SUCCESS: Sale → Store → "
                    f"{sale.store.name}"
                )
            else:
                raise Exception("Sale → Store relationship failed")

            # Sale → SaleItems
            if len(sale.items) == 1:
                print(
                    f"SUCCESS: Sale → SaleItems → "
                    f"{len(sale.items)} item"
                )
            else:
                raise Exception(
                    f"Expected 1 sale item, "
                    f"found {len(sale.items)}"
                )

            # SaleItem → Product
            if sale_item.product is not None:
                print(
                    f"SUCCESS: SaleItem → Product → "
                    f"{sale_item.product.name}"
                )
            else:
                raise Exception(
                    "SaleItem → Product relationship failed"
                )

            # Product → Inventory
            if product.inventory is not None:
                print(
                    f"SUCCESS: Product → Inventory → "
                    f"{product.inventory.quantity_on_hand} units"
                )
            else:
                raise Exception(
                    "Product → Inventory relationship failed"
                )

            # ==========================================================
            # 9. TEST DATABASE QUERY
            # ==========================================================

            print("\n[9] Testing SELECT query...")

            statement = (
                select(Sale)
                .where(Sale.sale_number == "ORM-TEST-SALE-001")
            )

            result = session.execute(statement)

            retrieved_sale = result.scalar_one()

            print("SUCCESS: Sale retrieved from PostgreSQL")

            print(f"Sale number: {retrieved_sale.sale_number}")
            print(f"Customer: {retrieved_sale.customer.name}")
            print(f"Store: {retrieved_sale.store.name}")

            # ==========================================================
            # 10. VERIFY CALCULATIONS
            # ==========================================================

            print("\n[10] Verifying sale calculations...")

            expected_total = (
                sale_item.quantity *
                sale_item.unit_price
            )

            if expected_total == sale.total_amount:
                print(
                    f"SUCCESS: "
                    f"{sale_item.quantity} × "
                    f"{sale_item.unit_price} = "
                    f"{sale.total_amount}"
                )
            else:
                raise Exception(
                    f"Sale total mismatch: "
                    f"expected {expected_total}, "
                    f"got {sale.total_amount}"
                )

            # ==========================================================
            # 11. VERIFY INVENTORY
            # ==========================================================

            print("\n[11] Verifying inventory...")

            if inventory.quantity_on_hand == 50:
                print(
                    "SUCCESS: Initial inventory quantity is 50"
                )
            else:
                raise Exception(
                    "Unexpected inventory quantity"
                )

            # ==========================================================
            # 12. ROLLBACK EVERYTHING
            # ==========================================================

            print("\n[12] Rolling back test data...")

            session.rollback()

            print("SUCCESS: Test transaction rolled back.")

            # ==========================================================
            # FINAL RESULT
            # ==========================================================

            print("\n" + "=" * 70)
            print("SQLALCHEMY ORM TEST PASSED")
            print("=" * 70)

            print("\nVerified:")
            print("  ✓ Store creation")
            print("  ✓ Category creation")
            print("  ✓ Product creation")
            print("  ✓ Customer creation")
            print("  ✓ Inventory creation")
            print("  ✓ Sale creation")
            print("  ✓ Sale item creation")
            print("  ✓ ORM relationships")
            print("  ✓ SELECT queries")
            print("  ✓ Sale calculation")
            print("  ✓ Transaction rollback")

            print("\nNo test data was permanently stored.")

        except Exception as error:

            print("\n" + "=" * 70)
            print("SQLALCHEMY ORM TEST FAILED")
            print("=" * 70)

            print("\nError type:")
            print(type(error).__name__)

            print("\nError:")
            print(error)

            print("\nRolling back...")
            session.rollback()

            print("Rollback completed.")


if __name__ == "__main__":
    main()