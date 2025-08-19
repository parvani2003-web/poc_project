import sqlite3, random, datetime, os

DB = "demo.sqlite"

def main():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.executescript(
        '''
        PRAGMA foreign_keys = ON;
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TEXT
        );
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            sku TEXT UNIQUE,
            name TEXT NOT NULL,
            category TEXT,
            price_cents INTEGER
        );
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT,
            status TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
        );
        CREATE TABLE order_items (
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            unit_price_cents INTEGER,
            PRIMARY KEY (order_id, product_id),
            FOREIGN KEY(order_id) REFERENCES orders(order_id),
            FOREIGN KEY(product_id) REFERENCES products(product_id)
        );
        '''
    )

    names = ["Arun", "Beena", "Chitra", "Divya", "Eshan", "Fatima", "Gautam", "Hira"]
    domains = ["example.com", "shop.test", "mail.local"]
    for cid in range(1, 21):
        name = random.choice(names) + f" {cid}"
        email = f"user{cid}@{random.choice(domains)}"
        created_at = (datetime.datetime(2023,1,1) + datetime.timedelta(days=random.randint(0,600))).isoformat()
        cur.execute("INSERT INTO customers (customer_id, name, email, created_at) VALUES (?, ?, ?, ?)",
                    (cid, name, email, created_at))

    cats = ["Books", "Electronics", "Clothing", "Home"]
    for pid in range(1, 31):
        sku = f"SKU{pid:04d}"
        name = f"Product {pid}"
        category = random.choice(cats)
        price_cents = random.randint(199, 9999)
        cur.execute("INSERT INTO products (product_id, sku, name, category, price_cents) VALUES (?, ?, ?, ?, ?)",
                    (pid, sku, name, category, price_cents))

    oid = 1
    for _ in range(80):
        customer_id = random.randint(1, 20)
        order_date = (datetime.datetime(2024,1,1) + datetime.timedelta(days=random.randint(0,590))).isoformat()
        status = random.choice(["CREATED", "PAID", "SHIPPED", "CANCELLED"])
        cur.execute("INSERT INTO orders (order_id, customer_id, order_date, status) VALUES (?, ?, ?, ?)",
                    (oid, customer_id, order_date, status))

        # items
        for _ in range(random.randint(1, 4)):
            product_id = random.randint(1, 30)
            qty = random.randint(1, 3)
            # copy price from product
            cur.execute("SELECT price_cents FROM products WHERE product_id=?", (product_id,))
            unit_price = cur.fetchone()[0]
            cur.execute(
                "INSERT OR REPLACE INTO order_items (order_id, product_id, quantity, unit_price_cents) VALUES (?, ?, ?, ?)",
                (oid, product_id, qty, unit_price)
            )
        oid += 1

    conn.commit()
    conn.close()
    print(f"Created {DB}")

if __name__ == "__main__":
    main()
