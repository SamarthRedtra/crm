frappe.pages.agency_billing_setup.on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Agency Billing Setup"),
		single_column: true,
	});

	const html = frappe.render_template("agency_billing_setup", {});
	$(html).appendTo(page.body);
};
