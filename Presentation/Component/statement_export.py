import os
from tkinter import filedialog, messagebox

from Presentation.API.Client.account_api_client import (
    AccountApiClient,
    AccountApiError,
)


def export_statement(account, account_api_client: AccountApiClient):
    """Ask for a destination and save the selected account's PDF statement."""
    pdf_path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF file", "*.pdf")],
        initialfile=f"statement_{account.account_number}.pdf",
        title="Export Account Statement",
    )

    if not pdf_path:
        return

    try:
        account_api_client.download_statement_pdf(account.id, pdf_path)
    except (AccountApiError, OSError) as ex:
        messagebox.showerror("Export Statement", str(ex))
        return
    except Exception:
        messagebox.showerror(
            "Export Statement",
            "The statement could not be exported. Please try again.",
        )
        return

    messagebox.showinfo("Export Statement", "The statement was exported successfully.")

    try:
        os.startfile(pdf_path)
    except (OSError, AttributeError):
        pass
