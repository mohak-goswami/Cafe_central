# cafe_streamlit.py

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ----------------------------
# Database Setup
# ----------------------------
conn = sqlite3.connect("cafe_central.db", check_same_thread=False)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS menu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    upi_number TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (item_id) REFERENCES menu(id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    review_text TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (item_id) REFERENCES menu(id)
);
""")
conn.commit()

# ----------------------------
# Session State Initialization
# ----------------------------
default_states = {
    "role": None,
    "customer_id": None,
    "cart": [],
    "logged_in": False
}
for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ----------------------------
# Helper Functions
# ----------------------------
def get_customer_name(customer_id):
    cursor.execute("SELECT name FROM customers WHERE id=?", (customer_id,))
    row = cursor.fetchone()
    return row[0] if row else "Unknown"

# ----------------------------
# UI
# ----------------------------
st.title("☕ Cafe Central")

menu_choice = st.sidebar.radio("Navigation", ["Home", "Customer", "Admin"])

# ----------------------------
# Customer Section
# ----------------------------
if menu_choice == "Customer":
    st.header("Customer Section")

    action = st.radio("Choose an option", ["New Customer Registration", "Existing Customer Login"])

    if action == "New Customer Registration":
        st.subheader("📝 New Customer Registration")
        name = st.text_input("Name")
        phone = st.text_input("Phone Number")

        if st.button("Register"):
            if name and phone:
                try:
                    cursor.execute("INSERT INTO customers (name, phone) VALUES (?, ?)", (name, phone))
                    conn.commit()
                    st.success("Registration successful! Please login now.")
                except sqlite3.IntegrityError:
                    st.error("Phone number already registered.")
            else:
                st.warning("Please fill all fields.")

    elif action == "Existing Customer Login":
        st.subheader("🔑 Existing Customer Login")
        phone = st.text_input("Enter your Phone Number to Login")

        if st.button("Login"):
            cursor.execute("SELECT id FROM customers WHERE phone=?", (phone,))
            customer = cursor.fetchone()
            if customer:
                st.session_state.customer_id = customer[0]
                st.session_state.logged_in = True
                st.success("Login successful!")
            else:
                st.error("Customer not found. Please register first.")

    # If logged in
    if st.session_state.logged_in and st.session_state.customer_id:
        st.success(f"Welcome, {get_customer_name(st.session_state.customer_id)}! 🎉")

        customer_tab = st.radio("Choose Action", ["Menu", "Cart", "Order History", "Reviews"])

        # ---------------- Menu ----------------
        if customer_tab == "Menu":
            cursor.execute("SELECT id, name, price FROM menu")
            items = cursor.fetchall()
            if items:
                df_menu = pd.DataFrame(items, columns=["Item ID", "Name", "Price"])
                st.table(df_menu)

                item_id = st.number_input("Enter Item ID to Add to Cart", min_value=1, step=1)
                qty = st.number_input("Quantity", min_value=1, step=1)

                if st.button("Add to Cart"):
                    cursor.execute("SELECT id FROM menu WHERE id=?", (item_id,))
                    if cursor.fetchone():
                        st.session_state.cart.append((item_id, qty))
                        st.success("Item added to cart!")
                    else:
                        st.error("Invalid Item ID.")
            else:
                st.info("No items available in menu.")

        # ---------------- Cart ----------------
        elif customer_tab == "Cart":
            st.subheader("🛒 Your Cart")
            if st.session_state.cart:
                cart_items = []
                total = 0
                for item_id, qty in st.session_state.cart:
                    cursor.execute("SELECT name, price FROM menu WHERE id=?", (item_id,))
                    item = cursor.fetchone()
                    if item:
                        name, price = item
                        subtotal = price * qty
                        total += subtotal
                        cart_items.append([name, qty, price, subtotal])

                df_cart = pd.DataFrame(cart_items, columns=["Item", "Quantity", "Price", "Subtotal"])
                st.table(df_cart)
                st.write(f"**Total: ₹{total}**")

                upi_number = st.text_input("Enter UPI Number for Payment")
                if st.button("Place Order"):
                    order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute("INSERT INTO orders (customer_id, order_date, upi_number) VALUES (?, ?, ?)",
                                   (st.session_state.customer_id, order_date, upi_number))
                    order_id = cursor.lastrowid
                    for item_id, qty in st.session_state.cart:
                        cursor.execute("INSERT INTO order_items (order_id, item_id, quantity) VALUES (?, ?, ?)",
                                       (order_id, item_id, qty))
                    conn.commit()
                    st.session_state.cart = []
                    st.success("Order placed successfully!")
            else:
                st.info("Your cart is empty.")

        # ---------------- Order History ----------------
        elif customer_tab == "Order History":
            cursor.execute("SELECT id, order_date, upi_number FROM orders WHERE customer_id=?",
                           (st.session_state.customer_id,))
            orders = cursor.fetchall()
            if orders:
                df_orders = pd.DataFrame(orders, columns=["Order ID", "Date", "UPI Number"])
                st.table(df_orders)

                order_id = st.number_input("Enter Order ID to Reorder", min_value=1, step=1)
                if st.button("Reorder"):
                    cursor.execute("SELECT item_id, quantity FROM order_items WHERE order_id=?", (order_id,))
                    past_items = cursor.fetchall()
                    if past_items:
                        order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute("INSERT INTO orders (customer_id, order_date, upi_number) VALUES (?, ?, ?)",
                                       (st.session_state.customer_id, order_date, "Reorder"))
                        new_order_id = cursor.lastrowid
                        for item_id, qty in past_items:
                            cursor.execute("INSERT INTO order_items (order_id, item_id, quantity) VALUES (?, ?, ?)",
                                           (new_order_id, item_id, qty))
                        conn.commit()
                        st.success("Reorder placed successfully!")
                    else:
                        st.error("Invalid Order ID.")
            else:
                st.info("No past orders found.")

        # ---------------- Reviews ----------------
        elif customer_tab == "Reviews":
            st.subheader("⭐ Rate & Review Items")
            cursor.execute("SELECT id, name FROM menu")
            menu_items = cursor.fetchall()
            if menu_items:
                item_dict = {item[1]: item[0] for item in menu_items}
                selected_item = st.selectbox("Select Item", list(item_dict.keys()))
                rating = st.slider("Rating", 1, 5, 3)
                review_text = st.text_area("Write a Review")

                if st.button("Submit Review"):
                    cursor.execute("INSERT INTO reviews (customer_id, item_id, rating, review_text) VALUES (?, ?, ?, ?)",
                                   (st.session_state.customer_id, item_dict[selected_item], rating, review_text))
                    conn.commit()
                    st.success("Review submitted successfully!")
            else:
                st.info("No items available to review.")

# ----------------------------
# Admin Section
# ----------------------------
elif menu_choice == "Admin":
    st.header("Admin Section")

    admin_tab = st.radio("Choose Action", ["Menu Management", "View Orders", "View Customers", "View Reviews"])

    # ---------------- Menu Management ----------------
    if admin_tab == "Menu Management":
        st.subheader("Add Menu Item")
        name = st.text_input("Item Name")
        price = st.number_input("Price", min_value=1.0, step=1.0)

        if st.button("Add Item"):
            cursor.execute("INSERT INTO menu (name, price) VALUES (?, ?)", (name, price))
            conn.commit()
            st.success("Item added to menu!")

        st.subheader("Update Menu Item")
        cursor.execute("SELECT id, name, price FROM menu")
        menu_items = cursor.fetchall()
        if menu_items:
            item_dict = {f"{item[1]} (₹{item[2]})": item[0] for item in menu_items}
            selected_item = st.selectbox("Select Item to Update", list(item_dict.keys()))

            new_name = st.text_input("New Name")
            new_price = st.number_input("New Price", min_value=1.0, step=1.0)

            if st.button("Update Item"):
                item_id = item_dict[selected_item]
                if new_name.strip():
                    cursor.execute("UPDATE menu SET name=? WHERE id=?", (new_name, item_id))
                if new_price:
                    cursor.execute("UPDATE menu SET price=? WHERE id=?", (new_price, item_id))
                conn.commit()
                st.success("Menu item updated successfully!")
        else:
            st.info("No items in the menu yet.")

        st.subheader("Menu Items")
        cursor.execute("SELECT id, name, price FROM menu")
        menu_items = cursor.fetchall()
        if menu_items:
            df_menu = pd.DataFrame(menu_items, columns=["Item ID", "Name", "Price"])
            st.table(df_menu)
        else:
            st.info("Menu is empty.")

    # ---------------- View Orders ----------------
    elif admin_tab == "View Orders":
        cursor.execute("SELECT * FROM orders")
        orders = cursor.fetchall()
        if orders:
            df_orders = pd.DataFrame(orders, columns=["Order ID", "Customer ID", "Date", "UPI Number"])
            st.table(df_orders)
        else:
            st.info("No orders placed yet.")

    # ---------------- View Customers ----------------
    elif admin_tab == "View Customers":
        cursor.execute("SELECT * FROM customers")
        customers = cursor.fetchall()
        if customers:
            df_customers = pd.DataFrame(customers, columns=["Customer ID", "Name", "Phone"])
            st.table(df_customers)
        else:
            st.info("No customers registered yet.")

    # ---------------- View Reviews ----------------
    elif admin_tab == "View Reviews":
        cursor.execute("""
            SELECT m.name, AVG(r.rating) as avg_rating, COUNT(r.id) as total_reviews
            FROM reviews r
            JOIN menu m ON r.item_id = m.id
            GROUP BY m.id
        """)
        reviews = cursor.fetchall()
        if reviews:
            df_reviews = pd.DataFrame(reviews, columns=["Item", "Average Rating", "Total Reviews"])
            st.table(df_reviews)
        else:
            st.info("No reviews submitted yet.")
                                    
