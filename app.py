from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Optional

from calc_core import FREQUENCIES_HZ, compute_c_and_ctr, compute_dnt, compute_dnt_w, round_half_up

APP_PASSWORD = "88961109"


def parse_number(text: str) -> Optional[float]:
    s = text.strip()
    if not s:
        return None
    s = s.replace("，", ".").replace(",", ".")
    try:
        return float(s)
    except ValueError as exc:
        raise ValueError(f"无法识别的数字：{text}") from exc


def fmt1(value: Optional[float]) -> str:
    if value is None:
        return ""
    return f"{round_half_up(value, 1):.1f}"


def fmt2(value: Optional[float]) -> str:
    if value is None:
        return ""
    return f"{round_half_up(value, 2):.2f}"


class DnTApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("现场墙体隔声测量计算表（ISO717-1-2013）")
        self.root.geometry("860x900")
        self.root.minsize(820, 760)

        self.l1_entries: list[tk.Entry] = []
        self.l2_entries: list[tk.Entry] = []
        self.rt_entries: list[tk.Entry] = []
        self.dnt_labels: list[tk.Label] = []

        self.result_dntw_var = tk.StringVar(value="")
        self.result_c_var = tk.StringVar(value="")
        self.result_ctr_var = tk.StringVar(value="")
        self.export_cache = ""

        self._build_ui()
        self._refresh_export_text()

    def _symbol_label(
        self,
        parent: tk.Widget,
        base_text: str,
        sub_text: str = "",
        suffix_text: str = "",
        base_font: tuple[str, int, str] = ("Microsoft YaHei UI", 12, "bold"),
        sub_font: tuple[str, int] = ("Microsoft YaHei UI", 9),
        bg: str = "#f2f2f2",
        fg: Optional[str] = None,
    ) -> tk.Frame:
        """Render a compact symbol with visual subscript using two labels."""
        frame = tk.Frame(parent, bg=bg)
        base = tk.Label(frame, text=base_text, font=base_font, bg=bg, fg=fg)
        base.pack(side=tk.LEFT, anchor="s")
        if sub_text:
            sub = tk.Label(frame, text=sub_text, font=sub_font, bg=bg, fg=fg)
            sub.pack(side=tk.LEFT, anchor="s", pady=(6, 0))
        if suffix_text:
            suffix = tk.Label(frame, text=suffix_text, font=base_font, bg=bg, fg=fg)
            suffix.pack(side=tk.LEFT, anchor="s")
        return frame

    def _table_cell(self, parent: tk.Widget, row: int, col: int, width: int, height: int) -> tk.Frame:
        cell = tk.Frame(
            parent,
            bg="white",
            width=width,
            height=height,
            highlightbackground="#6d6d6d",
            highlightthickness=1,
            bd=0,
        )
        cell.grid(row=row, column=col, sticky="nsew")
        # Cells contain widgets laid out by `pack`, so disable pack propagation
        # (in addition to grid propagation) to lock the designed width/height.
        cell.pack_propagate(False)
        cell.grid_propagate(False)
        return cell

    def _build_ui(self) -> None:
        main = tk.Frame(self.root, bg="#f2f2f2")
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        title_row = tk.Frame(main, bg="#f2f2f2")
        title_row.pack(pady=(2, 40))
        tk.Label(
            title_row,
            text="现场墙体隔声测量计算表",
            font=("Microsoft YaHei UI", 20),
            bg="#f2f2f2",
        ).pack(side=tk.LEFT)
        tk.Label(
            title_row,
            text="（ISO717-1-2013）",
            font=("Microsoft YaHei UI", 18),
            bg="#f2f2f2",
        ).pack(side=tk.LEFT)

        content_row = tk.Frame(main, bg="#f2f2f2")
        content_row.pack(anchor="n", pady=(0, 8))

        table_outer = tk.Frame(content_row, bg="#f2f2f2")
        table_outer.pack(side=tk.LEFT, anchor="n")

        table = tk.Frame(table_outer, bg="white")
        table.pack(anchor="n")

        button_panel = tk.Frame(content_row, bg="#f2f2f2")
        # Move the button group downward to align approximately with table middle.
        button_panel.pack(side=tk.LEFT, anchor="n", padx=(24, 0), pady=(235, 0))

        calc_btn = tk.Button(
            button_panel,
            text="计算",
            font=("Microsoft YaHei UI", 12, "bold"),
            bg="#3f8ad8",
            fg="white",
            relief="raised",
            bd=1,
            width=10,
            pady=6,
            command=self.calculate,
        )
        calc_btn.pack(fill=tk.X)

        copy_btn = tk.Button(
            button_panel,
            text="复制结果",
            font=("Microsoft YaHei UI", 12, "bold"),
            relief="raised",
            bd=1,
            width=10,
            pady=6,
            command=self.copy_export_text,
        )
        copy_btn.pack(fill=tk.X, pady=(12, 0))

        headers = ["1/3 倍频程\n频率 (Hz)", "声源室\n声压级 (dB)", "受声室\n声压级 (dB)", "混响时间 T(s)", ""]
        # Convert desired visual pixel widths into Tk logical units so the UI remains
        # correct under Windows display scaling (DPI).
        scale = float(self.root.tk.call("tk", "scaling"))
        desired_first_px = 150
        desired_col_2_4_px = 150
        desired_col_5_px = 100
        first_col = max(60, int(round(desired_first_px / scale)))
        col_2_4 = max(40, int(round(desired_col_2_4_px / scale)))
        col_5 = max(35, int(round(desired_col_5_px / scale)))
        col_px = [first_col, col_2_4, col_2_4, col_2_4, col_5]
        header_h = 52
        row_h = 35
        table.configure(width=sum(col_px))
        table.pack_propagate(False)

        for c, htext in enumerate(headers):
            cell = self._table_cell(table, 0, c, col_px[c], header_h)
            if c == 4:
                symbol = self._symbol_label(
                    cell,
                    base_text="D",
                    sub_text="nT",
                    suffix_text="",
                    base_font=("Microsoft YaHei UI", 12, "bold"),
                    sub_font=("Microsoft YaHei UI", 9),
                    bg="white",
                )
                # Keep DnT visually centered in header cell.
                symbol.place(relx=0.5, rely=0.5, anchor="center")
            else:
                lbl = tk.Label(
                    cell,
                    text=htext,
                    font=("Microsoft YaHei UI", 12, "bold"),
                    bg="white",
                    justify="center",
                )
                lbl.pack(fill=tk.BOTH, expand=True)

        for i, freq in enumerate(FREQUENCIES_HZ):
            r = i + 1

            cell_f = self._table_cell(table, r, 0, col_px[0], row_h)
            tk.Label(cell_f, text=str(freq), font=("Microsoft YaHei UI", 12), bg="white").pack(
                fill=tk.BOTH, expand=True
            )

            c1 = self._table_cell(table, r, 1, col_px[1], row_h)
            e1 = tk.Entry(c1, font=("Microsoft YaHei UI", 12), justify="center", relief="flat", bd=0)
            e1.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

            c2 = self._table_cell(table, r, 2, col_px[2], row_h)
            e2 = tk.Entry(c2, font=("Microsoft YaHei UI", 12), justify="center", relief="flat", bd=0)
            e2.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

            c3 = self._table_cell(table, r, 3, col_px[3], row_h)
            e3 = tk.Entry(c3, font=("Microsoft YaHei UI", 12), justify="center", relief="flat", bd=0)
            e3.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)

            c4 = self._table_cell(table, r, 4, col_px[4], row_h)
            dnt_lbl = tk.Label(c4, text="", font=("Microsoft YaHei UI", 12), bg="white")
            dnt_lbl.pack(fill=tk.BOTH, expand=True)

            e1.bind("<Control-v>", lambda e, rr=i, cc=0: self._on_paste(e, rr, cc))
            e1.bind("<Control-V>", lambda e, rr=i, cc=0: self._on_paste(e, rr, cc))
            e2.bind("<Control-v>", lambda e, rr=i, cc=1: self._on_paste(e, rr, cc))
            e2.bind("<Control-V>", lambda e, rr=i, cc=1: self._on_paste(e, rr, cc))
            e3.bind("<Control-v>", lambda e, rr=i, cc=2: self._on_paste(e, rr, cc))
            e3.bind("<Control-V>", lambda e, rr=i, cc=2: self._on_paste(e, rr, cc))

            self.l1_entries.append(e1)
            self.l2_entries.append(e2)
            self.rt_entries.append(e3)
            self.dnt_labels.append(dnt_lbl)

        # Hard-lock column widths to make visual changes deterministic.
        table.grid_columnconfigure(0, minsize=col_px[0], weight=0)
        for c in range(1, 4):
            table.grid_columnconfigure(c, minsize=col_2_4, weight=0)
        table.grid_columnconfigure(4, minsize=col_5, weight=0)

        # Keep the metrics panel width aligned with the main table width so its left edge
        # lines up with the first table column.
        table_total_width = sum(col_px)
        # Keep fixed width for left-edge alignment with table, but also set explicit
        # height to avoid clipping when pack_propagate(False) is enabled.
        # Place result panel under table container so its left edge aligns with table.
        result = tk.Frame(table_outer, bg="#f2f2f2", width=table_total_width, height=64)
        result.pack(anchor="w", pady=(10, 6))
        result.pack_propagate(False)
        # Use a blue highlighted plate similar to the "计算" button style.
        metrics_plate = tk.Frame(
            result,
            bg="#3f8ad8",
            highlightbackground="#2e6ead",
            highlightthickness=1,
            bd=0,
        )
        metrics_plate.pack(side=tk.LEFT, padx=(0, 0), pady=(0, 0), ipadx=12, ipady=8)

        item1 = tk.Frame(metrics_plate, bg="#3f8ad8")
        item1.pack(side=tk.LEFT, padx=(0, 48))
        self._symbol_label(
            item1,
            base_text="D",
            sub_text="nT,w",
            suffix_text=":",
            base_font=("Microsoft JhengHei UI Light", 14, "bold"),
            sub_font=("Microsoft JhengHei UI Light", 11, "bold"),
            bg="#3f8ad8",
            fg="white",
        ).pack(side=tk.LEFT)
        tk.Label(
            item1,
            textvariable=self.result_dntw_var,
            font=("Microsoft JhengHei UI Light", 14, "bold"),
            fg="white",
            bg="#3f8ad8",
        ).pack(side=tk.LEFT, padx=(6, 0))

        # Keep spacing a bit tighter before Ctr (equivalent to moving Ctr left)
        # without using negative padding (which crashes in packaged app).
        item2 = tk.Frame(metrics_plate, bg="#3f8ad8")
        item2.pack(side=tk.LEFT, padx=(0, 28))
        self._symbol_label(
            item2,
            base_text="C",
            sub_text="",
            suffix_text=":",
            base_font=("Microsoft JhengHei UI Light", 14, "bold"),
            sub_font=("Microsoft JhengHei UI Light", 11, "bold"),
            bg="#3f8ad8",
            fg="white",
        ).pack(side=tk.LEFT)
        tk.Label(
            item2,
            textvariable=self.result_c_var,
            font=("Microsoft JhengHei UI Light", 14, "bold"),
            fg="white",
            bg="#3f8ad8",
        ).pack(side=tk.LEFT, padx=(6, 0))
        item3 = tk.Frame(metrics_plate, bg="#3f8ad8")
        item3.pack(side=tk.LEFT, padx=(0, 0))
        self._symbol_label(
            item3,
            base_text="C",
            sub_text="tr",
            suffix_text=":",
            base_font=("Microsoft JhengHei UI Light", 14, "bold"),
            sub_font=("Microsoft JhengHei UI Light", 11, "bold"),
            bg="#3f8ad8",
            fg="white",
        ).pack(side=tk.LEFT)
        tk.Label(
            item3,
            textvariable=self.result_ctr_var,
            font=("Microsoft JhengHei UI Light", 14, "bold"),
            fg="white",
            bg="#3f8ad8",
        ).pack(side=tk.LEFT, padx=(6, 0))

        # Bottom results text area intentionally removed from UI per latest design.
        copyright_label = tk.Label(
            main,
            text="版权所有 © 张磊300035",
            font=("Microsoft YaHei UI", 9),
            fg="#666666",
            bg="#f2f2f2",
        )
        copyright_label.pack(anchor="e", pady=(6, 0))

    def _on_paste(self, _event: tk.Event, start_row: int, start_col: int) -> str:
        try:
            block = self.root.clipboard_get()
        except tk.TclError:
            return "break"

        lines = block.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        lines = [ln for ln in lines if ln.strip()]
        if not lines:
            return "break"

        targets = [self.l1_entries, self.l2_entries, self.rt_entries]

        for r_off, line in enumerate(lines):
            row = start_row + r_off
            if row >= len(FREQUENCIES_HZ):
                break

            cols = [c.strip() for c in line.split("\t")]
            if not cols:
                continue

            maybe_freq = None
            try:
                maybe_freq = parse_number(cols[0])
            except ValueError:
                maybe_freq = None
            if maybe_freq is not None and abs(maybe_freq - FREQUENCIES_HZ[row]) < 0.6:
                cols = cols[1:]

            for c_off, value in enumerate(cols):
                c = start_col + c_off
                if c > 2:
                    break
                entry = targets[c][row]
                entry.delete(0, tk.END)
                entry.insert(0, value)

        return "break"

    def calculate(self) -> None:
        dnt_values: list[float] = []
        errors: list[str] = []

        for i, freq in enumerate(FREQUENCIES_HZ):
            l1_raw = self.l1_entries[i].get().strip()
            l2_raw = self.l2_entries[i].get().strip()
            t_raw = self.rt_entries[i].get().strip()

            try:
                l1 = parse_number(l1_raw)
                l2 = parse_number(l2_raw)
                t_sec = parse_number(t_raw)
            except ValueError as exc:
                errors.append(f"{freq} Hz：{exc}")
                self.dnt_labels[i].configure(text="")
                continue

            if l1 is None and l2 is None and t_sec is None:
                self.dnt_labels[i].configure(text="")
                continue

            if l1 is None or l2 is None or t_sec is None:
                errors.append(f"{freq} Hz：请完整输入 声源室声压级、受声室声压级、混响时间 T(s)")
                self.dnt_labels[i].configure(text="")
                continue

            if t_sec <= 0:
                errors.append(f"{freq} Hz：混响时间 T(s) 必须大于 0")
                self.dnt_labels[i].configure(text="")
                continue

            dnt = compute_dnt(l1, l2, t_sec)
            dnt_values.append(dnt)

            self.l1_entries[i].delete(0, tk.END)
            self.l1_entries[i].insert(0, fmt1(l1))
            self.l2_entries[i].delete(0, tk.END)
            self.l2_entries[i].insert(0, fmt1(l2))
            self.rt_entries[i].delete(0, tk.END)
            self.rt_entries[i].insert(0, fmt2(t_sec))
            self.dnt_labels[i].configure(text=fmt1(dnt))

        dnt_w: Optional[int] = None
        c_val: Optional[int] = None
        ctr_val: Optional[int] = None

        if len(dnt_values) == len(FREQUENCIES_HZ):
            try:
                dnt_w, _shift, _sum_dev = compute_dnt_w(dnt_values)
                c_val, ctr_val = compute_c_and_ctr(dnt_values, dnt_w)
            except ValueError as exc:
                errors.append(str(exc))

        self.result_dntw_var.set("" if dnt_w is None else str(dnt_w) + " dB")
        self.result_c_var.set("" if c_val is None else str(c_val) + " dB")
        self.result_ctr_var.set("" if ctr_val is None else str(ctr_val) + " dB")

        self._refresh_export_text(dnt_w, c_val, ctr_val)

        if errors:
            messagebox.showwarning("输入提示", "发现以下问题：\n\n" + "\n".join(errors))

    def _build_export_tsv(self, dnt_w: Optional[int], c: Optional[int], ctr: Optional[int]) -> str:
        lines = ["1/3倍频程频率(Hz)\t声源室声压级\t受声室声压级\tT(s)\tDnT"]
        for i, freq in enumerate(FREQUENCIES_HZ):
            lines.append(
                "\t".join(
                    [
                        str(freq),
                        self.l1_entries[i].get().strip(),
                        self.l2_entries[i].get().strip(),
                        self.rt_entries[i].get().strip(),
                        self.dnt_labels[i].cget("text").strip(),
                    ]
                )
            )
        lines.append(f"DnT,w\t\t\t\t{'' if dnt_w is None else dnt_w}")
        lines.append(f"C\t\t\t\t{'' if c is None else c}")
        lines.append(f"Ctr\t\t\t\t{'' if ctr is None else ctr}")
        lines.append(f"C, Ctr\t\t\t\t{'' if c is None or ctr is None else str(c) + ', ' + str(ctr)}")
        return "\n".join(lines)

    def _refresh_export_text(
        self, dnt_w: Optional[int] = None, c: Optional[int] = None, ctr: Optional[int] = None
    ) -> None:
        self.export_cache = self._build_export_tsv(dnt_w, c, ctr)

    def copy_export_text(self) -> None:
        text = self.export_cache.strip()
        if not text:
            self._refresh_export_text()
            text = self.export_cache.strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        messagebox.showinfo("完成", "完整表格数据已复制，可直接粘贴到 Excel。")


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    for _ in range(3):
        pwd = simpledialog.askstring("密码验证", "请输入启动密码：", show="*", parent=root)
        if pwd is None:
            root.destroy()
            return
        if pwd == APP_PASSWORD:
            break
        messagebox.showerror("密码错误", "密码不正确，请重试。", parent=root)
    else:
        messagebox.showerror("已锁定", "密码错误次数过多，程序将退出。", parent=root)
        root.destroy()
        return

    root.deiconify()
    DnTApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
