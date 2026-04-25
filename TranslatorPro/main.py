"""
TranslatorPro V3 — Production Localizer для Ren'Py
Точка входа с графическим интерфейсом

ИСПРАВЛЕНО:
- Убрана поддержка .rpyc (проблемные бинарные файлы)
- Убраны дублирующие модули (m01, m04, m05, m07)
- Добавлен централизованный ErrorLogger
- Исправлены пути и импорты
"""
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional, List, Dict, Any
import threading

# === БАЗОВЫЕ ПУТИ ===
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    PROJECT_ROOT as CONFIG_ROOT,
    CACHE_DB,
    LOG_FILE,
    SOURCE_LANGUAGE,
    TARGET_LANGUAGE,
    USE_ARGOS,
    USE_NLLB,
    version,
    GLOSSARY_FILE,
    GUI_THEME,
    GUI_LANGUAGE
)
from infrastructure.utils.logger import setup_logger, get_logger
from infrastructure.utils.error_logger import ErrorLogger
from infrastructure.guards.code_guard import CodeGuard
from infrastructure.guards.protection_manager import ProtectionManager
from infrastructure.guards.quote_guard import QuoteGuard
from infrastructure.cache.sqlite_cache import SQLiteCache
from domain.glossary.glossary_manager import GlossaryManager
from domain.qa.qa_engine import QAEngine
from infrastructure.engines.argos_engine import ArgosEngine
from infrastructure.engines.nllb_engine import NLLBEngine
from domain.pipeline.localization_pipeline import LocalizationPipeline
from infrastructure.extractors.renpy_extractor import RenPyExtractor
from infrastructure.generators.renpy_generator import RenPyGenerator
from core.event_bus import event_bus
from modules.m06_code_protector import CodeProtector
from modules.m08_text_fitter import TextFitter
from modules.m09_font_manager import FontManager
from modules.m10_post_processor import PostProcessor
from modules.m11_integrity_checker import IntegrityChecker
from modules.m12_report_generator import ReportGenerator

logger = get_logger(__name__)


class TranslatorProGUI:
    """Графический интерфейс TranslatorPro V3"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"TranslatorPro V3 — Production Localizer ({version})")
        self.root.geometry("1000x750")
        self.root.minsize(900, 650)

        self.border_color = '#808080'
        self.border_width = 3

        self.root.configure(bg=self.border_color)

        self.main_frame = tk.Frame(
            root,
            bg=self.border_color,
            bd=self.border_width,
            relief='ridge'
        )
        self.main_frame.pack(fill='both', expand=True, padx=3, pady=3)

        self.content_frame = tk.Frame(self.main_frame, bg='#ffffff')
        self.content_frame.pack(fill='both', expand=True, padx=1, pady=1)

        self._setup_style()

        # === ИНИЦИАЛИЗАЦИЯ КОМПОНЕНТОВ ===
        self.cache = SQLiteCache(CACHE_DB)
        self.code_guard = CodeGuard()
        self.protection_manager = ProtectionManager()
        self.quote_guard = QuoteGuard()
        self.glossary = GlossaryManager()
        self.qa = QAEngine()
        self.code_protector = CodeProtector()
        self.post_processor = PostProcessor()
        self.integrity_checker = IntegrityChecker()
        self.font_manager = FontManager()
        self.text_fitter = TextFitter()
        self.report_generator = ReportGenerator(PROJECT_ROOT / "logs")
        self.error_logger = ErrorLogger(PROJECT_ROOT / "logs")

        self.engines: List = []
        self._init_engines()

        self.pipeline: Optional[LocalizationPipeline] = None
        self.extractor: Optional[RenPyExtractor] = None
        self.generator: Optional[RenPyGenerator] = None

        self.game_dir: Optional[Path] = None
        self.is_processing = False
        self.extracted_terms: List[Any] = []
        self.last_translation_results: Optional[List[Dict]] = None

        self._create_widgets()

        logger.info(f"TranslatorPro V3 запущен. Защищено {self.code_guard.get_protected_keywords_count()} ключевых слов.")
        logger.info(f"ErrorLogger активен: {self.error_logger.log_dir}")

    def _setup_style(self):
        style = ttk.Style()

        if GUI_THEME == "dark":
            style.theme_use('clam')
        else:
            style.theme_use('default')

        style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'), foreground='#2c3e50')
        style.configure('Status.TLabel', font=('Helvetica', 10), foreground='#7f8c8d')
        style.configure('Success.TLabel', foreground='#27ae60')
        style.configure('Warning.TLabel', foreground='#f39c12')
        style.configure('Error.TLabel', foreground='#e74c3c')
        style.configure('Primary.TButton', font=('Helvetica', 11, 'bold'))
        style.configure('Secondary.TButton', font=('Helvetica', 10))

        style.configure('Glossary.Treeview', rowheight=25, font=('Helvetica', 10))
        style.configure('Glossary.Treeview.Heading', font=('Helvetica', 10, 'bold'))

    def _init_engines(self):
        if USE_ARGOS:
            try:
                self.engines.append(ArgosEngine())
                logger.info("Argos Engine добавлен")
            except Exception as e:
                logger.warning(f"Argos Engine не добавлен: {e}")
                self.error_logger.log_warning(
                    "engine_init_failed", "Argos Engine недоступен",
                    details=str(e), module="main", recovery_hint="Установите: pip install argostranslate"
                )

        if USE_NLLB:
            try:
                self.engines.append(NLLBEngine())
                logger.info("NLLB Engine добавлен")
            except Exception as e:
                logger.warning(f"NLLB Engine не добавлен: {e}")
                self.error_logger.log_warning(
                    "engine_init_failed", "NLLB Engine недоступен",
                    details=str(e), module="main", recovery_hint="Установите: pip install transformers torch"
                )

    def _create_widgets(self):
        self.notebook = ttk.Notebook(self.content_frame)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text=' Основная')
        self._create_main_tab()

        self.glossary_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.glossary_tab, text=' Глоссарий')
        self._create_glossary_tab()

        self.errors_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.errors_tab, text=' Ошибки')
        self._create_errors_tab()

        self.status_var = tk.StringVar(value=" Готов к работе")
        status_bar = ttk.Label(
            self.content_frame, textvariable=self.status_var, relief="sunken",
            style='Status.TLabel'
        )
        status_bar.pack(fill='x', padx=10, pady=5)

        info_frame = ttk.Frame(self.content_frame, padding=10)
        info_frame.pack(fill='x', padx=10)

        self.keywords_label = ttk.Label(
            info_frame,
            text=f" Защищено ключевых слов: {self.code_guard.get_protected_keywords_count()}",
            style='Success.TLabel'
        )
        self.keywords_label.pack(side='left')

        self.engines_label = ttk.Label(
            info_frame,
            text=f" Движков доступно: {len(self.engines)}",
            style='Status.TLabel'
        )
        self.engines_label.pack(side='left', padx=20)

        self.glossary_label = ttk.Label(
            info_frame,
            text=f" Терминов в глоссарии: {self.glossary.get_terms_count()}",
            style='Status.TLabel'
        )
        self.glossary_label.pack(side='left', padx=20)

    def _create_main_tab(self):
        header_frame = ttk.Frame(self.main_tab, padding=20)
        header_frame.pack(fill='x')

        ttk.Label(
            header_frame,
            text=" TranslatorPro V3",
            style='Title.TLabel'
        ).pack(anchor='w')

        ttk.Label(
            header_frame,
            text=f"Production Localizer для Ren'Py | Версия {version} | Без .rpyc",
            style='Status.TLabel'
        ).pack(anchor='w')

        settings_frame = ttk.LabelFrame(self.main_tab, text=" Настройки проекта", padding=15)
        settings_frame.pack(fill='x', padx=20, pady=10)

        path_frame = ttk.Frame(settings_frame)
        path_frame.pack(fill='x', pady=5)

        ttk.Label(path_frame, text=" Путь к игре:", width=15).pack(side='left')
        self.game_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.game_path_var, width=50).pack(side='left', padx=10)
        ttk.Button(path_frame, text="Обзор...", command=self._browse_game).pack(side='left')

        engine_frame = ttk.Frame(settings_frame)
        engine_frame.pack(fill='x', pady=5)

        ttk.Label(engine_frame, text=" Движки:", width=15).pack(side='left')
        self.argos_var = tk.BooleanVar(value=USE_ARGOS)
        self.nllb_var = tk.BooleanVar(value=USE_NLLB)
        ttk.Checkbutton(engine_frame, text="Argos (оффлайн)", variable=self.argos_var).pack(side='left', padx=10)
        ttk.Checkbutton(engine_frame, text="NLLB (качественнее)", variable=self.nllb_var).pack(side='left')

        action_frame = ttk.LabelFrame(self.main_tab, text=" Действия", padding=15)
        action_frame.pack(fill='x', padx=20, pady=10)

        btn_frame = ttk.Frame(action_frame)
        btn_frame.pack(fill='x')

        self.btn_extract = ttk.Button(
            btn_frame, text=" Распаковать RPA", command=self._extract_rpa,
            style='Primary.TButton'
        )
        self.btn_extract.pack(side='left', padx=5, pady=5)

        self.btn_translate = ttk.Button(
            btn_frame, text=" Перевести", command=self._translate,
            style='Primary.TButton'
        )
        self.btn_translate.pack(side='left', padx=5, pady=5)

        self.btn_generate = ttk.Button(
            btn_frame, text=" Генерировать TL", command=self._generate_tl,
            style='Primary.TButton'
        )
        self.btn_generate.pack(side='left', padx=5, pady=5)

        self.btn_clear = ttk.Button(
            btn_frame, text=" Очистить кэш", command=self._clear_cache,
            style='Secondary.TButton'
        )
        self.btn_clear.pack(side='left', padx=5, pady=5)

        progress_frame = ttk.Frame(self.main_tab, padding=15)
        progress_frame.pack(fill='x', padx=20)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill='x')

        self.progress_label = ttk.Label(
            progress_frame, text="Готов к работе", style='Status.TLabel'
        )
        self.progress_label.pack(anchor='w', pady=5)

        log_frame = ttk.LabelFrame(self.main_tab, text=" Лог операций", padding=15)
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)

        self.log_text = tk.Text(log_frame, height=15, state="disabled", font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True)

        scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=scrollbar.set)

    def _create_glossary_tab(self):
        btn_frame = ttk.Frame(self.glossary_tab, padding=10)
        btn_frame.pack(fill='x')

        ttk.Button(
            btn_frame,
            text=" Авто-извлечение терминов",
            command=self._auto_extract_terms
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text=" Сохранить глоссарий",
            command=self._save_glossary
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text=" Загрузить глоссарий",
            command=self._load_glossary
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text=" Очистить глоссарий",
            command=self._clear_glossary
        ).pack(side='left', padx=5)

        columns = ('term', 'frequency', 'category', 'translation', 'examples')
        self.glossary_tree = ttk.Treeview(
            self.glossary_tab,
            columns=columns,
            show='headings',
            style='Glossary.Treeview'
        )

        self.glossary_tree.heading('term', text='Термин')
        self.glossary_tree.heading('frequency', text='Частота')
        self.glossary_tree.heading('category', text='Категория')
        self.glossary_tree.heading('translation', text='Перевод')
        self.glossary_tree.heading('examples', text='Примеры')

        self.glossary_tree.column('term', width=150)
        self.glossary_tree.column('frequency', width=80, anchor='center')
        self.glossary_tree.column('category', width=100, anchor='center')
        self.glossary_tree.column('translation', width=200)
        self.glossary_tree.column('examples', width=300)

        self.glossary_tree.pack(fill='both', expand=True, padx=10, pady=10)

        edit_frame = ttk.Frame(self.glossary_tab, padding=10)
        edit_frame.pack(fill='x')

        ttk.Label(edit_frame, text="Перевод:").pack(side='left')

        self.translation_entry = ttk.Entry(edit_frame, width=50)
        self.translation_entry.pack(side='left', padx=5)

        ttk.Button(
            edit_frame,
            text=" Применить",
            command=self._apply_translation
        ).pack(side='left', padx=5)

        ttk.Button(
            edit_frame,
            text=" Удалить термин",
            command=self._remove_term
        ).pack(side='left', padx=5)

        self.glossary_tree.bind('<<TreeviewSelect>>', self._on_term_select)

        self.glossary_info_label = ttk.Label(
            self.glossary_tab,
            text="Нажмите 'Авто-извлечение терминов' для анализа игры",
            style='Status.TLabel'
        )
        self.glossary_info_label.pack(pady=5)

    def _create_errors_tab(self):
        """Вкладка с ошибками перевода."""
        btn_frame = ttk.Frame(self.errors_tab, padding=10)
        btn_frame.pack(fill='x')

        ttk.Button(
            btn_frame,
            text=" Обновить",
            command=self._refresh_errors
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text=" Очистить лог",
            command=self._clear_error_log
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text=" Открыть папку логов",
            command=self._open_log_dir
        ).pack(side='left', padx=5)

        # Статистика
        self.errors_stats_label = ttk.Label(
            btn_frame, text="Ошибок: 0 | Предупреждений: 0",
            style='Status.TLabel'
        )
        self.errors_stats_label.pack(side='right', padx=10)

        # Текстовое поле для ошибок
        errors_frame = ttk.LabelFrame(self.errors_tab, text=" Лог ошибок", padding=10)
        errors_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.errors_text = tk.Text(errors_frame, height=20, state="disabled", font=('Consolas', 9))
        self.errors_text.pack(fill='both', expand=True)

        errors_scrollbar = ttk.Scrollbar(self.errors_text, command=self.errors_text.yview)
        errors_scrollbar.pack(side='right', fill='y')
        self.errors_text.config(yscrollcommand=errors_scrollbar.set)

    def _refresh_errors(self):
        """Обновляет отображение ошибок."""
        stats = self.error_logger.get_stats()
        self.errors_stats_label.config(
            text=f"Ошибок: {stats['total_errors']} | Предупреждений: {stats['total_warnings']} | Критических: {stats['total_critical']}"
        )

        self.errors_text.config(state="normal")
        self.errors_text.delete("1.0", "end")

        errors = self.error_logger.get_errors()
        if not errors:
            self.errors_text.insert("end", "Ошибок пока нет. Все системы работают нормально.\n")
        else:
            for e in errors:
                self.errors_text.insert("end", f"[{e.severity}] {e.module} | {e.error_type}\n")
                self.errors_text.insert("end", f"  {e.message}\n")
                if e.details:
                    self.errors_text.insert("end", f"  Детали: {e.details}\n")
                if e.recovery_hint:
                    self.errors_text.insert("end", f"  Подсказка: {e.recovery_hint}\n")
                self.errors_text.insert("end", "-" * 50 + "\n")

        self.errors_text.config(state="disabled")

    def _clear_error_log(self):
        """Очищает лог ошибок."""
        if messagebox.askyesno("Подтверждение", "Очистить весь лог ошибок?"):
            self.error_logger.clear()
            self._refresh_errors()
            self._log("Лог ошибок очищен")

    def _open_log_dir(self):
        """Открывает папку с логами."""
        import platform
        import subprocess
        log_dir = str(self.error_logger.log_dir)
        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", log_dir])
            elif platform.system() == "Darwin":
                subprocess.run(["open", log_dir])
            else:
                subprocess.run(["xdg-open", log_dir])
        except Exception as e:
            self._log(f"Не удалось открыть папку: {e}")

    def _browse_game(self):
        directory = filedialog.askdirectory(title="Выберите папку с игрой")
        if directory:
            self.game_dir = Path(directory)
            self.game_path_var.set(str(self.game_dir))
            self._log(f" Выбрана игра: {self.game_dir}")

            try:
                self.extractor = RenPyExtractor(str(self.game_dir))
                self.generator = RenPyGenerator(self.cache, self.game_dir)
                self.pipeline = LocalizationPipeline(
                    code_guard=self.code_guard,
                    protection_manager=self.protection_manager,
                    quote_guard=self.quote_guard,
                    cache=self.cache,
                    glossary=self.glossary,
                    qa=self.qa,
                    engines=self.engines,
                    post_processor=self.post_processor,
                    integrity_checker=self.integrity_checker,
                    text_fitter=self.text_fitter,
                    code_protector=self.code_protector,
                    src_lang=SOURCE_LANGUAGE,
                    tgt_lang=TARGET_LANGUAGE
                )
                self.pipeline.set_progress_callback(self._update_progress)

                self._log(f" Компоненты инициализированы")
                self._log(f" Папка игры: {self.extractor.temp_dir}")
                self._log(f" Нажмите 'Распаковать RPA' если нужно извлечь .rpa архивы")
                self.status_var.set(" Игра выбрана, готовы к работе")
            except Exception as e:
                self._log(f" Ошибка инициализации: {e}")
                self.error_logger.log_error(
                    "init_failed", "Ошибка инициализации компонентов",
                    details=str(e), module="main",
                    recovery_hint="Проверьте путь к игре и наличие .rpa/.rpy файлов"
                )
                self._refresh_errors()

    def _auto_extract_terms(self):
        if not self.game_dir:
            messagebox.showerror("Ошибка", "Выберите папку с игрой!")
            return

        if self.is_processing:
            messagebox.showwarning("Внимание", "Процесс уже выполняется!")
            return

        self.is_processing = True
        self.status_var.set(" Извлечение терминов...")
        self._log(" Начало анализа игры...")

        thread = threading.Thread(target=self._extract_terms_thread, daemon=True)
        thread.start()

    def _extract_terms_thread(self):
        try:
            self.extracted_terms = self.glossary.auto_extract(self.game_dir)
            self.root.after(0, self._populate_glossary_tree)
            self._log(f" Найдено {len(self.extracted_terms)} потенциальных терминов")
            self.status_var.set(f" Найдено {len(self.extracted_terms)} терминов")
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self._log(f" Ошибка извлечения: {e}"))
            self.root.after(0, lambda: self.status_var.set(" Ошибка извлечения"))
            self.error_logger.log_error(
                "term_extraction_failed", "Ошибка извлечения терминов",
                details=error_msg, module="glossary",
                recovery_hint="Проверьте права доступа к файлам игры"
            )
        finally:
            self.root.after(0, lambda: setattr(self, 'is_processing', False))
            self.root.after(0, self._refresh_errors)

    def _get_term_data(self, term_data: Any) -> Dict:
        if hasattr(term_data, 'term'):
            return {
                'term': term_data.term,
                'frequency': term_data.frequency,
                'category': term_data.category.value if hasattr(term_data.category, 'value') else str(term_data.category),
                'translation': term_data.translation,
                'examples': term_data.examples if hasattr(term_data, 'examples') else []
            }
        elif isinstance(term_data, dict):
            return {
                'term': term_data.get('term', ''),
                'frequency': term_data.get('frequency', '-'),
                'category': term_data.get('category', 'other'),
                'translation': term_data.get('translation', ''),
                'examples': term_data.get('examples', [])
            }
        else:
            return {
                'term': str(term_data),
                'frequency': '-',
                'category': 'unknown',
                'translation': '',
                'examples': []
            }

    def _populate_glossary_tree(self):
        for item in self.glossary_tree.get_children():
            self.glossary_tree.delete(item)

        for term_data in self.extracted_terms:
            data = self._get_term_data(term_data)

            examples_list = data['examples'][:2] if data['examples'] else []
            examples_str = "; ".join(examples_list)

            self.glossary_tree.insert('', 'end', values=(
                data['term'],
                data['frequency'],
                data['category'],
                data['translation'],
                examples_str[:50] + "..." if len(examples_str) > 50 else examples_str
            ))

        self._update_glossary_info()

    def _on_term_select(self, event):
        selection = self.glossary_tree.selection()
        if selection:
            item = self.glossary_tree.item(selection[0])
            translation = item['values'][3]
            self.translation_entry.delete(0, 'end')
            self.translation_entry.insert(0, str(translation))

    def _apply_translation(self):
        selection = self.glossary_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите термин!")
            return

        translation = self.translation_entry.get().strip()
        if not translation:
            messagebox.showwarning("Предупреждение", "Введите перевод!")
            return

        item = self.glossary_tree.item(selection[0])
        term = item['values'][0]

        values = list(item['values'])
        values[3] = translation
        self.glossary_tree.item(selection[0], values=values)

        for i, term_data in enumerate(self.extracted_terms):
            if hasattr(term_data, 'term'):
                if term_data.term == term:
                    term_data.translation = translation
                    break
            elif isinstance(term_data, dict):
                if term_data.get('term') == term:
                    term_data['translation'] = translation
                    break

        self.glossary.add(term, translation)
        self._update_glossary_info()
        self._log(f" Термин '{term}' добавлен в глоссарий")

    def _remove_term(self):
        selection = self.glossary_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите термин!")
            return

        item = self.glossary_tree.item(selection[0])
        term = item['values'][0]

        if messagebox.askyesno("Подтверждение", f"Удалить термин '{term}' из глоссария?"):
            self.glossary.remove(term)
            self.glossary_tree.delete(selection[0])
            self._update_glossary_info()
            self._log(f" Термин '{term}' удалён из глоссария")

    def _save_glossary(self):
        try:
            self.glossary.review_and_save(self.extracted_terms)
            messagebox.showinfo("Успех", f"Глоссарий сохранён в {self.glossary.glossary_path}!")
            self._log(f" Глоссарий сохранён: {self.glossary.get_terms_count()} терминов")
            self._update_glossary_info()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")
            self.error_logger.log_error(
                "glossary_save_failed", "Ошибка сохранения глоссария",
                details=str(e), module="glossary"
            )

    def _load_glossary(self):
        file_path = filedialog.askopenfilename(
            title="Выберите glossary.txt",
            filetypes=[("Text files", "*.txt")]
        )

        if file_path:
            try:
                self.glossary.glossary_path = Path(file_path)
                self.glossary._load()

                for item in self.glossary_tree.get_children():
                    self.glossary_tree.delete(item)

                for term, translation in self.glossary.terms.items():
                    self.glossary_tree.insert('', 'end', values=(
                        term, '-', 'loaded', translation, '-'
                    ))

                self._update_glossary_info()
                messagebox.showinfo("Успех", "Глоссарий загружен!")
                self._log(f" Глоссарий загружен: {self.glossary.get_terms_count()} терминов")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить: {e}")
                self.error_logger.log_error(
                    "glossary_load_failed", "Ошибка загрузки глоссария",
                    details=str(e), module="glossary"
                )

    def _clear_glossary(self):
        if messagebox.askyesno("Подтверждение", "Очистить весь глоссарий?"):
            self.glossary.clear()
            self.extracted_terms = []
            for item in self.glossary_tree.get_children():
                self.glossary_tree.delete(item)
            self._update_glossary_info()
            self._log(" Глоссарий очищен")

    def _update_glossary_info(self):
        count = self.glossary.get_terms_count()
        self.glossary_label.config(text=f" Терминов в глоссарии: {count}")
        self.glossary_info_label.config(
            text=f"Найдено терминов: {len(self.extracted_terms)} | В глоссарии: {count}"
        )

    def _extract_rpa(self):
        """Распаковывает RPA архивы игры."""
        if not self.game_dir:
            messagebox.showerror("Ошибка", "Выберите папку с игрой!")
            return

        if self.is_processing:
            messagebox.showwarning("Внимание", "Процесс уже выполняется!")
            return

        self.is_processing = True
        self.status_var.set(" Распаковка RPA...")
        self._log(" Начало распаковки RPA архивов...")

        thread = threading.Thread(target=self._extract_rpa_thread, daemon=True)
        thread.start()

    def _extract_rpa_thread(self):
        try:
            from infrastructure.utils.rpa_extractor import extract_all_rpa_in_game

            game_folder = self.game_dir / "game" if (self.game_dir / "game").exists() else self.game_dir
            results = extract_all_rpa_in_game(str(game_folder))

            total_extracted = sum(r[1] for r in results.values() if r[0])
            total_errors = sum(r[2] for r in results.values())
            success_count = sum(1 for r in results.values() if r[0])

            self._log(f" Распаковано {success_count}/{len(results)} архивов")
            self._log(f" Всего извлечено: {total_extracted} файлов")
            if total_errors > 0:
                self._log(f" Ошибок: {total_errors}")
                self.error_logger.log_warning(
                    "rpa_extraction_errors", f"Ошибки при распаковке RPA",
                    details=f"{total_errors} ошибок", module="rpa",
                    recovery_hint="Проверьте целостность .rpa файлов"
                )

            self.status_var.set(f" RPA распакованы: {total_extracted} файлов")

            # Переинициализируем экстрактор после распаковки
            self.root.after(0, self._reinit_extractor)

        except Exception as e:
            self._log(f" Ошибка распаковки RPA: {e}")
            self.error_logger.log_error(
                "rpa_extraction_failed", "Ошибка распаковки RPA",
                details=str(e), module="rpa",
                recovery_hint="Установите: pip install unrpa"
            )
            self.status_var.set(" Ошибка распаковки RPA")
        finally:
            self.is_processing = False
            self.root.after(0, self._refresh_errors)

    def _reinit_extractor(self):
        """Переинициализирует экстрактор после распаковки RPA."""
        try:
            self.extractor = RenPyExtractor(str(self.game_dir))
            self._log(" Экстрактор переинициализирован с распакованными файлами")
        except Exception as e:
            self._log(f" Ошибка переинициализации: {e}")

    def _translate(self):
        if not self.pipeline:
            messagebox.showerror("Ошибка", "Выберите папку с игрой!")
            return

        if self.is_processing:
            messagebox.showwarning("Внимание", "Процесс уже выполняется!")
            return

        self.is_processing = True
        self.status_var.set(" Перевод...")
        self._log(" Начало перевода...")

        thread = threading.Thread(target=self._translate_thread, daemon=True)
        thread.start()

    def _translate_thread(self):
        try:
            if not self.extractor:
                raise Exception("Экстрактор не инициализирован")

            texts = self.extractor.extract_all()
            self._log(f"Извлечено {len(texts)} строк для перевода")

            if not texts:
                self._log("Нет текста для перевода. Проверьте наличие .rpy файлов.")
                self.error_logger.log_warning(
                    "no_text_found", "Не найден текст для перевода",
                    module="extractor",
                    recovery_hint="Убедитесь что вы распаковали .rpa архивы"
                )
                return

            if self.pipeline:
                results = self.pipeline.translate_batch(texts)
                self.last_translation_results = results
                
                # Подсчитываем статистику
                total = len(results)
                translated_count = sum(1 for r in results if r.get('translated') and r.get('translated') != r.get('text'))
                failed_count = total - translated_count
                
                self._log(f" Переведено {translated_count}/{total} строк")
                
                if failed_count > 0:
                    self._log(f" ⚠️ {failed_count} строк не удалось перевести")
                    self.error_logger.log_warning(
                        "translation_partial_failure", f"{failed_count} строк не переведены",
                        module="translator",
                        recovery_hint="Проверьте доступность движков перевода"
                    )
                else:
                    self._log(f" ✅ Все строки успешно переведены!")

            self.status_var.set(" Перевод завершён")
        except Exception as e:
            self._log(f" Ошибка перевода: {e}")
            self.error_logger.log_error(
                "translation_failed", "Ошибка процесса перевода",
                details=str(e), module="translator",
                recovery_hint="Проверьте настройки движков и пути к игре"
            )
            self.status_var.set(" Ошибка перевода")
        finally:
            self.is_processing = False
            self.progress_var.set(100)
            self.root.after(0, self._refresh_errors)

    def _generate_tl(self):
        if not self.game_dir or not self.generator:
            messagebox.showerror("Ошибка", "Выберите папку с игрой!")
            return

        if self.is_processing:
            messagebox.showwarning("Внимание", "Процесс уже выполняется!")
            return

        self.is_processing = True
        self.status_var.set(" Генерация TL файлов...")
        self._log(" Генерация языкового пакета...")

        thread = threading.Thread(target=self._generate_tl_thread, daemon=True)
        thread.start()

    def _generate_tl_thread(self):
        try:
            if not self.generator:
                raise Exception("Генератор не инициализирован")

            # ✅ ИСПРАВЛЕНО: используем результаты перевода напрямую, если они есть
            translations_data = None
            if self.last_translation_results:
                # Фильтруем только успешно переведённые строки
                translations_data = [
                    r for r in self.last_translation_results
                    if r.get('translated') and r.get('translated') != r.get('text')
                ]
                self._log(f" Используем {len(translations_data)} переводов из последнего сеанса")
            else:
                self._log(" ⚠️ Нет результатов перевода в памяти. Запустите 'Перевести' перед генерацией.")
                # Fallback на кэш (может содержать устаревшие данные)
                self._log(" Используем кэш как fallback...")

            output_dir = self.generator.generate_language_pack(
                self.game_dir,
                translations_data=translations_data
            )
            self._log(f" Языковой пакет создан: {output_dir}")

            # Считаем файлы
            rpy_files = list(output_dir.glob("*.rpy"))
            self._log(f" Создано файлов: {len(rpy_files)}")

            # Генерируем отчёт
            try:
                error_stats = self.error_logger.get_stats()
                report_path = self.report_generator.generate(
                    {
                        "cache_entries": self.cache.get_stats().get('total_entries', 0),
                        "translated_files": len(rpy_files),
                        **error_stats
                    },
                    [f"{e.error_type}: {e.message}" for e in self.error_logger.get_errors()]
                )
                self._log(f" Отчёт сохранён: {report_path}")
            except Exception as e:
                self._log(f" Не удалось создать отчёт: {e}")

            self.status_var.set(" Генерация завершена")
        except Exception as e:
            self._log(f" Ошибка генерации: {e}")
            self.error_logger.log_error(
                "generation_failed", "Ошибка генерации TL файлов",
                details=str(e), module="generator",
                recovery_hint="Проверьте права записи в папку game/tl/"
            )
            self.status_var.set(" Ошибка генерации")
        finally:
            self.is_processing = False
            self.progress_var.set(100)
            self.root.after(0, self._refresh_errors)

    def _clear_cache(self):
        if messagebox.askyesno("Подтверждение", "Очистить весь кэш переводов?"):
            self.cache.clear_cache()
            self._log(" Кэш очищен")
            self.status_var.set(" Кэш очищен")

    def _update_progress(self, current: int, total: int):
        if total > 0:
            progress = (current / total) * 100
            self.progress_var.set(progress)
            self.progress_label.config(text=f"Прогресс: {current}/{total} ({progress:.1f}%)")
            self.root.update_idletasks()

    def _log(self, message: str):
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")


def main():
    """Точка входа"""
    root = tk.Tk()
    icon_path = PROJECT_ROOT / "assets" / "icon.ico"
    if icon_path.exists():
        root.iconbitmap(str(icon_path))
    app = TranslatorProGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
