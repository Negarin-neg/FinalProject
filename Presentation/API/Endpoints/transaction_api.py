from fastapi import APIRouter, Depends, HTTPException

from BusinessLogic.account_business_logic import AccountBusinessLogic
from Presentation.API.DI.account_dependency_injection import get_account_business_logic
from Presentation.API.DTOs.transaction import CreateTransaction, TransactionResponse

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])


@router.get("", response_model=list[TransactionResponse])
def get_transactions(
    account_id: int,
    business_logic: AccountBusinessLogic = Depends(get_account_business_logic),
):
    response = business_logic.get_transactions(account_id)

    if not response.success:
        status_code = 404 if response.message == "Account not found." else 400
        raise HTTPException(status_code=status_code, detail=response.message)

    return [
        TransactionResponse(
            id=transaction.id,
            account_id=transaction.account.id,
            amount=transaction.amount,
            transaction_type=transaction.transaction_type.title,
            created_at=transaction.created_at,
        )
        for transaction in response.data
    ]


@router.post("")
def create_transaction(
    request: CreateTransaction,
    business_logic: AccountBusinessLogic = Depends(get_account_business_logic),
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
