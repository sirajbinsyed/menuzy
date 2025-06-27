from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from models.schemas import (
    RestaurantCreate, RestaurantUpdate, RestaurantResponse,
    CategoryCreate, CategoryResponse, UserResponse, UserCreate
)
from database.connection import get_db_connection
from utils.auth import get_current_user_role, hash_password
from psycopg2.extras import RealDictCursor
from typing import List

router = APIRouter()
security = HTTPBearer()

def verify_super_admin(credentials: HTTPAuthorizationCredentials):
    """Verify user is super admin"""
    user_role = get_current_user_role(credentials.credentials)
    
    if user_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )

@router.get("/dashboard")
async def get_dashboard_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get dashboard statistics for super admin"""
    verify_super_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get various statistics
        cursor.execute("SELECT COUNT(*) as total_restaurants FROM restaurants WHERE is_active = TRUE")
        restaurants_count = cursor.fetchone()["total_restaurants"]
        
        cursor.execute("SELECT COUNT(*) as total_users FROM users WHERE is_active = TRUE")
        users_count = cursor.fetchone()["total_users"]
        
        cursor.execute("SELECT COUNT(*) as total_reviews FROM reviews")
        reviews_count = cursor.fetchone()["total_reviews"]
        
        cursor.execute("SELECT COUNT(*) as total_categories FROM categories WHERE is_active = TRUE")
        categories_count = cursor.fetchone()["total_categories"]
        
        return {
            "total_restaurants": restaurants_count,
            "total_users": users_count,
            "total_reviews": reviews_count,
            "total_categories": categories_count
        }

@router.post("/create-restaurant", response_model=RestaurantResponse)
async def create_restaurant_with_owner(
    restaurant_data: RestaurantCreate,
    owner_email: str,
    owner_name: str,
    owner_phone: str = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new restaurant and assign an owner"""
    verify_super_admin(credentials)
    print(restaurant_data)
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if owner email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (owner_email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            owner_id = existing_user["id"]
            # Update user role to restaurant_admin
            cursor.execute("""
                UPDATE users SET role = 'restaurant_admin' WHERE id = %s
            """, (owner_id,))
        else:
            # Create new restaurant admin user
            cursor.execute("""
                INSERT INTO users (email, full_name, phone, role)
                VALUES (%s, %s, %s, 'restaurant_admin')
                RETURNING id
            """, (owner_email, owner_name, owner_phone))
            owner_id = cursor.fetchone()["id"]
        
        # Create restaurant
        cursor.execute("""
            INSERT INTO restaurants (
                name, description, address, latitude, longitude,
                phone, email, category_id, owner_id, image_url, opening_hours
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            restaurant_data.name, restaurant_data.description, restaurant_data.address,
            restaurant_data.latitude, restaurant_data.longitude, restaurant_data.phone,
            restaurant_data.email, restaurant_data.category_id, owner_id,
            restaurant_data.image_url, restaurant_data.opening_hours
        ))
        
        new_restaurant = cursor.fetchone()
        
        # Get category name
        cursor.execute("SELECT name FROM categories WHERE id = %s", (restaurant_data.category_id,))
        category = cursor.fetchone()
        
        conn.commit()
        
        restaurant_data = dict(new_restaurant)
        restaurant_data["category_name"] = category["name"] if category else None
        
        return restaurant_data

@router.get("/restaurants", response_model=List[RestaurantResponse])
async def get_all_restaurants(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get all restaurants"""
    verify_super_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT r.*, c.name as category_name
            FROM restaurants r
            LEFT JOIN categories c ON r.category_id = c.id
            ORDER BY r.created_at DESC
        """)
        
        restaurants = cursor.fetchall()
        return [dict(restaurant) for restaurant in restaurants]

@router.put("/restaurant/{restaurant_id}", response_model=RestaurantResponse)
async def update_restaurant(
    restaurant_id: int,
    restaurant_data: RestaurantUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update restaurant information"""
    verify_super_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        for field, value in restaurant_data.dict(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = %s")
                params.append(value)
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        params.append(restaurant_id)
        
        cursor.execute(f"""
            UPDATE restaurants SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING *
        """, params)
        
        updated_restaurant = cursor.fetchone()
        
        if not updated_restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )
        
        # Get category name
        cursor.execute("SELECT name FROM categories WHERE id = %s", (updated_restaurant["category_id"],))
        category = cursor.fetchone()
        
        conn.commit()
        
        restaurant_data = dict(updated_restaurant)
        restaurant_data["category_name"] = category["name"] if category else None
        
        return restaurant_data

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get all users"""
    verify_super_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, email, full_name, phone, role, is_active, created_at
            FROM users
            ORDER BY created_at DESC
        """)
        
        users = cursor.fetchall()
        return [dict(user) for user in users]

@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user_details(
    user_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get detailed information about a specific user"""
    verify_super_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, email, full_name, phone, role, is_active, created_at
            FROM users WHERE id = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return dict(user)

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get all categories"""
    verify_super_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM categories ORDER BY name")
        categories = cursor.fetchall()
        return [dict(category) for category in categories]

@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    category: CategoryCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new category"""
    verify_super_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            INSERT INTO categories (name, description, icon)
            VALUES (%s, %s, %s)
            RETURNING *
        """, (category.name, category.description, category.icon))
        
        new_category = cursor.fetchone()
        conn.commit()
        
        return dict(new_category)

@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category: CategoryCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a category"""
    verify_super_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            UPDATE categories SET name = %s, description = %s, icon = %s
            WHERE id = %s
            RETURNING *
        """, (category.name, category.description, category.icon, category_id))
        
        updated_category = cursor.fetchone()
        
        if not updated_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        conn.commit()
        
        return dict(updated_category)

@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a category"""
    verify_super_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if category is being used by restaurants
        cursor.execute("SELECT COUNT(*) FROM restaurants WHERE category_id = %s", (category_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete category that is being used by restaurants"
            )
        
        cursor.execute("DELETE FROM categories WHERE id = %s", (category_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        conn.commit()
        
        return {"message": "Category deleted successfully"}
