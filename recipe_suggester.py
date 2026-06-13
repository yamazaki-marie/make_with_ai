"""
食材から料理を提案するGUIアプリ
必要なライブラリ: pip install anthropic
実行方法: python recipe_suggester.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import anthropic
import os
import tkinter.font as tkfont


def get_jp_font():
    """利用可能な日本語フォントを自動検出して返す"""
    candidates = [
        "Noto Sans CJK JP", "Noto Sans JP", "IPAGothic", "IPAPGothic",
        "TakaoGothic", "VL Gothic", "Meiryo", "MS Gothic", "TkDefaultFont"
    ]
    try:
        available = set(tkfont.families())
        for f in candidates:
            if f in available:
                return f
    except Exception:
        pass
    return "TkDefaultFont"


JP_FONT = None  # 起動後に設定


# ===== APIキーの設定 =====
# 方法1: 環境変数 ANTHROPIC_API_KEY を設定する（推奨）
# 方法2: 下の行のコメントを外してAPIキーを直接入力する
# API_KEY = "sk-ant-xxxxxxxxxx"
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


SYSTEM_PROMPT = """あなたは料理の提案をするアシスタントです。
ユーザーが入力した食材と調味料をもとに、作ることができる料理を2〜3品提案してください。
各料理について以下の形式で回答してください：

【料理名】
・説明：（一言で料理の特徴）
・材料：（使用する食材）
・作り方：
  1. 手順1
  2. 手順2
  3. 手順3（以降必要なだけ）
・ポイント：（コツや注意点）

---（区切り線）---

次の料理…という形で続けてください。"""


class RecipeApp:
    def __init__(self, root):
        global JP_FONT
        self.root = root
        self.root.title("食材から料理提案アプリ")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        self.root.configure(bg="#f5f5f0")

        JP_FONT = get_jp_font()
        self._build_ui()

    def _build_ui(self):
        f = JP_FONT
        # タイトル
        title = tk.Label(
            self.root, text="食材から料理を提案", font=(f, 16, "bold"),
            bg="#f5f5f0", fg="#1a1a1a"
        )
        title.pack(pady=(20, 4))

        subtitle = tk.Label(
            self.root, text="手元にある食材を入力してください",
            font=(f, 10), bg="#f5f5f0", fg="#888"
        )
        subtitle.pack(pady=(0, 16))

        # 食材入力エリア
        frame_input = tk.Frame(self.root, bg="#f5f5f0")
        frame_input.pack(fill="x", padx=24)

        tk.Label(frame_input, text="食材・調味料（カンマまたは改行で区切って入力）",
                 font=(f, 10), bg="#f5f5f0", fg="#444").pack(anchor="w")

        self.ingredients_text = scrolledtext.ScrolledText(
            frame_input, height=4, font=(f, 11),
            relief="solid", bd=1, wrap="word"
        )
        self.ingredients_text.pack(fill="x", pady=(4, 0))
        self.ingredients_text.insert("1.0", "例：じゃがいも、玉ねぎ、人参、バジル、塩、オリーブオイル")

        # 追加オプション
        frame_options = tk.Frame(self.root, bg="#f5f5f0")
        frame_options.pack(fill="x", padx=24, pady=(10, 0))

        tk.Label(frame_options, text="ジャンル：",
                 font=(f, 10), bg="#f5f5f0", fg="#444").pack(side="left")

        self.genre_var = tk.StringVar(value="どちらでも")
        for genre in ["どちらでも", "和食", "洋食", "中華"]:
            tk.Radiobutton(
                frame_options, text=genre, variable=self.genre_var, value=genre,
                font=(f, 10), bg="#f5f5f0", fg="#333",
                activebackground="#f5f5f0"
            ).pack(side="left", padx=8)

        # ボタン
        self.suggest_btn = tk.Button(
            self.root, text="料理を提案する →", font=(f, 11, "bold"),
            bg="#378ADD", fg="white", relief="flat", padx=20, pady=8,
            cursor="hand2", command=self.suggest_recipes
        )
        self.suggest_btn.pack(pady=(16, 8))

        # 結果エリア
        frame_result = tk.Frame(self.root, bg="#f5f5f0")
        frame_result.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        tk.Label(frame_result, text="提案された料理",
                 font=(f, 10), bg="#f5f5f0", fg="#444").pack(anchor="w")

        self.result_text = scrolledtext.ScrolledText(
            frame_result, font=(f, 10), relief="solid", bd=1,
            wrap="word", state="disabled", bg="white"
        )
        self.result_text.pack(fill="both", expand=True, pady=(4, 0))

        # ステータスバー
        self.status_var = tk.StringVar(value="食材を入力して「料理を提案する」ボタンを押してください")
        status_bar = tk.Label(
            self.root, textvariable=self.status_var,
            font=(f, 9), bg="#e8e8e3", fg="#666",
            anchor="w", padx=12, pady=4
        )
        status_bar.pack(fill="x", side="bottom")

    def suggest_recipes(self):
        ingredients = self.ingredients_text.get("1.0", "end").strip()
        if not ingredients or ingredients.startswith("例："):
            messagebox.showwarning("入力エラー", "食材を入力してください。")
            return

        if not API_KEY:
            messagebox.showerror(
                "APIキーエラー",
                "ANTHROPIC_API_KEY が設定されていません。\n\n"
                "環境変数を設定するか、スクリプト内の API_KEY に直接入力してください。"
            )
            return

        self.suggest_btn.config(state="disabled", text="提案中...")
        self.status_var.set("Claude APIに接続中...")
        self._set_result("")

        thread = threading.Thread(target=self._call_api, args=(ingredients,), daemon=True)
        thread.start()

    def _call_api(self, ingredients):
        genre = self.genre_var.get()
        genre_text = f"（ジャンル：{genre}）" if genre != "どちらでも" else ""

        user_message = f"手元にある食材：{ingredients}\n{genre_text}\nこれらで作れる料理を提案してください。"

        try:
            client = anthropic.Anthropic(api_key=API_KEY)
            self.root.after(0, lambda: self.status_var.set("料理を考え中..."))

            result = ""
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}]
            ) as stream:
                for text in stream.text_stream:
                    result += text
                    self.root.after(0, self._set_result, result)

            self.root.after(0, self._on_done)

        except anthropic.AuthenticationError:
            self.root.after(0, self._on_error, "APIキーが無効です。正しいキーを設定してください。")
        except Exception as e:
            self.root.after(0, self._on_error, str(e))

    def _set_result(self, text):
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.see("end")
        self.result_text.config(state="disabled")

    def _on_done(self):
        self.suggest_btn.config(state="normal", text="料理を提案する →")
        self.status_var.set("提案が完了しました！")

    def _on_error(self, msg):
        self.suggest_btn.config(state="normal", text="料理を提案する →")
        self.status_var.set(f"エラー：{msg}")
        messagebox.showerror("エラー", msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = RecipeApp(root)
    root.mainloop()
