#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Poker Overlay GUI - Захват окна и распознавание"""
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import ImageGrab, Image
import sys
import win32gui
import win32con
import yaml
from pathlib import Path

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    from yolo_detector import YoloCardDetector
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    YoloCardDetector = None

HAS_DETECTOR = HAS_YOLO


class PokerOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Poker Assistant')
        self.root.geometry('350x500')
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#1a1a2e')
        self.selected_window = None
        self.selected_hwnd = None
        self.config = None
        self.config_path = None
        
        # YOLOv8 AI детектор (обученный на картах!)
        self.yolo_detector = None
        self.detector = None
        self.detector_name = "Не инициализирован"
        
        if HAS_YOLO:
            self.yolo_detector = YoloCardDetector()
            if self.yolo_detector.model:
                # Проверяем какая модель загружена
                if hasattr(self.yolo_detector, 'is_pretrained') and self.yolo_detector.is_pretrained:
                    self.detector = self.yolo_detector
                    self.detector_name = "YOLOv8 AI (обучен на картах!)"
                else:
                    self.detector_name = "⚠️ Нужна обученная модель!"
            else:
                self.detector_name = "YOLO не загружен"
        else:
            self.detector_name = "YOLO не установлен"
        
        self.use_auto_detect = tk.BooleanVar(value=True)
        
        # Заголовок
        title_label = tk.Label(self.root, text='🎴 POKER ASSISTANT', 
                              font=('Arial', 16, 'bold'),
                              bg='#1a1a2e', fg='#2196F3')
        title_label.pack(pady=15)
        
        # Кнопка выбора стола
        btn_select = tk.Button(self.root, text='+ ВЫБРАТЬ СТОЛ', 
                               command=self.select_table, 
                               bg='#2196F3', fg='white', 
                               font=('Arial', 13, 'bold'), 
                               height=2,
                               cursor='hand2',
                               relief='flat')
        btn_select.pack(fill='x', padx=30, pady=10)
        
        # Выбранное окно
        self.label_selected = tk.Label(self.root, text='Окно не выбрано', 
                                       fg='#888',
                                       bg='#1a1a2e',
                                       font=('Arial', 10))
        self.label_selected.pack(pady=5)
        
        # Кнопка загрузки конфига
        btn_config = tk.Button(self.root, text='⚙️ ЗАГРУЗИТЬ КОНФИГ',
                              command=self.load_config,
                              bg='#FF9800', fg='white',
                              font=('Arial', 11),
                              cursor='hand2',
                              relief='flat')
        btn_config.pack(fill='x', padx=30, pady=5)
        
        self.label_config = tk.Label(self.root, text='Конфиг не загружен',
                                     fg='#888', bg='#1a1a2e',
                                     font=('Arial', 9))
        self.label_config.pack(pady=2)
        
        # Информация о детекторе
        if HAS_DETECTOR:
            detector_label = tk.Label(self.root, 
                                     text=f'🤖 Детектор: {self.detector_name}',
                                     bg='#1a1a2e', fg='#4CAF50',
                                     font=('Arial', 10, 'bold'))
            detector_label.pack(pady=5)
            
            check_frame = tk.Frame(self.root, bg='#1a1a2e')
            check_frame.pack(pady=5)
            
            tk.Checkbutton(check_frame, 
                          text='🤖 Автопоиск карт',
                          variable=self.use_auto_detect,
                          bg='#1a1a2e', fg='white',
                          selectcolor='#1a1a2e',
                          activebackground='#1a1a2e',
                          activeforeground='white',
                          font=('Arial', 10)).pack()
        
        # Кнопка теста
        self.btn_test = tk.Button(self.root, text='ТЕСТ РАСПОЗНАВАНИЯ',
                                  command=self.test_capture,
                                  bg='#4CAF50', fg='white',
                                  font=('Arial', 13, 'bold'), 
                                  height=2,
                                  cursor='hand2',
                                  relief='flat',
                                  state='disabled')
        self.btn_test.pack(fill='x', padx=30, pady=10)
        
        # Область вывода
        output_frame = tk.Frame(self.root, bg='#1a1a2e')
        output_frame.pack(fill='both', expand=True, padx=30, pady=10)
        
        tk.Label(output_frame, text='Вывод:', 
                bg='#1a1a2e', fg='#888',
                font=('Arial', 10)).pack(anchor='w')
        
        self.output = tk.Text(output_frame, height=12, width=40,
                             bg='#0f0f1e', fg='#4CAF50',
                             font=('Consolas', 9),
                             relief='flat')
        self.output.pack(fill='both', expand=True, pady=5)
        
        # Кнопка выхода
        btn_exit = tk.Button(self.root, text='Выход', 
                            command=self.root.quit,
                            bg='#f44336', fg='white',
                            font=('Arial', 10),
                            relief='flat',
                            cursor='hand2')
        btn_exit.pack(pady=10)
    
    def get_all_windows(self):
        """Получить список всех окон через win32gui"""
        windows = []
        
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    if width > 300 and height > 300:
                        windows.append({
                            'hwnd': hwnd,
                            'title': title,
                            'rect': rect,
                            'width': width,
                            'height': height
                        })
            return True
        
        win32gui.EnumWindows(callback, None)
        return windows
    
    def load_config(self):
        """Загрузка конфигурации зон ROI"""
        # Автопоиск конфига
        default_path = Path('stol/poker_table_config (1).yaml')
        
        if default_path.exists():
            config_path = str(default_path)
        else:
            config_path = filedialog.askopenfilename(
                title='Выберите конфиг',
                filetypes=[('YAML files', '*.yaml'), ('All files', '*.*')]
            )
        
        if not config_path:
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                self.config_path = config_path
            
            zones_count = len(self.config.get('rois', {}))
            self.label_config.config(text=f'✓ Загружено зон: {zones_count}', fg='#4CAF50')
            self.log(f'Конфиг загружен: {Path(config_path).name}')
            self.log(f'Зон ROI: {zones_count}')
            
        except Exception as e:
            messagebox.showerror('Ошибка', f'Не удалось загрузить конфиг:\n{e}')
    
    def extract_text_from_roi(self, image, roi):
        """Извлечение текста из зоны ROI"""
        if not HAS_TESSERACT:
            return '[Tesseract не установлен]'
        
        try:
            x, y, w, h = roi['x'], roi['y'], roi['w'], roi['h']
            cropped = image.crop((x, y, x + w, y + h))
            text = pytesseract.image_to_string(cropped, config='--psm 10')
            return text.strip() if text.strip() else '[пусто]'
        except Exception as e:
            return f'[ошибка: {e}]'
    
    def select_table(self):
        """Окно выбора покер-стола"""
        select_win = tk.Toplevel(self.root)
        select_win.title('Выбор покер-стола')
        select_win.geometry('500x400')
        select_win.attributes('-topmost', True)
        select_win.configure(bg='#1a1a2e')
        
        tk.Label(select_win, text='Выберите окно покер-клиента:', 
                font=('Arial', 12, 'bold'),
                bg='#1a1a2e', fg='white').pack(pady=10)
        
        # Listbox с прокруткой
        list_frame = tk.Frame(select_win, bg='#1a1a2e')
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        listbox = tk.Listbox(list_frame, height=15,
                            yscrollcommand=scrollbar.set,
                            bg='#0f0f1e', fg='white',
                            font=('Arial', 10),
                            selectbackground='#2196F3')
        listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Получаем список окон через win32gui
        try:
            windows = self.get_all_windows()
            
            if not windows:
                listbox.insert(0, '[Нет доступных окон]')
            else:
                for i, win in enumerate(windows):
                    listbox.insert(i, win['title'])
                    
        except Exception as e:
            messagebox.showerror('Ошибка', f'Ошибка получения списка окон:\n{e}')
            select_win.destroy()
            return
        
        def on_select():
            if windows and listbox.curselection():
                idx = listbox.curselection()[0]
                self.selected_window = windows[idx]
                self.selected_hwnd = windows[idx]['hwnd']
                title = windows[idx]['title']
                short_title = title[:35] + '...' if len(title) > 35 else title
                self.label_selected.config(text=f'✓ {short_title}', fg='#4CAF50')
                self.btn_test.config(state='normal')
                self.log(f'Выбрано окно: {title}')
                select_win.destroy()
        
        # Кнопки
        btn_frame = tk.Frame(select_win, bg='#1a1a2e')
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text='ВЫБРАТЬ', 
                 command=on_select,
                 bg='#2196F3', fg='white',
                 font=('Arial', 11, 'bold'),
                 width=12,
                 relief='flat',
                 cursor='hand2').pack(side='left', padx=5)
        
        tk.Button(btn_frame, text='Отмена', 
                 command=select_win.destroy,
                 bg='#666', fg='white',
                 font=('Arial', 11),
                 width=12,
                 relief='flat',
                 cursor='hand2').pack(side='left', padx=5)
    
    def test_capture(self):
        """Тест захвата окна"""
        self.output.delete(1.0, tk.END)
        self.log('=' * 40)
        self.log('ТЕСТ ЗАХВАТА ОКНА')
        self.log('=' * 40)
        
        if not self.selected_window:
            self.log('❌ Окно не выбрано!')
            return
        
        try:
            self.log('\n📡 Захват окна...')
            
            win = self.selected_window
            rect = win['rect']
            
            self.log(f'   Размер: {win["width"]}x{win["height"]}')
            self.log(f'   Позиция: ({rect[0]}, {rect[1]})')
            
            # Захват через PIL
            bbox = (rect[0], rect[1], rect[2], rect[3])
            img = ImageGrab.grab(bbox=bbox)
            
            self.log(f'\n✅ Захват успешен!')
            self.log(f'   Изображение: {img.size[0]}x{img.size[1]}')
            
            filename = 'test_capture_overlay.png'
            img.save(filename)
            self.log(f'   Сохранено: {filename}')
            
            # АВТОМАТИЧЕСКИЙ ПОИСК КАРТ
            if self.use_auto_detect.get() and self.detector:
                self.log(f'\n🤖 ДЕТЕКТОР: {self.detector_name}')
                self.log(f'=' * 40)
                
                try:
                    result = self.detector.detect_and_recognize(img)
                    
                    # Информация об области стола
                    if self.detector.table_area:
                        tx, ty, tw, th = self.detector.table_area
                        self.log(f'\n🎯 Область стола:')
                        self.log(f'   Позиция: ({tx}, {ty})')
                        self.log(f'   Размер: {tw}x{th}')
                    
                    # Информация о найденных регионах
                    if hasattr(self.detector, 'regions_count'):
                        self.log(f'\n🔍 Найдено регионов: {self.detector.regions_count}')
                    
                    # Если Roboflow, показываем confidence
                    if 'all_detections' in result:
                        avg_conf = sum(d.get('confidence', 0) for d in result['all_detections']) / max(len(result['all_detections']), 1)
                        self.log(f'🎯 Средняя уверенность: {avg_conf:.1%}')
                    
                    # Карты героя
                    self.log(f'\n🃏 Карты героя ({len(result["hero_cards"])}):')
                    for i, card in enumerate(result['hero_cards'], 1):
                        self.log(f'   Карта #{i}: {card}')
                    
                    # Борд
                    self.log(f'\n🎴 Борд ({len(result["board_cards"])}):')
                    board_names = ['Флоп #1', 'Флоп #2', 'Флоп #3', 'Терн', 'Ривер']
                    for i, card in enumerate(result['board_cards']):
                        name = board_names[i] if i < len(board_names) else f'Карта #{i+1}'
                        self.log(f'   {name}: {card}')
                    
                    # Сохраняем debug изображение
                    debug_filename = 'cards_detected_debug.png'
                    result['debug_image'].save(debug_filename)
                    self.log(f'\n📸 Debug: {debug_filename}')
                    self.log(f'   (серые рамки = проверенные зоны)')
                    
                    # Показываем количество найденных объектов
                    if 'all_detections' in result:
                        self.log(f'\n🔍 Найдено объектов YOLO: {len(result["all_detections"])}')
                    
                except Exception as e:
                    self.log(f'\n⚠️ Ошибка автопоиска: {e}')
                    import traceback
                    self.log(traceback.format_exc()[:300])
            
            # OCR по координатам (если конфиг загружен)
            elif self.config and HAS_TESSERACT and not self.use_auto_detect.get():
                self.log(f'\n🎴 OCR ПО КООРДИНАТАМ:')
                rois = self.config.get('rois', {})
                
                # Карты героя
                self.log(f'\n🃏 Карты героя:')
                for i in [1, 2]:
                    key = f'hero_card_{i}'
                    if key in rois:
                        text = self.extract_text_from_roi(img, rois[key])
                        self.log(f'   Карта #{i}: {text}')
                
                # Борд
                self.log(f'\n🎴 Борд:')
                board_names = ['Флоп #1', 'Флоп #2', 'Флоп #3', 'Терн', 'Ривер']
                for i in [1, 2, 3, 4, 5]:
                    key = f'board_card_{i}'
                    if key in rois:
                        text = self.extract_text_from_roi(img, rois[key])
                        self.log(f'   {board_names[i-1]}: {text}')
                
                # Банк и стек
                self.log(f'\n💰 Банк и стеки:')
                if 'pot' in rois:
                    pot = self.extract_text_from_roi(img, rois['pot'])
                    self.log(f'   Банк: {pot}')
                
                if 'hero_stack' in rois:
                    stack = self.extract_text_from_roi(img, rois['hero_stack'])
                    self.log(f'   Стек героя: {stack}')
                
                # Оппоненты
                self.log(f'\n👥 Оппоненты:')
                for i in range(1, 6):
                    key = f'opponent_{i}'
                    if key in rois:
                        opp = self.extract_text_from_roi(img, rois[key])
                        if opp and opp != '[пусто]':
                            self.log(f'   Оппонент #{i}: {opp}')
            
            elif not HAS_DETECTOR:
                self.log(f'\n⚠️ Автопоиск недоступен!')
                self.log(f'   Установите: pip install opencv-python')
            
            elif not self.config:
                self.log(f'\n⚠️ Конфиг не загружен!')
                self.log(f'   Загрузите конфиг или включите автопоиск')
            
            elif not HAS_TESSERACT:
                self.log(f'\n⚠️ Tesseract не установлен!')
                self.log(f'   pip install pytesseract')
            
            self.log(f'\n' + '=' * 40)
            self.log(f'✓ ТЕСТ ЗАВЕРШЕН')
            self.log(f'=' * 40)
            
        except Exception as e:
            self.log(f'\n❌ ОШИБКА: {e}')
            import traceback
            self.log(traceback.format_exc())
    
    def log(self, message):
        """Вывод в лог"""
        self.output.insert(tk.END, message + '\n')
        self.output.see(tk.END)
        self.root.update()
    
    def run(self):
        """Запуск"""
        self.root.mainloop()


if __name__ == '__main__':
    try:
        app = PokerOverlay()
        app.run()
    except Exception as e:
        print(f'Ошибка: {e}')
        import traceback
        traceback.print_exc()
        input('Press Enter to exit...')
