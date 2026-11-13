import os
from tkinter import filedialog, messagebox

from BusinessLogic.account_business_logic import AccountBusinessLogic


def export_statement(account, account_business: AccountBusinessLogic):
    """Ask for a destination and save the selected account's PDF statement."""
    pdf_path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF file", "*.pdf")],
        initialfile=f"statement_{account.account_number}.pdf",
        title="Export Account Statement",
    )

    if not pdf_path:
        return

    response = account_business.generate_statement_pdf(account.id, pdf_path)

    if not response.success:
        messagebox.showerror(
            "Export Statement",
            response.message or "The statement could not be exported.",
        )
        return

    messagebox.showinfo("Export Statement", "The statement was exported successfully.")

    try:
        os.startfile(pdf_path)
    except (OSError, AttributeError):
        pass
