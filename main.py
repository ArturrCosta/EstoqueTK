import tkinter as tk
from tkinter import messagebox

from database import DatabaseManager
from gui import MainWindow
from logger import Logger
from login import LoginWindow


def main():
    Logger.configurar()
    root = tk.Tk()

    database = DatabaseManager()
    try:
        database.initialize_database()
    except Exception as error:
        Logger.registrar(error)
        messagebox.showerror(
            "Erro de inicialização",
            "Não foi possível criar/acessar o banco de dados.\n\n"
            "Confira o MySQL e os dados em database.py.\n"
            "Mais detalhes foram registrados em error.log.",
        )
        root.destroy()
        return

    login_window = None
    main_window = None

    def return_to_login():
        nonlocal main_window
        database.clear_current_user()
        main_window = None
        root.deiconify()
        root.lift()
        root.focus_force()
        login_window.user_entry.focus_set()

    def open_main_window(user):
        nonlocal main_window
        database.set_current_user(user["id"])
        root.withdraw()
        main_window = MainWindow(root, database, on_logout=return_to_login)

    login_window = LoginWindow(root, database, open_main_window)
    root.mainloop()


if __name__ == "__main__":
    main()
