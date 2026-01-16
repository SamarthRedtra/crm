/**
 * Lucide Icons Integration for CRM App
 * Overrides Frappe's default icon system to use Lucide icons
 */

// List of commonly used Lucide icons for amenities and general use
// This list can be expanded based on needs
frappe.lucide_icons = [
	// Amenities & Property
	'home', 'building', 'building-2', 'warehouse', 'house', 'apartment',
	'bed', 'bath', 'sofa', 'armchair', 'tv', 'wifi', 'wifi-off',
	'airplay', 'wind', 'thermometer', 'snowflake', 'flame',
	'car', 'car-front', 'parking-circle', 'parking-square',
	'swimming-pool', 'tree-pine', 'leaf', 'sun', 'moon',
	'key', 'lock', 'unlock', 'shield', 'shield-check',
	
	// Utilities
	'utensils', 'utensils-crossed', 'coffee', 'cup-soda',
	'washing-machine', 'refrigerator', 'microwave', 'oven',
	'phone', 'phone-call', 'mail', 'message-square',
	'dumbbell', 'bike', 'dog', 'cat',
	
	// Locations & Navigation
	'map', 'map-pin', 'navigation', 'compass', 'globe',
	'location', 'building-landmark', 'landmark',
	
	// General
	'star', 'heart', 'check', 'x', 'plus', 'minus',
	'search', 'filter', 'settings', 'user', 'users',
	'calendar', 'clock', 'bell', 'eye', 'eye-off',
	'share', 'download', 'upload', 'image', 'file',
	'edit', 'trash', 'save', 'copy', 'link',
	'arrow-up', 'arrow-down', 'arrow-left', 'arrow-right',
	'chevron-up', 'chevron-down', 'chevron-left', 'chevron-right',
	'menu', 'more-vertical', 'more-horizontal',
	
	// Status & Alerts
	'check-circle', 'x-circle', 'alert-circle', 'alert-triangle',
	'info', 'help-circle', 'alert-octagon',
	
	// Business & Finance
	'dollar-sign', 'credit-card', 'wallet', 'receipt',
	'briefcase', 'briefcase-business', 'briefcase-medical',
	
	// Transportation
	'plane', 'train', 'ship', 'bus', 'taxi',
	
	// Technology
	'computer', 'laptop', 'smartphone', 'tablet',
	'router', 'server', 'database', 'cloud',
	
	// Nature & Environment
	'mountain', 'waves', 'tree', 'flower', 'mushroom',
	'fish', 'bird', 'bug', 'flower-2',
	
	// Sports & Recreation
	'football', 'basketball', 'volleyball', 'tennis',
	'gamepad-2', 'music', 'headphones',
	
	// Healthcare & Safety
	'cross', 'pill', 'stethoscope', 'heart-pulse',
	'activity', 'heart-handshake',
	
	// Education & Office
	'book', 'book-open', 'graduation-cap', 'pen-tool',
	'printer', 'scissors', 'ruler', 'calculator',
	
	// Shopping & Retail
	'shopping-cart', 'shopping-bag', 'tag', 'tags',
	'gift', 'ticket', 'package', 'box',
	
	// Communication
	'video', 'video-off', 'camera', 'camera-off',
	'radio', 'megaphone', 'volume', 'volume-2', 'volume-x',
	
	// Food & Beverage
	'wine', 'beer', 'chef-hat', 'ice-cream',
	'croissant', 'cake', 'cookie',
	
	// Miscellaneous
	'puzzle', 'palette', 'brush', 'sparkles',
	'rocket', 'zap', 'lightbulb', 'crown',
	'gem', 'trophy', 'medal', 'award',
	'flag', 'anchor', 'umbrella', 'hand',
];

// Load Lucide icons dynamically
frappe.load_lucide_icons = function() {
	if (window.lucide && window.lucide.icons) {
		// Lucide is already loaded - extract all available icons
		frappe.extract_lucide_icon_names();
		return Promise.resolve();
	}
	
	// Load Lucide from CDN if not available
	return new Promise((resolve, reject) => {
		if (document.getElementById('lucide-icons-script')) {
			// Script is loading or loaded
			const checkInterval = setInterval(() => {
				if (window.lucide && window.lucide.icons) {
					clearInterval(checkInterval);
					frappe.extract_lucide_icon_names();
					resolve();
				}
			}, 100);
			
			// Timeout after 10 seconds
			setTimeout(() => {
				clearInterval(checkInterval);
				if (window.lucide && window.lucide.icons) {
					frappe.extract_lucide_icon_names();
					resolve();
				} else {
					reject(new Error('Timeout loading Lucide icons'));
				}
			}, 10000);
			return;
		}
		
		const script = document.createElement('script');
		script.id = 'lucide-icons-script';
		script.src = 'https://cdn.jsdelivr.net/npm/lucide@latest/dist/umd/lucide.js';
		script.onload = () => {
			// Initialize Lucide and extract icon names
			if (window.lucide) {
				frappe.extract_lucide_icon_names();
				lucide.createIcons();
				resolve();
			} else {
				reject(new Error('Failed to load Lucide icons'));
			}
		};
		script.onerror = () => reject(new Error('Failed to load Lucide icons script'));
		document.head.appendChild(script);
	});
};

// Extract all available icon names from Lucide library
frappe.extract_lucide_icon_names = function() {
	if (!window.lucide || !window.lucide.icons) {
		return;
	}
	
	try {
		// Get all icon names from Lucide
		const all_icons = Object.keys(window.lucide.icons || {});
		
		// Merge with predefined list and sort
		const combined_icons = [...new Set([...frappe.lucide_icons, ...all_icons])];
		combined_icons.sort();
		
		frappe.lucide_icons = combined_icons;
	} catch (e) {
		console.warn('Failed to extract all Lucide icons, using predefined list:', e);
		// Keep using predefined list
	}
};

// Normalize icon name (convert camelCase/PascalCase to kebab-case)
frappe.utils.normalize_lucide_icon_name = function(icon_name) {
	if (!icon_name) return '';
	
	// Convert camelCase/PascalCase to kebab-case
	// e.g., "CableCar" -> "cable-car", "wifi" -> "wifi"
	return icon_name
		.replace(/([a-z0-9])([A-Z])/g, '$1-$2') // Add dash before capital letters
		.toLowerCase();
};

// Override Frappe's icon function to use Lucide
frappe.utils.get_lucide_icon_html = function(icon_name, size = 'md') {
	if (!icon_name) return '';
	
	// Normalize icon name to kebab-case
	const normalized_name = frappe.utils.normalize_lucide_icon_name(icon_name);
	
	// Size mapping
	const size_map = {
		'sm': '16',
		'md': '24',
		'lg': '32',
		'xl': '48'
	};
	
	const icon_size = size_map[size] || '24';
	const stroke_width = size === 'sm' ? 1.5 : size === 'lg' ? 2 : 1.5;
	
	// Return SVG element for Lucide icon with better visibility
	return `<i data-lucide="${normalized_name}" class="lucide-icon lucide-${normalized_name}" style="width: ${icon_size}px; height: ${icon_size}px; color: var(--lucide-icon-color, #374151); stroke-width: ${stroke_width};"></i>`;
};

// Get all available Lucide icons
frappe.utils.get_lucide_icon_list = function() {
	return frappe.lucide_icons || [];
};

// Check if icon exists in Lucide
frappe.utils.is_lucide_icon = function(icon_name) {
	if (!icon_name) return false;
	return frappe.lucide_icons.includes(icon_name);
};

// Override Frappe's Icon formatter to use Lucide
// This will be set when Frappe is ready
frappe.ready(() => {
	if (frappe.form && frappe.form.formatters) {
		const originalIconFormatter = frappe.form.formatters.Icon;
		frappe.form.formatters.Icon = function(value) {
			if (!value) {
				if (originalIconFormatter) {
					return originalIconFormatter(value);
				}
				return '';
			}
			
			// Normalize icon name
			const normalized_name = frappe.utils.normalize_lucide_icon_name(value);
			
			return `<div class='flex lucide-icon-formatted' style='gap: 8px; align-items: center;'>
				<div class="selected-icon lucide-selected-icon" style="width: 20px; height: 20px; flex-shrink: 0;">${frappe.utils.get_lucide_icon_html(normalized_name, "sm")}</div>
				<span class="icon-value">${value}</span>
			</div>`;
		};
	}
	
	// Also override get_formatter for list views
	if (frappe.form && frappe.form.get_formatter) {
		const originalGetFormatter = frappe.form.get_formatter;
		frappe.form.get_formatter = function(fieldtype) {
			if (fieldtype === 'Icon') {
				return frappe.form.formatters.Icon;
			}
			return originalGetFormatter ? originalGetFormatter(fieldtype) : frappe.form.formatters[fieldtype];
		};
	}
});

// Helper function to initialize Lucide icons
frappe.init_lucide_icons = function(container) {
	if (!window.lucide || !window.lucide.createIcons) {
		return;
	}
	
	const target = container || document.body;
	const icons = target.querySelectorAll('[data-lucide]:not([data-lucide-initialized])');
	
	if (icons.length > 0) {
		window.lucide.createIcons({
			icons: icons
		});
		
		// Mark as initialized
		icons.forEach(icon => {
			icon.setAttribute('data-lucide-initialized', 'true');
		});
	}
};

// Initialize Lucide icons when document is ready
$(document).ready(function() {
	frappe.load_lucide_icons().then(() => {
		// Create all icons after Lucide is loaded
		setTimeout(() => {
			frappe.init_lucide_icons();
		}, 200);
		
		// Use MutationObserver for better performance
		const observer = new MutationObserver(function(mutations) {
			let containersToUpdate = new Set();
			
			mutations.forEach(function(mutation) {
				if (mutation.addedNodes.length) {
					mutation.addedNodes.forEach(function(node) {
						if (node.nodeType === 1) { // Element node
							if ($(node).find('[data-lucide]').length > 0 || $(node).is('[data-lucide]')) {
								containersToUpdate.add(node);
							}
						}
					});
				}
			});
			
			if (containersToUpdate.size > 0 && window.lucide) {
				setTimeout(() => {
					containersToUpdate.forEach(container => {
						frappe.init_lucide_icons(container);
					});
				}, 100);
			}
		});
		
		// Observe document body for changes
		observer.observe(document.body, {
			childList: true,
			subtree: true
		});
	}).catch(err => {
		console.error('Failed to load Lucide icons:', err);
	});
	
	// Re-initialize icons periodically (for dynamic content like list views)
	setInterval(() => {
		frappe.init_lucide_icons();
	}, 2000);
	
	// Initialize icons when list view refreshes
	if (frappe.views && frappe.views.list_view) {
		const original_refresh = frappe.views.list_view.ListView.prototype.refresh;
		frappe.views.list_view.ListView.prototype.refresh = function() {
			const result = original_refresh.apply(this, arguments);
			setTimeout(() => {
				frappe.init_lucide_icons(this.wrapper);
			}, 500);
			return result;
		};
	}
});

