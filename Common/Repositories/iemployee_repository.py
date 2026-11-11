from abc import ABC, abstractmethod
from Common.Entities.employee import Employee


class IEmployeeRepository(ABC):
    @abstractmethod
    def get_by_username_password(self, username: str, password: str) -> Employee:
        pass

    @abstractmethod
    def get_by_id(self, employee_id: int) -> Employee:
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Employee:
        pass

    @abstractmethod
    def get_by_mobile(self, mobile: str) -> Employee:
        pass

    @abstractmethod
    def insert(self, employee: Employee):
        pass

    @abstractmethod
    def update_profile(self, employee: Employee):
        pass

    @abstractmethod
    def update_photo_path(self, employee_id: int, photo_path):
        pass
