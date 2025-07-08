import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from datetime import datetime

# Initialize FastAPI app
app = FastAPI()

# --- IMPORTANT CORS Configuration ---
# You MUST replace "https://your-juice-shop-frontend.vercel.app" with the actual domain of your Vercel frontend.
# This ensures that only your frontend can make requests to your backend API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://juice-wine.vercel.app"], # <--- REPLACE THIS WITH YOUR ACTUAL VERCEL FRONTEND URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Setup ---
def init_db():
    """Initializes the SQLite database and creates tables if they don't exist."""
    conn = sqlite3.connect('juice_shop.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    
    # Create orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity TEXT NOT NULL,
            price REAL NOT NULL,
            order_date TEXT NOT NULL
            -- Note: 'count' per item is handled by inserting multiple rows for now.
            -- A more robust solution for multiple items in one order would be a separate 'order_items' table.
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database when the app starts
init_db()

# --- Pydantic Models for Request Body Validation ---
class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class OrderItem(BaseModel):
    product_name: str
    quantity: str
    price: float

class OrderCreate(BaseModel):
    user_email: str
    items: list[OrderItem]


@app.post("/signup")
async def signup(user: UserCreate):
    conn = sqlite3.connect('juice_shop.db')
    cursor = conn.cursor()
    try:
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered.")
        
        # Insert new user (password hashing is skipped as per your specific showcase requirement)
        cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                       (user.name, user.email, user.password)) # No hashing for showcase
        conn.commit()
        return {"success": True, "message": "User registered successfully!", "user_name": user.name}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/login")
async def login(user: UserLogin):
    conn = sqlite3.connect('juice_shop.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name, password FROM users WHERE email = ?", (user.email,))
        user_record = cursor.fetchone()

        if not user_record:
            raise HTTPException(status_code=400, detail="User not found.")
        
        db_name, db_password = user_record
        
        # Direct password comparison (no hashing for showcase)
        if db_password == user.password:
            return {"success": True, "message": "Login successful!", "user_name": db_name, "user_email": user.email}
        else:
            raise HTTPException(status_code=400, detail="Invalid credentials.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/purchase")
async def create_order(order: OrderCreate):
    conn = sqlite3.connect('juice_shop.db')
    cursor = conn.cursor()
    try:
        order_date = datetime.now().isoformat()
        
        for item in order.items:
            # Insert each item as a separate row for simplicity, based on the count for each item
            cursor.execute(
                "INSERT INTO orders (user_email, product_name, quantity, price, order_date) VALUES (?, ?, ?, ?, ?)",
                (order.user_email, item.product_name, item.quantity, item.price, order_date)
            )

        conn.commit()
        return {"success": True, "message": "Order placed successfully!"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="An error occurred while placing the order.")
    finally:
        conn.close()

@app.get("/orders/{user_email}")
def get_user_orders(user_email: str):
    """Fetches all past orders for a given user email."""
    conn = sqlite3.connect('juice_shop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT product_name, quantity, price, order_date FROM orders WHERE user_email = ?", (user_email,))
    orders_raw = cursor.fetchall()
    conn.close()

    orders_list = []
    for order in orders_raw:
        orders_list.append({
            "product_name": order[0],
            "quantity": order[1],
            "price": order[2],
            "order_date": order[3]
            # 'count' is not directly retrieved here as it's not a column
        })
    return orders_list

# This block is for local development only and will not run on Render when deployed via Procfile
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
