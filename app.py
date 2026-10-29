import hmac
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Load local settings
load_dotenv(Path(__file__).with_name(".env"))

st.set_page_config(page_title="Customer Order Entry", layout="wide")

st.title("Customer Order Entry")
st.write(
    "View customers and products, create orders, "
    "and verify them in Supabase."
)

# Password protection
app_password = os.getenv("APP_PASSWORD", "")

if not app_password:
    st.error(
        "App password is not configured. "
        "Add APP_PASSWORD to your .env or deployment secrets."
    )
    st.stop()

if not st.session_state.get("logged_in", False):

    with st.form("login_form"):
        password_input = st.text_input(
            "App Password",
            type="password"
        )

        login_clicked = st.form_submit_button("Log In")

    if login_clicked:

        if hmac.compare_digest(password_input, app_password):
            st.session_state.logged_in = True
            st.rerun()

        else:
            st.error("Incorrect password.")

    st.stop()


# Import database functions after login
from database import get_client, get_customers, get_orders, get_products


# Format prices
def money(amount):
    return f"${Decimal(str(amount)):.2f}"


# Retrieve the current product price
def get_current_price(product_id):

    response = (
        get_client()
        .table("products")
        .select("price")
        .eq("product_id", product_id)
        .execute()
    )

    if not response.data:
        return None

    return Decimal(str(response.data[0]["price"]))


# Format saved orders for tables
def order_row(order):

    customer = order.get("customers") or {}
    product = order.get("products") or {}

    unit_price = Decimal(str(order["unit_price"]))

    return {
        "Order ID": order["order_id"],
        "Customer": customer.get(
            "name",
            str(order.get("customer_id", "Unknown"))
        ),
        "Product": product.get(
            "product_name",
            str(order.get("product_id", "Unknown"))
        ),
        "Quantity": order["quantity"],
        "Unit Price": money(unit_price),
        "Total": money(unit_price * int(order["quantity"])),
        "Order Date": order["order_date"]
    }


# Set up session information
if "review" not in st.session_state:
    st.session_state.review = None

if "review_version" not in st.session_state:
    st.session_state.review_version = 0

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "notice" not in st.session_state:
    st.session_state.notice = None


# Refresh Data button
refresh_clicked = st.button("Refresh Data")


# Retrieve customers and products
try:
    customers = get_customers()
    products = get_products()

except Exception:
    st.error(
        "Could not load customers or products. "
        "Check your Supabase connection."
    )
    st.stop()


# Display customer table
st.subheader("Customers")

customer_table = []

for customer in customers:

    customer_table.append({
        "Customer ID": customer["customer_id"],
        "Customer Name": customer["name"]
    })

st.dataframe(
    customer_table,
    hide_index=True,
    use_container_width=True
)


# Display product table
st.subheader("Products")

product_table = []

for product in products:

    product_table.append({
        "Product ID": product["product_id"],
        "Product Name": product["product_name"],
        "Category": product["category"],
        "Price": money(product["price"])
    })

st.dataframe(
    product_table,
    hide_index=True,
    use_container_width=True
)


# Make sure data is available
if not customers or not products:
    st.warning(
        "Customers and products must be available "
        "before creating an order."
    )
    st.stop()


# Organize customer and product information
customer_by_id = {
    c["customer_id"]: c for c in customers
}

product_by_id = {
    p["product_id"]: p for p in products
}


# Order entry section
st.subheader("Create a New Order")


# Customer dropdown
customer_id = st.selectbox(
    "Select a Customer",
    list(customer_by_id),
    format_func=lambda cid: (
        f"{customer_by_id[cid]['name']} (ID {cid})"
    )
)


# Product dropdown
product_id = st.selectbox(
    "Select a Product",
    list(product_by_id),
    format_func=lambda pid: (
        f"{product_by_id[pid]['product_name']} (ID {pid})"
    )
)


# Quantity input
quantity = st.number_input(
    "Enter Quantity",
    min_value=1,
    value=1,
    step=1
)


# Track selected order details
selection = (customer_id, product_id, int(quantity))

if st.session_state.review is not None:

    if st.session_state.review["selection"] != selection:
        st.session_state.review = None


# Review Order button
if st.button("Review Order"):

    try:
        current_price = get_current_price(product_id)

        if current_price is None:
            st.error("This product is no longer available.")

        else:
            st.session_state.review = {
                "selection": selection,
                "customer_name": customer_by_id[customer_id]["name"],
                "product_name": product_by_id[product_id]["product_name"],
                "price": str(current_price)
            }

            st.session_state.review_version += 1
            st.rerun()

    except Exception:
        st.error(
            "Could not retrieve the current price. "
            "Please try again later."
        )


# Display price change warnings
if st.session_state.notice:

    st.warning(st.session_state.notice)
    st.session_state.notice = None


# Display order summary
review = st.session_state.review

if review is not None and review["selection"] == selection:

    reviewed_price = Decimal(review["price"])

    st.subheader("Order Summary")

    st.write("Customer:", review["customer_name"])
    st.write("Product:", review["product_name"])
    st.write("Quantity:", quantity)
    st.write("Unit Price:", money(reviewed_price))
    st.write(
        "Total Price:",
        money(reviewed_price * int(quantity))
    )


    # Confirmation checkbox
    confirmed = st.checkbox(
        "I confirm this order",
        key=f"confirm_{st.session_state.review_version}"
    )


    # Submit Order button
    if st.button("Submit Order"):

        if not confirmed:
            st.warning(
                "Please check the confirmation box before submitting."
            )

        else:

            try:
                latest_price = get_current_price(product_id)

            except Exception:
                st.error(
                    "Could not check the current price. "
                    "No order was submitted."
                )

            else:

                if latest_price is None:

                    st.error(
                        "This product is no longer available. "
                        "No order was submitted."
                    )

                elif latest_price != reviewed_price:

                    st.session_state.review["price"] = str(latest_price)

                    st.session_state.review_version += 1

                    st.session_state.notice = (
                        f"The price changed to {money(latest_price)}. "
                        "Review the new total and confirm again."
                    )

                    st.rerun()

                else:

                    # Save order to Supabase
                    try:

                        response = (
                            get_client()
                            .table("orders")
                            .insert({
                                "customer_id": customer_id,
                                "product_id": product_id,
                                "quantity": int(quantity),
                                "unit_price": str(latest_price),
                                "order_date": date.today().isoformat()
                            })
                            .execute()
                        )

                        if (
                            not response.data
                            or "order_id" not in response.data[0]
                        ):
                            raise RuntimeError(
                                "No generated order ID was returned."
                            )

                        order_id = response.data[0]["order_id"]

                    except Exception:

                        st.error(
                            "Could not confirm whether the order was saved. "
                            "Check Order History before trying again."
                        )

                    else:

                        # Verify the saved order
                        result = {
                            "order_id": order_id,
                            "verified": None
                        }

                        try:

                            verification = (
                                get_client()
                                .table("orders")
                                .select(
                                    "*, customers(name), "
                                    "products(product_name)"
                                )
                                .eq("order_id", order_id)
                                .execute()
                            )

                            if verification.data:

                                result["verified"] = order_row(
                                    verification.data[0]
                                )

                        except Exception:
                            pass

                        st.session_state.last_result = result

                        st.session_state.review = None
                        st.session_state.review_version += 1

                        st.rerun()


# Display saved order verification
if st.session_state.last_result is not None:

    result = st.session_state.last_result

    st.success(
        f"Order {result['order_id']} was saved successfully!"
    )

    if result["verified"] is not None:

        st.subheader("Verified Order")

        st.dataframe(
            [result["verified"]],
            hide_index=True,
            use_container_width=True
        )

        st.success(
            "The saved order was retrieved from Supabase and verified."
        )

    else:

        st.warning(
            "The order was saved, but it could not be retrieved "
            "for verification. Do not submit it again."
        )


# Order History section
st.subheader("Order History")

try:

    orders = get_orders()

    history_table = []

    for order in reversed(orders):
        history_table.append(order_row(order))

    st.dataframe(
        history_table,
        hide_index=True,
        use_container_width=True
    )

    if refresh_clicked:
        st.success(
            "Customers, products, and order history "
            "refreshed from Supabase."
        )

except Exception:

    st.error(
        "Could not load order history. "
        "Please try Refresh Data again."
    )