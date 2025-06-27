from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    CUSTOMER = "customer"
    RESTAURANT_ADMIN = "restaurant_admin"
    SUPER_ADMIN = "super_admin"

# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleLogin(BaseModel):
    google_token: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    phone: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime

# Restaurant schemas
class RestaurantCreate(BaseModel):
    name: str
    description: Optional[str] = None
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    category_id: int
    image_url: Optional[str] = None
    opening_hours: Optional[Dict[str, Any]] = None

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = None
    opening_hours: Optional[Dict[str, Any]] = None

class RestaurantResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    address: str
    latitude: Optional[float]
    longitude: Optional[float]
    phone: Optional[str]
    email: Optional[str]
    category_id: int
    category_name: Optional[str]
    owner_id: int
    image_url: Optional[str]
    opening_hours: Optional[Dict[str, Any]]
    is_active: bool
    rating: float
    total_reviews: int
    created_at: datetime

# Menu Category schemas
class MenuCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    display_order: Optional[int] = 0

class MenuCategoryResponse(BaseModel):
    id: int
    restaurant_id: int
    name: str
    description: Optional[str]
    display_order: int
    is_active: bool
    created_at: datetime

# Menu Item schemas
class MenuItemCreate(BaseModel):
    menu_category_id: int
    name: str
    description: Optional[str] = None
    price: Dict[str, Any]  # JSON for different pricing options
    image_url: Optional[str] = None
    is_vegetarian: Optional[bool] = False
    is_vegan: Optional[bool] = False
    is_gluten_free: Optional[bool] = False
    ingredients: Optional[List[str]] = []
    allergens: Optional[List[str]] = []
    display_order: Optional[int] = 0

class MenuItemUpdate(BaseModel):
    menu_category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    is_vegetarian: Optional[bool] = None
    is_vegan: Optional[bool] = None
    is_gluten_free: Optional[bool] = None
    ingredients: Optional[List[str]] = None
    allergens: Optional[List[str]] = None
    is_available: Optional[bool] = None
    display_order: Optional[int] = None

class MenuItemResponse(BaseModel):
    id: int
    restaurant_id: int
    menu_category_id: int
    category_name: Optional[str]
    name: str
    description: Optional[str]
    price: Dict[str, Any]
    image_url: Optional[str]
    is_vegetarian: bool
    is_vegan: bool
    is_gluten_free: bool
    ingredients: List[str]
    allergens: List[str]
    is_available: bool
    display_order: int
    created_at: datetime

# Review schemas
class ReviewCreate(BaseModel):
    rating: int
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    restaurant_id: int
    user_id: int
    user_name: str
    rating: int
    comment: Optional[str]
    created_at: datetime

# Category schemas
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    is_active: bool
    created_at: datetime

# Location schema
class LocationUpdate(BaseModel):
    latitude: float
    longitude: float
    address: str

# Token schema
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
