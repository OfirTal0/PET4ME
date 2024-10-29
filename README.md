# PET4ME - Online Pet Store

**PET4ME** is a dynamic online store built for a pet shop, offering a versatile product catalog and an ordering system that allows customers to send orders directly to the store owner via the website.

## Features

1. **Website Homepage**
   - General information about the store
   - Customer Club registration
   - Monthly promotions (dynamic)
   - Popular products (dynamic)
   - Adoption section
   - Contact form that sends messages directly to the store’s email

2. **Product Catalog**
   - Search and filter capabilities
   - View products and a catalog
   - Add items to a shopping cart.

3. **Shopping Cart**
   - Quantity updates, item removal, and total amount calculation
   - Order submission with details sent to the store’s email

4. **Admin Page**
   - Secure login for store management
   - Update and add inventory items with all details and images
   - Update adoption posts on the homepage
   - Export leads, orders, Customer Club members, and manual inventory entries to Excel

5. **Database Interaction**
    - using SQLite for data storage, with various SQL queries to fetch, insert, and update data.

6. **User Interaction**
   - utilize sessions to maintain cart data and provide flash messages for user feedback.

## Getting Started

Locally:
1.Clone the repository: git clone https://github.com/OfirTal0/PET4ME.git 
2.Navigate to the project directory: cd PET4ME 
3.python -m pip install -r requirements.txt 
4.python ./manage.py runserver

## Changes and Fixes for Future

1. Make the website responsive for mobile devices
2. Create a Dockerfile for easier deployment
