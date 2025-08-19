import streamlit as st
import sqlite3
from datetime import datetime

# ----------------------------
# Database Setup
# ----------------------------
conn = sqlite3.connect("cafe_central.db", check_same_thread=False)
cursor = conn.cursor()

# Create tables if they don’t exist
cursor.executescript("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT
);

CREATE TABLE IF NOT EXISTS menu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    menu_id INTEGER,
    quantity INTEGER,
    order_time TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(id),
    FOREIGN KEY(menu_id) REFERENCES menu(id)
);
""")
conn.commit()

# ----------------------------
# Customer Registration / Login
# ----------------------------
def customer_page():
    st.header("Customer Page")

    # Register new customer
    st.subheader("Register New Customer")
    name = st.text_input("Name")
    phone = st.text_input("Phone")
    if st.button("Register"):
        if name and phone:
            cursor.execute("INSERT INTO customers (name, phone) VALUES (?, ?)", (name, phone))
            conn.commit()
            st.success("Registration successful! Please note your Customer ID.")
            cursor.execute("SELECT id FROM customers WHERE phone=?", (phone,))
            customer_id = cursor.fetchone()[0]
            st.info(f"Your Customer ID is: {customer_id}")
        else:
            st.error("Please enter both name and phone.")

    # Existing customer login
    st.subheader("Existing Customer Login")
    cust_id = st.number_input("Customer ID", min_value=1, step=1)
    if st.button("Login"):
        cursor.execute("SELECT * FROM customers WHERE id=?", (cust_id,))
        if cursor.fetchone():
            st.session_state.customer_id = cust_id
            st.success(f"Logged in as Customer ID: {cust_id}")
        else:
            st.error("Invalid Customer ID.")

    # Only show options if logged in
    if "customer_id" in st.session_state:
        st.subheader("Place an Order")

        cursor.execute("SELECT * FROM menu")
        menu_items = cursor.fetchall()

        if menu_items:
            for item in menu_items:
                qty = st.number_input(f"{item[1]} (₹{item[2]})", min_value=0, step=1, key=f"order_{item[0]}")
                if qty > 0 and st.button(f"Order {item[1]}", key=f"btn_{item[0]}"):
                    cursor.execute(
                        "INSERT INTO orders (customer_id, menu_id, quantity, order_time) VALUES (?, ?, ?, ?)",
                        (st.session_state.customer_id, item[0], qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    )
                    conn.commit()
                    st.success(f"Ordered {qty} x {item[1]}")

        # Show past orders (FIXED: only runs if logged in)
        st.subheader("Your Orders")
        cursor.execute("""
            SELECT orders.id, menu.name, orders.quantity, orders.order_time
            FROM orders
            JOIN menu ON orders.menu_id = menu.id
            WHERE orders.customer_id = ?
            ORDER BY orders.order_time DESC
        """, (st.session_state.customer_id,))
        customer_orders = cursor.fetchall()

        if customer_orders:
            for order in customer_orders:
                st.write(f"Order ID: {order[0]} | Item: {order[1]} | Quantity: {order[2]} | Time: {order[3]}")
        else:
            st.info("You haven’t placed any orders yet.")


# ----------------------------
# Admin Page
# ----------------------------
def admin_page():
    st.header("Admin Page")

    password = st.text_input("Password", type="password")
    if st.button("Admin Login"):
        if password == "admin123":
            st.session_state.admin = True
        else:
            st.error("Wrong password")

    if "admin" in st.session_state and st.session_state.admin:
        st.subheader("Menu Management")

        # Add menu item
        name = st.text_input("Item Name")
        price = st.number_input("Price", min_value=0.0, step=0.5)
        if st.button("Add Item"):
            if name and price:
                cursor.execute("INSERT INTO menu (name, price) VALUES (?, ?)", (name, price))
                conn.commit()
                st.success("Item added")

        # Update menu item
        cursor.execute("SELECT * FROM menu")
        menu_items = cursor.fetchall()
        if menu_items:
            st.subheader("Update Menu Item")
            menu_id = st.selectbox("Select Item", [item[0] for item in menu_items])
            new_price = st.number_input("New Price", min_value=0.0, step=0.5)
            if st.button("Update Price"):
                cursor.execute("UPDATE menu SET price=? WHERE id=?", (new_price, menu_id))
                conn.commit()
                st.success("Price updated")

        # Show orders
        st.subheader("All Orders")
        cursor.execute("""
            SELECT orders.id, customers.name, menu.name, orders.quantity, orders.order_time
            FROM orders
            JOIN customers ON orders.customer_id = customers.id
            JOIN menu ON orders.menu_id = menu.id
            ORDER BY orders.order_time DESC
        """)
        all_orders = cursor.fetchall()
        if all_orders:
            for order in all_orders:
                st.write(f"Order ID: {order[0]} | Customer: {order[1]} | Item: {order[2]} | Quantity: {order[3]} | Time: {order[4]}")
        else:
            st.info("No orders yet.")


# ----------------------------
# Page Selection
# ----------------------------
page = st.sidebar.radio("Select Page", ["Customer", "Admin"])

if page == "Customer":
    customer_page()
elif page == "Admin":
    admin_page()
    
