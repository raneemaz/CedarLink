# Functional Requirements

These describe what the system **must do**.

## User Management

- Users can register and log in as either customers or store owners
- Users can update their profile information
- System supports role-based access (customer, vendor, admin)

---

## Store Management

- Store owners can create and manage a store profile
- Store owners can update store details (name, description, location, contact info)
- Store owners can activate or deactivate their store

---

## Product Management

- Store owners can add new products
- Store owners can edit and delete products
- Products include name, description, price, images, category, and stock
- Customers can view product details

---

## Search & Filter

- Customers can browse all stores
- Customers can search for products using keywords
- Customers can filter products by category, price, and location
- Customers can view products by store

---

## Cart System

- Customers can add products to cart
- Customers can update product quantities in cart
- Customers can remove products from cart
- Cart can contain products from multiple stores

---

## Order Management

- Customers can place orders from cart
- System creates order with multiple order items
- Customers can view order history
- Store owners can view incoming orders
- Orders have statuses (pending, processing, delivered, canceled)

---

## Delivery Handling

- Store owners can define delivery fee and delivery availability
- Customers can enter delivery address during checkout
- System calculates total price including delivery

---

## Admin Panel (Basic)

- Admin can view users and stores
- Admin can manage or remove stores if needed

---

# Non-Functional Requirements

These describe **how the system should behave**.

---

## Performance

- Pages should load within 2–3 seconds under normal usage
- System should handle multiple users simultaneously without crashing

---

## Security

- Passwords must be hashed and securely stored
- Role-based access control must be enforced
- Users can only access their own data (orders, store info)

---

## Scalability

- System should support adding many stores and products without redesign
- Database structure should support growth (multi-vendor architecture)

---

## Maintainability

- Code should follow modular structure (separation of concerns)
- Database should be normalized to avoid redundancy

---

## Usability

- Simple and intuitive UI for both customers and store owners
- Mobile-friendly design (responsive layout)

---

## Reliability

- System should prevent data loss during order creation
- Transactions should ensure order consistency

---

## Availability

- Platform should be accessible 24/7 (web-based system)

---

# User Stories

User stories describe features from the **user perspective**.

---

## Customer Stories

- As a customer, I want to create an account so that I can shop on the platform
- As a customer, I want to browse stores so that I can discover local businesses
- As a customer, I want to search for products so that I can find what I need quickly
- As a customer, I want to filter products by category and location so that I can refine my search
- As a customer, I want to add products to my cart so that I can purchase multiple items at once
- As a customer, I want to place an order so that I can receive products at my address
- As a customer, I want to view my order history so that I can track my purchases

---

## Store Owner Stories

- As a store owner, I want to create a store profile so that I can sell products online
- As a store owner, I want to add products so that customers can buy them
- As a store owner, I want to edit product details so that I can keep information updated
- As a store owner, I want to receive orders so that I can fulfill customer purchases
- As a store owner, I want to manage my store information so that customers see correct details

---

## Admin Stories

- As an admin, I want to view all users so that I can manage the platform
- As an admin, I want to view all stores so that I can ensure platform quality
- As an admin, I want to remove inappropriate stores so that the platform stays safe

---

# System Actors

the **system actors** are the external entities that interact with the platform.

---

## Primary Actors:

### Customer

A user who browses products and places orders through the platform.

**Responsibilities:**

- Register/Login
- Browse stores
- Search products
- View product details
- Add items to cart
- Place orders
- Track orders
- Manage profile
- Leave reviews (future feature)

### Store Owner / Vendor

A business owner managing their store on the platform.

**Responsibilities:**

- Register store / Login the account created by admin
- Manage store profile
- Add/Edit/Delete products
- Manage inventory
- Receive orders
- Update order status
- Configure delivery areas and fees
- View sales statistics

### Admin

The platform administrator responsible for system management.

**Responsibilities:**

- Approve or reject store registrations
- Create a store account
- Manage users
- Manage vendors
- Monitor orders
- Manage product categories
- Handle reports and complaints
- Generate system reports
- Suspend accounts when necessary

## Secondary Actors:

### Delivery Service / Delivery Driver

Responsible for delivering orders from stores to customers.

**Responsibilities:**

- View assigned deliveries
- Update delivery status
- Confirm completed deliveries

### Payment Gateway (External System Actor)

An external system that processes online payments.

**Responsibilities:**

- Process payment transactions
- Confirm payment success/failure
- Return transaction status

Examples:

- Wish Money
- OMT Pay
- Credit Card Processors

---

# System Architecture

The Lebanese Multi-Store E-Commerce Platform follows a **three-tier client-server architecture** composed of:

### 1. Presentation Layer (Frontend)

Technologies:

- HTML
- CSS
- JavaScript

Responsibilities:

- Display stores and products
- Allow users to search and browse products
- Manage shopping cart interactions
- Submit orders
- Display order tracking information
- Provide dashboards for customers, store owners, and administrators

### 2. Application Layer (Backend)

Technology:

- Python Flask

Responsibilities:

- User authentication and authorization
- Store management
- Product management
- Order processing
- Cart management
- Delivery management
- Business logic implementation
- Communication with the database

### 3. Data Layer (Database)

Technology:

- SQLite

Responsibilities:

- Store user accounts
- Store vendor information
- Store products and categories
- Store orders and order details
- Store cart information
- Maintain platform data integrity

## Architecture Diagram

```
+----------------------+
|      Frontend        |
| HTML + CSS + JS      |
+----------+-----------+
           |
           | HTTP Requests
           v
+----------------------+
|    Flask Backend     |
| Business Logic       |
| Authentication       |
| Product Management   |
| Order Management     |
+----------+-----------+
           |
           | SQL Queries
           v
+----------------------+
|      SQLite DB        |
+----------------------+
```

### Data Flow

1. The user interacts with the frontend through a web browser.
2. The frontend sends HTTP requests to the Flask backend.
3. Flask processes the request and applies business logic.
4. Flask retrieves or updates data in the SQLite database.
5. The response is returned to the frontend and displayed to the user.

---

# Use Case Diagram:

CedarLink_UseCaseDiagram.drawio.svg