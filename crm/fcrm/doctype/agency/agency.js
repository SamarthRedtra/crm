// Copyright (c) 2026, Redtra Technologies FZE LLC and contributors
// For license information, please see license.txt

function canReviewVerification() {
	return frappe.user.has_role("System Manager") || frappe.user.has_role("Sales Manager");
}

frappe.ui.form.on("Agency", {
	refresh(frm) {
		if (!canReviewVerification()) return;

		const status = frm.doc.verification_status || "Verified";
		if (!["Pending Verification", "Rejected"].includes(status)) return;

		frm.add_custom_button(__("Approve Verification"), () => {
			frappe.prompt(
				[
					{
						fieldname: "notes",
						fieldtype: "Small Text",
						label: __("Approval Notes"),
					},
					{
						fieldname: "start_trial",
						fieldtype: "Check",
						label: __("Start trial immediately"),
						default: 1,
					},
				],
				(values) => {
					frappe.call({
						method: "crm.api.redtra.billing.approve_agency_verification",
						args: {
							agency_id: frm.doc.name,
							notes: values.notes || "",
							start_trial: values.start_trial ? 1 : 0,
						},
						callback: () => frm.reload_doc(),
					});
				},
				__("Approve Agency Verification"),
				__("Approve")
			);
		});

		frm.add_custom_button(__("Reject Verification"), () => {
			frappe.prompt(
				[
					{
						fieldname: "notes",
						fieldtype: "Small Text",
						label: __("Rejection Reason"),
						reqd: 1,
					},
				],
				(values) => {
					frappe.call({
						method: "crm.api.redtra.billing.reject_agency_verification",
						args: {
							agency_id: frm.doc.name,
							notes: values.notes || "",
						},
						callback: () => frm.reload_doc(),
					});
				},
				__("Reject Agency Verification"),
				__("Reject")
			);
		});
	},
});

frappe.listview_settings["Agency"] = {
	add_fields: ["verification_status", "onboarding_status", "billing_status", "trial_status"],
	get_indicator(doc) {
		if (doc.verification_status === "Pending Verification") {
			return [__("Pending Verification"), "orange", "verification_status,=,Pending Verification"];
		}
		if (doc.verification_status === "Rejected") {
			return [__("Verification Rejected"), "red", "verification_status,=,Rejected"];
		}
		if (doc.trial_status === "Expired") {
			return [__("Trial Expired"), "red", "trial_status,=,Expired"];
		}
		if (doc.billing_status === "Past Due") {
			return [__("Past Due"), "red", "billing_status,=,Past Due"];
		}
		return [__("Active"), "green", "status,=,Active"];
	},
};
