
from database import get_customers, get_products, create_order, get_client


# Display customers from Supabase
def show_customers(customers):
    print("\nCUSTOMERS")
    print(f"{'ID':<6}{'Customer Name':<25}")
    print("--------------------------------")

    for customer in customers:
        print(f"{customer['customer_id']:<6}{customer['name']:<25}")


# Display products from Supabase
def show_products(products):
    print("\nPRODUCTS")
    print(f"{'ID':<6}{'Product Name':<25}{'Price'}")
    print("------------------------------------------")

    for product in products:
        price = float(product["price"])
        print(f"{product['product_id']:<6}{product['product_name']:<25}${price:.2f}")


# Ask for a valid customer ID
def choose_customer(customers):
    while True:
        try:
            customer_id = int(input("\nEnter customer ID: "))
        except ValueError:
            print("Please enter a whole number.")
            continue

        for customer in customers:
            if customer["customer_id"] == customer_id:
                return customer

        print("Customer ID not found. Try again.")


# Ask for a valid product ID
def choose_product(products):
    while True:
        try:
            product_id = int(input("Enter product ID: "))
        except ValueError:
            print("Please enter a whole number.")
            continue

        for product in products:
            if product["product_id"] == product_id:
                return product

        print("Product ID not found. Try again.")


# Ask for a valid quantity
def choose_quantity():
    while True:
        try:
            quantity = int(input("Enter quantity: "))

            if quantity > 0:
                return quantity
            else:
                print("Quantity must be greater than zero.")

        except ValueError:
            print("Please enter a positive whole number.")


# Ask a yes or no question
def ask_yes_no(question):
    while True:
        answer = input(question).strip().upper()

        if answer == "Y":
            return True
        elif answer == "N":
            return False
        else:
            print("Please enter Y or N.")


# Retrieve the saved order from Supabase
def verify_order(order_id):
    try:
        response = (get_client().table("orders")
                    .select("*, customers(name), products(product_name)")
                    .eq("order_id", order_id)
                    .execute())

        if not response.data:
            print("Order verification could not be completed.")
            return

        order = response.data[0]

        price = float(order["unit_price"])
        total = price * order["quantity"]

        customer_name = order["customers"]["name"]
        product_name = order["products"]["product_name"]

        print("\nVERIFIED ORDER")
        print(f"{'Order ID':<10}{'Customer':<22}{'Product':<20}{'Quantity':<10}{'Unit Price':<14}{'Total':<14}{'Order Date'}")
        print("-" * 105)

        print(f"{order['order_id']:<10}{customer_name:<22}{product_name:<20}{order['quantity']:<10}{'$' + format(price, '.2f'):<14}{'$' + format(total, '.2f'):<14}{order['order_date']}")

        print("\nOrder successfully verified in Supabase!")

    except Exception:
        print("Order was saved, but verification could not be completed.")


# Main program
def main():
    while True:
        try:
            customers = get_customers()
            products = get_products()
        except Exception:
            print("Could not load database information. Check your connection.")
            return

        show_customers(customers)
        show_products(products)

        customer = choose_customer(customers)
        product = choose_product(products)
        quantity = choose_quantity()

        price = float(product["price"])
        total = price * quantity

        print("\nORDER SUMMARY")
        print("Customer:", customer["name"])
        print("Product:", product["product_name"])
        print("Quantity:", quantity)
        print("Unit Price: $" + format(price, ".2f"))
        print("Order Total: $" + format(total, ".2f"))

        confirm = ask_yes_no("\nConfirm purchase? (Y/N): ")

        if confirm:
            try:
                saved_order = create_order(
                    customer["customer_id"],
                    product["product_id"],
                    quantity
                )

                order_id = saved_order["order_id"]

            except Exception:
                print("Could not confirm the order was saved.")
                print("Check Supabase before trying again.")
            else:
                print("\nOrder saved successfully!")
                verify_order(order_id)

        else:
            print("\nOrder cancelled. Nothing was saved.")

        again = ask_yes_no("\nEnter another order? (Y/N): ")

        if not again:
            print("Thank you! Program finished.")
            break


main()
