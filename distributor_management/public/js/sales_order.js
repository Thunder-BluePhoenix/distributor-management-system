frappe.ui.form.on('Sales Order', {
    custom_customer_type: function(frm) {
        // When customer type changes, update rates for all existing items
        if (frm.doc.items && frm.doc.items.length) {
            $.each(frm.doc.items || [], function(i, item) {
                if (item.item_code) {
                    update_item_rate(frm, item.doctype, item.name);
                }
            });
        }
    }
});

frappe.ui.form.on('Sales Order Item', {
    items_add: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if (row.item_code) {
            // The standard API will be called first, then our custom code
            setTimeout(function() {
                update_item_rate(frm, cdt, cdn);
            }, 500); // Small delay to ensure the default API call completes
        }
    },
    
    item_code: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if (row.item_code) {
            // The standard API will be called first, then our custom code
            setTimeout(function() {
                update_item_rate(frm, cdt, cdn);
            }, 500); // Small delay to ensure the default API call completes
        }
    },
    qty: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if (row.item_code) {
            // The standard API will be called first, then our custom code
            setTimeout(function() {
                update_item_rate(frm, cdt, cdn);
            }, 500); // Small delay to ensure the default API call completes
        }
    }
});



// Helper function to update item rate.base_price_list_rate
function update_item_rate(frm, cdt, cdn) {
    let row = frappe.get_doc(cdt, cdn);
    
    frappe.call({
        method: 'distributor_management.overrides.item.get_price',
        args: {
            'item': row.item_code,
            'c_type': frm.doc.custom_customer_type
        },
        callback: function(r) {
            if (r.message) {
                frappe.model.set_value(cdt, cdn, 'base_price_list_rate', r.message);
                frappe.model.set_value(cdt, cdn, 'price_list_rate', r.message);
                frappe.model.set_value(cdt, cdn, 'rate', r.message);
            }
        }
    });
}




frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        frm.set_query("item_code", "custom_item_info", function(doc, cdt, cdn) {
            // Create an array of item codes from the items table
            let items = [];
            if (doc.items && doc.items.length) {
                items = $.map(doc.items, function(item) {
                    return item.item_code;
                });
            }
           
            return {
                filters: {
                    "name": ["in", items]
                }
            };
        });
       
        frm.set_query("serial_no", "custom_item_info", function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
           
            // Only filter if we're in retailer mode
            if (doc.custom_customer_type === "Retailer" && row.item_code) {
                return {
                    filters: {
                        "item_code": row.item_code,
                        "custom_distributor": doc.custom_sold_by,
                        "custom_retailer": ["in", ["", null]]
                    }
                };
            } else if (doc.custom_customer_type === "Ordinary" && row.item_code) {
                return {
                    filters: {
                        "item_code": row.item_code,
                        "custom_sold": 0
                       
                    }
                };
            }else if (row.item_code) {
                // For other customer types, just filter by item_code
                return {
                    filters: {
                        "item_code": row.item_code
                    }
                };
            }
        });
    },
   
    // Re-apply filters when customer type changes
    custom_customer_type: function(frm) {
        frm.refresh();
    }
 });
 
 // Additional event when item_code changes in the custom_item_info table
 frappe.ui.form.on('Serial Details', {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        // Clear serial_no when item_code changes
        if (row.serial_no) {
            frappe.model.set_value(cdt, cdn, 'serial_no', '');
        }
    },
    
    serial_no: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.serial_no) {
            // Fetch the Serial No document to get the IMEI number
            frappe.call({
                method: "frappe.client.get",
                args: {
                    doctype: "Serial No",
                    name: row.serial_no
                },
                callback: function(response) {
                    if (response.message) {
                        let serial_doc = response.message;
                        // Update the IMEI number from the serial document
                        frappe.model.set_value(cdt, cdn, 'imei_no', serial_doc.custom_imei_no || '');
                    }
                }
            });
        } else {
            // Clear the IMEI when serial number is cleared
            frappe.model.set_value(cdt, cdn, 'imei_no', '');
        }
    }
 });
 
 