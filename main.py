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

    def open_main_window():
        root.withdraw()
        MainWindow(root, database)

    LoginWindow(root, database, open_main_window)
    root.mainloop()


if __name__ == "__main__":
    main()
