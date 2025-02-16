from decimal import Decimal

def calculate_service_fee(order_total):
    service_fee = 5
    return Decimal(order_total) * Decimal(service_fee) / 100