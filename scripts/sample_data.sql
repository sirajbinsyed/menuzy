-- Sample data for testing the Menuzy API

-- Insert sample super admin user
INSERT INTO users (email, password_hash, full_name, role) VALUES
('admin@menuzy.com', '$2b$12$LQv3c1yqBwlVHpPjrPyBXOu4TlVHdWpQ2V9jn/ZzO.Qr5K5K5K5K5', 'Super Admin', 'super_admin');

-- Insert sample restaurant admin users
INSERT INTO users (email, password_hash, full_name, phone, role) VALUES
('john@pizzapalace.com', '$2b$12$LQv3c1yqBwlVHpPjrPyBXOu4TlVHdWpQ2V9jn/ZzO.Qr5K5K5K5K5', 'John Smith', '+1234567890', 'restaurant_admin'),
('maria@tacotown.com', '$2b$12$LQv3c1yqBwlVHpPjrPyBXOu4TlVHdWpQ2V9jn/ZzO.Qr5K5K5K5K5', 'Maria Garcia', '+1234567891', 'restaurant_admin');

-- Insert sample customer users
INSERT INTO users (email, password_hash, full_name, phone, role) VALUES
('customer1@example.com', '$2b$12$LQv3c1yqBwlVHpPjrPyBXOu4TlVHdWpQ2V9jn/ZzO.Qr5K5K5K5K5', 'Alice Johnson', '+1234567892', 'customer'),
('customer2@example.com', '$2b$12$LQv3c1yqBwlVHpPjrPyBXOu4TlVHdWpQ2V9jn/ZzO.Qr5K5K5K5K5', 'Bob Wilson', '+1234567893', 'customer');

-- Insert sample restaurants
INSERT INTO restaurants (name, description, address, latitude, longitude, phone, email, category_id, owner_id, image_url, opening_hours) VALUES
('Pizza Palace', 'Authentic Italian pizzas with fresh ingredients', '123 Main St, New York, NY', 40.7128, -74.0060, '+1234567890', 'info@pizzapalace.com', 4, 2, 'https://example.com/pizza-palace.jpg', '{"monday": "11:00-22:00", "tuesday": "11:00-22:00", "wednesday": "11:00-22:00", "thursday": "11:00-22:00", "friday": "11:00-23:00", "saturday": "11:00-23:00", "sunday": "12:00-21:00"}'),
('Taco Town', 'Fresh Mexican cuisine and authentic flavors', '456 Oak Ave, Los Angeles, CA', 34.0522, -118.2437, '+1234567891', 'info@tacotown.com', 7, 3, 'https://example.com/taco-town.jpg', '{"monday": "10:00-21:00", "tuesday": "10:00-21:00", "wednesday": "10:00-21:00", "thursday": "10:00-21:00", "friday": "10:00-22:00", "saturday": "10:00-22:00", "sunday": "11:00-20:00"}');

-- Insert menu categories for Pizza Palace
INSERT INTO menu_categories (restaurant_id, name, description, display_order) VALUES
(1, 'Appetizers', 'Start your meal with our delicious appetizers', 1),
(1, 'Pizzas', 'Our signature wood-fired pizzas', 2),
(1, 'Beverages', 'Refreshing drinks to complement your meal', 3);

-- Insert menu categories for Taco Town
INSERT INTO menu_categories (restaurant_id, name, description, display_order) VALUES
(2, 'Tacos', 'Authentic Mexican tacos', 1),
(2, 'Burritos', 'Large and filling burritos', 2),
(2, 'Sides', 'Perfect sides to complete your meal', 3),
(2, 'Drinks', 'Traditional Mexican beverages', 4);

-- Insert sample menu items for Pizza Palace
INSERT INTO menu_items (restaurant_id, menu_category_id, name, description, price, image_url, is_vegetarian, ingredients, display_order) VALUES
(1, 1, 'Garlic Bread', 'Fresh baked bread with garlic butter', '{"small": 6.99, "large": 9.99}', 'https://example.com/garlic-bread.jpg', true, ARRAY['bread', 'garlic', 'butter', 'herbs'], 1),
(1, 1, 'Mozzarella Sticks', 'Crispy breaded mozzarella with marinara sauce', '{"regular": 8.99}', 'https://example.com/mozzarella-sticks.jpg', true, ARRAY['mozzarella', 'breadcrumbs', 'marinara sauce'], 2),
(1, 2, 'Margherita Pizza', 'Classic pizza with tomato sauce, mozzarella, and basil', '{"small": 12.99, "
