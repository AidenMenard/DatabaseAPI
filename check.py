
from database import get_customers, get_products

customers = get_customers()
products = get_products()

print("Connection successful!")
print("Customers found:", len(customers))
print("Products found:", len(products))
