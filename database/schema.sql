CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('admin', 'user')),
    points INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
); 

CREATE TABLE menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL unique,
    description TEXT,
    price REAL NOT NULL CHECK(price >= 0),
    category TEXT NOT NULL CHECK(category IN ('main', 'drinks', 'dessert')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_available BOOLEAN DEFAULT TRUE CHECK(is_available IN (TRUE, FALSE))
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total_price REAL NOT NULL CHECK(total_price >= 0),
    status TEXT NOT NULL CHECK(status IN ('pending', 'preparing', 'completed', 'delivered')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed BOOLEAN DEFAULT FALSE CHECK(reviewed IN (TRUE, FALSE)),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    menu_item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    price REAL NOT NULL CHECK(price >= 0),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
);


CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    read_status BOOLEAN DEFAULT FALSE,
    type TEXT NOT NULL CHECK(type IN ('order', 'reservation', 'store_update')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    order_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (order_id) REFERENCES orders(id)
    
);
CREATE TABLE tables (
    table_number INTEGER PRIMARY KEY,
    seats INTEGER NOT NULL
);

CREATE TABLE reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    table_number INTEGER NOT NULL,
    seats INTEGER NOT NULL,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT CHECK (STATUS IN ('available', 'booked')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (table_number) REFERENCES tables(table_number)
);


INSERT INTO users (user_name, password_hash, role) VALUES 
('admin', 'scrypt:32768:8:1$GeAz0157dBcbPXbC$91ea82656e5a9fc95c8dce2cd65b11dff6553c05c1ad0fb42cd803a578e6c795b5d106e79be01f0ce9ecf1f496c9a48e3de0c9fda2a56d84c3728307046ac810', 'admin');

INSERT INTO users (user_name, password_hash, role) VALUES 
('user1', 'scrypt:32768:8:1$ar42IPCNNblbljaI$c26c6075240d9e8f158ca647e8e6361b3c0c3d5e574eef20d911fb7706c986823e2359bd7b9e1d4ef77f1c65b7a648d3858274e6de3a05d352142237f28c2052', 'user');

INSERT INTO users (user_name, password_hash, role) VALUES 
('user2', 'scrypt:32768:8:1$nRlcNPnSXDZBrcRl$13a8bc5e909fa522b0e4b15a8fb3f353c0e5f5ad75ea250b01d7ff12a16c00c6e95dab3277beea26f7d2eaf04bbc198a641107941d5944ce49c8476acd1d1688', 'user');

INSERT INTO menu_items (name, description, price, category) VALUES ('Brownies', 'Warm fudge chocolate brownie', 6.0, 'dessert');
INSERT INTO menu_items (name, description, price, category) VALUES ('Cheesecake', 'Classic creamy vanilla cheesecake', 6.0, 'dessert'); 
INSERT INTO menu_items (name, description, price, category) VALUES ('Chocolate Cake', 'Rich and moist chocolate cake', 5.5, 'dessert');
INSERT INTO menu_items (name, description, price, category) VALUES ('Mango Smoothie', 'Cold blended mango juice', 4.0, 'drinks'); 
INSERT INTO menu_items (name, description, price, category) VALUES ('Iced Latte', 'Cold espresso with milk', 4.0, 'drinks'); 
INSERT INTO menu_items (name, description, price, category) VALUES ('Cappuccino', 'Espresso with milk and foam', 4.0, 'drinks');
INSERT INTO menu_items (name, description, price, category) VALUES ('Espresso', 'Strong and rich double espresso', 4.0, 'drinks');
INSERT INTO menu_items (name, description, price, category) VALUES ('Cheesburger', 'Juicy beef patty topped with melted cheese', 20.0, 'main');
INSERT INTO menu_items (name, description, price, category) VALUES ('pizza', 'Classic backed cheese pizza', 12.0, 'main'); 

INSERT INTO tables (table_number, seats) VALUES (1,2), (2,2), (3,4), (4,4), (5,6), (6,6);