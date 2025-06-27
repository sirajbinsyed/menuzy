from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from models.schemas import RestaurantResponse, ReviewCreate, ReviewResponse, MenuItemResponse
from database.connection import get_db_connection
from utils.auth import get_current_user_id
from psycopg2.extras import RealDictCursor
from typing import List, Optional
import json

router = APIRouter()
security = HTTPBearer()

@router.get("/nearby", response_model=List[RestaurantResponse])
async def get_nearby_restaurants(
    latitude: float = Query(..., description="User's latitude"),
    longitude: float = Query(..., description="User's longitude"),
    radius: float = Query(10.0, description="Search radius in kilometers"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    limit: int = Query(20, description="Number of results to return")
):
    """Get nearby restaurants based on GPS coordinates"""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        base_query = """
            SELECT r.*, c.name as category_name,
                   (6371 * acos(cos(radians(%s)) * cos(radians(r.latitude)) * 
                   cos(radians(r.longitude) - radians(%s)) + 
                   sin(radians(%s)) * sin(radians(r.latitude)))) AS distance
            FROM restaurants r
            LEFT JOIN categories c ON r.category_id = c.id
            WHERE r.is_active = TRUE AND r.latitude IS NOT NULL AND r.longitude IS NOT NULL
        """
        
        params = [latitude, longitude, latitude]
        
        if category_id:
            base_query += " AND r.category_id = %s"
            params.append(category_id)
        
        base_query += """
            HAVING distance <= %s
            ORDER BY distance
            LIMIT %s
        """
        params.extend([radius, limit])
        
        cursor.execute(base_query, params)
        restaurants = cursor.fetchall()
        
        return [dict(restaurant) for restaurant in restaurants]

@router.get("/search", response_model=List[RestaurantResponse])
async def search_restaurants(
    q: str = Query(..., description="Search query"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    limit: int = Query(20, description="Number of results to return")
):
    """Search restaurants by name or location"""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        base_query = """
            SELECT r.*, c.name as category_name
            FROM restaurants r
            LEFT JOIN categories c ON r.category_id = c.id
            WHERE r.is_active = TRUE AND (
                r.name ILIKE %s OR 
                r.description ILIKE %s OR 
                r.address ILIKE %s
            )
        """
        
        search_term = f"%{q}%"
        params = [search_term, search_term, search_term]
        
        if category_id:
            base_query += " AND r.category_id = %s"
            params.append(category_id)
        
        base_query += " ORDER BY r.rating DESC, r.name LIMIT %s"
        params.append(limit)
        
        cursor.execute(base_query, params)
        restaurants = cursor.fetchall()
        
        return [dict(restaurant) for restaurant in restaurants]

@router.get("/{restaurant_id}", response_model=RestaurantResponse)
async def get_restaurant_detail(restaurant_id: int):
    """Get detailed information about a specific restaurant"""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT r.*, c.name as category_name
            FROM restaurants r
            LEFT JOIN categories c ON r.category_id = c.id
            WHERE r.id = %s AND r.is_active = TRUE
        """, (restaurant_id,))
        
        restaurant = cursor.fetchone()
        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )
        
        return dict(restaurant)

@router.get("/{restaurant_id}/menu", response_model=List[MenuItemResponse])
async def get_restaurant_menu(restaurant_id: int):
    """Get menu items for a specific restaurant"""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # First check if restaurant exists
        cursor.execute("SELECT id FROM restaurants WHERE id = %s AND is_active = TRUE", (restaurant_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )
        
        cursor.execute("""
            SELECT mi.*, mc.name as category_name
            FROM menu_items mi
            LEFT JOIN menu_categories mc ON mi.menu_category_id = mc.id
            WHERE mi.restaurant_id = %s AND mi.is_available = TRUE
            ORDER BY mc.display_order, mi.display_order, mi.name
        """, (restaurant_id,))
        
        menu_items = cursor.fetchall()
        return [dict(item) for item in menu_items]

@router.post("/{restaurant_id}/review", response_model=ReviewResponse)
async def add_review(
    restaurant_id: int,
    review: ReviewCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Add a review for a restaurant (requires authentication)"""
    user_id = get_current_user_id(credentials.credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if restaurant exists
        cursor.execute("SELECT id FROM restaurants WHERE id = %s AND is_active = TRUE", (restaurant_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )
        
        # Check if user already reviewed this restaurant
        cursor.execute("""
            SELECT id FROM reviews WHERE restaurant_id = %s AND user_id = %s
        """, (restaurant_id, user_id))
        
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this restaurant"
            )
        
        # Add review
        cursor.execute("""
            INSERT INTO reviews (restaurant_id, user_id, rating, comment)
            VALUES (%s, %s, %s, %s)
            RETURNING id, restaurant_id, user_id, rating, comment, created_at
        """, (restaurant_id, user_id, review.rating, review.comment))
        
        new_review = cursor.fetchone()
        
        # Update restaurant rating
        cursor.execute("""
            UPDATE restaurants SET 
                rating = (SELECT AVG(rating)::DECIMAL(3,2) FROM reviews WHERE restaurant_id = %s),
                total_reviews = (SELECT COUNT(*) FROM reviews WHERE restaurant_id = %s)
            WHERE id = %s
        """, (restaurant_id, restaurant_id, restaurant_id))
        
        # Get user name for response
        cursor.execute("SELECT full_name FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        conn.commit()
        
        review_data = dict(new_review)
        review_data["user_name"] = user["full_name"]
        
        return review_data

@router.get("/{restaurant_id}/reviews", response_model=List[ReviewResponse])
async def get_restaurant_reviews(restaurant_id: int, limit: int = Query(50)):
    """Get reviews for a specific restaurant"""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT r.*, u.full_name as user_name
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            WHERE r.restaurant_id = %s
            ORDER BY r.created_at DESC
            LIMIT %s
        """, (restaurant_id, limit))
        
        reviews = cursor.fetchall()
        return [dict(review) for review in reviews]

@router.post("/favorites/{restaurant_id}")
async def add_to_favorites(
    restaurant_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Add restaurant to user's favorites"""
    user_id = get_current_user_id(credentials.credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if restaurant exists
        cursor.execute("SELECT id FROM restaurants WHERE id = %s AND is_active = TRUE", (restaurant_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )
        
        # Add to favorites (ignore if already exists)
        cursor.execute("""
            INSERT INTO favorites (user_id, restaurant_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, restaurant_id) DO NOTHING
        """, (user_id, restaurant_id))
        
        conn.commit()
        
        return {"message": "Restaurant added to favorites"}

@router.delete("/favorites/{restaurant_id}")
async def remove_from_favorites(
    restaurant_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Remove restaurant from user's favorites"""
    user_id = get_current_user_id(credentials.credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM favorites WHERE user_id = %s AND restaurant_id = %s
        """, (user_id, restaurant_id))
        
        conn.commit()
        
        return {"message": "Restaurant removed from favorites"}

@router.get("/favorites/my", response_model=List[RestaurantResponse])
async def get_my_favorites(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get user's favorite restaurants"""
    user_id = get_current_user_id(credentials.credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT r.*, c.name as category_name
            FROM restaurants r
            JOIN favorites f ON r.id = f.restaurant_id
            LEFT JOIN categories c ON r.category_id = c.id
            WHERE f.user_id = %s AND r.is_active = TRUE
            ORDER BY f.created_at DESC
        """, (user_id,))
        
        favorites = cursor.fetchall()
        return [dict(restaurant) for restaurant in favorites]
