# cafe_streamlit.py

import streamlit as st
import sqlite3
from datetime import datetime

# ----------------------------
# Database Setup
# ----------------------------
conn = sqlite3.connect("cafe_central.db", check_same_thread=False)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS menu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    item_id INTEGER,
    quantity INTEGER,
    order_time TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(id),
    FOREIGN KEY(item_id) REFERENCES menu(id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    item_id INTEGER,
    rating INTEGER,
    review TEXT,
    review_time TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(id),
    FOREIGN KEY(item_id) REFERENCES menu(id)
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
def place_order(customer_id, item_id, qty):
    cursor.execute(
        "INSERT INTO orders (customer_id, item_id, quantity, order_time) VALUES (?, ?, ?, ?)",
        (customer_id, item_id, qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()

# ----------------------------
# Customer Registration/Login
# ----------------------------
st.title("☕ Cafe Central")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("New Customer Registration")
    new_name = st.text_input("Name", key="reg_name")
    new_phone = st.text_input("Phone", key="reg_phone")
    if st.button("Register"):
        if new_name.strip() and new_phone.strip():
            try:
                cursor.execute("INSERT INTO customers (name, phone) VALUES (?, ?)", (new_name, new_phone))
                conn.commit()
                customer_id = cursor.lastrowid
                st.success(f"Registration successful! Your Customer ID is **{customer_id}**. Please use this to log in.")
            except sqlite3.IntegrityError:
                st.error("Phone already registered.")
        else:
            st.warning("Fill all fields.")

with col2:
    st.subheader("Existing Customer Login")
    cust_id_input = st.number_input("Customer ID", min_value=1, step=1, key="login_id")
    if st.button("Login"):
        cursor.execute("SELECT id, name FROM customers WHERE id=?", (cust_id_input,))
        user = cursor.fetchone()
        if user:
            st.session_state.role = "Customer"
            st.session_state.customer_id = user[0]
            st.session_state.logged_in = True
            st.success(f"Welcome back, {user[1]}!")
        else:
            st.error("Invalid Customer ID.")
#-----------------------------
# Customer Dashboard
# ----------------------------
if st.session_state.role == "Customer" and st.session_state.logged_in:
    st.header("Menu")

    cursor.execute("SELECT id, name, price FROM menu")
    menu_items = cursor.fetchall()

    for item in menu_items:
        colA, colB, colC, colD = st.columns([3, 2, 2, 2])
        with colA:
            st.write(f"**{item[1]}** (₹{item[2]})")
        with colB:
            qty = st.number_input(f"Qty_{item[0]}", min_value=1, step=1, value=1, label_visibility="collapsed")
        with colC:
            if st.button("Order", key=f"order_{item[0]}"):
                place_order(st.session_state.customer_id, item[0], qty)
                st.success("Order placed!")
        with colD:
            cursor.execute("SELECT AVG(rating) FROM reviews WHERE item_id=?", (item[0],))
            avg_rating = cursor.fetchone()[0]
            if avg_rating:
                st.write(f"⭐ {round(avg_rating,1)}")

        with st.expander(f"Leave a Review for {item[1]}"):
            rating = st.slider(f"Rating_{item[0]}", 1, 5, 5)
            review_text = st.text_area(f"Review_{item[0]}", "")
            if st.button(f"Submit Review_{item[0]}"):
                cursor.execute(
                    "INSERT INTO reviews (customer_id, item_id, rating, review, review_time) VALUES (?, ?, ?, ?, ?)",
                    (st.session_state.customer_id, item[0], rating, review_text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                )
                conn.commit()
                st.success("Review submitted!")

    st.header("Your Order History")
    cursor.execute("""
        SELECT orders.id, menu.name, orders.quantity, orders.order_time
        FROM orders
        JOIN menu ON orders.item_id = menu.id
        WHERE orders.customer_id=?
        ORDER BY orders.order_time DESC
    """, (st.session_state.customer_id,))
    past_orders = cursor.fetchall()

    if past_orders:
        for order in past_orders:
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.write(f"**{order[1]}** × {order[2]}")
            with col2:
                st.write(order[3])
            with col3:
                if st.button("Reorder", key=f"reorder_{order[0]}"):
                    cursor.execute("SELECT item_id, quantity FROM orders WHERE id=?", (order[0],))
                    old = cursor.fetchone()
                    place_order(st.session_state.customer_id, old[0], old[1])
                    st.success("Order placed again!")
    else:
        st.info("No past orders.")

# ----------------------------
# Admin Dashboard
# ----------------------------
if st.session_state.role == "Admin" and st.session_state.logged_in:
    st.header("Manage Menu")

    st.subheader("Add Menu Item")
    item_name = st.text_input("Item Name")
    item_price = st.number_input("Price", min_value=1.0, step=1.0)
    if st.button("Add Item"):
        if item_name.strip():
            cursor.execute("INSERT INTO menu (name, price) VALUES (?, ?)", (item_name, item_price))
            conn.commit()
            st.success("Item added!")

    st.subheader("Update Menu Item")
    cursor.execute("SELECT id, name, price FROM menu")
    menu_items = cursor.fetchall()
    if menu_items:
        item_dict = {f"{m[1]} (₹{m[2]})": m[0] for m in menu_items}
        selected_item = st.selectbox("Select Item", list(item_dict.keys()))
        new_name = st.text_input("New Name")
        new_price = st.number_input("New Price", min_value=1.0, step=1.0)
        if st.button("Update Item"):
            item_id = item_dict[selected_item]
            if new_name.strip():
                cursor.execute("UPDATE menu SET name=? WHERE id=?", (new_name, item_id))
            if new_price:
                cursor.execute("UPDATE menu SET price=? WHERE id=?", (new_price, item_id))
            conn.commit()
            st.success("Item updated!")
    else:
        st.info("Menu is empty.")

    st.subheader("Delete Menu Item")
    cursor.execute("SELECT id, name FROM menu")
    items = cursor.fetchall()
    if items:
        item_dict = {m[1]: m[0] for m in items}
        del_item = st.selectbox("Select Item to Delete", list(item_dict.keys()))
        if st.button("Delete Item"):
            cursor.execute("DELETE FROM menu WHERE id=?", (item_dict[del_item],))
            conn.commit()
            st.success("Item deleted!")
    else:
        st.info("No items to delete.")

    st.subheader("Item Ratings & Reviews")
    cursor.execute("""
        SELECT menu.name, AVG(reviews.rating), COUNT(reviews.id)
        FROM reviews
        JOIN menu ON reviews.item_id = menu.id
        GROUP BY menu.id
    """)
    ratings = cursor.fetchall()
    if ratings:
        for r in ratings:
            st.write(f"**{r[0]}** → ⭐ {round(r[1],1)} ({r[2]} reviews)")
    else:
        st.info("No reviews yet.")
        

