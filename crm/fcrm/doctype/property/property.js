// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const PROPERTY_TYPE_BY_CATEGORY = {
	Residential: "Apartment\nVilla\nTownhouse\nPenthouse\nVilla Compound\nHotel Apartment\nLand\nFloor\nBuilding",
	Commercial: "Office\nShop\nWarehouse\nLabour Camp\nVilla\nBulk Unit\nLand\nFloor\nBuilding\nFactory\nIndustrial Land\nMixed Use Land\nShowroom\nOther Commercial",
};

frappe.ui.form.on("Property", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm._original_is_sold = frm.doc.is_sold;
			frm._original_is_rented = frm.doc.is_rented;
		}
		_toggle_transaction_flags_visibility(frm);
		_set_completion_status_options(frm);
		_set_property_type_options(frm);
	},

	property_category(frm) {
		_set_property_type_options(frm);
	},

	listing_type(frm) {
		_toggle_transaction_flags_visibility(frm);
	},

	is_sold(frm) {
		_set_completion_status_options(frm);
	},

	before_save(frm) {
		if (frm.is_new()) return;

		const is_sold_ticked = frm.doc.is_sold && !frm._original_is_sold;
		const is_rented_ticked = frm.doc.is_rented && !frm._original_is_rented;
		if (!is_sold_ticked && !is_rented_ticked) return;

		const transaction_type = is_sold_ticked ? "Sold" : "Rented";
		const label = is_sold_ticked ? __("sold") : __("rented");

		frappe.validated = false;
		frappe.confirm(
			__("Marking this property as {0} will create a transaction log. Do you want to add transaction details?", [label]),
			() => {
				_show_transaction_dialog(frm, transaction_type);
			},
			() => {
				frm.doc.is_sold = frm._original_is_sold || 0;
				frm.doc.is_rented = frm._original_is_rented || 0;
				frm.refresh_field("is_sold");
				frm.refresh_field("is_rented");
			}
		);
	},
});

function _show_transaction_dialog(frm, transaction_type) {
	const fields = [
		{ fieldname: "amount", fieldtype: "Currency", label: __("Amount"), default: frm.doc.price },
		{ fieldname: "currency", fieldtype: "Link", label: __("Currency"), options: "Currency", default: frm.doc.currency, default: frm.doc.currency },
		{ fieldname: "customer", fieldtype: "Link", label: __("Customer"), options: "Customer" },
	];

	if (transaction_type === "Rented") {
		fields.push({
			fieldname: "rent_type",
			fieldtype: "Select",
			label: __("Rent Type"),
			options: "Daily\nWeekly\nMonthly\nYearly",
		});
		fields.push({
			fieldname: "start_date",
			fieldtype: "Date",
			label: __("Start Date"),
			default: frappe.datetime.get_today(),
		});
	}

	fields.push({ fieldname: "notes", fieldtype: "Small Text", label: __("Notes") });

	frappe.prompt(
		fields,
		(values) => {
			frappe.call({
				method: "crm.fcrm.doctype.property.property.create_transaction_from_mark",
				args: {
					property: frm.doc.name,
					agent: frm.doc.agent,
					transaction_type: transaction_type,
					amount: values.amount,
					currency: values.currency || frm.doc.currency,
					customer: values.customer || null,
					rent_type: transaction_type === "Rented" ? values.rent_type : null,
					start_date: transaction_type === "Rented" ? values.start_date : null,
					notes: values.notes || null,
				},
				callback(r) {
					if (!r.exc) {
						frm._original_is_sold = frm.doc.is_sold;
						frm._original_is_rented = frm.doc.is_rented;
						frappe.show_alert({ message: __("Transaction created"), indicator: "green" });

						if (r.message && r.message.property_modified) {
							frm.doc.modified = r.message.property_modified;
						}
						frm.save();
					} else {
						frm.doc.is_sold = frm._original_is_sold || 0;
						frm.doc.is_rented = frm._original_is_rented || 0;
						frm.refresh_field("is_sold");
						frm.refresh_field("is_rented");
					}
				},
			});
		},
		__("Add Transaction Details"),
		__("Create")
	);
}

function _set_completion_status_options(frm) {
	if (!frm.fields_dict.completion_status) return;

	const options = "All\nReady\nOff-Plan";
	frm.set_df_property("completion_status", "options", options);
	frm.refresh_field("completion_status");
}

function _toggle_transaction_flags_visibility(frm) {
	const should_show_is_sold = frm.doc.listing_type === "Buy";
	const should_show_is_rented = frm.doc.listing_type === "Rent";

	frm.set_df_property("is_sold", "hidden", !should_show_is_sold);
	frm.set_df_property("is_rented", "hidden", !should_show_is_rented);

	if (!should_show_is_sold && frm.doc.is_sold) {
		frm.set_value("is_sold", 0);
	}

	if (!should_show_is_rented && frm.doc.is_rented) {
		frm.set_value("is_rented", 0);
	}
	frm.refresh_field("is_sold");
	frm.refresh_field("is_rented");
}

function _set_property_type_options(frm) {
	if (!frm.fields_dict.property_type) return;

	const category = frm.doc.property_category || "Residential";
	const options = PROPERTY_TYPE_BY_CATEGORY[category] || PROPERTY_TYPE_BY_CATEGORY.Residential;
	frm.set_df_property("property_type", "options", options);

	// If current value is not in the new options, reset to first option
	const valid_types = options.split("\n");
	if (frm.doc.property_type && !valid_types.includes(frm.doc.property_type)) {
		frm.set_value("property_type", valid_types[0]);
	}
	frm.refresh_field("property_type");
}
