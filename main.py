


"""
╔══════════════════════════════════════════════════════════╗
║        CAKE SHOP MANAGEMENT SYSTEM  v2.0                ║
║        Built with Python Tkinter + MySQL                 ║
║        DBMS Concepts: Views, Stored Procedures,          ║
║        Triggers, Joins, Aggregates, Transactions         ║
╚══════════════════════════════════════════════════════════╝
"""
 
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
import mysql.connector
 
# ═══════════════════════════════════════════════════════════
#  THEME CONSTANTS
# ═══════════════════════════════════════════════════════════
BG        = "#1a1a2e"   # deep navy
SIDEBAR   = "#16213e"   # darker navy
CARD      = "#0f3460"   # card bg
ACCENT    = "#e94560"   # pink-red accent
ACCENT2   = "#f5a623"   # golden yellow
TEXT      = "#eaeaea"   # light text
MUTED     = "#8892a4"   # muted text
SUCCESS   = "#2ecc71"
WARNING   = "#f39c12"
DANGER    = "#e74c3c"
BTN_FONT  = ("Segoe UI", 10, "bold")
LBL_FONT  = ("Segoe UI", 10)
HDR_FONT  = ("Segoe UI", 18, "bold")
SUB_FONT  = ("Segoe UI", 13, "bold")
 
 
# ═══════════════════════════════════════════════════════════
#  DATABASE CONNECTION & SETUP
# ═══════════════════════════════════════════════════════════
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="cake_shop"
    )
 
 
def setup_database():
    """
    Creates all tables, views, stored procedures, and triggers.
    DBMS Concepts demonstrated:
      - DDL (CREATE TABLE with constraints)
      - Views (for reporting)
      - Stored Procedures (for business logic)
      - Triggers (for stock update on sale)
      - Foreign Keys (referential integrity)
    """
    conn = get_connection()
    cursor = conn.cursor()
 
    # ── TABLES ──────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id       INT AUTO_INCREMENT PRIMARY KEY,
            name     VARCHAR(100) NOT NULL,
            flavor   VARCHAR(100),
            price    DECIMAL(10,2) NOT NULL,
            stock    INT DEFAULT 0,
            expiry   DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            product_id      INT,
            cake_name       VARCHAR(100),
            customer_name   VARCHAR(100),
            customer_phone  VARCHAR(15),
            flavor          VARCHAR(100),
            price           DECIMAL(10,2),
            quantity        INT,
            total_amount    DECIMAL(10,2) GENERATED ALWAYS AS (price * quantity) STORED,
            sale_date       DATE DEFAULT (CURRENT_DATE),
            expiry          DATE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
        )
    """)
 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS advance_bookings (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            customer_name   VARCHAR(100) NOT NULL,
            customer_phone  VARCHAR(15),
            cake_name       VARCHAR(100),
            flavor          VARCHAR(100),
            quantity        INT DEFAULT 1,
            advance_paid    DECIMAL(10,2) DEFAULT 0,
            total_amount    DECIMAL(10,2) DEFAULT 0,
            delivery_date   DATE,
            status          ENUM('Pending','Ready','Delivered','Cancelled') DEFAULT 'Pending',
            booked_on       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_cash (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            entry_date  DATE UNIQUE,
            cash_in     DECIMAL(10,2) DEFAULT 0,
            cash_out    DECIMAL(10,2) DEFAULT 0,
            balance     DECIMAL(10,2) GENERATED ALWAYS AS (cash_in - cash_out) STORED,
            notes       TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            expense_date DATE DEFAULT (CURRENT_DATE),
            category     VARCHAR(50),
            description  TEXT,
            amount       DECIMAL(10,2),
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
 
    # ── VIEW: Daily Sales Summary ───────────────────────────
    cursor.execute("DROP VIEW IF EXISTS vw_daily_sales_summary")
    cursor.execute("""
        CREATE VIEW vw_daily_sales_summary AS
        SELECT
            sale_date,
            COUNT(*)            AS total_orders,
            SUM(quantity)       AS total_items,
            SUM(total_amount)   AS total_revenue
        FROM sales
        GROUP BY sale_date
        ORDER BY sale_date DESC
    """)
 
    # ── VIEW: Low Stock Alert ──────────────────────────────
    cursor.execute("DROP VIEW IF EXISTS vw_low_stock")
    cursor.execute("""
        CREATE VIEW vw_low_stock AS
        SELECT id, name, flavor, stock, expiry
        FROM products
        WHERE stock < 5
        ORDER BY stock ASC
    """)
 
    # ── VIEW: Monthly Revenue ──────────────────────────────
    cursor.execute("DROP VIEW IF EXISTS vw_monthly_revenue")
    cursor.execute("""
        CREATE VIEW vw_monthly_revenue AS
        SELECT
            YEAR(sale_date)  AS yr,
            MONTH(sale_date) AS mo,
            MONTHNAME(sale_date) AS month_name,
            SUM(total_amount) AS revenue,
            COUNT(*)          AS orders
        FROM sales
        GROUP BY YEAR(sale_date), MONTH(sale_date)
        ORDER BY yr DESC, mo DESC
    """)
 
    # ── STORED PROCEDURE: Get Product Sales Report ─────────
    cursor.execute("DROP PROCEDURE IF EXISTS sp_product_sales_report")
    cursor.execute("""
        CREATE PROCEDURE sp_product_sales_report()
        BEGIN
            SELECT
                p.id,
                p.name,
                p.flavor,
                p.price,
                p.stock,
                COALESCE(SUM(s.quantity), 0)      AS units_sold,
                COALESCE(SUM(s.total_amount), 0)  AS revenue
            FROM products p
            LEFT JOIN sales s ON p.id = s.product_id
            GROUP BY p.id, p.name, p.flavor, p.price, p.stock
            ORDER BY revenue DESC;
        END
    """)
 
    # ── STORED PROCEDURE: Add Sale with Stock Deduction ────
    cursor.execute("DROP PROCEDURE IF EXISTS sp_add_sale")
    cursor.execute("""
        CREATE PROCEDURE sp_add_sale(
            IN p_product_id    INT,
            IN p_cake_name     VARCHAR(100),
            IN p_customer_name VARCHAR(100),
            IN p_customer_phone VARCHAR(15),
            IN p_flavor        VARCHAR(100),
            IN p_price         DECIMAL(10,2),
            IN p_quantity      INT,
            IN p_expiry        DATE
        )
        BEGIN
            DECLARE current_stock INT;
            SELECT stock INTO current_stock FROM products WHERE id = p_product_id;
 
            IF current_stock < p_quantity THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Insufficient stock for this product';
            ELSE
                INSERT INTO sales
                    (product_id, cake_name, customer_name, customer_phone,
                     flavor, price, quantity, expiry, sale_date)
                VALUES
                    (p_product_id, p_cake_name, p_customer_name, p_customer_phone,
                     p_flavor, p_price, p_quantity, p_expiry, CURDATE());
 
                UPDATE products SET stock = stock - p_quantity WHERE id = p_product_id;
            END IF;
        END
    """)
 
    # ── TRIGGER: Log low stock warning after update ────────
    cursor.execute("DROP TRIGGER IF EXISTS trg_after_stock_update")
    cursor.execute("""
        CREATE TRIGGER trg_after_stock_update
        AFTER UPDATE ON products
        FOR EACH ROW
        BEGIN
            IF NEW.stock < 5 AND OLD.stock >= 5 THEN
                INSERT INTO daily_cash (entry_date, cash_in, cash_out, notes)
                VALUES (CURDATE(), 0, 0,
                    CONCAT('LOW STOCK ALERT: ', NEW.name, ' has only ', NEW.stock, ' left'))
                ON DUPLICATE KEY UPDATE
                    notes = CONCAT(COALESCE(notes,''), ' | LOW STOCK: ', NEW.name);
            END IF;
        END
    """)
 
    conn.commit()
    conn.close()
 
 
# ═══════════════════════════════════════════════════════════
#  HELPER WIDGETS
# ═══════════════════════════════════════════════════════════
def clear_content(content):
    for w in content.winfo_children():
        w.destroy()
 
 
def styled_button(parent, text, command, color=ACCENT, width=18):
    return tk.Button(parent, text=text, command=command,
                     bg=color, fg="white", font=BTN_FONT,
                     relief="flat", cursor="hand2", width=width,
                     padx=8, pady=6)
 
 
def styled_label(parent, text, font=LBL_FONT, fg=TEXT, bg=BG):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg)
 
 
def make_treeview(parent, columns, heights=15):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Custom.Treeview",
                    background=CARD,
                    foreground=TEXT,
                    fieldbackground=CARD,
                    rowheight=28,
                    font=("Segoe UI", 10))
    style.configure("Custom.Treeview.Heading",
                    background=SIDEBAR,
                    foreground=ACCENT2,
                    font=("Segoe UI", 10, "bold"))
    style.map("Custom.Treeview",
              background=[("selected", ACCENT)])
 
    tree = ttk.Treeview(parent, columns=columns,
                        show="headings", height=heights,
                        style="Custom.Treeview")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=110)
 
    sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    return tree
 
 
def form_row(parent, label, var=None, widget_type="entry",
             options=None, bg=BG):
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", padx=20, pady=4)
    tk.Label(row, text=label, font=LBL_FONT, fg=MUTED,
             bg=bg, width=20, anchor="w").pack(side="left")
    if widget_type == "entry":
        e = tk.Entry(row, textvariable=var, font=LBL_FONT,
                     bg=SIDEBAR, fg=TEXT, insertbackground=TEXT,
                     relief="flat", width=28)
        e.pack(side="left", padx=5)
        return e
    elif widget_type == "combo":
        c = ttk.Combobox(row, values=options, font=LBL_FONT,
                         state="readonly", width=26)
        c.pack(side="left", padx=5)
        return c
 
 
def section_header(parent, title, bg=BG):
    f = tk.Frame(parent, bg=ACCENT, height=3)
    f.pack(fill="x", padx=20, pady=(15, 0))
    tk.Label(parent, text=title, font=SUB_FONT,
             fg=ACCENT2, bg=bg).pack(anchor="w", padx=22, pady=6)
 
 
# ═══════════════════════════════════════════════════════════
#  MODULES
# ═══════════════════════════════════════════════════════════
 
# ── 1. DASHBOARD HOME ───────────────────────────────────
def show_home(content):
    clear_content(content)
 
    tk.Label(content, text="📊  Dashboard Overview",
             font=HDR_FONT, fg=TEXT, bg=BG).pack(pady=(20, 5))
    tk.Label(content, text=f"Today: {date.today().strftime('%A, %d %B %Y')}",
             font=LBL_FONT, fg=MUTED, bg=BG).pack()
 
    # ── KPI Cards Row ──
    cards_frame = tk.Frame(content, bg=BG)
    cards_frame.pack(pady=20, padx=20, fill="x")
 
    try:
        conn = get_connection()
        cursor = conn.cursor()
 
        cursor.execute("SELECT COALESCE(SUM(total_amount),0) FROM sales WHERE sale_date = CURDATE()")
        today_sales = float(cursor.fetchone()[0])
 
        cursor.execute("SELECT COUNT(*) FROM sales WHERE sale_date = CURDATE()")
        today_orders = cursor.fetchone()[0]
 
        cursor.execute("SELECT COUNT(*) FROM products WHERE stock < 5")
        low_stock = cursor.fetchone()[0]
 
        cursor.execute("SELECT COUNT(*) FROM advance_bookings WHERE status='Pending'")
        pending_bookings = cursor.fetchone()[0]
 
        cursor.execute("SELECT COALESCE(SUM(total_amount),0) FROM sales WHERE MONTH(sale_date)=MONTH(CURDATE()) AND YEAR(sale_date)=YEAR(CURDATE())")
        month_revenue = float(cursor.fetchone()[0])
 
        conn.close()
 
        kpis = [
            ("💰 Today's Revenue", f"₹{today_sales:,.2f}", SUCCESS),
            ("🛒 Today's Orders",  str(today_orders),      ACCENT2),
            ("⚠️  Low Stock Items", str(low_stock),         DANGER if low_stock > 0 else SUCCESS),
            ("📅 Pending Bookings", str(pending_bookings),  ACCENT),
            ("📈 Month Revenue",   f"₹{month_revenue:,.2f}", "#3498db"),
        ]
 
        for title, value, color in kpis:
            card = tk.Frame(cards_frame, bg=CARD, padx=15, pady=15,
                            relief="flat", bd=0)
            card.pack(side="left", expand=True, fill="both", padx=8)
            tk.Label(card, text=title, font=("Segoe UI", 9),
                     fg=MUTED, bg=CARD).pack()
            tk.Label(card, text=value, font=("Segoe UI", 20, "bold"),
                     fg=color, bg=CARD).pack(pady=5)
 
    except Exception as e:
        tk.Label(content, text=f"Could not load stats:\n{e}",
                 fg=DANGER, bg=BG, font=LBL_FONT).pack(pady=20)
        return
 
    # ── Recent Sales Table ──
    section_header(content, "Recent Sales (Last 10 Records)")
 
    tframe = tk.Frame(content, bg=BG)
    tframe.pack(fill="both", expand=True, padx=20, pady=5)
 
    cols = ("Date", "Customer", "Cake", "Qty", "Total (₹)")
    tree = make_treeview(tframe, cols, heights=8)
 
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sale_date, customer_name, cake_name, quantity, total_amount
            FROM sales ORDER BY id DESC LIMIT 10
        """)
        for row in cursor.fetchall():
            tree.insert("", tk.END, values=row)
        conn.close()
    except Exception as e:
        pass
 
    # ── Low Stock Alert ──
    if low_stock > 0:
        section_header(content, f"⚠️  Low Stock Alert ({low_stock} items)", bg=BG)
        aframe = tk.Frame(content, bg=BG)
        aframe.pack(fill="x", padx=20, pady=5)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vw_low_stock")
            for row in cursor.fetchall():
                tk.Label(aframe,
                         text=f"  🎂 {row[1]}  ({row[2]})  —  Stock: {row[3]}",
                         font=LBL_FONT, fg=WARNING, bg=BG).pack(anchor="w")
            conn.close()
        except:
            pass
 
 
# ── 2. INVENTORY ─────────────────────────────────────────
def show_inventory(content):
    clear_content(content)
 
    tk.Label(content, text="🎂  Inventory Management",
             font=HDR_FONT, fg=TEXT, bg=BG).pack(pady=(15, 5))
 
    # Search bar
    search_frame = tk.Frame(content, bg=BG)
    search_frame.pack(fill="x", padx=20, pady=5)
    tk.Label(search_frame, text="🔍 Search:", font=LBL_FONT,
             fg=MUTED, bg=BG).pack(side="left")
    search_var = tk.StringVar()
    search_entry = tk.Entry(search_frame, textvariable=search_var,
                            font=LBL_FONT, bg=SIDEBAR, fg=TEXT,
                            insertbackground=TEXT, width=30, relief="flat")
    search_entry.pack(side="left", padx=8)
 
    # Table
    tframe = tk.Frame(content, bg=BG)
    tframe.pack(fill="both", expand=False, padx=20, pady=5)
 
    cols = ("ID", "Name", "Flavor", "Price (₹)", "Stock", "Expiry", "Added On")
    tree = make_treeview(tframe, cols, heights=10)
 
    def load_products(filter_text=""):
        for i in tree.get_children():
            tree.delete(i)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            if filter_text:
                cursor.execute("""
                    SELECT id, name, flavor, price, stock, expiry, DATE(created_at)
                    FROM products
                    WHERE name LIKE %s OR flavor LIKE %s
                """, (f"%{filter_text}%", f"%{filter_text}%"))
            else:
                cursor.execute("""
                    SELECT id, name, flavor, price, stock, expiry, DATE(created_at)
                    FROM products
                """)
            for row in cursor.fetchall():
                tag = "low" if row[4] is not None and int(row[4]) < 5 else ""
                tree.insert("", tk.END, values=row, tags=(tag,))
            tree.tag_configure("low", foreground=DANGER)
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", str(e))
 
    search_var.trace("w", lambda *a: load_products(search_var.get()))
    load_products()
 
    # ── Entry Form ──
    form_bg = SIDEBAR
    form_outer = tk.Frame(content, bg=form_bg, pady=10)
    form_outer.pack(fill="x", padx=20, pady=8)
 
    section_header(form_outer, "Add / Update Product", bg=form_bg)
 
    fields = {}
    for lbl in ["Name", "Flavor", "Price (₹)", "Stock", "Expiry (YYYY-MM-DD)"]:
        fields[lbl] = form_row(form_outer, lbl, bg=form_bg)
 
    # Auto-fill on row select
    def on_select(event):
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0])["values"]
        labels = list(fields.keys())
        for i, key in enumerate(labels):
            fields[key].delete(0, tk.END)
            fields[key].insert(0, vals[i + 1] if i + 1 < len(vals) else "")
 
    tree.bind("<<TreeviewSelect>>", on_select)
 
    def save_product():
        name   = fields["Name"].get().strip()
        flavor = fields["Flavor"].get().strip()
        price  = fields["Price (₹)"].get().strip()
        stock  = fields["Stock"].get().strip()
        expiry = fields["Expiry (YYYY-MM-DD)"].get().strip()
 
        if not name or not price or not stock:
            messagebox.showwarning("Validation", "Name, Price and Stock are required.")
            return
        try:
            float(price); int(stock)
        except:
            messagebox.showerror("Validation", "Price must be a number and Stock must be an integer.")
            return
 
        try:
            conn = get_connection()
            cursor = conn.cursor()
            sel = tree.selection()
            if sel:
                pid = tree.item(sel[0])["values"][0]
                cursor.execute("""
                    UPDATE products
                    SET name=%s, flavor=%s, price=%s, stock=%s, expiry=%s
                    WHERE id=%s
                """, (name, flavor, price, stock, expiry or None, pid))
                msg = "Product updated!"
            else:
                cursor.execute("""
                    INSERT INTO products (name, flavor, price, stock, expiry)
                    VALUES (%s,%s,%s,%s,%s)
                """, (name, flavor, price, stock, expiry or None))
                msg = "Product added!"
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", msg)
            load_products()
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
 
    def delete_product():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a product to delete.")
            return
        pid = tree.item(sel[0])["values"][0]
        if not messagebox.askyesno("Confirm", "Delete this product?"):
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id=%s", (pid,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Deleted", "Product removed.")
            load_products()
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
 
    btn_row = tk.Frame(form_outer, bg=form_bg)
    btn_row.pack(pady=10)
    styled_button(btn_row, "💾  Save / Update", save_product, color=SUCCESS).pack(side="left", padx=8)
    styled_button(btn_row, "🗑️  Delete Selected", delete_product, color=DANGER).pack(side="left", padx=8)
    styled_button(btn_row, "🔄  Refresh", lambda: load_products(), color=CARD).pack(side="left", padx=8)
 
 
# ── 3. SALES ENTRY ───────────────────────────────────────
def show_sales_entry(content):
    clear_content(content)
 
    tk.Label(content, text="🛒  New Sale Entry",
             font=HDR_FONT, fg=TEXT, bg=BG).pack(pady=(15, 5))
 
    # Load product names for dropdown
    product_map = {}  # name -> (id, flavor, price, expiry)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, flavor, price, expiry FROM products WHERE stock > 0")
        for row in cursor.fetchall():
            product_map[f"{row[1]} ({row[2]})"] = row
        conn.close()
    except Exception as e:
        messagebox.showerror("DB Error", str(e))
 
    form_bg = SIDEBAR
    form_outer = tk.Frame(content, bg=form_bg, pady=10)
    form_outer.pack(fill="x", padx=20, pady=10)
 
    section_header(form_outer, "Customer & Product Details", bg=form_bg)
 
    # Product dropdown (auto-fills price, flavor, expiry)
    prod_row = tk.Frame(form_outer, bg=form_bg)
    prod_row.pack(fill="x", padx=20, pady=4)
    tk.Label(prod_row, text="Select Product", font=LBL_FONT,
             fg=MUTED, bg=form_bg, width=20, anchor="w").pack(side="left")
    product_var = tk.StringVar()
    prod_combo = ttk.Combobox(prod_row, values=list(product_map.keys()),
                              textvariable=product_var,
                              font=LBL_FONT, state="readonly", width=26)
    prod_combo.pack(side="left", padx=5)
 
    fields = {}
    for lbl in ["Customer Name", "Customer Phone", "Flavor",
                 "Price (₹)", "Quantity", "Expiry (YYYY-MM-DD)"]:
        fields[lbl] = form_row(form_outer, lbl, bg=form_bg)
 
    total_var = tk.StringVar(value="Total: ₹0.00")
    tk.Label(form_outer, textvariable=total_var, font=("Segoe UI", 13, "bold"),
             fg=ACCENT2, bg=form_bg).pack(pady=5)
 
    def on_product_select(event):
        key = product_var.get()
        if key not in product_map:
            return
        row = product_map[key]
        # id=row[0], name=row[1], flavor=row[2], price=row[3], expiry=row[4]
        fields["Flavor"].delete(0, tk.END)
        fields["Flavor"].insert(0, row[2])
        fields["Price (₹)"].delete(0, tk.END)
        fields["Price (₹)"].insert(0, str(row[3]))
        fields["Expiry (YYYY-MM-DD)"].delete(0, tk.END)
        fields["Expiry (YYYY-MM-DD)"].insert(0, str(row[4]) if row[4] else "")
        update_total()
 
    def update_total(*args):
        try:
            price = float(fields["Price (₹)"].get())
            qty   = int(fields["Quantity"].get())
            total_var.set(f"Total: ₹{price * qty:,.2f}")
        except:
            total_var.set("Total: ₹0.00")
 
    prod_combo.bind("<<ComboboxSelected>>", on_product_select)
    fields["Quantity"].bind("<KeyRelease>", update_total)
 
    def save_sale():
        key = product_var.get()
        if key not in product_map:
            messagebox.showwarning("Validation", "Please select a product.")
            return
        product_id = product_map[key][0]
        cake_name  = product_map[key][1]
 
        cname  = fields["Customer Name"].get().strip()
        cphone = fields["Customer Phone"].get().strip()
        flavor = fields["Flavor"].get().strip()
        price  = fields["Price (₹)"].get().strip()
        qty    = fields["Quantity"].get().strip()
        expiry = fields["Expiry (YYYY-MM-DD)"].get().strip()
 
        if not cname or not qty:
            messagebox.showwarning("Validation", "Customer Name and Quantity are required.")
            return
        try:
            int(qty); float(price)
        except:
            messagebox.showerror("Validation", "Price and Quantity must be numbers.")
            return
 
        try:
            conn = get_connection()
            cursor = conn.cursor()
            # Uses stored procedure — demonstrates DBMS concept
            cursor.callproc("sp_add_sale", [
                product_id, cake_name, cname, cphone,
                flavor, float(price), int(qty), expiry or None
            ])
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Sale saved!\nTotal: ₹{float(price)*int(qty):,.2f}")
            show_sales_entry(content)
        except Exception as e:
            messagebox.showerror("Error", str(e))
 
    btn_row = tk.Frame(form_outer, bg=form_bg)
    btn_row.pack(pady=12)
    styled_button(btn_row, "💾  Save Sale", save_sale, color=SUCCESS).pack(side="left", padx=8)
    styled_button(btn_row, "🔄  Clear", lambda: show_sales_entry(content), color=MUTED).pack(side="left", padx=8)
 
 
# ── 4. VIEW SALES ────────────────────────────────────────
def show_sales_data(content):
    clear_content(content)
 
    tk.Label(content, text="📋  Sales Records",
             font=HDR_FONT, fg=TEXT, bg=BG).pack(pady=(15, 5))
 
    # Filter row
    filter_frame = tk.Frame(content, bg=BG)
    filter_frame.pack(fill="x", padx=20, pady=5)
    tk.Label(filter_frame, text="🔍 Filter by customer/cake:",
             font=LBL_FONT, fg=MUTED, bg=BG).pack(side="left")
    filter_var = tk.StringVar()
    tk.Entry(filter_frame, textvariable=filter_var, font=LBL_FONT,
             bg=SIDEBAR, fg=TEXT, insertbackground=TEXT,
             width=25, relief="flat").pack(side="left", padx=8)
 
    tk.Label(filter_frame, text="Date:", font=LBL_FONT,
             fg=MUTED, bg=BG).pack(side="left", padx=(15, 3))
    date_var = tk.StringVar()
    tk.Entry(filter_frame, textvariable=date_var, font=LBL_FONT,
             bg=SIDEBAR, fg=TEXT, insertbackground=TEXT,
             width=12, relief="flat").pack(side="left")
 
    tframe = tk.Frame(content, bg=BG)
    tframe.pack(fill="both", expand=True, padx=20, pady=5)
 
    cols = ("ID", "Date", "Customer", "Phone", "Cake", "Flavor", "Price", "Qty", "Total (₹)")
    tree = make_treeview(tframe, cols, heights=14)
 
    def load_sales():
        for i in tree.get_children():
            tree.delete(i)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            q = """
                SELECT id, sale_date, customer_name, customer_phone,
                       cake_name, flavor, price, quantity, total_amount
                FROM sales WHERE 1=1
            """
            params = []
            if filter_var.get():
                q += " AND (customer_name LIKE %s OR cake_name LIKE %s)"
                params += [f"%{filter_var.get()}%", f"%{filter_var.get()}%"]
            if date_var.get():
                q += " AND sale_date = %s"
                params.append(date_var.get())
            q += " ORDER BY id DESC"
            cursor.execute(q, params)
            for row in cursor.fetchall():
                tree.insert("", tk.END, values=row)
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", str(e))
 
    filter_var.trace("w", lambda *a: load_sales())
    date_var.trace("w", lambda *a: load_sales())
    load_sales()
 
    def delete_sale():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Please select a sale to delete.")
            return
        sid = tree.item(sel[0])["values"][0]
        if not messagebox.askyesno("Confirm", "Delete this sale record?"):
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sales WHERE id=%s", (sid,))
            conn.commit()
            conn.close()
            load_sales()
            messagebox.showinfo("Deleted", "Record deleted.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
 
    btn_row = tk.Frame(content, bg=BG)
    btn_row.pack(pady=5)
    styled_button(btn_row, "🔄  Refresh", load_sales, color=CARD).pack(side="left", padx=8)
    styled_button(btn_row, "🗑️  Delete Selected", delete_sale, color=DANGER).pack(side="left", padx=8)
 
 
# ── 5. ADVANCE BOOKINGS ──────────────────────────────────
def show_bookings(content):
    clear_content(content)
 
    tk.Label(content, text="📅  Advance Bookings",
             font=HDR_FONT, fg=TEXT, bg=BG).pack(pady=(15, 5))
 
    tframe = tk.Frame(content, bg=BG)
    tframe.pack(fill="both", expand=False, padx=20, pady=5)
 
    cols = ("ID", "Customer", "Phone", "Cake", "Flavor", "Qty",
            "Advance (₹)", "Total (₹)", "Delivery Date", "Status", "Booked On")
    tree = make_treeview(tframe, cols, heights=9)
 
    def load_bookings():
        for i in tree.get_children():
            tree.delete(i)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, customer_name, customer_phone, cake_name, flavor,
                       quantity, advance_paid, total_amount, delivery_date,
                       status, DATE(booked_on)
                FROM advance_bookings ORDER BY delivery_date ASC
            """)
            for row in cursor.fetchall():
                tag = "pending" if row[9] == "Pending" else ("delivered" if row[9] == "Delivered" else "")
                tree.insert("", tk.END, values=row, tags=(tag,))
            tree.tag_configure("pending", foreground=WARNING)
            tree.tag_configure("delivered", foreground=SUCCESS)
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", str(e))
 
    load_bookings()
 
    # Form
    form_bg = SIDEBAR
    form_outer = tk.Frame(content, bg=form_bg, pady=10)
    form_outer.pack(fill="x", padx=20, pady=8)
 
    section_header(form_outer, "New Booking", bg=form_bg)
 
    fields = {}
    for lbl in ["Customer Name", "Customer Phone", "Cake Name", "Flavor",
                 "Quantity", "Advance Paid (₹)", "Total Amount (₹)",
                 "Delivery Date (YYYY-MM-DD)"]:
        fields[lbl] = form_row(form_outer, lbl, bg=form_bg)
 
    status_row = tk.Frame(form_outer, bg=form_bg)
    status_row.pack(fill="x", padx=20, pady=4)
    tk.Label(status_row, text="Status", font=LBL_FONT,
             fg=MUTED, bg=form_bg, width=20, anchor="w").pack(side="left")
    status_combo = ttk.Combobox(status_row,
                                values=["Pending", "Ready", "Delivered", "Cancelled"],
                                font=LBL_FONT, state="readonly", width=26)
    status_combo.set("Pending")
    status_combo.pack(side="left", padx=5)
 
    def on_booking_select(event):
        sel = tree.selection()
        if not sel:
            return
        vals = tree.item(sel[0])["values"]
        keys = list(fields.keys())
        mapping = [1, 2, 3, 4, 5, 6, 7, 8]
        for i, key in enumerate(keys):
            fields[key].delete(0, tk.END)
            fields[key].insert(0, str(vals[mapping[i]]) if mapping[i] < len(vals) else "")
        status_combo.set(vals[9])
 
    tree.bind("<<TreeviewSelect>>", on_booking_select)
 
    def save_booking():
        cname    = fields["Customer Name"].get().strip()
        cphone   = fields["Customer Phone"].get().strip()
        cake     = fields["Cake Name"].get().strip()
        flavor   = fields["Flavor"].get().strip()
        qty      = fields["Quantity"].get().strip()
        advance  = fields["Advance Paid (₹)"].get().strip()
        total    = fields["Total Amount (₹)"].get().strip()
        delivery = fields["Delivery Date (YYYY-MM-DD)"].get().strip()
        status   = status_combo.get()
 
        if not cname or not cake or not delivery:
            messagebox.showwarning("Validation", "Customer Name, Cake Name and Delivery Date are required.")
            return
 
        try:
            conn = get_connection()
            cursor = conn.cursor()
            sel = tree.selection()
            if sel:
                bid = tree.item(sel[0])["values"][0]
                cursor.execute("""
                    UPDATE advance_bookings
                    SET customer_name=%s, customer_phone=%s, cake_name=%s,
                        flavor=%s, quantity=%s, advance_paid=%s,
                        total_amount=%s, delivery_date=%s, status=%s
                    WHERE id=%s
                """, (cname, cphone, cake, flavor, qty or 1,
                      advance or 0, total or 0, delivery, status, bid))
            else:
                cursor.execute("""
                    INSERT INTO advance_bookings
                    (customer_name, customer_phone, cake_name, flavor,
                     quantity, advance_paid, total_amount, delivery_date, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (cname, cphone, cake, flavor, qty or 1,
                      advance or 0, total or 0, delivery, status))
            conn.commit()
            conn.close()
            messagebox.showinfo("Saved", "Booking saved successfully!")
            load_bookings()
        except Exception as e:
            messagebox.showerror("Error", str(e))
 
    def delete_booking():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select a booking to delete.")
            return
        bid = tree.item(sel[0])["values"][0]
        if not messagebox.askyesno("Confirm", "Delete this booking?"):
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM advance_bookings WHERE id=%s", (bid,))
            conn.commit()
            conn.close()
            load_bookings()
        except Exception as e:
            messagebox.showerror("Error", str(e))
 
    btn_row = tk.Frame(form_outer, bg=form_bg)
    btn_row.pack(pady=10)
    styled_button(btn_row, "💾  Save Booking", save_booking, color=SUCCESS).pack(side="left", padx=8)
    styled_button(btn_row, "🗑️  Delete", delete_booking, color=DANGER).pack(side="left", padx=8)
    styled_button(btn_row, "🔄  Refresh", load_bookings, color=CARD).pack(side="left", padx=8)
 
 
# ── 6. DAILY CASH ────────────────────────────────────────
def show_daily_cash(content):
    clear_content(content)
 
    tk.Label(content, text="💵  Daily Cash Ledger",
             font=HDR_FONT, fg=TEXT, bg=BG).pack(pady=(15, 5))
 
    tframe = tk.Frame(content, bg=BG)
    tframe.pack(fill="both", expand=False, padx=20, pady=5)
 
    cols = ("ID", "Date", "Cash In (₹)", "Cash Out (₹)", "Balance (₹)", "Notes")
    tree = make_treeview(tframe, cols, heights=8)
    for col in cols:
        tree.column(col, width=130 if col != "Notes" else 250)
 
    def load_cash():
        for i in tree.get_children():
            tree.delete(i)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, entry_date, cash_in, cash_out, balance, notes
                FROM daily_cash ORDER BY entry_date DESC
            """)
            for row in cursor.fetchall():
                tag = "profit" if (row[4] or 0) >= 0 else "loss"
                tree.insert("", tk.END, values=row, tags=(tag,))
            tree.tag_configure("profit", foreground=SUCCESS)
            tree.tag_configure("loss",   foreground=DANGER)
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", str(e))
 
    load_cash()
 
    form_bg = SIDEBAR
    form_outer = tk.Frame(content, bg=form_bg, pady=10)
    form_outer.pack(fill="x", padx=20, pady=8)
 
    section_header(form_outer, "Add / Update Cash Entry", bg=form_bg)
 
    fields = {}
    for lbl in ["Date (YYYY-MM-DD)", "Cash In (₹)", "Cash Out (₹)", "Notes"]:
        fields[lbl] = form_row(form_outer, lbl, bg=form_bg)
 
    fields["Date (YYYY-MM-DD)"].insert(0, str(date.today()))
 
    def save_cash():
        entry_date = fields["Date (YYYY-MM-DD)"].get().strip()
        cash_in    = fields["Cash In (₹)"].get().strip() or "0"
        cash_out   = fields["Cash Out (₹)"].get().strip() or "0"
        notes      = fields["Notes"].get().strip()
 
        if not entry_date:
            messagebox.showwarning("Validation", "Date is required.")
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            # INSERT … ON DUPLICATE KEY UPDATE (upsert) — demonstrates DBMS concept
            cursor.execute("""
                INSERT INTO daily_cash (entry_date, cash_in, cash_out, notes)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    cash_in  = VALUES(cash_in),
                    cash_out = VALUES(cash_out),
                    notes    = VALUES(notes)
            """, (entry_date, cash_in, cash_out, notes))
            conn.commit()
            conn.close()
            messagebox.showinfo("Saved", "Cash entry saved!")
            load_cash()
        except Exception as e:
            messagebox.showerror("Error", str(e))
 
    btn_row = tk.Frame(form_outer, bg=form_bg)
    btn_row.pack(pady=10)
    styled_button(btn_row, "💾  Save Entry", save_cash, color=SUCCESS).pack(side="left", padx=8)
    styled_button(btn_row, "🔄  Refresh", load_cash, color=CARD).pack(side="left", padx=8)
 
 
# ── 7. EXPENSES ──────────────────────────────────────────
def show_expenses(content):
    clear_content(content)
 
    tk.Label(content, text="💸  Expense Tracker",
             font=HDR_FONT, fg=TEXT, bg=BG).pack(pady=(15, 5))
 
    tframe = tk.Frame(content, bg=BG)
    tframe.pack(fill="both", expand=False, padx=20, pady=5)
 
    cols = ("ID", "Date", "Category", "Description", "Amount (₹)")
    tree = make_treeview(tframe, cols, heights=9)
 
    def load_expenses():
        for i in tree.get_children():
            tree.delete(i)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, expense_date, category, description, amount
                FROM expenses ORDER BY expense_date DESC
            """)
            for row in cursor.fetchall():
                tree.insert("", tk.END, values=row)
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", str(e))
 
    load_expenses()
 
    form_bg = SIDEBAR
    form_outer = tk.Frame(content, bg=form_bg, pady=10)
    form_outer.pack(fill="x", padx=20, pady=8)
 
    section_header(form_outer, "Add Expense", bg=form_bg)
 
    fields = {}
    for lbl in ["Date (YYYY-MM-DD)", "Description", "Amount (₹)"]:
        fields[lbl] = form_row(form_outer, lbl, bg=form_bg)
    fields["Date (YYYY-MM-DD)"].insert(0, str(date.today()))
 
    cat_row = tk.Frame(form_outer, bg=form_bg)
    cat_row.pack(fill="x", padx=20, pady=4)
    tk.Label(cat_row, text="Category", font=LBL_FONT,
             fg=MUTED, bg=form_bg, width=20, anchor="w").pack(side="left")
    cat_combo = ttk.Combobox(cat_row,
                             values=["Ingredients", "Electricity", "Rent",
                                     "Salary", "Packaging", "Transport", "Other"],
                             font=LBL_FONT, state="readonly", width=26)
    cat_combo.set("Ingredients")
    cat_combo.pack(side="left", padx=5)
 
    def save_expense():
        exp_date = fields["Date (YYYY-MM-DD)"].get().strip()
        desc     = fields["Description"].get().strip()
        amount   = fields["Amount (₹)"].get().strip()
        category = cat_combo.get()
 
        if not exp_date or not amount:
            messagebox.showwarning("Validation", "Date and Amount are required.")
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO expenses (expense_date, category, description, amount)
                VALUES (%s, %s, %s, %s)
            """, (exp_date, category, desc, amount))
            conn.commit()
            conn.close()
            messagebox.showinfo("Saved", "Expense recorded!")
            load_expenses()
        except Exception as e:
            messagebox.showerror("Error", str(e))
 
    def delete_expense():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Select", "Select an expense to delete.")
            return
        eid = tree.item(sel[0])["values"][0]
        if not messagebox.askyesno("Confirm", "Delete this expense?"):
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM expenses WHERE id=%s", (eid,))
            conn.commit()
            conn.close()
            load_expenses()
        except Exception as e:
            messagebox.showerror("Error", str(e))
 
    btn_row = tk.Frame(form_outer, bg=form_bg)
    btn_row.pack(pady=10)
    styled_button(btn_row, "💾  Save Expense", save_expense, color=SUCCESS).pack(side="left", padx=8)
    styled_button(btn_row, "🗑️  Delete", delete_expense, color=DANGER).pack(side="left", padx=8)
    styled_button(btn_row, "🔄  Refresh", load_expenses, color=CARD).pack(side="left", padx=8)
 
 
# ── 8. REPORTS ───────────────────────────────────────────
def show_reports(content):
    clear_content(content)
 
    tk.Label(content, text="📊  Reports & Analytics",
             font=HDR_FONT, fg=TEXT, bg=BG).pack(pady=(15, 5))
 
    # ── Monthly Revenue (from VIEW) ──
    section_header(content, "Monthly Revenue Summary  (SQL View: vw_monthly_revenue)")
    tframe1 = tk.Frame(content, bg=BG)
    tframe1.pack(fill="x", padx=20, pady=5)
    cols1 = ("Year", "Month", "Revenue (₹)", "Orders")
    tree1 = make_treeview(tframe1, cols1, heights=5)
 
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT yr, month_name, revenue, orders FROM vw_monthly_revenue")
        for row in cursor.fetchall():
            tree1.insert("", tk.END, values=row)
    except Exception as e:
        pass
 
    # ── Product Sales Report (from Stored Procedure) ──
    section_header(content, "Product Performance  (Stored Procedure: sp_product_sales_report)")
    tframe2 = tk.Frame(content, bg=BG)
    tframe2.pack(fill="both", expand=True, padx=20, pady=5)
    cols2 = ("ID", "Name", "Flavor", "Price", "Stock Left", "Units Sold", "Revenue (₹)")
    tree2 = make_treeview(tframe2, cols2, heights=8)
 
    try:
        cursor.callproc("sp_product_sales_report")
        for result in cursor.stored_results():
            for row in result.fetchall():
                tree2.insert("", tk.END, values=row)
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", str(e))
 
    # Profit summary
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COALESCE((SELECT SUM(total_amount) FROM sales WHERE MONTH(sale_date)=MONTH(CURDATE()) AND YEAR(sale_date)=YEAR(CURDATE())), 0) AS revenue,
                COALESCE((SELECT SUM(amount) FROM expenses WHERE MONTH(expense_date)=MONTH(CURDATE()) AND YEAR(expense_date)=YEAR(CURDATE())), 0) AS expenses
        """)
        rev, exp = cursor.fetchone()
        profit = float(rev) - float(exp)
        conn.close()
 
        summary = tk.Frame(content, bg=CARD, pady=12, padx=20)
        summary.pack(fill="x", padx=20, pady=10)
        tk.Label(summary, text=f"This Month:   Revenue ₹{float(rev):,.2f}   |   Expenses ₹{float(exp):,.2f}   |   Net Profit ₹{profit:,.2f}",
                 font=("Segoe UI", 12, "bold"),
                 fg=SUCCESS if profit >= 0 else DANGER, bg=CARD).pack()
    except:
        pass
 
 
# ═══════════════════════════════════════════════════════════
#  MAIN APPLICATION WINDOW
# ═══════════════════════════════════════════════════════════
root = tk.Tk()
root.title("🎂 Cake Shop Management System")
root.geometry("1100x680")
root.configure(bg=BG)
root.resizable(True, True)
 
# ── LOGIN FRAME ─────────────────────────────────────────
login_frame = tk.Frame(root, bg=BG)
login_frame.pack(fill="both", expand=True)
 
center = tk.Frame(login_frame, bg=CARD, padx=50, pady=40)
center.place(relx=0.5, rely=0.5, anchor="center")
 
tk.Label(center, text="🎂", font=("Segoe UI", 48), bg=CARD).pack()
tk.Label(center, text="CAKE SHOP",
         font=("Segoe UI", 22, "bold"), fg=ACCENT2, bg=CARD).pack()
tk.Label(center, text="Management System",
         font=("Segoe UI", 12), fg=MUTED, bg=CARD).pack(pady=(0, 25))
 
tk.Label(center, text="Username", font=LBL_FONT, fg=MUTED, bg=CARD).pack(anchor="w")
username_entry = tk.Entry(center, font=("Segoe UI", 12), bg=SIDEBAR,
                          fg=TEXT, insertbackground=TEXT, relief="flat",
                          width=28)
username_entry.pack(pady=(3, 12), ipady=6)
 
tk.Label(center, text="Password", font=LBL_FONT, fg=MUTED, bg=CARD).pack(anchor="w")
password_entry = tk.Entry(center, font=("Segoe UI", 12), bg=SIDEBAR,
                          fg=TEXT, insertbackground=TEXT, relief="flat",
                          show="*", width=28)
password_entry.pack(pady=(3, 20), ipady=6)
 
def login():
    if username_entry.get() == "admin" and password_entry.get() == "1234":
        try:
            setup_database()
        except Exception as e:
            messagebox.showerror("DB Setup Error", str(e))
            return
        login_frame.pack_forget()
        dashboard_frame.pack(fill="both", expand=True)
        show_home(content)
    else:
        messagebox.showerror("Login Failed", "Invalid username or password.")
 
password_entry.bind("<Return>", lambda e: login())
 
tk.Button(center, text="Login  →", command=login,
          bg=ACCENT, fg="white", font=("Segoe UI", 12, "bold"),
          relief="flat", cursor="hand2", width=22,
          padx=10, pady=8).pack()
 
tk.Label(center, text="Default: admin / 1234",
         font=("Segoe UI", 9), fg=MUTED, bg=CARD).pack(pady=(12, 0))
 
 
# ── DASHBOARD FRAME ──────────────────────────────────────
dashboard_frame = tk.Frame(root, bg=BG)
 
# Sidebar
sidebar = tk.Frame(dashboard_frame, bg=SIDEBAR, width=200)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)
 
# Logo area
logo_frame = tk.Frame(sidebar, bg=ACCENT, height=70)
logo_frame.pack(fill="x")
logo_frame.pack_propagate(False)
tk.Label(logo_frame, text="🎂 CakeShop", font=("Segoe UI", 13, "bold"),
         fg="white", bg=ACCENT).pack(expand=True)
 
# Content area
content = tk.Frame(dashboard_frame, bg=BG)
content.pack(side="right", fill="both", expand=True)
 
# Sidebar nav buttons
nav_items = [
    ("🏠  Dashboard",        lambda: show_home(content)),
    ("🎂  Inventory",        lambda: show_inventory(content)),
    ("🛒  New Sale",         lambda: show_sales_entry(content)),
    ("📋  View Sales",       lambda: show_sales_data(content)),
    ("📅  Advance Bookings", lambda: show_bookings(content)),
    ("💵  Daily Cash",       lambda: show_daily_cash(content)),
    ("💸  Expenses",         lambda: show_expenses(content)),
    ("📊  Reports",          lambda: show_reports(content)),
]
 
for label, cmd in nav_items:
    btn = tk.Button(sidebar, text=label, command=cmd,
                    bg=SIDEBAR, fg=TEXT, font=("Segoe UI", 10),
                    relief="flat", anchor="w", padx=18, pady=10,
                    cursor="hand2", activebackground=CARD,
                    activeforeground=ACCENT2, width=22)
    btn.pack(fill="x")
 
    def on_enter(e, b=btn):
        b.config(bg=CARD, fg=ACCENT2)
    def on_leave(e, b=btn):
        b.config(bg=SIDEBAR, fg=TEXT)
 
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
 
# Divider
tk.Frame(sidebar, bg=MUTED, height=1).pack(fill="x", pady=10, padx=15)
 
def logout():
    if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
        dashboard_frame.pack_forget()
        username_entry.delete(0, tk.END)
        password_entry.delete(0, tk.END)
        login_frame.pack(fill="both", expand=True)
 
tk.Button(sidebar, text="🚪  Logout", command=logout,
          bg=SIDEBAR, fg=DANGER, font=("Segoe UI", 10, "bold"),
          relief="flat", anchor="w", padx=18, pady=10,
          cursor="hand2", width=22).pack(fill="x", side="bottom", pady=5)
 
# ── RUN ─────────────────────────────────────────────────
root.mainloop()