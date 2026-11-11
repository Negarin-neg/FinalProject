from Presentation.main_view import MainView
from BusinessLogic.user_business_logic import UserBusinessLogic
from DataAccess.Repositories.SQLAlchemy.employee_repository import SQLAlchemyEmployeeRepository

repository = SQLAlchemyEmployeeRepository()
user_business = UserBusinessLogic(repository)

MainView(user_business)
