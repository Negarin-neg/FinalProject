class Customer:
    def __init__(self, id, firstname, lastname):
        self.id = id
        self.first_name = firstname
        self.last_name = lastname

    def get_fullname(self):
        return f"{self.first_name} {self.last_name or ''}".strip()
