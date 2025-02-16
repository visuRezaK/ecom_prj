from plugin.countries import countries

def tax_calculation(country, order_total):
    for c in countries():
        if country == c['country']:
            tax_rate = float(c['tax_rate']) / 100
            return tax_rate * float(order_total)
    return 0