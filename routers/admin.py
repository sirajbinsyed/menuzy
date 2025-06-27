from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from models.schemas import (
    MenuItemCreate, MenuItemUpdate, MenuItemResponse,
    MenuCategoryCreate, MenuCategoryResponse,
    LocationUpdate, ReviewResponse
)
from database.connection import get_db_connection
from utils.auth import get_current_user_id, get_current_user_role
from psycopg2.extras import RealDictCursor
from typing import List
import json

router = APIRouter()
security = HTTPBearer()

def verify_restaurant_admin(credentials: HTTPAuthorizationCredentials, restaurant_id: int = None):
    """Verify user is restaurant admin and optionally owns the restaurant"""
    user_id = get_current_user_id(credentials.credentials)
    user_role = get_current_user_role(credentials.credentials)
    
    if user_role not in ["restaurant_admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access restaurant admin features"
        )
    
    if restaurant_id and user_role == "restaurant_admin":
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT owner_id FROM restaurants WHERE id = %s", (restaurant_id,))
            restaurant = cursor.fetchone()
            
            if not restaurant or restaurant[0] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to manage this restaurant"
                )
    
    return user_id

@router.get("/restaurant")
async def get_my_restaurant(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get restaurant owned by current admin"""
    user_id = verify_restaurant_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT r.*, c.name as category_name
            FROM restaurants r
            LEFT JOIN categories c ON r.category_id = c.id
            WHERE r.owner_id = %s
        """, (user_id,))
        
        restaurant = cursor.fetchone()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No restaurant found for this admin"
            )
        
        return dict(restaurant)

@router.get("/menu-categories", response_model=List[MenuCategoryResponse])
async def get_menu_categories(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get menu categories for admin's restaurant"""
    user_id = verify_restaurant_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get restaurant ID
        cursor.execute("SELECT id FROM restaurants WHERE owner_id = %s", (user_id,))
        restaurant = cursor.fetchone()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No restaurant found"
            )
        
        cursor.execute("""
            SELECT * FROM menu_categories 
            WHERE restaurant_id = %s AND is_active = TRUE
            ORDER BY display_order, name
        """, (restaurant["id"],))
        
        categories = cursor.fetchall()
        return [dict(category) for category in categories]

@router.post("/menu-categories", response_model=MenuCategoryResponse)
async def create_menu_category(
    category: MenuCategoryCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new menu category"""
    user_id = verify_restaurant_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get restaurant ID
        cursor.execute("SELECT id FROM restaurants WHERE owner_id = %s", (user_id,))
        restaurant = cursor.fetchone()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No restaurant found"
            )
        
        cursor.execute("""
            INSERT INTO menu_categories (restaurant_id, name, description, display_order)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """, (restaurant["id"], category.name, category.description, category.display_order))
        
        new_category = cursor.fetchone()
        conn.commit()
        
        return dict(new_category)

@router.get("/menu", response_model=List[MenuItemResponse])
async def get_menu_items(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get all menu items for admin's restaurant"""
    user_id = verify_restaurant_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get restaurant ID
        cursor.execute("SELECT id FROM restaurants WHERE owner_id = %s", (user_id,))
        restaurant = cursor.fetchone()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No restaurant found"
            )
        
        cursor.execute("""
            SELECT mi.*, mc.name as category_name
            FROM menu_items mi
            LEFT JOIN menu_categories mc ON mi.menu_category_id = mc.id
            WHERE mi.restaurant_id = %s
            ORDER BY mc.display_order, mi.display_order, mi.name
        """, (restaurant["id"],))
        
        menu_items = cursor.fetchall()
        return [dict(item) for item in menu_items]

@router.post("/menu", response_model=MenuItemResponse)
async def create_menu_item(
    menu_item: MenuItemCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new menu item"""
    user_id = verify_restaurant_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get restaurant ID
        cursor.execute("SELECT id FROM restaurants WHERE owner_id = %s", (user_id,))
        restaurant = cursor.fetchone()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No restaurant found"
            )
        
        restaurant_id = restaurant["id"]
        
        # Verify menu category belongs to this restaurant
        cursor.execute("""
            SELECT id FROM menu_categories 
            WHERE id = %s AND restaurant_id = %s
        """, (menu_item.menu_category_id, restaurant_id))
        
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid menu category"
            )
        
        cursor.execute("""
            INSERT INTO menu_items (
                restaurant_id, menu_category_id, name, description, price,
                image_url, is_vegetarian, is_vegan, is_gluten_free,
                ingredients, allergens, display_order
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            restaurant_id, menu_item.menu_category_id, menu_item.name,
            menu_item.description, json.dumps(menu_item.price), menu_item.image_url,
            menu_item.is_vegetarian, menu_item.is_vegan, menu_item.is_gluten_free,
            menu_item.ingredients, menu_item.allergens, menu_item.display_order
        ))
        
        new_item = cursor.fetchone()
        
        # Get category name
        cursor.execute("SELECT name FROM menu_categories WHERE id = %s", (menu_item.menu_category_id,))
        category = cursor.fetchone()
        
        conn.commit()
        
        item_data = dict(new_item)
        item_data["category_name"] = category["name"] if category else None
        
        return item_data

@router.put("/menu/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    item_id: int,
    menu_item: MenuItemUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a menu item"""
    user_id = verify_restaurant_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get restaurant ID and verify ownership
        cursor.execute("SELECT id FROM restaurants WHERE owner_id = %s", (user_id,))
        restaurant = cursor.fetchone()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No restaurant found"
            )
        
        restaurant_id = restaurant["id"]
        
        # Verify menu item belongs to this restaurant
        cursor.execute("""
            SELECT * FROM menu_items WHERE id = %s AND restaurant_id = %s
        """, (item_id, restaurant_id))
        
        existing_item = cursor.fetchone()
        if not existing_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        for field, value in menu_item.dict(exclude_unset=True).items():
            if field == "price" and value is not None:
                update_fields.append(f"{field} = %s")
                params.append(json.dumps(value))
            elif value is not None:
                update_fields.append(f"{field} = %s")
                params.append(value)
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        params.append(item_id)
        
        cursor.execute(f"""
            UPDATE menu_items SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING *
        """, params)
        
        updated_item = cursor.fetchone()
        
        # Get category name
        cursor.execute("SELECT name FROM menu_categories WHERE id = %s", (updated_item["menu_category_id"],))
        category = cursor.fetchone()
        
        conn.commit()
        
        item_data = dict(updated_item)
        item_data["category_name"] = category["name"] if category else None
        
        return item_data

@router.delete("/menu/{item_id}")
async def delete_menu_item(
    item_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a menu item"""
    user_id = verify_restaurant_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get restaurant ID
        cursor.execute("SELECT id FROM restaurants WHERE owner_id = %s", (user_id,))
        restaurant = cursor.fetchone()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No restaurant found"
            )
        
        # Delete menu item
        cursor.execute("""
            DELETE FROM menu_items WHERE id = %s AND restaurant_id = %s
        """, (item_id, restaurant[0]))
        
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )
        
        conn.commit()
        
        return {"message": "Menu item deleted successfully"}

@router.put("/location")
async def update_location(
    location: LocationUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update restaurant location"""
    user_id = verify_restaurant_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE restaurants SET 
                latitude = %s, longitude = %s, address = %s, updated_at = CURRENT_TIMESTAMP
            WHERE owner_id = %s
        """, (location.latitude, location.longitude, location.address, user_id))
        
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )
        
        conn.commit()
        
        return {"message": "Location updated successfully"}

@router.get("/reviews", response_model=List[ReviewResponse])
async def get_restaurant_reviews(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get all reviews for admin's restaurant"""
    user_id = verify_restaurant_admin(credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get restaurant ID
        cursor.execute("SELECT id FROM restaurants WHERE owner_id = %s", (user_id,))
        restaurant = cursor.fetchone()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No restaurant found"
            )
        
        cursor.execute("""
            SELECT r.*, u.full_name as user_name
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            WHERE r.restaurant_id = %s
            ORDER BY r.created_at DESC
        """, (restaurant["id"],))
        
        reviews = cursor.fetchall()
        return [dict(review) for review in reviews]
