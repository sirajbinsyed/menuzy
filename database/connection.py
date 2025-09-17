import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

# Prefer DATABASE_URL (Render), fallback to manual config for local
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    DB_CONN_STRING = DATABASE_URL
else:
    DB_CONN_STRING = (
        f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
        f"{os.getenv('DB_PASSWORD', 'postgres')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'menuzy')}"
    )

@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(DB_CONN_STRING, cursor_factory=RealDictCursor)
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def init_db():
    """Initialize database with required tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255),
                full_name VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                role VARCHAR(20) DEFAULT 'customer' CHECK (role IN ('customer', 'restaurant_admin', 'super_admin')),
                google_id VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                icon VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Restaurants table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS restaurants (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                address TEXT NOT NULL,
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                phone VARCHAR(20),
                email VARCHAR(255),
                category_id INTEGER REFERENCES categories(id),
                owner_id INTEGER REFERENCES users(id),
                image_url VARCHAR(500),
                opening_hours JSONB,
                is_active BOOLEAN DEFAULT TRUE,
                rating DECIMAL(3, 2) DEFAULT 0.0,
                total_reviews INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Menu categories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_categories (
                id SERIAL PRIMARY KEY,
                restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Menu items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_items (
                id SERIAL PRIMARY KEY,
                restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
                menu_category_id INTEGER REFERENCES menu_categories(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price JSONB NOT NULL,
                image_url VARCHAR(500),
                is_vegetarian BOOLEAN DEFAULT FALSE,
                is_vegan BOOLEAN DEFAULT FALSE,
                is_gluten_free BOOLEAN DEFAULT FALSE,
                ingredients TEXT[],
                allergens TEXT[],
                is_available BOOLEAN DEFAULT TRUE,
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Reviews
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
                restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(restaurant_id, user_id)
            );
        """)
        
        # Favorites
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, restaurant_id)
            );
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_location ON restaurants(latitude, longitude);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_category ON restaurants(category_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_items_restaurant ON menu_items(restaurant_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_restaurant ON reviews(restaurant_id);")
        
        # Default categories
        cursor.execute("""
            INSERT INTO categories (name, description, icon) VALUES
            ('Fast Food', 'Quick service restaurants', '🍔'),
            ('Fine Dining', 'Upscale dining experience', '🍽️'),
            ('Cafe', 'Coffee shops and light meals', '☕'),
            ('Pizza', 'Pizza restaurants', '🍕'),
            ('Asian', 'Asian cuisine', '🥢'),
            ('Italian', 'Italian cuisine', '🍝'),
            ('Mexican', 'Mexican cuisine', '🌮'),
            ('Indian', 'Indian cuisine', '🍛'),
            ('Desserts', 'Dessert and sweet shops', '🍰'),
            ('Healthy', 'Health-focused restaurants', '🥗')
            ON CONFLICT (name) DO NOTHING;
        """)
        
        conn.commit()
        print("✅ Database initialized successfully!")
