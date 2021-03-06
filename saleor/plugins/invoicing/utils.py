import os
import re
from datetime import datetime

import pytz
from django.conf import settings
from django.template.loader import get_template
from weasyprint import HTML

from ...invoice.models import Invoice

MAX_PRODUCTS_WITH_TABLE = 3
MAX_PRODUCTS_WITHOUT_TABLE = 4
MAX_PRODUCTS_PER_PAGE = 13


def make_full_invoice_number(number=1):
    month_and_year = datetime.now().strftime("%m/%Y")
    return f"{number}/{month_and_year}"


def parse_invoice_number(invoice):
    number = re.match(r"^(\d+)\/", invoice.number).group(1)
    return int(number)


def generate_invoice_number():
    last_invoice = Invoice.objects.last()
    if not last_invoice or not last_invoice.number:
        return make_full_invoice_number()

    try:
        last_number = parse_invoice_number(last_invoice)
        return make_full_invoice_number(last_number + 1)
    except (IndexError, ValueError, AttributeError):
        return make_full_invoice_number()


def chunk_products(products, product_limit):
    """Split products to list of chunks.

    Each chunk represents products per page, product_limit defines chunk size.
    """
    chunks = []
    for i in range(0, len(products), product_limit):
        limit = i + product_limit
        chunks.append(products[i:limit])
    return chunks


def get_product_limit_first_page(products):
    if len(products) < MAX_PRODUCTS_WITHOUT_TABLE:
        return MAX_PRODUCTS_WITH_TABLE

    return MAX_PRODUCTS_WITHOUT_TABLE


def generate_invoice_pdf(invoice):
    font_path = os.path.join(
        settings.PROJECT_ROOT, "templates", "invoices", "inter.ttf"
    )

    all_products = invoice.order.lines.all()

    product_limit_first_page = get_product_limit_first_page(all_products)

    products_first_page = all_products[:product_limit_first_page]
    rest_of_products = chunk_products(
        all_products[product_limit_first_page:], MAX_PRODUCTS_PER_PAGE
    )
    creation_date = datetime.now(tz=pytz.utc)
    rendered_template = get_template("invoices/invoice.html").render(
        {
            "invoice": invoice,
            "creation_date": creation_date.strftime("%d %b %Y"),
            "order": invoice.order,
            "font_path": f"file://{font_path}",
            "products_first_page": products_first_page,
            "rest_of_products": rest_of_products,
        }
    )
    return HTML(string=rendered_template).write_pdf(), creation_date
