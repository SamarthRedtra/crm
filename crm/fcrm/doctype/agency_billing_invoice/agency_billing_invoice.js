frappe.breadcrumbs.add("Property Management");

frappe.ui.form.on("Agency Billing Invoice", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (["Paid", "Cancelled"].includes(frm.doc.status)) return;

		if (frm.doc.stripe_hosted_invoice_url) {
			frm.add_custom_button(__("Open Stripe Invoice"), () => {
				window.open(frm.doc.stripe_hosted_invoice_url, "_blank");
			});
			return;
		}

		frm.add_custom_button(__("Generate Stripe Invoice Link"), async () => {
			try {
				const response = await frappe.call({
					method: "crm.api.redtra.billing.pay_agency_invoice",
					args: { invoice_name: frm.doc.name },
					freeze: true,
				});
				const hostedUrl = response?.message?.stripe_hosted_invoice_url;
				await frm.reload_doc();

				if (hostedUrl) {
					frappe.show_alert({ message: __("Stripe invoice link generated"), indicator: "green" });
					window.open(hostedUrl, "_blank");
					return;
				}

				frappe.show_alert({ message: __("Invoice synced, but no hosted URL was returned"), indicator: "orange" });
			} catch (error) {
				frappe.msgprint({
					title: __("Unable to generate Stripe invoice link"),
					message: error?.message || __("Please check error logs and Stripe settings."),
					indicator: "red",
				});
			}
		});
	},
});
