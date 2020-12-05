import asyncio
from tkinter import *
from tkinter import messagebox

from client import register
from utils import get_run_params


async def register_user(root, entry):
    args = get_run_params()
    username = entry.get()
    if not username:
        messagebox.showinfo("Неверный username", "Введите не пустой username!")
        return

    account_token = await register(entry.get(), args.host, args.write_port)
    with open('config.conf', 'a') as f:
        f.write(f'\ntoken={account_token}')
    root.destroy()


if __name__ == '__main__':
    root = Tk()
    entry = Entry(width=50)
    Label(text="Username").pack(side=LEFT)
    button = Button(text="Register", command=lambda: asyncio.run(register_user(root, entry)))
    entry.pack(side=LEFT)
    button.pack()

    root.mainloop()
