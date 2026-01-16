/**
 * Custom Icon Control for Lucide Icons
 * Overrides Frappe's default Icon control to use Lucide icons
 */

frappe.ui.form.ControlIcon = class ControlIcon extends frappe.ui.form.ControlData {
	make_input() {
		this.df.placeholder = this.df.placeholder || __("Choose a Lucide icon");
		super.make_input();
		
		// Create selected icon container immediately with smaller size
		if (!this.selected_icon) {
			const default_icon = this.get_icon() || "home";
			this.selected_icon = $(
				`<div class="selected-icon lucide-selected-icon">${frappe.utils.get_lucide_icon_html(default_icon, "sm")}</div>`
			);
			// Insert before input, not after
			if (this.$input.parent().hasClass('control-input')) {
				this.$input.parent().append(this.selected_icon);
			} else {
				this.selected_icon.insertAfter(this.$input);
			}
		}
		
		// Ensure Lucide is loaded
		frappe.load_lucide_icons().then(() => {
			this.get_all_lucide_icons();
			this.make_lucide_icon_input();
			// Initialize icons after setup
			setTimeout(() => {
				if (window.lucide) {
					lucide.createIcons();
				}
				this.refresh();
			}, 100);
		}).catch(err => {
			console.error('Failed to load Lucide icons:', err);
			// Fallback to default behavior
			this.get_all_icons();
			this.make_icon_input();
		});
	}

	get_all_lucide_icons() {
		if (!frappe.lucide_icons) {
			frappe.lucide_icons = [];
		}
		this.available_icons = frappe.lucide_icons || [];
	}

	get_all_icons() {
		// Fallback to Frappe's default icon system
		frappe.symbols = [];
		$("#all-symbols > svg > symbol[id]").each(function () {
			this.id.includes("icon-") && frappe.symbols.push(this.id.replace("icon-", ""));
		});
	}

	make_lucide_icon_input() {
		let picker_wrapper = $("<div>");
		
		// Normalize current icon value
		const current_icon = frappe.utils.normalize_lucide_icon_name(this.get_icon());
		
		// Create custom Lucide icon picker
		this.picker = new frappe.ui.LucideIconPicker({
			parent: picker_wrapper,
			icon: current_icon,
			icons: this.available_icons,
			include_emoji: this.df.options == "Emojis",
		});

		this.$wrapper
			.popover({
				trigger: "manual",
				offset: `${-this.$wrapper.width() / 4.5}, 5`,
				boundary: "viewport",
				placement: "bottom",
				template: `
				<div class="popover icon-picker-popover lucide-icon-picker-popover">
					<div class="picker-arrow arrow"></div>
					<div class="popover-body popover-content"></div>
				</div>
			`,
				content: () => picker_wrapper,
				html: true,
			})
			.on("show.bs.popover", () => {
				setTimeout(() => {
					this.picker.refresh();
					// Recreate Lucide icons after popover is shown
					if (window.lucide) {
						lucide.createIcons();
					}
				}, 10);
			})
			.on("hidden.bs.popover", () => {
				$("body").off("click.icon-popover");
				$(window).off("hashchange.icon-popover");
			});

		this.picker.on_change = (icon) => {
			// Store normalized icon name
			this.set_value(icon);
		};

		// Ensure selected icon exists and is updated
		if (this.selected_icon) {
			const icon_value = this.get_icon();
			const normalized_icon = frappe.utils.normalize_lucide_icon_name(icon_value);
			const icon_html = icon_value 
				? frappe.utils.get_lucide_icon_html(normalized_icon, "md")
				: frappe.utils.get_lucide_icon_html("home", "md");
			this.selected_icon.html(icon_html);
		}

		this.$wrapper
			.find(".selected-icon")
			.parent()
			.on("click", (e) => {
				this.$wrapper.popover("toggle");
				if (!this.get_icon()) {
					this.$input.val("");
				}
				e.stopPropagation();
				$("body").on("click.icon-popover", (ev) => {
					if (!$(ev.target).parents().is(".popover")) {
						this.$wrapper.popover("hide");
					}
				});
				$(window).on("hashchange.icon-popover", () => {
					this.$wrapper.popover("hide");
				});
			});
		
		// Initialize Lucide icons after setup
		setTimeout(() => {
			if (window.lucide) {
				lucide.createIcons();
			}
		}, 100);
	}

	make_icon_input() {
		// Fallback to Frappe's default icon input
		let picker_wrapper = $("<div>");
		this.picker = new Picker({
			parent: picker_wrapper,
			icon: this.get_icon(),
			icons: frappe.symbols,
			include_emoji: this.df.options == "Emojis",
		});

		this.$wrapper
			.popover({
				trigger: "manual",
				offset: `${-this.$wrapper.width() / 4.5}, 5`,
				boundary: "viewport",
				placement: "bottom",
				template: `
				<div class="popover icon-picker-popover">
					<div class="picker-arrow arrow"></div>
					<div class="popover-body popover-content"></div>
				</div>
			`,
				content: () => picker_wrapper,
				html: true,
			})
			.on("show.bs.popover", () => {
				setTimeout(() => {
					this.picker.refresh();
				}, 10);
			})
			.on("hidden.bs.popover", () => {
				$("body").off("click.icon-popover");
				$(window).off("hashchange.icon-popover");
			});

		this.picker.on_change = (icon) => {
			this.set_value(icon);
		};

		if (!this.selected_icon) {
			this.selected_icon = $(
				`<div class="selected-icon">${frappe.utils.icon("folder-normal", "md")}</div>`
			);
			this.selected_icon.insertAfter(this.$input);
		}

		this.$wrapper
			.find(".selected-icon")
			.parent()
			.on("click", (e) => {
				this.$wrapper.popover("toggle");
				if (!this.get_icon()) {
					this.$input.val("");
				}
				e.stopPropagation();
				$("body").on("click.icon-popover", (ev) => {
					if (!$(ev.target).parents().is(".popover")) {
						this.$wrapper.popover("hide");
					}
				});
				$(window).on("hashchange.icon-popover", () => {
					this.$wrapper.popover("hide");
				});
			});
	}

	refresh() {
		super.refresh();
		let icon = this.get_icon();
		const normalized_icon = frappe.utils.normalize_lucide_icon_name(icon);
		
		if (this.picker && this.picker.icon !== normalized_icon) {
			this.picker.icon = normalized_icon;
			this.picker.refresh();
		}
		
		// Ensure selected icon exists
		if (!this.selected_icon) {
			this.selected_icon = $(
				`<div class="selected-icon lucide-selected-icon">${frappe.utils.get_lucide_icon_html(normalized_icon, "sm")}</div>`
			);
			if (this.$input.parent().hasClass('control-input')) {
				this.$input.parent().append(this.selected_icon);
			} else {
				this.selected_icon.insertAfter(this.$input);
			}
		}
		
		// Update selected icon display with smaller size
		const icon_html = icon 
			? frappe.utils.get_lucide_icon_html(normalized_icon, "sm")
			: frappe.utils.get_lucide_icon_html("home", "sm");
		this.selected_icon.html(icon_html);
		this.selected_icon.toggleClass("no-value", !icon);
		
		// Initialize Lucide icons for selected icon only
		setTimeout(() => {
			if (window.lucide && window.lucide.createIcons) {
				const icons = this.selected_icon[0]?.querySelectorAll('[data-lucide]');
				if (icons && icons.length > 0) {
					window.lucide.createIcons({
						icons: icons
					});
				}
			}
		}, 50);
	}

	set_formatted_input(value) {
		super.set_formatted_input(value);
		this.$input.val(value);
		
		// Ensure selected icon exists
		if (!this.selected_icon) {
			this.selected_icon = $(
				`<div class="selected-icon lucide-selected-icon"></div>`
			);
			if (this.$input.parent().hasClass('control-input')) {
				this.$input.parent().append(this.selected_icon);
			} else {
				this.selected_icon.insertAfter(this.$input);
			}
		}
		
		// Normalize and display icon with smaller size
		const normalized_icon = frappe.utils.normalize_lucide_icon_name(value);
		const icon_html = value 
			? frappe.utils.get_lucide_icon_html(normalized_icon, "sm")
			: frappe.utils.get_lucide_icon_html("home", "sm");
		this.selected_icon.html(icon_html);
		this.selected_icon.toggleClass("no-value", !value);
		
		// Initialize Lucide icons for selected icon only
		setTimeout(() => {
			if (window.lucide && window.lucide.createIcons) {
				const icons = this.selected_icon[0]?.querySelectorAll('[data-lucide]');
				if (icons && icons.length > 0) {
					window.lucide.createIcons({
						icons: icons
					});
				}
			}
		}, 50);
	}

	get_icon() {
		const value = this.get_value();
		if (!value) return "home";
		// Return normalized value for display
		return frappe.utils.normalize_lucide_icon_name(value);
	}
};

// Lucide Icon Picker Class
frappe.ui.LucideIconPicker = class LucideIconPicker {
	constructor(opts) {
		this.parent = opts.parent;
		this.width = opts.width;
		this.height = opts.height;
		this.set_icon(opts.icon);
		this.icons = opts.icons || [];
		this.include_emoji = opts.include_emoji;
		this.setup_picker();
	}

	refresh() {
		this.update_icon_selected(true);
	}

	setup_picker() {
		this.icon_picker_wrapper = $(`
			<div class="icon-picker lucide-icon-picker">
				<div class="search-icons">
					<input type="search" placeholder="${__("Search for icons...")}" class="form-control">
					<span class="search-icon">${frappe.utils.get_lucide_icon_html("search", "sm")}</span>
				</div>
				<div class="icon-section" id='lucide-icon-section'>
					<div class="icons lucide-icons-grid"></div>
				</div>
			</div>
		`);
		this.parent.append(this.icon_picker_wrapper);
		this.icon_wrapper = this.icon_picker_wrapper.find(".icons");
		this.search_input = this.icon_picker_wrapper.find(".search-icons > input");
		this.refresh();
		this.setup_icons();
		
		if (this.include_emoji) {
			this.setup_emojis();
		}
		
		// Setup search
		this.search_input.on("input", (e) => {
			this.filter_icons();
		});
	}

	setup_icons() {
		// Clear existing icons
		this.icon_wrapper.empty();
		
		// Create document fragment for better performance
		const fragment = document.createDocumentFragment();
		
		this.icons.forEach((icon_name) => {
			// Normalize icon name
			const normalized_name = frappe.utils.normalize_lucide_icon_name(icon_name);
			
			const iconDiv = document.createElement('div');
			iconDiv.className = 'icon-wrapper lucide-icon-wrapper';
			iconDiv.setAttribute('data-icon', normalized_name);
			iconDiv.setAttribute('title', icon_name);
			
			const iconElement = document.createElement('i');
			iconElement.setAttribute('data-lucide', normalized_name);
			iconElement.style.width = '24px';
			iconElement.style.height = '24px';
			iconElement.style.display = 'flex';
			iconElement.style.alignItems = 'center';
			iconElement.style.justifyContent = 'center';
			
			iconDiv.appendChild(iconElement);
			fragment.appendChild(iconDiv);
		});
		
		// Append all icons at once
		this.icon_wrapper[0].appendChild(fragment);
		
		// Add click handlers
		this.icon_wrapper.find('.icon-wrapper').on('click', (e) => {
			const normalized_name = $(e.currentTarget).attr('data-icon');
			this.set_icon(normalized_name);
			this.update_icon_selected();
			if (this.on_change) {
				this.on_change(normalized_name);
			}
		});
		
		// Initialize Lucide icons after DOM is ready
		setTimeout(() => {
			if (frappe.init_lucide_icons) {
				frappe.init_lucide_icons(this.icon_wrapper[0]);
			} else if (window.lucide && window.lucide.createIcons) {
				const icons = this.icon_wrapper[0].querySelectorAll('[data-lucide]');
				if (icons.length > 0) {
					window.lucide.createIcons({
						icons: icons
					});
				}
			}
		}, 200);
	}

	filter_icons() {
		let value = this.search_input.val().toLowerCase();
		
		this.icon_wrapper.find(".icon-wrapper").each(function() {
			const icon_name = $(this).attr("data-icon");
			const icon_title = $(this).attr("title") || icon_name;
			
			// Search in both normalized name and title
			if ((icon_name && icon_name.toLowerCase().includes(value)) ||
				(icon_title && icon_title.toLowerCase().includes(value))) {
				$(this).show();
			} else {
				$(this).hide();
			}
		});
	}

	set_icon(icon) {
		this.icon = icon;
	}

	update_icon_selected(silent) {
		if (!silent && this.on_change) {
			this.on_change(this.icon);
		}
		
		this.icon_wrapper.find(".icon-wrapper").removeClass("selected");
		if (this.icon) {
			this.icon_wrapper.find(`.icon-wrapper[data-icon="${this.icon}"]`).addClass("selected");
		}
	}

	setup_emojis() {
		// Emoji support can be added later if needed
		console.log("Emoji support not yet implemented for Lucide icons");
	}
};

