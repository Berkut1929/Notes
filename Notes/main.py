import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
import sqlite3
from datetime import datetime
import os
import re
from typing import Optional, List, Tuple

class NotesApp:
    def __init__(self, root: tk.Tk):
        """Инициализация приложения для заметок."""
        self.root = root
        self.root.title("Приложение для заметок")
        self.root.geometry("1200x800")
        self.theme = "light"  # Тема по умолчанию: светлая
        self.current_note_id: Optional[int] = None  # ID текущей заметки
        self.search_query = tk.StringVar()  # Переменная для поискового запроса
        self.search_query.trace("w", self.search_notes)  # Отслеживание изменений в поиске

        # Инициализация базы данных
        self.init_database()

        # Создание главного контейнера
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Настройка элементов интерфейса
        self.setup_menu()
        self.setup_toolbar()
        self.setup_main_layout()
        self.load_categories()
        self.load_notes()

        # Настройка стилей и тем
        self.style = ttk.Style()
        self.configure_themes()

        # Привязка горячих клавиш
        self.bind_hotkeys()

    def init_database(self) -> None:
        """Инициализация базы данных SQLite и создание таблиц."""
        try:
            self.conn = sqlite3.connect("notes.db")
            self.cursor = self.conn.cursor()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT,
                    category_id INTEGER,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (category_id) REFERENCES categories (id)
                )
            """)
            self.conn.commit()
            # Добавление категории по умолчанию, если она не существует
            self.cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", ("Общее",))
            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось инициализировать базу данных: {e}")
            self.root.quit()

    def configure_themes(self) -> None:
        """Настройка светлой и темной тем."""
        self.style.configure("TButton", padding=5)
        self.style.configure("TEntry", padding=5)
        self.style.configure("TCombobox", padding=5)
        self.light_theme = {
            "bg": "#ffffff",
            "fg": "#000000",
            "entry_bg": "#f0f0f0",
            "text_bg": "#ffffff",
            "text_fg": "#000000",
            "highlight": "#0078d7"
        }
        self.dark_theme = {
            "bg": "#2d2d2d",
            "fg": "#ffffff",
            "entry_bg": "#3c3c3c",
            "text_bg": "#3c3c3c",
            "text_fg": "#ffffff",
            "highlight": "#1e90ff"
        }
        self.apply_theme(self.theme)

    def apply_theme(self, theme: str) -> None:
        """Применение выбранной темы к интерфейсу."""
        theme_colors = self.light_theme if theme == "light" else self.dark_theme
        self.root.configure(bg=theme_colors["bg"])
        self.main_frame.configure(style="TFrame")
        self.style.configure("TFrame", background=theme_colors["bg"])
        self.style.configure("TLabel", background=theme_colors["bg"], foreground=theme_colors["fg"])
        self.style.configure("TButton", background=theme_colors["entry_bg"], foreground=theme_colors["fg"])
        self.style.configure("TEntry", fieldbackground=theme_colors["entry_bg"], foreground=theme_colors["fg"])
        self.style.configure("TCombobox", fieldbackground=theme_colors["entry_bg"], foreground=theme_colors["fg"])
        self.note_text.configure(bg=theme_colors["text_bg"], fg=theme_colors["text_fg"],
                               insertbackground=theme_colors["fg"])
        self.notes_list.configure(bg=theme_colors["text_bg"], fg=theme_colors["text_fg"])

    def setup_menu(self) -> None:
        """Настройка строки меню."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Новая заметка", command=self.new_note, accelerator="Ctrl+N")
        file_menu.add_command(label="Экспортировать заметку", command=self.export_note)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.quit_app)

        # Меню "Правка"
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Правка", menu=edit_menu)
        edit_menu.add_command(label="Отменить", command=lambda: self.note_text.event_generate("<<Undo>>"),
                            accelerator="Ctrl+Z")
        edit_menu.add_command(label="Повторить", command=lambda: self.note_text.event_generate("<<Redo>>"),
                            accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Вырезать", command=lambda: self.note_text.event_generate("<<Cut>>"),
                            accelerator="Ctrl+X")
        edit_menu.add_command(label="Копировать", command=lambda: self.note_text.event_generate("<<Copy>>"),
                            accelerator="Ctrl+C")
        edit_menu.add_command(label="Вставить", command=lambda: self.note_text.event_generate("<<Paste>>"),
                            accelerator="Ctrl+V")

        # Меню "Вид"
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_command(label="Переключить тему", command=self.toggle_theme)

    def setup_toolbar(self) -> None:
        """Настройка панели инструментов с кнопками и поиском."""
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(fill="x", pady=5)

        # Кнопка "Новая заметка"
        new_btn = ttk.Button(toolbar, text="Новая заметка", command=self.new_note)
        new_btn.pack(side="left", padx=5)

        # Кнопка "Сохранить заметку"
        save_btn = ttk.Button(toolbar, text="Сохранить заметку", command=self.save_note)
        save_btn.pack(side="left", padx=5)

        # Кнопка "Удалить заметку"
        delete_btn = ttk.Button(toolbar, text="Удалить заметку", command=self.delete_note)
        delete_btn.pack(side="left", padx=5)

        # Кнопки форматирования
        bold_btn = ttk.Button(toolbar, text="Ж", command=self.toggle_bold, style="TButton")
        bold_btn.pack(side="left", padx=5)
        italic_btn = ttk.Button(toolbar, text="К", command=self.toggle_italic, style="TButton")
        italic_btn.pack(side="left", padx=5)
        underline_btn = ttk.Button(toolbar, text="П", command=self.toggle_underline, style="TButton")
        underline_btn.pack(side="left", padx=5)

        # Поле поиска
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_query)
        self.search_entry.pack(side="right", padx=5, fill="x", expand=True)
        ttk.Label(toolbar, text="Поиск:").pack(side="right", padx=5)

    def setup_main_layout(self) -> None:
        """Настройка основного макета с списком заметок, категориями и редактором."""
        paned = ttk.PanedWindow(self.main_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # Левая панель (категории и список заметок)
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        # Категории
        ttk.Label(left_frame, text="Категория:").pack(anchor="w", padx=5, pady=2)
        self.category_combo = ttk.Combobox(left_frame, state="readonly")
        self.category_combo.pack(fill="x", padx=5, pady=2)
        self.category_combo.bind("<<ComboboxSelected>>", self.load_notes)

        # Список заметок
        ttk.Label(left_frame, text="Заметки:").pack(anchor="w", padx=5, pady=2)
        self.notes_list = tk.Listbox(left_frame, height=20, width=30)
        self.notes_list.pack(fill="both", expand=True, padx=5, pady=5)
        self.notes_list.bind("<<ListboxSelect>>", self.load_selected_note)

        # Правая панель (редактор заметок)
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=3)

        # Поле для заголовка
        ttk.Label(right_frame, text="Заголовок:").pack(anchor="w", padx=5, pady=2)
        self.title_entry = ttk.Entry(right_frame)
        self.title_entry.pack(fill="x", padx=5, pady=2)

        # Текстовое поле для заметки
        self.note_text = tk.Text(right_frame, height=20, wrap="word", undo=True)
        self.note_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Настройка тегов форматирования
        self.note_text.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))
        self.note_text.tag_configure("italic", font=("TkDefaultFont", 10, "italic"))
        self.note_text.tag_configure("underline", font=("TkDefaultFont", 10, "underline"))

    def bind_hotkeys(self) -> None:
        """Приспользование горячих клавиш для быстрых действий."""
        self.root.bind("<Control-n>", lambda event: self.new_note())
        self.root.bind("<Control-s>", lambda event: self.save_note())
        self.root.bind("<Control-d>", lambda event: self.delete_note())
        self.root.bind("<Control-t>", lambda event: self.toggle_theme())
        self.note_text.bind("<Control-b>", lambda event: self.toggle_bold())
        self.note_text.bind("<Control-i>", lambda event: self.toggle_italic())
        self.note_text.bind("<Control-u>", lambda event: self.toggle_underline())
        self.root.bind("<Control-e>", lambda event: self.export_note())

    def load_categories(self) -> None:
        """Загрузка категорий из базы данных в выпадающий список."""
        try:
            self.cursor.execute("SELECT name FROM categories ORDER BY name")
            categories = [row[0] for row in self.cursor.fetchall()]
            self.category_combo["values"] = categories
            if categories:
                self.category_combo.set(categories[0])
            else:
                self.category_combo.set("Общее")
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось загрузить категории: {e}")

    def load_notes(self, event: Optional[tk.Event] = None) -> None:
        """Загрузка заметок для выбранной категории."""
        self.notes_list.delete(0, tk.END)
        try:
            category_name = self.category_combo.get()
            if not category_name:
                return
            self.cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
            result = self.cursor.fetchone()
            if not result:
                return
            category_id = result[0]
            query = "SELECT id, title FROM notes WHERE category_id = ? ORDER BY updated_at DESC"
            self.cursor.execute(query, (category_id,))
            notes = self.cursor.fetchall()
            for note_id, title in notes:
                self.notes_list.insert(tk.END, f"{note_id}: {title}")
            self.clear_editor()
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось загрузить заметки: {e}")

    def search_notes(self, *args) -> None:
        """Поиск заметок по заголовку или содержимому."""
        self.notes_list.delete(0, tk.END)
        query = self.search_query.get().lower()
        if not query:
            self.load_notes()
            return
        try:
            self.cursor.execute("""
                SELECT id, title FROM notes
                WHERE lower(title) LIKE ? OR lower(content) LIKE ?
                ORDER BY updated_at DESC
            """, (f"%{query}%", f"%{query}%"))
            notes = self.cursor.fetchall()
            for note_id, title in notes:
                self.notes_list.insert(tk.END, f"{note_id}: {title}")
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось выполнить поиск: {e}")

    def load_selected_note(self, event: tk.Event) -> None:
        """Загрузка выбранной заметки в редактор."""
        selection = self.notes_list.curselection()
        if not selection:
            return
        note_id = int(self.notes_list.get(selection[0]).split(":")[0])
        try:
            self.cursor.execute("SELECT title, content FROM notes WHERE id = ?", (note_id,))
            title, content = self.cursor.fetchone()
            self.current_note_id = note_id
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, title)
            self.note_text.delete("1.0", tk.END)
            self.note_text.insert("1.0", content)
            # Применение тегов форматирования
            self.apply_formatting_tags(content)
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось загрузить заметку: {e}")

    def apply_formatting_tags(self, content: str) -> None:
        """Применение тегов форматирования к тексту."""
        try:
            # Формат: *текст* для жирного, _текст_ для курсива, ~текст~ для подчеркивания
            self.note_text.delete("1.0", tk.END)
            self.note_text.insert("1.0", content)
            for pattern, tag in [
                (r"\*(.*?)\*", "bold"),
                (r"_(.*?)_", "italic"),
                (r"~(.*?)~", "underline")
            ]:
                for match in re.finditer(pattern, content):
                    start = f"1.0 + {match.start()} chars"
                    end = f"1.0 + {match.end()} chars"
                    self.note_text.tag_add(tag, start, end)
        except tk.TclError as e:
            messagebox.showwarning("Ошибка форматирования", f"Ошибка при применении форматирования: {e}")

    def new_note(self) -> None:
        """Создание новой заметки."""
        self.current_note_id = None
        self.clear_editor()

    def save_note(self) -> None:
        """Сохранение текущей заметки."""
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Ошибка ввода", "Заголовок не может быть пустым!")
            return
        content = self.note_text.get("1.0", tk.END).strip()
        category_name = self.category_combo.get()
        timestamp = datetime.now().isoformat()

        try:
            self.cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
            result = self.cursor.fetchone()
            if not result:
                messagebox.showerror("Ошибка", "Выберите существующую категорию!")
                return
            category_id = result[0]

            if self.current_note_id:
                # Обновление существующей заметки
                self.cursor.execute("""
                    UPDATE notes SET title = ?, content = ?, category_id = ?, updated_at = ?
                    WHERE id = ?
                """, (title, content, category_id, timestamp, self.current_note_id))
            else:
                # Создание новой заметки
                self.cursor.execute("""
                    INSERT INTO notes (title, content, category_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (title, content, category_id, timestamp, timestamp))
                self.current_note_id = self.cursor.lastrowid
            self.conn.commit()
            self.load_notes()
            messagebox.showinfo("Успех", "Заметка успешно сохранена!")
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка базы данных", f"Не удалось сохранить заметку: {e}")

    def delete_note(self) -> None:
        """Удаление текущей заметки."""
        if not self.current_note_id:
            messagebox.showwarning("Ошибка выбора", "Заметка не выбрана!")
            return
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить эту заметку?"):
            try:
                self.cursor.execute("DELETE FROM notes WHERE id = ?", (self.current_note_id,))
                self.conn.commit()
                self.current_note_id = None
                self.clear_editor()
                self.load_notes()
                messagebox.showinfo("Успех", "Заметка успешно удалена!")
            except sqlite3.Error as e:
                messagebox.showerror("Ошибка базы данных", f"Не удалось удалить заметку: {e}")

    def export_note(self) -> None:
        """Экспорт текущей заметки в текстовый файл."""
        if not self.current_note_id:
            messagebox.showwarning("Ошибка выбора", "Заметка не выбрана!")
            return
        title = self.title_entry.get().strip()
        content = self.note_text.get("1.0", tk.END).strip()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
            initialfile=f"{title}.txt"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"Заголовок: {title}\n\n{content}")
                messagebox.showinfo("Успех", "Заметка успешно экспортирована!")
            except IOError as e:
                messagebox.showerror("Ошибка файла", f"Не удалось экспортировать заметку: {e}")

    def toggle_bold(self) -> None:
        """Переключение жирного форматирования."""
        if not self.note_text.tag_ranges("sel"):
            messagebox.showwarning("Ошибка выбора", "Выделите текст для форматирования!")
            return
        try:
            current_tags = self.note_text.tag_names("sel.first")
            if "bold" in current_tags:
                self.note_text.tag_remove("bold", "sel.first", "sel.last")
            else:
                self.note_text.tag_add("bold", "sel.first", "sel.last")
        except tk.TclError as e:
            messagebox.showerror("Ошибка форматирования", f"Не удалось применить форматирование: {e}")

    def toggle_italic(self) -> None:
        """Переключение курсивного форматирования."""
        if not self.note_text.tag_ranges("sel"):
            messagebox.showwarning("Ошибка выбора", "Выделите текст для форматирования!")
            return
        try:
            current_tags = self.note_text.tag_names("sel.first")
            if "italic" in current_tags:
                self.note_text.tag_remove("italic", "sel.first", "sel.last")
            else:
                self.note_text.tag_add("italic", "sel.first", "sel.last")
        except tk.TclError as e:
            messagebox.showerror("Ошибка форматирования", f"Не удалось применить форматирование: {e}")

    def toggle_underline(self) -> None:
        """Переключение подчеркивания."""
        if not self.note_text.tag_ranges("sel"):
            messagebox.showwarning("Ошибка выбора", "Выделите текст для форматирования!")
            return
        try:
            current_tags = self.note_text.tag_names("sel.first")
            if "underline" in current_tags:
                self.note_text.tag_remove("underline", "sel.first", "sel.last")
            else:
                self.note_text.tag_add("underline", "sel.first", "sel.last")
        except tk.TclError as e:
            messagebox.showerror("Ошибка форматирования", f"Не удалось применить форматирование: {e}")

    def toggle_theme(self) -> None:
        """Переключение между светлой и темной темами."""
        self.theme = "dark" if self.theme == "light" else "light"
        self.apply_theme(self.theme)

    def clear_editor(self) -> None:
        """Очистка редактора заметок."""
        self.title_entry.delete(0, tk.END)
        self.note_text.delete("1.0", tk.END)
        self.current_note_id = None

    def quit_app(self) -> None:
        """Выход из приложения."""
        if messagebox.askyesno("Подтверждение", "Вы хотите выйти?"):
            try:
                self.conn.close()
            except (sqlite3.Error, AttributeError):
                pass
            self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = NotesApp(root)
    root.mainloop()