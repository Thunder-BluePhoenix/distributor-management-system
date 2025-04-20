import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, nowdate, getdate



def on_submit(doc, method=None):
    if doc.custom_customer_type == "Distributor":
        create_serials(doc, method=None)
    if doc.custom_customer_type == "Retailer":
        validate(doc, method=None)
        update_sl_retailor(doc, method=None)
        update_scheme_sold_quantity_distributor(doc, method=None)
        update_scheme_imei(doc, method=None)
    if doc.custom_customer_type == "Ordinary":
        validate(doc, method=None)
        update_sl_ordinary(doc, method=None)
        update_scheme_sold_quantity_retailer(doc, method=None)


def update_after_submit(doc, method=None):
    if doc.custom_customer_type == "Distributor":
        update_emei(doc, method=None)
       






def create_serials(doc, method=None):
    if doc.custom_customer_type == "Distributor":
        if not doc.custom_serials_created:
            for i in doc.items:
                item_doc = frappe.get_doc("Item", i.item_code)

                # Process Accepted Quantity
                if int(i.qty or 0) > 0:
                    if item_doc.has_batch_no:
                        batch_no = frappe.model.naming.make_autoname(item_doc.batch_number_series or "BATCH-.#####")
                        batch = frappe.get_doc({
                            "doctype": "Batch",
                            "batch_id": batch_no,
                            "item": i.item_code,
                            "batch_qty": i.qty,
                            # "warehouse": self.accepted_warehouse,
                            "reference_doctype": "Sales Order",
                            "reference_name": doc.name,
                            # "use_batchwise_valuation": 1
                        })
                        batch.flags.ignore_validate = True
                        batch.flags.ignore_permissions = True
                        batch.insert()
                        # i.batch_no = batch_no

                    if item_doc.has_serial_no:
                        serial_nos = []
                        for i in range(int(i.qty or 0)):
                            serial_no = frappe.model.naming.make_autoname(item_doc.serial_no_series or "SERIAL-.#####")
                            serial_nos.append(serial_no)

                            custom_fields = {
                                "custom_distributor": doc.customer,
                                "custom_primary_sale_date": nowdate(),
                                "custom_primary_sale_reference": doc.name,
                                
                                "brand": item_doc.brand
                            }

                            serial = frappe.get_doc({
                                "doctype": "Serial No",
                                "serial_no": serial_no,
                                "item_code": item_doc.item_code,
                                "batch_no": batch.name,
                                # "warehouse": self.accepted_warehouse,
                                "custom_creation_reference_doctype": "Sales Order",
                                "custom_creation_document_name": doc.name,
                                "status": "Inactive",
                              
                                **custom_fields
                            })
                            serial.flags.ignore_validate = True
                            serial.flags.ignore_permissions = True
                          
                            serial.save()

                            row = doc.append("custom_item_info", {})
                            row.item_code = item_doc.item_code
                            row.serial_no = serial.name
                            


        doc.custom_serials_created = 1
        doc.save()
        

def update_emei(doc, method=None):
    for i in doc.custom_item_info:
        
        sl = frappe.get_doc("Serial No", i.serial_no)
        if not sl.custom_imei_no:
            sl.status = "Active"
            sl.custom_imei_no = i.imei_no
            sl.save()






def validate_serial_counts(doc):
    item_qty_map = {}
    
    for item in doc.items:
        if item.item_code not in item_qty_map:
            item_qty_map[item.item_code] = 0
        item_qty_map[item.item_code] += int(item.qty or 0)
    
    serial_count_map = {}
    
    for info in doc.custom_item_info:
        if info.item_code not in serial_count_map:
            serial_count_map[info.item_code] = 0
        if info.serial_no:
            serial_count_map[info.item_code] += 1
    
    mismatches = []
    for item_code, qty in item_qty_map.items():
        serial_count = serial_count_map.get(item_code, 0)
        if qty != serial_count:
            mismatches.append({
                "item_code": item_code,
                "expected": qty,
                "actual": serial_count
            })
    
    if not mismatches:
        return True
    else:
        return {
            "valid": False,
            "mismatches": mismatches
        }




def validate(doc, method=None):
    if doc.custom_customer_type == "Retailer" or doc.custom_customer_type == "Ordinary" :
        result = validate_serial_counts(doc)
        if result is not True:
            mismatch_msg = ""
            for mismatch in result["mismatches"]:
                mismatch_msg += f"Item {mismatch['item_code']}: Expected {mismatch['expected']} serials, found {mismatch['actual']}. "
            frappe.throw(_("Serial number count mismatch. " + mismatch_msg))



def update_sl_retailor(doc, method=None):
    if doc.custom_customer_type == "Retailer":
        for i in doc.custom_item_info:
            sl_doc = frappe.get_doc("Serial No", i.serial_no)
            sl_doc.custom_retailer = doc.customer
            sl_doc.custom_secondary_sale_date = nowdate()
            sl_doc.custom_secondary_sale_reference = doc.name
            sl_doc.save()


def update_sl_ordinary(doc, method=None):
    if doc.custom_customer_type == "Ordinary":
        for i in doc.custom_item_info:
            sl_doc = frappe.get_doc("Serial No", i.serial_no)
            sl_doc.custom_sold_to = doc.customer
            sl_doc.custom_tertiary_sale_date = nowdate()
            sl_doc.custom_tertiary_sale_reference = doc.name
            sl_doc.custom_sold = 1
            sl_doc.save()




def update_scheme_sold_quantity_retailer(doc, method=None):
    # Only process if this is a secondary sale (has retailer and date)
    if doc.custom_customer_type == "Ordinary":
    
    # Find active schemes that match this item and retailer
        for item in doc.items:
            schemes = frappe.get_all(
                "Scheme",
                filters={
                    "item": item.item_code,
                    "retailer": doc.custom_sold_by,
                    "docstatus": 1,
                    "status": "Active",
                    "from": ["<=", doc.transaction_date],
                    "to": [">=", doc.transaction_date]
                },
                fields=["*"]
            )
            
            # Process each matching scheme
            for scheme_data in schemes:
                scheme_name = scheme_data.name
                
                # Count all serial numbers that match the scheme criteria
                count = frappe.db.count(
                    "Serial No",
                    filters={
                        "item_code": item.item_code,
                        "custom_retailer": doc.custom_sold_by,
                        "custom_tertiary_sale_date": ["between", [
                            frappe.get_value("Scheme", scheme_name, "from"),
                            frappe.get_value("Scheme", scheme_name, "to")
                        ]]
                    }
                )
                t_i = float(count)*float(scheme_data.incentive)
                
                # Update the scheme's sold_quantity
                frappe.db.set_value("Scheme", scheme_name, "sold_quantity", count)
                frappe.db.set_value("Scheme", scheme_name, "total_incentive", t_i)
                frappe.db.commit()
                
                # Log for tracking
                frappe.logger().info(f"Updated Scheme {scheme_name} sold_quantity to {count}")






def update_scheme_sold_quantity_distributor(doc, method=None):
    # Only process if this is a secondary sale (has retailer and date)
    if doc.custom_customer_type == "Retailer":
    
    # Find active schemes that match this item and retailer
        for item in doc.items:
            schemes = frappe.get_all(
                "Scheme",
                filters={
                    "item": item.item_code,
                    "distributor": doc.custom_sold_by,
                    "docstatus": 1,
                    "status": "Active",
                    "from": ["<=", doc.transaction_date],
                    "to": [">=", doc.transaction_date]
                },
                fields=["*"]
            )
            
            # Process each matching scheme
            for scheme_data in schemes:
                scheme_name = scheme_data.name
                
                # Count all serial numbers that match the scheme criteria
                count = frappe.db.count(
                    "Serial No",
                    filters={
                        "item_code": item.item_code,
                        "custom_distributor": doc.custom_sold_by,
                        "custom_secondary_sale_date": ["between", [
                            frappe.get_value("Scheme", scheme_name, "from"),
                            frappe.get_value("Scheme", scheme_name, "to")
                        ]]
                    }
                )
                t_i = float(count)*float(scheme_data.incentive)
                
                # Update the scheme's sold_quantity
                frappe.db.set_value("Scheme", scheme_name, "sold_quantity", count)
                frappe.db.set_value("Scheme", scheme_name, "total_incentive", t_i)
                frappe.db.commit()
                
                # Log for tracking
                frappe.logger().info(f"Updated Scheme {scheme_name} sold_quantity to {count}")



def update_scheme_imei(doc, method=None):
    # Only process if this is a secondary sale (has retailer and date)
    if doc.custom_customer_type == "Retailer":
    
    # Find active schemes that match this item and retailer
        for item in doc.items:
            schemes = frappe.get_all(
                "Scheme",
                filters={
                    "item": item.item_code,
                    "distributor": doc.custom_sold_by,
                    "docstatus": 1,
                    "status": "Active",
                    "from": ["<=", doc.transaction_date],
                    "to": [">=", doc.transaction_date]
                },
                fields=["*"]
            )
            
            # Process each matching scheme
            # for scheme_data in schemes:
            #     scheme_name = scheme_data.name
                
            #     # Count all serial numbers that match the scheme criteria
            #     count = frappe.db.count(
            #         "Serial No",
            #         filters={
            #             "item_code": item.item_code,
            #             "custom_distributor": doc.custom_sold_by,
            #             "custom_secondary_sale_date": ["between", [
            #                 frappe.get_value("Scheme", scheme_name, "from"),
            #                 frappe.get_value("Scheme", scheme_name, "to")
            #             ]]
            #         }
            #     )
            
            #     t_i = float(count)*float(scheme_data.incentive)
                
            #     # Update the scheme's sold_quantity
            #     frappe.db.set_value("Scheme", scheme_name, "sold_quantity", count)
            #     frappe.db.set_value("Scheme", scheme_name, "total_incentive", t_i)
            #     frappe.db.commit()

            for scheme_data in schemes:
                scheme_name = scheme_data.name
                
                # Count all serial numbers that match the scheme criteria
                all_SL = frappe.get_all(
                    "Serial No",
                    filters={
                        "item_code": item.item_code,
                        "custom_distributor": doc.custom_sold_by,
                        "custom_secondary_sale_date": ["between", [
                            frappe.get_value("Scheme", scheme_name, "from"),
                            frappe.get_value("Scheme", scheme_name, "to")
                        ]]
                    },
                    fields=["*"]
                )    
                data=[]
                for sl in all_SL:
                    sl_doc=frappe.get_doc("Serial No", sl.name)
                    sl_Name=sl_doc.name
                    iemi=sl_doc.custom_imei_no
                    temp=sl_Name+"-"+iemi
                    data.append(temp)
                print("@@@@@@@@@@@@@@@@",data)
                fomatted_data=", ".join(data)
                frappe.db.set_value("Scheme", scheme_name, "imei_nos", fomatted_data)

                # frappe.db.set_value("Scheme",)

                frappe.db.commit()
                
                # Log for tracking
            

            
            

