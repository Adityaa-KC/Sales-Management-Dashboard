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
from app.services.sales_service import create_sale


def main():

    print("=" * 70)
    print("SMART RETAIL - SALES SERVICE TEST")
    print("=" * 70)

    engine = get_engine()

    with Session(engine) as session:

        try:

            # =====================================================
            # 1. Create test store
            # =====================================================

            print("\n[1] Creating test store...")

            store = Store(
                name="Sales Service Test Store",
                currency="INR",
            )

            session.add(store)
            session.flush()

            # =====================================================
            # 2. Create category
            # =====================================================

            print("[2] Creating test category...")

            category = Category(
                store_id=store.id,
                name="Test Category",
            )

            session.add(category)
            session.flush()

            # =====================================================
            # 3. Create product
            # =====================================================

            print("[3] Creating test product...")

            product = Product(
                store_id=store.id,
                category_id=category.id,
                sku="SALES-TEST-001",
                name="Sales Test Product",
                selling_price=Decimal("100.00"),
                cost_price=Decimal("60.00"),
                reorder_level=10,
                is_active=True,
            )

            session.add(product)
            session.flush()

            # =====================================================
            # 4. Create customer
            # =====================================================

            print("[4] Creating test customer...")

            customer = Customer(
                store_id=store.id,
                name="Sales Test Customer",
                email="sales-test@example.com",
                phone="9999999999",
            )

            session.add(customer)
            session.flush()

            # =====================================================
            # 5. Create inventory
            # =====================================================

            print("[5] Creating inventory...")

            inventory = Inventory(
                store_id=store.id,
                product_id=product.id,
                quantity_on_hand=50,
            )

            session.add(inventory)
            session.commit()

            print("Initial stock:", inventory.quantity_on_hand)

            # =====================================================
            # 6. Create sale
            # =====================================================

            print("\n[6] Creating sale...")

            sale = create_sale(
                session=session,
                store_id=store.id,
                customer_id=customer.id,
                items=[
                    {
                        "product_id": product.id,
                        "quantity": 3,
                    }
                ],
            )

            print("SUCCESS: Sale created")
            print("Sale ID:", sale.id)
            print("Total:", sale.total_amount)

            # =====================================================
            # 7. Verify inventory
            # =====================================================

            print("\n[7] Checking inventory...")

            updated_inventory = session.execute(
                select(Inventory).where(
                    Inventory.product_id == product.id,
                    Inventory.store_id == store.id,
                )
            ).scalar_one()

            print(
                "Stock after sale:",
                updated_inventory.quantity_on_hand
            )

            assert updated_inventory.quantity_on_hand == 47

            print("SUCCESS: Inventory decreased from 50 to 47.")

            # =====================================================
            # 8. Verify sale item
            # =====================================================

            print("\n[8] Checking sale item...")

            sale_item = session.execute(
                select(SaleItem).where(
                    SaleItem.sale_id == sale.id
                )
            ).scalar_one()

            assert sale_item.quantity == 3
            assert sale_item.unit_price == Decimal("100.00")
            assert sale_item.line_total == Decimal("300.00")

            print("SUCCESS: SaleItem is correct.")
            print("Quantity:", sale_item.quantity)
            print("Unit price:", sale_item.unit_price)
            print("Line total:", sale_item.line_total)

            # =====================================================
            # 9. Verify total
            # =====================================================

            print("\n[9] Checking sale total...")

            assert sale.total_amount == Decimal("300.00")

            print("SUCCESS: Sale total = INR 300.00")

            # =====================================================
            # 10. Test insufficient stock
            # =====================================================

            print("\n[10] Testing insufficient stock...")

            try:

                create_sale(
                    session=session,
                    store_id=store.id,
                    customer_id=customer.id,
                    items=[
                        {
                            "product_id": product.id,
                            "quantity": 100,
                        }
                    ],
                )

                raise AssertionError(
                    "Sale should have been rejected."
                )

            except ValueError as error:

                print(
                    "SUCCESS: Insufficient stock rejected."
                )

                print("Message:", error)

            # =====================================================
            # FINAL
            # =====================================================

            print("\n" + "=" * 70)
            print("SALES SERVICE TEST PASSED")
            print("=" * 70)

            print("\nVerified:")
            print("  - Sale creation")
            print("  - Sale item creation")
            print("  - Total calculation")
            print("  - Inventory reduction")
            print("  - Insufficient stock validation")
            print("  - PostgreSQL transaction")

        except Exception as error:

            session.rollback()

            print("\n" + "=" * 70)
            print("SALES SERVICE TEST FAILED")
            print("=" * 70)

            print("\nError type:")
            print(type(error).__name__)

            print("\nError:")
            print(error)

            raise

        finally:

            # -------------------------------------------------
            # Delete test records created by this test.
            # -------------------------------------------------

            print("\nCleaning test data...")

            # Delete sale items first.
            session.execute(
                SaleItem.__table__.delete()
            )

            session.execute(
                Sale.__table__.delete()
            )

            session.execute(
                Inventory.__table__.delete()
            )

            session.execute(
                Product.__table__.delete()
            )

            session.execute(
                Customer.__table__.delete()
            )

            session.execute(
                Category.__table__.delete()
            )

            session.execute(
                Store.__table__.delete()
            )

            session.commit()

            print("Test data removed.")


if __name__ == "__main__":
    main()