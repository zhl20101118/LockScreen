# config.py - 最终稳定版 | 托盘图标 | 4:3 | 自动配色 | @Zhl2010
import os
import sys
import json
import hashlib
import subprocess
import threading
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageDraw

# 确保 pystray 已安装
try:
    import pystray
except ImportError:
    print("请先安装 pystray: pip install pystray")
    sys.exit(1)

# ------------------------------- 路径与目录 -------------------------------
LOG_DIR = "log"
PASSWORD_FILE = os.path.join(LOG_DIR, "pass")
SETTINGS_FILE = os.path.join(LOG_DIR, "settings.json")
ICON_FILE = os.path.join(LOG_DIR, "icon.png")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# ------------------------------- 密码管理器 -------------------------------
class PasswordManager:
    PASSWORD_FILE = PASSWORD_FILE
    SALT = b"lockscreen_secure_salt"

    @classmethod
    def _hash(cls, pwd):
        h = hashlib.sha256()
        h.update(cls.SALT)
        h.update(pwd.encode('utf-8'))
        return h.hexdigest()

    @classmethod
    def initialize(cls):
        if not os.path.exists(cls.PASSWORD_FILE):
            cls.save_password("123456")
            print("初始密码已设为 123456")

    @classmethod
    def save_password(cls, new_pwd):
        with open(cls.PASSWORD_FILE, "w") as f:
            f.write(cls._hash(new_pwd))

    @classmethod
    def verify(cls, pwd):
        if not os.path.exists(cls.PASSWORD_FILE):
            cls.initialize()
        try:
            with open(cls.PASSWORD_FILE, "r") as f:
                stored = f.read().strip()
            return stored == cls._hash(pwd)
        except:
            return False

# ------------------------------- 设置管理器 -------------------------------
class SettingsManager:
    SETTINGS_FILE = SETTINGS_FILE

    @classmethod
    def load(cls):
        if os.path.exists(cls.SETTINGS_FILE):
            try:
                with open(cls.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"wallpaper": "", "show_time": False, "transparent_bg": False, "theme": "auto"}

    @classmethod
    def save(cls, settings):
        with open(cls.SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)

# ------------------------------- 主应用程序 -------------------------------
class ConfigApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("锁屏设置")                     # 修改标题
        self.geometry("800x600")                  # 4:3
        self.resizable(False, False)
        self.center_window()
        self.attributes('-alpha', 0.97)

        ctk.set_default_color_theme("green")      # 绿色主题，自动适配深浅色

        PasswordManager.initialize()
        self.settings = SettingsManager.load()

        theme = self.settings.get("theme", "auto")
        self._apply_theme(theme)

        self._notify_after_id = None

        # 主容器 (透明背景，让主题完全控制)
        self.main_frame = ctk.CTkFrame(self, corner_radius=28, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # 顶部栏
        top_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 12))
        title_lab = ctk.CTkLabel(top_bar, text="锁屏设置", font=ctk.CTkFont(size=26, weight="bold"))
        title_lab.pack(side="left", padx=10)

        self.theme_var = ctk.StringVar(value=self._theme_to_display(theme))
        theme_seg = ctk.CTkSegmentedButton(
            top_bar, values=["浅色", "深色", "自动"],
            variable=self.theme_var, command=self._change_theme,
            font=ctk.CTkFont(size=12), width=170, corner_radius=18
        )
        theme_seg.pack(side="right", padx=10)

        # 分段选择器
        self.seg_btn = ctk.CTkSegmentedButton(
            self.main_frame, values=["修改密码", "壁纸与样式", "关于"],
            command=self._switch_tab,
            font=ctk.CTkFont(size=14),
            corner_radius=24
        )
        self.seg_btn.pack(pady=(6, 18), padx=20, fill="x")
        self.seg_btn.set("修改密码")

        # 卡片容器
        self.card_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.card_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.card_pw = ctk.CTkFrame(self.card_container, corner_radius=22)
        self.card_wall = ctk.CTkFrame(self.card_container, corner_radius=22)
        self.card_about = ctk.CTkFrame(self.card_container, corner_radius=22)

        for card in (self.card_pw, self.card_wall, self.card_about):
            card.pack(fill="both", expand=True)

        self._build_password_ui()
        self._build_wallpaper_ui()
        self._build_about_ui()

        self._switch_tab("修改密码")

        # 底部通知栏
        self.notify_label = ctk.CTkLabel(self.main_frame, text="", font=ctk.CTkFont(size=12), corner_radius=14, padx=14, pady=6)
        self.notify_label.pack(pady=(0, 10))
        self.notify_label.pack_forget()

        # 延迟启动托盘线程 (确保图标出现)
        self.after(100, self._start_tray_thread)

        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.after(50, self._bring_to_front)
        self.after(200, self._bring_to_front)

    def _apply_theme(self, mode):
        if mode == "light":
            ctk.set_appearance_mode("light")
        elif mode == "dark":
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("system")

    def _theme_to_display(self, mode):
        mapping = {"light": "浅色", "dark": "深色", "system": "自动"}
        return mapping.get(mode, "自动")

    def center_window(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"800x600+{sw//2-400}+{sh//2-300}")

    def _bring_to_front(self):
        self.lift()
        self.focus_force()
        self.attributes('-topmost', True)
        self.after(200, lambda: self.attributes('-topmost', False))

    def hide_window(self):
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self._bring_to_front()

    def _change_theme(self, choice):
        mapping = {"浅色": "light", "深色": "dark", "自动": "system"}
        mode = mapping[choice]
        self._apply_theme(mode)
        self.settings["theme"] = mode
        SettingsManager.save(self.settings)
        self._show_notification(f"主题已切换为{choice}")

    def _show_notification(self, msg, is_err=False):
        if self._notify_after_id:
            self.after_cancel(self._notify_after_id)
        color = "#E67E22" if is_err else "#2E8B57"
        self.notify_label.configure(text=f"• {msg}", fg_color=color, text_color="white")
        self.notify_label.pack(pady=(0, 10))
        self._notify_after_id = self.after(2500, self._hide_notification)

    def _hide_notification(self):
        self.notify_label.pack_forget()
        self._notify_after_id = None

    def _switch_tab(self, tab_name):
        for card in (self.card_pw, self.card_wall, self.card_about):
            card.pack_forget()
        if tab_name == "修改密码":
            self.card_pw.pack(fill="both", expand=True)
        elif tab_name == "壁纸与样式":
            self.card_wall.pack(fill="both", expand=True)
        else:
            self.card_about.pack(fill="both", expand=True)

    # ==================== 修改密码页面 ====================
    def _build_password_ui(self):
        self.card_pw.grid_columnconfigure(0, weight=1)
        self.card_pw.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.card_pw, text="原密码", font=ctk.CTkFont(size=15)).grid(row=0, column=0, padx=10, pady=(45,20), sticky='e')
        self.old_entry = ctk.CTkEntry(self.card_pw, show="*", width=320, corner_radius=18, border_width=1)
        self.old_entry.grid(row=0, column=1, padx=10, pady=(45,20), sticky='w')

        ctk.CTkLabel(self.card_pw, text="新密码", font=ctk.CTkFont(size=15)).grid(row=1, column=0, padx=10, pady=18, sticky='e')
        self.new_entry = ctk.CTkEntry(self.card_pw, show="*", width=320, corner_radius=18, border_width=1)
        self.new_entry.grid(row=1, column=1, padx=10, pady=18, sticky='w')

        ctk.CTkLabel(self.card_pw, text="确认密码", font=ctk.CTkFont(size=15)).grid(row=2, column=0, padx=10, pady=18, sticky='e')
        self.confirm_entry = ctk.CTkEntry(self.card_pw, show="*", width=320, corner_radius=18, border_width=1)
        self.confirm_entry.grid(row=2, column=1, padx=10, pady=18, sticky='w')

        btn_frame = ctk.CTkFrame(self.card_pw, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=2, pady=45)
        ctk.CTkButton(btn_frame, text="确认修改", command=self._change_password, width=160, corner_radius=28, font=ctk.CTkFont(size=13)).pack(side='left', padx=20)
        ctk.CTkButton(btn_frame, text="清空字段", command=self._clear_password_fields, width=160, corner_radius=28, fg_color="#B85C5C", hover_color="#9E4646", font=ctk.CTkFont(size=13)).pack(side='left', padx=20)

    def _change_password(self):
        old = self.old_entry.get()
        new = self.new_entry.get()
        cf = self.confirm_entry.get()
        if not PasswordManager.verify(old):
            self._show_notification("原密码错误", is_err=True)
            self.old_entry.delete(0, 'end')
            return
        if new != cf:
            self._show_notification("两次密码不一致", is_err=True)
            self.confirm_entry.delete(0, 'end')
            return
        PasswordManager.save_password(new)
        self._show_notification("密码修改成功，下次锁屏生效")
        self._clear_password_fields()

    def _clear_password_fields(self):
        self.old_entry.delete(0, 'end')
        self.new_entry.delete(0, 'end')
        self.confirm_entry.delete(0, 'end')

    # ==================== 壁纸与样式页面 ====================
    def _build_wallpaper_ui(self):
        scroll_frame = ctk.CTkScrollableFrame(self.card_wall, fg_color="transparent", corner_radius=0)
        scroll_frame.pack(fill="both", expand=True)

        self.trans_var = ctk.BooleanVar(value=self.settings.get("transparent_bg", False))
        trans_sw = ctk.CTkSwitch(
            scroll_frame, text="透明背景模式 (忽略壁纸)", variable=self.trans_var,
            command=self._on_transparent_toggle, font=ctk.CTkFont(size=14), switch_width=50
        )
        trans_sw.pack(anchor='w', pady=(28, 16), padx=28)

        self.wall_group = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        self.wall_group.pack(fill='x', padx=28, pady=6)

        path_frame = ctk.CTkFrame(self.wall_group, fg_color="transparent")
        path_frame.pack(fill='x', pady=8)
        self.wall_entry = ctk.CTkEntry(path_frame, placeholder_text="选择壁纸图片", width=500, corner_radius=18)
        self.wall_entry.pack(side='left', padx=(0, 12))
        self.wall_entry.insert(0, self.settings.get("wallpaper", ""))
        self.browse_btn = ctk.CTkButton(path_frame, text="浏览", command=self._browse_wallpaper, width=90, corner_radius=18)
        self.browse_btn.pack(side='left')

        preview_container = ctk.CTkFrame(self.wall_group, fg_color="transparent")
        preview_container.pack(fill='x', pady=(20, 16))
        self.preview_label = ctk.CTkLabel(preview_container, text="壁纸预览", anchor='w', font=ctk.CTkFont(size=13))
        self.preview_label.pack(anchor='w', pady=(0, 8))
        self.preview_img = ctk.CTkLabel(
            preview_container, text="", width=680, height=180,
            corner_radius=22, fg_color=("#EFF3F8", "#2D2D3F")
        )
        self.preview_img.pack()

        if not self.trans_var.get() and self.settings.get("wallpaper"):
            self._update_preview(self.settings["wallpaper"])
        else:
            self.preview_img.configure(text="(暂无预览)")

        self.time_var = ctk.BooleanVar(value=self.settings.get("show_time", False))
        time_sw = ctk.CTkSwitch(
            scroll_frame, text="锁屏时显示当前时间 (左下角)", variable=self.time_var,
            command=self._on_time_toggle, font=ctk.CTkFont(size=14), switch_width=50
        )
        time_sw.pack(anchor='w', pady=(18, 30), padx=28)

        self._update_wallpaper_access()

    def _update_wallpaper_access(self):
        if self.trans_var.get():
            self.wall_entry.configure(state="disabled")
            self.browse_btn.configure(state="disabled")
            self.preview_img.configure(image=None, text="透明模式已开启，不显示壁纸")
        else:
            self.wall_entry.configure(state="normal")
            self.browse_btn.configure(state="normal")
            wp = self.settings.get("wallpaper", "")
            if wp:
                self._update_preview(wp)
            else:
                self.preview_img.configure(image=None, text="(未选择壁纸)")

    def _on_transparent_toggle(self):
        new_val = self.trans_var.get()
        self.settings["transparent_bg"] = new_val
        SettingsManager.save(self.settings)
        self._update_wallpaper_access()
        self._show_notification("透明模式已" + ("开启" if new_val else "关闭"))

    def _browse_wallpaper(self):
        if self.trans_var.get():
            return
        path = filedialog.askopenfilename(filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if path:
            self.wall_entry.delete(0, 'end')
            self.wall_entry.insert(0, path)
            self._save_wallpaper_path(path)

    def _save_wallpaper_path(self, path):
        if not path or not os.path.isfile(path):
            self._show_notification("文件不存在", is_err=True)
            return
        self.settings["wallpaper"] = path
        if self.settings["transparent_bg"]:
            self.settings["transparent_bg"] = False
            self.trans_var.set(False)
            self._update_wallpaper_access()
        SettingsManager.save(self.settings)
        self._update_preview(path)
        self._show_notification("壁纸已保存")

    def _update_preview(self, path):
        try:
            img = Image.open(path)
            img.thumbnail((660, 170), Image.Resampling.LANCZOS)
            photo = ctk.CTkImage(img, size=(img.width, img.height))
            self.preview_img.configure(image=photo, text="")
            self.preview_img.image = photo
        except Exception:
            self.preview_img.configure(image=None, text="预览失败，请检查图片文件")

    def _on_time_toggle(self):
        self.settings["show_time"] = self.time_var.get()
        SettingsManager.save(self.settings)
        self._show_notification("时间显示" + ("已开启" if self.time_var.get() else "已关闭"))

    # ==================== 关于页面 ====================
    def _build_about_ui(self):
        info = """锁屏设置 · 4:3 版本

• 自定义壁纸 / 透明背景
• 锁屏实时时钟
• 自动保存 / 双主题
• 系统托盘控制

@Zhl2010"""
        about_lab = ctk.CTkLabel(self.card_about, text=info, justify='left', font=ctk.CTkFont(size=13), padx=40, pady=30)
        about_lab.pack()

    # ==================== 系统托盘 ====================
    def _start_tray_thread(self):
        self.tray_thread = threading.Thread(target=self._setup_tray, daemon=True)
        self.tray_thread.start()

    def _create_tray_icon(self):
        size = 64
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.arc((20, 12, 44, 36), start=0, end=180, fill=(100, 150, 100), width=5)
        draw.rounded_rectangle((14, 30, 50, 58), radius=10, fill=(120, 180, 120), outline=(60, 100, 60))
        draw.ellipse((28, 42, 36, 50), fill=(40, 70, 40))
        draw.rectangle((30, 48, 34, 55), fill=(40, 70, 40))
        return img

    def _setup_tray(self):
        # 确保图标存在
        if os.path.exists(ICON_FILE):
            try:
                icon_img = Image.open(ICON_FILE).resize((64, 64), Image.Resampling.LANCZOS)
            except:
                icon_img = self._create_tray_icon()
        else:
            icon_img = self._create_tray_icon()

        menu = pystray.Menu(
            pystray.MenuItem("启动锁屏", self._launch_lockscreen),
            pystray.MenuItem("显示窗口", self.show_window),
            pystray.MenuItem("退出程序", self._quit_app)
        )
        icon = pystray.Icon("lock_config", icon_img, "锁屏设置", menu)
        icon.run()

    def _launch_lockscreen(self):
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
        exe = os.path.join(base, 'lockscreen.exe')
        py = os.path.join(base, 'lockscreen.py')
        if os.path.exists(exe):
            subprocess.Popen([exe])
        elif os.path.exists(py):
            subprocess.Popen([sys.executable, py])
        else:
            self._show_notification("未找到锁屏程序", is_err=True)

    def _quit_app(self):
        self.quit()
        os._exit(0)

if __name__ == "__main__":
    app = ConfigApp()
    app.mainloop()

