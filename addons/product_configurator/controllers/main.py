from odoo import http
from odoo.http import request

class ProductConfigurator(WebsiteSale):
	
	def get_attribute_value_ids(self,product):
		attribute_value_ids = super(WebsiteSale,self).get_attribute_value_ids(product)
		visible_attribute_id=product.attribute.name 
		type=product.attribute.type
		value_type = product.attribute.value_type
		attribute_value_ids.append([visible_attribute_id,type,value_type])
		return attribute_value_ids


