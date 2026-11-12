from fastapi import APIRouter, Depends, HTTPException

from BusinessLogic.account_business_logic import AccountBusinessLogic
from Common.Entities.employee import Employee
from Presentation.API.DI.account_dependency_injection import (
    get_account_business_logic,
    get_current_employee,
)
from Presentation.API.DTOs.account import CreateTransactionRequest

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])


@router.post("")
def create_transaction(
    request: CreateTransactionRequest,
    business_logic: AccountBusinessLogic = Depends(get_account_business_logic),
    employee: Employee = Depends(get_current_employee),
):
    response = business_logic.insert_transaction(
        request.account_id,
        request.amount,
        request.transaction_type,
    )

    if not response.success:
        status_code = 404 if response.message == "Account not found." else 400
        raise HTTPException(status_code=status_code, detail=response.message)

    return {"success": True, "message": response.message}
