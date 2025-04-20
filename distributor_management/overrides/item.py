import frappe
from frappe import _
from frappe.model.document import Document


def before_save_item(doc, method):

    if doc.get("__islocal") or doc.item_code: 
        doc.has_batch_no = 1
        doc.has_serial_no = 1
        doc.create_new_batch = 1


        doc.batch_number_series = doc.batch_number_series or "BN.########"
        doc.serial_no_series = doc.serial_no_series or "SN.########"



@frappe.whitelist()
def get_price(item, c_type):
    price = None
    i_doc = frappe.get_doc("Item", item)
    if c_type == "Distributor":
        price = i_doc.custom_selling_priceto_distributor
    elif c_type == "Retailer":
        price = i_doc.custom_selling_priceto_retailer
    elif c_type == "Ordinary":
        price = i_doc.custom_selling_pricemrp

    return price

