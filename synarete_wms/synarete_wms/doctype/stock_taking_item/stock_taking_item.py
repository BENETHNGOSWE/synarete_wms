from frappe.model.document import Document


class StockTakingItem(Document):
    def validate(self):
        self.variance = self.physical_qty - self.system_qty
