frappe.pages.property_management_setup.on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Property Management Setup"),
		single_column: true,
	});

	const html = frappe.render_template("property_management_setup", {});
	$(html).appendTo(page.body);
};
