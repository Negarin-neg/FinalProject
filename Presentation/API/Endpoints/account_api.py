import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response as RawResponse

from BusinessLogic.account_business_logic import AccountBusinessLogic
from Common.Entities.employee import Employee
from Presentation.API.DI.account_dependency_injection import (
    get_account_business_logic,
    get_current_employee,
)
from Presentation.API.DTOs.account import (
    AccountResponse,
    StatementResponse,
    account_to_response,
    statement_to_response,
)

router = APIRouter(prefix="/api/v1/accounts", tags=["Accounts"])


@router.get("", response_model=list[AccountResponse])
def get_accounts(
    search: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    business_logic: AccountBusinessLogic = Depends(get_account_business_logic),
    employee: Employee = Depends(get_current_employee),
):
    response = business_logic.get_account_list(search, page, page_size)

    if not response.success:
        raise HTTPException(status_code=400, detail=response.message)

    return [account_to_response(account) for account in response.data]


@router.get("/{account_id}/statement", response_model=StatementResponse)
def get_statement(
    account_id: int,
    business_logic: AccountBusinessLogic = Depends(get_account_business_logic),
    employee: Employee = Depends(get_current_employee),
):
    response = business_logic.get_statement(account_id)

    if not response.success:
        status_code = 404 if response.message == "Account not found." else 400
        raise HTTPException(status_code=status_code, detail=response.message)

    return statement_to_response(response.data)


@router.get("/{account_id}/statement/pdf")
def get_statement_pdf(
    account_id: int,
    business_logic: AccountBusinessLogic = Depends(get_account_business_logic),
    employee: Employee = Depends(get_current_employee),
):
    statement_response = business_logic.get_statement(account_id)

    if not statement_response.success:
        status_code = 404 if statement_response.message == "Account not found." else 400
        raise HTTPException(status_code=status_code, detail=statement_response.message)

    file_descriptor, file_path = tempfile.mkstemp(suffix=".pdf")
    os.close(file_descriptor)

    try:
        pdf_response = business_logic.generate_statement_pdf(account_id, file_path)
        if not pdf_response.success:
            raise HTTPException(status_code=400, detail=pdf_response.message)

        with open(file_path, "rb") as pdf_file:
            content = pdf_file.read()
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    account_number = statement_response.data.account_number
    return RawResponse(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="statement_{account_number}.pdf"'
            )
        },
    )
