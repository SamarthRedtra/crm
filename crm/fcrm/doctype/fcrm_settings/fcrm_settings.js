// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("FCRM Settings", {
	refresh(frm) {
		frappe.model.with_doctype("Property", () => {
			let meta = frappe.get_meta("Property");
			let fields = meta.fields
				.filter((f) => !frappe.model.no_value_type.includes(f.fieldtype))
				.map((f) => f.fieldname)
				.sort();

			let options = ["", ...fields].join("\n");
			frappe.meta.get_docfield("Property Field Config", "fieldname", frm.doc.name).options = options;
		});
	},
	restore_defaults: function (frm) {
		let message = __(
			"This will restore (if not exist) all the default statuses, custom fields and layouts. Delete & Restore will delete default layouts and then restore them."
		);
		let d = new frappe.ui.Dialog({
			title: __("Restore Defaults"),
			primary_action_label: __("Restore"),
			primary_action: () => {
				frm.call("restore_defaults", { force: false }, () => {
					frappe.show_alert({
						message: __(
							"Default statuses, custom fields and layouts restored successfully."
						),
						indicator: "green",
					});
				});
				d.hide();
			},
			secondary_action_label: __("Delete & Restore"),
			secondary_action: () => {
				frm.call("restore_defaults", { force: true }, () => {
					frappe.show_alert({
						message: __(
							"Default statuses, custom fields and layouts restored successfully."
						),
						indicator: "green",
					});
				});
				d.hide();
			},
		});
		d.show();
		d.set_message(message);
	},
});

frappe.ui.form.on("Property Field Config", {
	fieldname(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (row.fieldname) {
			let meta = frappe.get_meta("Property");
			let field = meta.fields.find(f => f.fieldname === row.fieldname);
			if (field) {
				frappe.model.set_value(cdt, cdn, "label", field.label);
			}
		}
	}
});
