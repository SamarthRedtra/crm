"""
API endpoint to get available Lucide icons for the CRM app
"""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from . import utils


@frappe.whitelist(allow_guest=True)
def list_lucide_icons(search: str = None) -> dict[str, Any]:
	"""
	Get list of available Lucide icons.
	This can be used by frontend to populate icon pickers or validate icon names.
	"""
	# Common Lucide icons used in CRM
	icon_list = [
		# Amenities & Property
		'home', 'building', 'building-2', 'warehouse', 'house', 'apartment',
		'bed', 'bath', 'sofa', 'armchair', 'tv', 'wifi', 'wifi-off',
		'airplay', 'wind', 'thermometer', 'snowflake', 'flame',
		'car', 'car-front', 'parking-circle', 'parking-square',
		'swimming-pool', 'tree-pine', 'leaf', 'sun', 'moon',
		'key', 'lock', 'unlock', 'shield', 'shield-check',
		
		# Utilities
		'utensils', 'utensils-crossed', 'coffee', 'cup-soda',
		'washing-machine', 'refrigerator', 'microwave', 'oven',
		'phone', 'phone-call', 'mail', 'message-square',
		'dumbbell', 'bike', 'dog', 'cat',
		
		# Locations & Navigation
		'map', 'map-pin', 'navigation', 'compass', 'globe',
		'location', 'building-landmark', 'landmark',
		
		# General
		'star', 'heart', 'check', 'x', 'plus', 'minus',
		'search', 'filter', 'settings', 'user', 'users',
		'calendar', 'clock', 'bell', 'eye', 'eye-off',
		'share', 'download', 'upload', 'image', 'file',
		'edit', 'trash', 'save', 'copy', 'link',
		'arrow-up', 'arrow-down', 'arrow-left', 'arrow-right',
		'chevron-up', 'chevron-down', 'chevron-left', 'chevron-right',
		'menu', 'more-vertical', 'more-horizontal',
		
		# Status & Alerts
		'check-circle', 'x-circle', 'alert-circle', 'alert-triangle',
		'info', 'help-circle', 'alert-octagon',
		
		# Business & Finance
		'dollar-sign', 'credit-card', 'wallet', 'receipt',
		'briefcase', 'briefcase-business', 'briefcase-medical',
		
		# Transportation
		'plane', 'train', 'ship', 'bus', 'taxi',
		
		# Technology
		'computer', 'laptop', 'smartphone', 'tablet',
		'router', 'server', 'database', 'cloud',
		
		# Nature & Environment
		'mountain', 'waves', 'tree', 'flower', 'mushroom',
		'fish', 'bird', 'bug', 'flower-2',
		
		# Sports & Recreation
		'football', 'basketball', 'volleyball', 'tennis',
		'gamepad-2', 'music', 'headphones',
		
		# Healthcare & Safety
		'cross', 'pill', 'stethoscope', 'heart-pulse',
		'activity', 'heart-handshake',
		
		# Education & Office
		'book', 'book-open', 'graduation-cap', 'pen-tool',
		'printer', 'scissors', 'ruler', 'calculator',
		
		# Shopping & Retail
		'shopping-cart', 'shopping-bag', 'tag', 'tags',
		'gift', 'ticket', 'package', 'box',
		
		# Communication
		'video', 'video-off', 'camera', 'camera-off',
		'radio', 'megaphone', 'volume', 'volume-2', 'volume-x',
		
		# Food & Beverage
		'wine', 'beer', 'chef-hat', 'ice-cream',
		'croissant', 'cake', 'cookie',
		
		# Miscellaneous
		'puzzle', 'palette', 'brush', 'sparkles',
		'rocket', 'zap', 'lightbulb', 'crown',
		'gem', 'trophy', 'medal', 'award',
		'flag', 'anchor', 'umbrella', 'hand',
	]
	
	# Filter by search if provided
	if search:
		search_lower = search.lower()
		icon_list = [icon for icon in icon_list if search_lower in icon.lower()]
	
	return {
		"icons": sorted(icon_list),
		"total": len(icon_list),
		"search": search,
	}

