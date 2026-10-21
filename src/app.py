import os
import sys
import json
import uuid
import tempfile
import threading
import webbrowser
from datetime import datetime

# Garante verificação de dependências antes de importar customtkinter, pillow e requests
if __name__ == "__main__":
    try:
        from check_dependencies import check_missing_packages, run_dependency_gui
        if check_missing_packages():
            if not run_dependency_gui():
                sys.exit(0)
    except Exception as _e:
        print(f"Aviso de verificação: {_e}")

from tkinter import filedialog, messagebox
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageGrab

from devops_api import AzureDevOpsClient, plain_text_to_html

# Set CustomTkinter appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

APP_VERSION = "1.3.0"
GITHUB_REPO = "M4teushds227/Cr_DevOps"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
HISTORY_FILE = os.path.join(APP_DIR, "history.json")
TEMP_ATTACH_DIR = os.path.join(tempfile.gettempdir(), "devops_demandas_attachments")
os.makedirs(TEMP_ATTACH_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "organization": "onebelezabemstar",
    "project": "One_FrontEnd",
    "projects_list": [
        "OneApp_V2",
        "One_FrontEnd",
        "OneCentralDeControle_BackEnd",
        "OneCentralDeControle_FrontEnd",
        "Conversor",
        "Repos",
        "Mobilidade",
        "OneSQL",
        "OneBeleza",
        "One Integrações",
        "Codinome Fenix"
    ],
    "work_item_type": "Spike",
    "work_item_types_list": ["Spike", "Bug", "User Story", "Task", "Product Backlog Item"],
    "default_tags": "Cr - Cadastro Rapido",
    "default_reported_by": "Cadastro Rapido",
    "default_urgency": "1",
    "default_area_path": "One_FrontEnd",
    "default_iteration_path": "One_FrontEnd",
    "modules_list": [
        "Outro",
        "Agenda",
        "Financeiro",
        "Clientes",
        "Colaboradores",
        "Estoque",
        "Produtos",
        "Serviços",
        "Relatórios",
        "Caixa",
        "Configurações",
        "Comissões",
        "Login / Acesso"
    ],
    "pat": "",
    "include_print_em_anexo": True
}


def load_json_file(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(default, dict):
                    merged = default.copy()
                    merged.update(data)
                    return merged
                return data
        except Exception:
            pass
    return default.copy() if isinstance(default, (dict, list)) else default


def save_json_file(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar {path}: {e}")


class DevOpsDemandasApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Azure DevOps - Cadastro Rápido & Dashboards")
        self.geometry("1180x800")
        self.minsize(980, 700)

        # Load state
        self.config_data = load_json_file(CONFIG_FILE, DEFAULT_CONFIG)
        self.history_data = load_json_file(HISTORY_FILE, [])
        self.attachments = []  # List of dicts: {"path": str, "name": str, "is_temp": bool}
        self._queries_map = {}  # Map display name -> query_id in Dashboard tab
        self._dash_loaded_once = False

        # Colors inspired by Azure DevOps Dark Theme
        self.bg_dark = "#1e1e1e"
        self.card_bg = "#252526"
        self.border_color = "#3b3a39"
        self.accent_orange = "#d86c1e"
        self.accent_blue = "#0078d4"
        self.text_muted = "#a19f9d"

        self.configure(fg_color=self.bg_dark)

        self._build_header()
        self._build_tabs()
        self._bind_shortcuts()

    # -------------------------------------------------------------------------
    # HEADER
    # -------------------------------------------------------------------------
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#181818", corner_radius=0, height=56)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        stripe = ctk.CTkFrame(header, fg_color=self.accent_orange, width=5, corner_radius=0)
        stripe.pack(side="left", fill="y")

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=8)

        lbl_title = ctk.CTkLabel(
            title_box,
            text="Azure DevOps  |  Cadastro Rápido & Dashboards",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#ffffff"
        )
        lbl_title.pack(side="left")

        # Quick lookup/edit by ID in the header
        lookup_frame = ctk.CTkFrame(header, fg_color="transparent")
        lookup_frame.pack(side="right", padx=(8, 16))

        self.status_badge = ctk.CTkButton(
            lookup_frame,
            text="",
            width=175,
            height=30,
            corner_radius=15,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self.tabview.set("⚙️ Configurações")
        )
        self.status_badge.pack(side="right", padx=(12, 0))
        self._update_header_badge()

        self.btn_open_id = ctk.CTkButton(
            lookup_frame,
            text="✏️ Editar #ID",
            width=95,
            height=28,
            fg_color="#323130",
            hover_color="#484644",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._open_id_from_header
        )
        self.btn_open_id.pack(side="right", padx=(4, 0))

        self.ent_quick_id = ctk.CTkEntry(
            lookup_frame,
            placeholder_text="Nº Card (ex: 9965)",
            width=130,
            height=28,
            font=ctk.CTkFont(size=12)
        )
        self.ent_quick_id.pack(side="right")
        self.ent_quick_id.bind("<Return>", lambda e: self._open_id_from_header())

    def _open_id_from_header(self):
        raw_id = self.ent_quick_id.get().strip().lstrip("#")
        if not raw_id.isdigit():
            messagebox.showwarning("ID Inválido", "Digite o número da demanda (ex: 9965) para abrir e editar.")
            return
        project = self.cmb_project.get().strip() or self.config_data.get("project", "One_FrontEnd")
        self.open_edit_work_item_modal(int(raw_id), project=project)

    def _update_header_badge(self):
        org = self.config_data.get("organization", "")
        has_pat = bool(self.config_data.get("pat", "").strip())
        if has_pat and org:
            self.status_badge.configure(
                text=f"● {org} (Ativo)",
                fg_color="#1f4e2c",
                hover_color="#286438",
                text_color="#89e09d"
            )
        else:
            self.status_badge.configure(
                text="⚠ Configurar Token PAT",
                fg_color="#5c2d16",
                hover_color="#75391c",
                text_color="#ffaa73"
            )

    # -------------------------------------------------------------------------
    # TABS
    # -------------------------------------------------------------------------
    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=self.bg_dark,
            segmented_button_fg_color="#252526",
            segmented_button_selected_color=self.accent_blue,
            segmented_button_selected_hover_color="#106ebe",
            segmented_button_unselected_color="#252526",
            segmented_button_unselected_hover_color="#323130",
            command=self._on_tab_changed
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(6, 12))

        self.tab_new = self.tabview.add("➕ Nova Demanda")
        self.tab_dash = self.tabview.add("📊 Dashboards")
        self.tab_history = self.tabview.add("🕒 Histórico")
        self.tab_settings = self.tabview.add("⚙️ Configurações")

        self._build_new_demand_tab()
        self._build_dashboard_tab()
        self._build_history_tab()
        self._build_settings_tab()

        if not self.config_data.get("pat", "").strip():
            self.lbl_feedback.configure(
                text="💡 Dica: Acesse a aba '⚙️ Configurações' para informar seu PAT Token do Azure DevOps antes do primeiro envio.",
                text_color="#ffaa73"
            )

        # Checagem automática de atualizações no GitHub
        self.after(3000, lambda: self.check_for_updates(manual=False))

    def _on_tab_changed(self):
        current = self.tabview.get()
        if current == "📊 Dashboards" and not self._dash_loaded_once:
            if self.config_data.get("pat", "").strip():
                self._dash_loaded_once = True
                self.refresh_dashboard()

    # -------------------------------------------------------------------------
    # TAB 1: NOVA DEMANDA
    # -------------------------------------------------------------------------
    def _build_new_demand_tab(self):
        self.tab_new.grid_columnconfigure(0, weight=3)
        self.tab_new.grid_columnconfigure(1, weight=2)
        self.tab_new.grid_rowconfigure(1, weight=1)

        top_card = ctk.CTkFrame(
            self.tab_new,
            fg_color=self.card_bg,
            corner_radius=8,
            border_width=1,
            border_color=self.border_color
        )
        top_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(2, 8))
        top_card.grid_columnconfigure(2, weight=1)

        top_stripe = ctk.CTkFrame(top_card, fg_color=self.accent_orange, width=6, corner_radius=2)
        top_stripe.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10), pady=2)

        meta_row = ctk.CTkFrame(top_card, fg_color="transparent")
        meta_row.grid(row=0, column=1, columnspan=2, sticky="ew", padx=8, pady=(8, 4))

        ctk.CTkLabel(meta_row, text="Tipo:", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.text_muted).pack(side="left", padx=(0, 4))
        self.cmb_type = ctk.CTkComboBox(
            meta_row,
            values=self.config_data.get("work_item_types_list", ["Spike", "Bug", "User Story", "Task"]),
            width=130,
            height=28
        )
        self.cmb_type.set(self.config_data.get("work_item_type", "Spike"))
        self.cmb_type.pack(side="left", padx=(0, 14))

        # Hidden project selector (defaults to One_FrontEnd)
        self.cmb_project = ctk.CTkComboBox(
            meta_row,
            values=self.config_data.get("projects_list", ["One_FrontEnd"]),
            width=170,
            height=28,
            command=self._on_project_changed
        )
        self.cmb_project.set(self.config_data.get("project", "One_FrontEnd"))

        ctk.CTkLabel(meta_row, text="Tag:", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.text_muted).pack(side="left", padx=(0, 4))
        self.ent_tags = ctk.CTkEntry(
            meta_row,
            placeholder_text="DemandasSistemaSuporte",
            width=210,
            height=28
        )
        self.ent_tags.insert(0, self.config_data.get("default_tags", "Cr - Cadastro Rapido"))
        self.ent_tags.pack(side="left", padx=(0, 8))

        # Quick tag presets dropdown
        tag_presets = [
            "Cr - Cadastro Rapido",
            "DemandasSistemaSuporte",
            "DE - Demandas Erros",
            "AES - Acompanhamento de Erros sem Solução",
            "PLib - Pendentes de Liberação",
            "RR - Renovação relatórios",
            "TVali - Testes de Validação",
            "Dm - Demandas Melhorias",
            "PClis - Pedidos de Clientes",
            "Sug - Sugestão",
            "ErrosSistemaSuporte",
            "DemandasMobilidadeSuporte",
            "ErrosMobilidadeSuporte",
            "SugestãoMelhoriaSuporte"
        ]
        self.cmb_tag_preset = ctk.CTkOptionMenu(
            meta_row,
            values=tag_presets,
            width=145,
            height=28,
            fg_color="#323130",
            button_color="#484644",
            button_hover_color="#605e5c",
            font=ctk.CTkFont(size=11),
            command=self._on_select_tag_preset
        )
        self.cmb_tag_preset.set("🏷️ Tags Rápidas")
        self.cmb_tag_preset.pack(side="left", padx=(0, 8))

        self.var_auto_title = ctk.BooleanVar(value=True)
        self.chk_auto_title = ctk.CTkCheckBox(
            meta_row,
            text="Gerar Título do Erro",
            variable=self.var_auto_title,
            font=ctk.CTkFont(size=12),
            checkbox_width=18,
            checkbox_height=18
        )
        self.chk_auto_title.pack(side="right", padx=6)

        title_row = ctk.CTkFrame(top_card, fg_color="transparent")
        title_row.grid(row=1, column=1, columnspan=2, sticky="ew", padx=8, pady=(2, 10))
        title_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            title_row,
            text="Título:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.ent_title = ctk.CTkEntry(
            title_row,
            placeholder_text="Titulo da demanda...",
            height=36,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.ent_title.grid(row=0, column=1, sticky="ew")
        self.ent_title.bind("<KeyRelease>", self._on_title_manual_edit)

        # --- LEFT COLUMN: DESCRIPTION ---
        desc_card = ctk.CTkFrame(
            self.tab_new,
            fg_color=self.card_bg,
            corner_radius=8,
            border_width=1,
            border_color=self.border_color
        )
        desc_card.grid(row=1, column=0, sticky="nsew", padx=(4, 6), pady=4)
        desc_card.grid_columnconfigure(0, weight=1)
        desc_card.grid_rowconfigure(3, weight=1)

        lbl_desc_header = ctk.CTkLabel(
            desc_card,
            text="Description (Padrão Demandas Suporte)",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        lbl_desc_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))

        cm_frame = ctk.CTkFrame(desc_card, fg_color="transparent")
        cm_frame.grid(row=1, column=0, sticky="ew", padx=14, pady=4)
        cm_frame.grid_columnconfigure(0, weight=3)
        cm_frame.grid_columnconfigure(1, weight=2)

        cli_box = ctk.CTkFrame(cm_frame, fg_color="transparent")
        cli_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(cli_box, text="Cliente *", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        self.ent_cliente = ctk.CTkEntry(
            cli_box,
            placeholder_text="Ex: Unique Beauty",
            height=32
        )
        self.ent_cliente.pack(fill="x", pady=(2, 0))

        mod_box = ctk.CTkFrame(cm_frame, fg_color="transparent")
        mod_box.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(mod_box, text="Módulo *", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        self.cmb_modulo = ctk.CTkComboBox(
            mod_box,
            values=self.config_data.get("modules_list", DEFAULT_CONFIG["modules_list"]),
            height=32
        )
        self.cmb_modulo.set("Agenda")
        self.cmb_modulo.pack(fill="x", pady=(2, 0))

        lbl_erro = ctk.CTkLabel(
            desc_card,
            text="Erro / Descrição detalhada *",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        lbl_erro.grid(row=2, column=0, sticky="ew", padx=14, pady=(8, 2))

        self.txt_erro = ctk.CTkTextbox(
            desc_card,
            font=ctk.CTkFont(size=13),
            fg_color="#1b1a19",
            border_width=1,
            border_color="#484644",
            wrap="word"
        )
        self.txt_erro.grid(row=3, column=0, sticky="nsew", padx=14, pady=(0, 8))
        self.txt_erro.bind("<KeyRelease>", self._on_erro_key_release)

        desc_footer = ctk.CTkFrame(desc_card, fg_color="transparent")
        desc_footer.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 10))

        self.var_print_anexo = ctk.BooleanVar(value=self.config_data.get("include_print_em_anexo", True))
        self.chk_print_anexo = ctk.CTkCheckBox(
            desc_footer,
            text='Incluir linha "print em anexo" na descrição',
            variable=self.var_print_anexo,
            font=ctk.CTkFont(size=12),
            checkbox_width=18,
            checkbox_height=18
        )
        self.chk_print_anexo.pack(side="left")

        btn_preview = ctk.CTkButton(
            desc_footer,
            text="👁 Ver Prévia do Texto",
            width=140,
            height=26,
            fg_color="#323130",
            hover_color="#484644",
            font=ctk.CTkFont(size=12),
            command=self._show_description_preview
        )
        btn_preview.pack(side="right")

        # --- RIGHT COLUMN: DETAILS & ATTACHMENTS ---
        right_col = ctk.CTkFrame(self.tab_new, fg_color="transparent")
        right_col.grid(row=1, column=1, sticky="nsew", padx=(6, 4), pady=4)
        right_col.grid_columnconfigure(0, weight=1)
        right_col.grid_rowconfigure(1, weight=1)

        details_card = ctk.CTkFrame(
            right_col,
            fg_color=self.card_bg,
            corner_radius=8,
            border_width=1,
            border_color=self.border_color
        )
        details_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        details_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            details_card,
            text="Details",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 6))

        na_frame = ctk.CTkFrame(details_card, fg_color="transparent")
        na_frame.grid(row=1, column=0, sticky="ew", padx=14, pady=3)
        na_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(na_frame, text="Observado em (Data/Hora)", font=ctk.CTkFont(size=12), text_color=self.text_muted).grid(row=0, column=0, sticky="w")
        self.ent_noticed_at = ctk.CTkEntry(na_frame, height=30)
        self.ent_noticed_at.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(2, 0))
        self._set_noticed_at_now()

        btn_now = ctk.CTkButton(
            na_frame,
            text="Agora",
            width=60,
            height=30,
            fg_color="#323130",
            hover_color="#484644",
            command=self._set_noticed_at_now
        )
        btn_now.grid(row=1, column=1, pady=(2, 0))

        ru_frame = ctk.CTkFrame(details_card, fg_color="transparent")
        ru_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=4)
        ru_frame.grid_columnconfigure(0, weight=3)
        ru_frame.grid_columnconfigure(1, weight=1)

        rep_box = ctk.CTkFrame(ru_frame, fg_color="transparent")
        rep_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(rep_box, text="Reportado por", font=ctk.CTkFont(size=12), text_color=self.text_muted).pack(anchor="w")
        self.ent_reported_by = ctk.CTkEntry(rep_box, height=30)
        self.ent_reported_by.insert(0, self.config_data.get("default_reported_by", ""))
        self.ent_reported_by.pack(fill="x", pady=(2, 0))

        urg_box = ctk.CTkFrame(ru_frame, fg_color="transparent")
        urg_box.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(urg_box, text="Urgência", font=ctk.CTkFont(size=12), text_color=self.text_muted).pack(anchor="w")
        self.cmb_urgency = ctk.CTkComboBox(
            urg_box,
            values=["1", "2", "3", "4", "5"],
            height=30
        )
        self.cmb_urgency.set(str(self.config_data.get("default_urgency", "4")))
        self.cmb_urgency.pack(fill="x", pady=(2, 0))

        ai_frame = ctk.CTkFrame(details_card, fg_color="transparent")
        ai_frame.grid(row=3, column=0, sticky="ew", padx=14, pady=(4, 12))
        ai_frame.grid_columnconfigure(0, weight=1)
        ai_frame.grid_columnconfigure(1, weight=1)

        area_box = ctk.CTkFrame(ai_frame, fg_color="transparent")
        area_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(area_box, text="Area", font=ctk.CTkFont(size=12), text_color=self.text_muted).pack(anchor="w")
        self.ent_area = ctk.CTkEntry(area_box, height=28)
        self.ent_area.insert(0, self.config_data.get("default_area_path", "One_FrontEnd"))
        self.ent_area.pack(fill="x", pady=(2, 0))

        iter_box = ctk.CTkFrame(ai_frame, fg_color="transparent")
        iter_box.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(iter_box, text="Iteration", font=ctk.CTkFont(size=12), text_color=self.text_muted).pack(anchor="w")
        self.ent_iteration = ctk.CTkEntry(iter_box, height=28)
        self.ent_iteration.insert(0, self.config_data.get("default_iteration_path", "One_FrontEnd"))
        self.ent_iteration.pack(fill="x", pady=(2, 0))

        att_card = ctk.CTkFrame(
            right_col,
            fg_color=self.card_bg,
            corner_radius=8,
            border_width=1,
            border_color=self.border_color
        )
        att_card.grid(row=1, column=0, sticky="nsew")
        att_card.grid_columnconfigure(0, weight=1)
        att_card.grid_rowconfigure(2, weight=1)

        att_header = ctk.CTkFrame(att_card, fg_color="transparent")
        att_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))

        self.lbl_att_count = ctk.CTkLabel(
            att_header,
            text="📎 Anexos / Prints (0)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_att_count.pack(side="left")

        btn_clear_att = ctk.CTkButton(
            att_header,
            text="Limpar Todos",
            width=80,
            height=24,
            fg_color="transparent",
            hover_color="#3b3a39",
            text_color="#f1707b",
            font=ctk.CTkFont(size=11),
            command=self._clear_attachments
        )
        btn_clear_att.pack(side="right")

        att_btns = ctk.CTkFrame(att_card, fg_color="transparent")
        att_btns.grid(row=1, column=0, sticky="ew", padx=14, pady=4)
        att_btns.grid_columnconfigure(0, weight=1)
        att_btns.grid_columnconfigure(1, weight=1)

        self.btn_paste_clip = ctk.CTkButton(
            att_btns,
            text="📋 Colar Print (Ctrl+V)",
            height=32,
            fg_color="#2d5a88",
            hover_color="#3972ab",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.paste_from_clipboard
        )
        self.btn_paste_clip.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.btn_add_file = ctk.CTkButton(
            att_btns,
            text="📁 Selecionar Arquivo...",
            height=32,
            fg_color="#323130",
            hover_color="#484644",
            font=ctk.CTkFont(size=12),
            command=self.select_attachment_files
        )
        self.btn_add_file.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.att_list_frame = ctk.CTkScrollableFrame(
            att_card,
            fg_color="#1b1a19",
            corner_radius=6
        )
        self.att_list_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=(4, 10))
        self.att_list_frame.grid_columnconfigure(0, weight=1)
        self._render_attachments_list()

        # --- BOTTOM ACTION BAR ---
        bottom_bar = ctk.CTkFrame(self.tab_new, fg_color="transparent")
        bottom_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=(6, 2))
        bottom_bar.grid_columnconfigure(0, weight=1)

        left_bottom = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        left_bottom.grid(row=0, column=0, sticky="ew", padx=6)
        left_bottom.grid_columnconfigure(1, weight=1)

        self.lbl_feedback = ctk.CTkLabel(
            left_bottom,
            text="Atalhos: [Ctrl+V] Colar print da área de transferência  |  [Ctrl+Enter] Cadastrar Demanda",
            font=ctk.CTkFont(size=12),
            text_color=self.text_muted,
            anchor="w"
        )
        self.lbl_feedback.grid(row=0, column=0, columnspan=3, sticky="w")

        self.last_link_frame = ctk.CTkFrame(left_bottom, fg_color="transparent")
        self.last_link_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        self.last_link_frame.grid_columnconfigure(1, weight=1)
        self.last_link_frame.grid_remove()

        ctk.CTkLabel(
            self.last_link_frame,
            text="🔗 Link:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#89e09d"
        ).grid(row=0, column=0, padx=(0, 6))

        self.ent_last_link = ctk.CTkEntry(
            self.last_link_frame,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="#1b1a19",
            border_color="#286438"
        )
        self.ent_last_link.grid(row=0, column=1, sticky="ew", padx=(0, 6))

        self.btn_copy_last_link = ctk.CTkButton(
            self.last_link_frame,
            text="📋 Copiar Link",
            width=110,
            height=28,
            fg_color="#1f4e2c",
            hover_color="#286438",
            text_color="#89e09d",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self.copy_to_clipboard(self.ent_last_link.get(), self.btn_copy_last_link)
        )
        self.btn_copy_last_link.grid(row=0, column=2, padx=(0, 8))

        btn_box = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        self.btn_clear_form = ctk.CTkButton(
            btn_box,
            text="🧹 Limpar Campos",
            width=130,
            height=40,
            fg_color="#323130",
            hover_color="#484644",
            font=ctk.CTkFont(size=13),
            command=self.clear_form
        )
        self.btn_clear_form.pack(side="left", padx=(0, 10))

        self.btn_submit = ctk.CTkButton(
            btn_box,
            text="🚀 Cadastrar no DevOps (Ctrl+Enter)",
            width=260,
            height=40,
            fg_color=self.accent_blue,
            hover_color="#106ebe",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.submit_demand
        )
        self.btn_submit.pack(side="left")

    def _on_select_tag_preset(self, selected_tag: str):
        if selected_tag and not selected_tag.startswith("🏷️"):
            self.ent_tags.delete(0, "end")
            self.ent_tags.insert(0, selected_tag)
            self.cmb_tag_preset.set("🏷️ Tags Rápidas")

    # -------------------------------------------------------------------------
    # TAB 2: DASHBOARDS (Overview 6 Widgets + Any Saved Query)
    # -------------------------------------------------------------------------
    def _build_dashboard_tab(self):
        self.tab_dash.grid_columnconfigure(0, weight=1)
        self.tab_dash.grid_rowconfigure(1, weight=1)

        # Toolbar
        toolbar = ctk.CTkFrame(
            self.tab_dash,
            fg_color=self.card_bg,
            corner_radius=8,
            border_width=1,
            border_color=self.border_color
        )
        toolbar.grid(row=0, column=0, sticky="ew", padx=4, pady=(2, 8))

        self.lbl_dash_header_title = ctk.CTkLabel(
            toolbar,
            text="📋 Equipe de Desenvolvimento - Overview",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#ffffff"
        )
        self.lbl_dash_header_title.pack(side="left", padx=(14, 16), pady=8)

        # Hidden project selector in dashboard toolbar (defaults to One_FrontEnd)
        self.cmb_dash_project = ctk.CTkComboBox(
            toolbar,
            values=self.config_data.get("projects_list", ["One_FrontEnd"]),
            width=155,
            height=30,
            command=lambda _: self._on_dash_project_changed()
        )
        self.cmb_dash_project.set(self.config_data.get("project", "One_FrontEnd"))

        ctk.CTkLabel(
            toolbar,
            text="Dashboard:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.text_muted
        ).pack(side="left", padx=(0, 4))

        default_dash_options = [
            "📋 Equipe de Desenvolvimento - Overview",
            "🎧 Dashboard - Equipe de Suporte",
            "⚙️ Dashboard - Acompanhamento Geral & Sprint",
            "📊 Todos os Blocos (Visão Completa)"
        ]
        self.cmb_dash_mode = ctk.CTkComboBox(
            toolbar,
            values=default_dash_options,
            width=310,
            height=30,
            command=lambda _: self.refresh_dashboard()
        )
        self.cmb_dash_mode.set("📋 Equipe de Desenvolvimento - Overview")
        self.cmb_dash_mode.pack(side="left", padx=(0, 12))

        self.btn_refresh_dash = ctk.CTkButton(
            toolbar,
            text="🔄 Atualizar",
            width=115,
            height=30,
            fg_color=self.accent_blue,
            hover_color="#106ebe",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.refresh_dashboard
        )
        self.btn_refresh_dash.pack(side="right", padx=14, pady=8)

        self.lbl_dash_status = ctk.CTkLabel(
            toolbar,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.text_muted
        )
        self.lbl_dash_status.pack(side="right", padx=8)

        # Main Dashboard Container
        self.dash_container = ctk.CTkScrollableFrame(
            self.tab_dash,
            fg_color="transparent",
            corner_radius=0
        )
        self.dash_container.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        for c in range(3):
            self.dash_container.grid_columnconfigure(c, weight=1, uniform="dash_col")

    def _on_dash_project_changed(self):
        self._queries_map.clear()
        default_dash_options = [
            "📋 Equipe de Desenvolvimento - Overview",
            "🎧 Dashboard - Equipe de Suporte",
            "⚙️ Dashboard - Acompanhamento Geral & Sprint",
            "📊 Todos os Blocos (Visão Completa)"
        ]
        self.cmb_dash_mode.configure(values=default_dash_options)
        self.cmb_dash_mode.set("📋 Equipe de Desenvolvimento - Overview")
        self.refresh_dashboard()

    def refresh_dashboard(self):
        pat = self.config_data.get("pat", "").strip()
        org = self.config_data.get("organization", "").strip()
        project = self.cmb_dash_project.get().strip() or self.config_data.get("project", "")
        mode = self.cmb_dash_mode.get().strip()

        if not pat:
            messagebox.showwarning("Token PAT Necessário", "Configure seu PAT Token na aba '⚙️ Configurações' primeiro.")
            self.tabview.set("⚙️ Configurações")
            return

        self.lbl_dash_header_title.configure(text=mode)
        self.btn_refresh_dash.configure(state="disabled", text="⏳ Carregando...")
        self.lbl_dash_status.configure(text=f"Carregando {mode}...", text_color="#ffaa73")

        def worker():
            client = AzureDevOpsClient(org, pat)
            try:
                queries_list = client.get_project_queries(project)
                if mode not in self._queries_map:
                    panels = client.get_overview_dashboard_data(project, dashboard_name=mode)
                    is_overview = True
                else:
                    q_id = self._queries_map[mode]
                    items = client.run_query_by_id(project, q_id)
                    panels = [{
                        "key": "QUERY",
                        "title": mode,
                        "tag": "",
                        "query_id": q_id,
                        "query_url": f"{client.base_url}/{project}/_queries/query/{q_id}/",
                        "items": items
                    }]
                    is_overview = False

                def on_done():
                    self.btn_refresh_dash.configure(state="normal", text="🔄 Atualizar")
                    now_str = datetime.now().strftime("%H:%M:%S")
                    self.lbl_dash_status.configure(
                        text=f"{len(panels)} blocos ({now_str}) — Clique no card ou ✏️ para editar",
                        text_color="#89e09d"
                    )

                    combo_vals = [
                        "📋 Equipe de Desenvolvimento - Overview",
                        "🎧 Dashboard - Equipe de Suporte",
                        "⚙️ Dashboard - Acompanhamento Geral & Sprint",
                        "📊 Todos os Blocos (Visão Completa)"
                    ]
                    self._queries_map.clear()
                    for q in queries_list:
                        label = f"🔎 Query: {q['name']}"
                        self._queries_map[label] = q["id"]
                        combo_vals.append(label)
                    self.cmb_dash_mode.configure(values=combo_vals)

                    if is_overview:
                        self._render_overview_grid(panels, project)
                    else:
                        self._render_single_query_panel(panels[0], project)

                self.after(0, on_done)

            except Exception as e:
                err_msg = str(e)

                def on_err():
                    self.btn_refresh_dash.configure(state="normal", text="🔄 Atualizar")
                    self.lbl_dash_status.configure(text=f"❌ Erro: {err_msg[:60]}", text_color="#f1707b")

                self.after(0, on_err)

        threading.Thread(target=worker, daemon=True).start()

    def _get_state_color_and_dot(self, state: str):
        st = (state or "").strip().lower()
        if st in ("in progress", "active", "committed", "em progresso"):
            return "#0078d4", "●"
        elif st in ("done", "closed", "completed", "resolved"):
            return "#339947", "●"
        elif st in ("validation", "testing"):
            return "#d86c1e", "●"
        else:
            return "#a19f9d", "●"

    def _get_type_icon_and_color(self, wi_type: str):
        wt = (wi_type or "").strip().lower()
        if wt == "spike":
            return "✦", "#d86c1e"
        elif wt == "bug":
            return "🐞", "#cc293d"
        elif wt == "feature":
            return "🏆", "#773b93"
        elif wt in ("task", "product backlog item", "user story"):
            return "📋", "#f2cb1d"
        else:
            return "✦", "#d86c1e"

    def _render_overview_grid(self, panels: list, project: str):
        for w in self.dash_container.winfo_children():
            w.destroy()

        for idx, panel in enumerate(panels):
            row = idx // 3
            col = idx % 3

            card = ctk.CTkFrame(
                self.dash_container,
                fg_color="#181818",
                corner_radius=6,
                border_width=1,
                border_color="#323130",
                height=310
            )
            card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(2, weight=1)

            items = panel.get("items", [])
            count = len(items)
            title_txt = f"{panel['title']} ({count})" if count > 0 else panel["title"]

            # Card Header
            hdr = ctk.CTkFrame(card, fg_color="transparent")
            hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
            ctk.CTkLabel(
                hdr,
                text=title_txt,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#e1dfdd",
                anchor="w"
            ).pack(side="left")

            # Column headers (Title | Assigned To | State)
            if count > 0:
                col_hdr = ctk.CTkFrame(card, fg_color="transparent")
                col_hdr.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 2))
                col_hdr.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(col_hdr, text="Title", font=ctk.CTkFont(size=11), text_color=self.text_muted, anchor="w").grid(row=0, column=0, sticky="w")
                ctk.CTkLabel(col_hdr, text="Assigned To", font=ctk.CTkFont(size=11), text_color=self.text_muted, width=90, anchor="w").grid(row=0, column=1, sticky="w", padx=4)
                ctk.CTkLabel(col_hdr, text="State", font=ctk.CTkFont(size=11), text_color=self.text_muted, width=85, anchor="w").grid(row=0, column=2, sticky="w")

                list_scroll = ctk.CTkScrollableFrame(card, fg_color="#181818", corner_radius=0, height=210)
                list_scroll.grid(row=2, column=0, sticky="nsew", padx=6, pady=2)
                list_scroll.grid_columnconfigure(0, weight=1)

                for item in items:
                    self._create_dashboard_item_row(list_scroll, item, project, compact=True)
            else:
                empty_box = ctk.CTkFrame(card, fg_color="transparent", height=225)
                empty_box.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=12, pady=12)
                empty_box.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(
                    empty_box,
                    text="Last time you checked, there were no results.",
                    font=ctk.CTkFont(size=12),
                    text_color=self.text_muted
                ).pack(pady=(35, 10))
                badge_zero = ctk.CTkLabel(
                    empty_box,
                    text=" 0 ",
                    font=ctk.CTkFont(size=28, weight="bold"),
                    fg_color="#0078d4",
                    text_color="#ffffff",
                    corner_radius=6
                )
                badge_zero.pack(pady=6)

            # Footer: View query
            ftr = ctk.CTkFrame(card, fg_color="transparent")
            ftr.grid(row=3, column=0, sticky="ew", padx=10, pady=(2, 6))
            q_url = panel.get("query_url", "")
            btn_vq = ctk.CTkButton(
                ftr,
                text="View query",
                width=75,
                height=20,
                fg_color="transparent",
                hover_color="#252526",
                text_color="#4ba3ff",
                font=ctk.CTkFont(size=11, underline=True),
                command=lambda u=q_url: webbrowser.open(u)
            )
            btn_vq.pack(side="right")

    def _render_single_query_panel(self, panel: dict, project: str):
        for w in self.dash_container.winfo_children():
            w.destroy()

        card = ctk.CTkFrame(
            self.dash_container,
            fg_color="#181818",
            corner_radius=6,
            border_width=1,
            border_color="#323130"
        )
        card.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=6, pady=6)
        card.grid_columnconfigure(0, weight=1)

        items = panel.get("items", [])
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            hdr,
            text=f"{panel['title']}  ({len(items)} itens)",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#ffffff"
        ).pack(side="left")

        if not items:
            ctk.CTkLabel(
                card,
                text="Nenhum item retornado para esta query.",
                font=ctk.CTkFont(size=13),
                text_color=self.text_muted
            ).pack(pady=40)
            return

        for item in items:
            self._create_dashboard_item_row(card, item, project, compact=False)

    def _create_dashboard_item_row(self, parent, item: dict, project: str, compact: bool = True):
        row = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=4)
        row.pack(fill="x", padx=2, pady=2)
        row.grid_columnconfigure(1, weight=1)

        wi_id = item["id"]
        wi_type = item.get("type", "Spike")
        title = item.get("title", "")
        assigned = item.get("assigned_to", "")
        state = item.get("state", "New")
        url = item.get("url", "")

        icon_char, icon_color = self._get_type_icon_and_color(wi_type)
        st_color, st_dot = self._get_state_color_and_dot(state)

        # Icon
        lbl_icon = ctk.CTkLabel(
            row,
            text=icon_char,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=icon_color,
            width=18
        )
        lbl_icon.grid(row=0, column=0, padx=(2, 4), sticky="w")

        # Title button (clicking opens Edit Modal!)
        max_title_len = 33 if compact else 75
        disp_title = title if len(title) <= max_title_len else title[:max_title_len - 1] + "…"
        if not compact:
            disp_title = f"#{wi_id}  {disp_title}"

        btn_title = ctk.CTkButton(
            row,
            text=disp_title,
            fg_color="transparent",
            hover_color="#292827",
            text_color="#e1dfdd",
            anchor="w",
            height=24,
            font=ctk.CTkFont(size=12),
            command=lambda i=wi_id, p=project: self.open_edit_work_item_modal(i, p)
        )
        btn_title.grid(row=0, column=1, sticky="ew")

        # Assigned To
        max_ass_len = 12 if compact else 24
        disp_ass = assigned if len(assigned) <= max_ass_len else assigned[:max_ass_len - 1] + "…"
        ctk.CTkLabel(
            row,
            text=disp_ass,
            font=ctk.CTkFont(size=11),
            text_color="#c8c6c4",
            width=82 if compact else 150,
            anchor="w"
        ).grid(row=0, column=2, padx=4, sticky="w")

        # State dot + text
        max_st_len = 9 if compact else 16
        disp_st = state if len(state) <= max_st_len else state[:max_st_len - 1] + "…"
        st_frame = ctk.CTkFrame(row, fg_color="transparent", width=72 if compact else 110)
        st_frame.grid(row=0, column=3, padx=(2, 2), sticky="w")
        ctk.CTkLabel(st_frame, text=st_dot, font=ctk.CTkFont(size=11), text_color=st_color).pack(side="left", padx=(0, 3))
        ctk.CTkLabel(st_frame, text=disp_st, font=ctk.CTkFont(size=11), text_color="#e1dfdd").pack(side="left")

        # Quick Edit button
        btn_edit = ctk.CTkButton(
            row,
            text="✏️",
            width=26,
            height=22,
            fg_color="#252526",
            hover_color="#0078d4",
            font=ctk.CTkFont(size=11),
            command=lambda i=wi_id, p=project: self.open_edit_work_item_modal(i, p)
        )
        btn_edit.grid(row=0, column=4, padx=(2, 2))

        if not compact and url:
            btn_cp = ctk.CTkButton(
                row,
                text="📋 Link",
                width=65,
                height=22,
                fg_color="#323130",
                hover_color="#484644",
                font=ctk.CTkFont(size=11),
                command=lambda u=url: self.copy_to_clipboard(u)
            )
            btn_cp.grid(row=0, column=5, padx=2)

    # -------------------------------------------------------------------------
    # IMAGE VIEWER MODAL (Open Screen with Full Print)
    # -------------------------------------------------------------------------
    def open_image_viewer_modal(self, source_path_or_url: str, title: str = "Visualizar Print", is_remote: bool = False):
        """Open a dedicated window displaying the print / screenshot."""
        viewer = ctk.CTkToplevel(self)
        viewer.title(f"Visualizador de Print - {title}")
        viewer.geometry("920x680")
        viewer.minsize(640, 480)
        viewer.configure(fg_color=self.bg_dark)
        viewer.transient(self)

        self.update_idletasks()
        vx = self.winfo_x() + (self.winfo_width() // 2) - 460
        vy = self.winfo_y() + (self.winfo_height() // 2) - 340
        viewer.geometry(f"+{max(0, vx)}+{max(0, vy)}")

        viewer.grid_columnconfigure(0, weight=1)
        viewer.grid_rowconfigure(1, weight=1)

        # Top Bar
        top_bar = ctk.CTkFrame(viewer, fg_color=self.card_bg, corner_radius=6)
        top_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        top_bar.grid_columnconfigure(0, weight=1)

        lbl_info = ctk.CTkLabel(
            top_bar,
            text=f"🖼️ {title}",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        lbl_info.grid(row=0, column=0, sticky="w", padx=12, pady=8)

        btn_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e", padx=10, pady=6)

        resolved_path = [None]
        if not is_remote and os.path.exists(source_path_or_url):
            resolved_path[0] = source_path_or_url

        def open_in_windows():
            if resolved_path[0] and os.path.exists(resolved_path[0]):
                os.startfile(resolved_path[0])
            else:
                messagebox.showinfo("Aviso", "Aguarde o carregamento da imagem...", parent=viewer)

        def copy_img_to_clipboard():
            if resolved_path[0] and os.path.exists(resolved_path[0]):
                try:
                    import subprocess
                    ps_cmd = f"Set-Clipboard -Path '{resolved_path[0]}'"
                    subprocess.run(["powershell", "-Command", ps_cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    lbl_info.configure(text=f"📋 Print copiado para a área de transferência!", text_color="#89e09d")
                except Exception as ex:
                    messagebox.showerror("Erro ao copiar", str(ex), parent=viewer)

        btn_win = ctk.CTkButton(
            btn_box,
            text="🔍 Abrir no Windows",
            height=28,
            fg_color="#323130",
            hover_color="#484644",
            font=ctk.CTkFont(size=11),
            command=open_in_windows
        )
        btn_win.pack(side="left", padx=4)

        btn_copy = ctk.CTkButton(
            btn_box,
            text="📋 Copiar",
            height=28,
            fg_color="#323130",
            hover_color="#484644",
            font=ctk.CTkFont(size=11),
            command=copy_img_to_clipboard
        )
        btn_copy.pack(side="left", padx=4)

        btn_close = ctk.CTkButton(
            btn_box,
            text="✕ Fechar",
            height=28,
            width=70,
            fg_color="#5c2d16",
            hover_color="#80381b",
            font=ctk.CTkFont(size=11),
            command=viewer.destroy
        )
        btn_close.pack(side="left", padx=(4, 0))

        # Main Viewer Area
        img_container = ctk.CTkFrame(viewer, fg_color="#181818", corner_radius=8)
        img_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        img_container.grid_columnconfigure(0, weight=1)
        img_container.grid_rowconfigure(0, weight=1)

        lbl_display = ctk.CTkLabel(
            img_container,
            text="⏳ Carregando imagem...",
            font=ctk.CTkFont(size=13),
            text_color=self.text_muted
        )
        lbl_display.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        viewer._image_ref = None

        def display_local_image(local_path):
            resolved_path[0] = local_path
            try:
                ext = os.path.splitext(local_path)[1].lower()
                if ext not in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
                    lbl_display.configure(
                        text=f"📄 Arquivo: {os.path.basename(local_path)}\n\nEste formato não é uma imagem pré-visualizável.\nClique em 'Abrir no Windows' para abri-lo.",
                        image=None
                    )
                    return

                im = Image.open(local_path)
                orig_w, orig_h = im.size
                f_size = os.path.getsize(local_path) / 1024.0

                lbl_info.configure(
                    text=f"🖼️ {title}  •  {orig_w}x{orig_h} px  •  {f_size:.1f} KB",
                    text_color="white"
                )

                max_w = max(400, viewer.winfo_width() - 60)
                max_h = max(300, viewer.winfo_height() - 110)

                scale = min(max_w / orig_w, max_h / orig_h, 1.0)
                disp_w = int(orig_w * scale)
                disp_h = int(orig_h * scale)

                ctk_img = ctk.CTkImage(light_image=im, dark_image=im, size=(disp_w, disp_h))
                viewer._image_ref = ctk_img
                lbl_display.configure(text="", image=ctk_img)
            except Exception as e:
                lbl_display.configure(text=f"❌ Erro ao exibir imagem:\n{e}", image=None)

        if not is_remote:
            viewer.after(60, lambda: display_local_image(source_path_or_url))
        else:
            lbl_display.configure(text="⏳ Baixando print do Azure DevOps...")
            def download_worker():
                pat = self.config_data.get("pat", "").strip()
                org = self.config_data.get("organization", "").strip()
                try:
                    client = AzureDevOpsClient(org, pat)
                    local_f = client.download_attachment(source_path_or_url)
                    viewer.after(0, lambda: display_local_image(local_f))
                except Exception as err:
                    viewer.after(0, lambda: lbl_display.configure(
                        text=f"❌ Erro ao baixar print do Azure DevOps:\n{err}",
                        image=None
                    ))

            threading.Thread(target=download_worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # EDIT WORK ITEM MODAL (Edit Title, State, AssignedTo, Tags, Description, Comment, Attachments)
    # -------------------------------------------------------------------------
    def open_edit_work_item_modal(self, work_item_id: int, project: str = None):
        pat = self.config_data.get("pat", "").strip()
        org = self.config_data.get("organization", "").strip()
        if not project:
            project = self.config_data.get("project", "").strip()

        if not pat:
            messagebox.showwarning("Token PAT Necessário", "Configure seu PAT Token na aba '⚙️ Configurações' primeiro.")
            return

        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Editar Demanda #{work_item_id} - Azure DevOps")
        dlg.geometry("960x720")
        dlg.minsize(860, 620)
        dlg.configure(fg_color=self.bg_dark)
        dlg.transient(self)
        dlg.grab_set()

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 480
        y = self.winfo_y() + (self.winfo_height() // 2) - 360
        dlg.geometry(f"+{max(0, x)}+{max(0, y)}")

        dlg.grid_columnconfigure(0, weight=1)
        dlg.grid_rowconfigure(1, weight=1)

        # Header bar
        hdr = ctk.CTkFrame(dlg, fg_color=self.card_bg, corner_radius=8, border_width=1, border_color=self.border_color)
        hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        hdr.grid_columnconfigure(1, weight=1)

        stripe = ctk.CTkFrame(hdr, fg_color=self.accent_orange, width=6, corner_radius=2)
        stripe.grid(row=0, column=0, rowspan=2, sticky="ns", padx=(0, 10), pady=2)

        lbl_wi_badge = ctk.CTkLabel(
            hdr,
            text=f"⏳ Carregando Demanda #{work_item_id}...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.accent_orange,
            anchor="w"
        )
        lbl_wi_badge.grid(row=0, column=1, sticky="w", padx=6, pady=(8, 2))

        # Link copy & open in header
        hdr_btns = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_btns.grid(row=0, column=2, padx=10, pady=(8, 2), sticky="e")

        wi_url_var = tk.StringVar(value=f"https://dev.azure.com/{org}/{project}/_workitems/edit/{work_item_id}")

        btn_copy_link = ctk.CTkButton(
            hdr_btns,
            text="📋 Copiar Link",
            width=110,
            height=26,
            fg_color="#323130",
            hover_color="#484644",
            font=ctk.CTkFont(size=11)
        )
        btn_copy_link.configure(command=lambda: self.copy_to_clipboard(wi_url_var.get(), btn_copy_link))
        btn_copy_link.pack(side="left", padx=(0, 6))

        btn_open_web = ctk.CTkButton(
            hdr_btns,
            text="🌐 Abrir no DevOps",
            width=130,
            height=26,
            fg_color="#2d5a88",
            hover_color="#3972ab",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: webbrowser.open(wi_url_var.get())
        )
        btn_open_web.pack(side="left")

        ent_edit_title = ctk.CTkEntry(
            hdr,
            height=34,
            font=ctk.CTkFont(size=14, weight="bold"),
            placeholder_text="Título da demanda..."
        )
        ent_edit_title.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(6, 10), pady=(2, 10))

        # Body frame
        body = ctk.CTkFrame(dlg, fg_color=self.card_bg, corner_radius=8, border_width=1, border_color=self.border_color)
        body.grid(row=1, column=0, sticky="nsew", padx=14, pady=6)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(2, weight=1)

        # Row 0: State, Assigned To, Urgency, Tags
        meta_grid = ctk.CTkFrame(body, fg_color="transparent")
        meta_grid.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(10, 6))
        meta_grid.grid_columnconfigure(0, weight=1)
        meta_grid.grid_columnconfigure(1, weight=2)
        meta_grid.grid_columnconfigure(2, weight=1)
        meta_grid.grid_columnconfigure(3, weight=2)

        # State
        st_box = ctk.CTkFrame(meta_grid, fg_color="transparent")
        st_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(st_box, text="State (Status):", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.text_muted).pack(anchor="w")
        cmb_state = ctk.CTkComboBox(
            st_box,
            values=["New", "To Do", "In Progress", "Committed", "Validation", "Done", "Removed"],
            height=30
        )
        cmb_state.pack(fill="x", pady=(2, 0))

        # Assigned To
        ass_box = ctk.CTkFrame(meta_grid, fg_color="transparent")
        ass_box.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(ass_box, text="Assigned To (Responsável):", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.text_muted).pack(anchor="w")
        ent_assigned = ctk.CTkEntry(ass_box, height=30, placeholder_text="Ex: alex.costa ou nome do dev")
        ent_assigned.pack(fill="x", pady=(2, 0))

        # Urgency
        urg_box = ctk.CTkFrame(meta_grid, fg_color="transparent")
        urg_box.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        ctk.CTkLabel(urg_box, text="Urgency:", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.text_muted).pack(anchor="w")
        cmb_urg = ctk.CTkComboBox(urg_box, values=["1", "2", "3", "4", "5"], height=30)
        cmb_urg.pack(fill="x", pady=(2, 0))

        # Reported By
        rep_box = ctk.CTkFrame(meta_grid, fg_color="transparent")
        rep_box.grid(row=0, column=3, sticky="ew")
        ctk.CTkLabel(rep_box, text="Reported By:", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.text_muted).pack(anchor="w")
        ent_rep = ctk.CTkEntry(rep_box, height=30)
        ent_rep.pack(fill="x", pady=(2, 0))

        # Row 1: Tags + Quick Tag selector (to move card between Dashboard columns!)
        tag_row = ctk.CTkFrame(body, fg_color="transparent")
        tag_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(2, 8))
        tag_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(tag_row, text="Tags:", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.text_muted).grid(row=0, column=0, padx=(0, 8), sticky="w")
        ent_edit_tags = ctk.CTkEntry(tag_row, height=30, placeholder_text="Tags separadas por ponto e vírgula (;)")
        ent_edit_tags.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        dash_tags = [
            "DE - Demandas Erros",
            "AES - Acompanhamento de Erros sem Solução",
            "PLib - Pendentes de Liberação",
            "RR - Renovação relatórios",
            "TVali - Testes de Validação",
            "Dm - Demandas Melhorias",
            "PClis - Pedidos de Clientes",
            "Sug - Sugestão",
            "Cr - Cadastro Rapido",
            "DemandasSistemaSuporte",
            "ErrosSistemaSuporte",
            "DemandasMobilidadeSuporte",
            "ErrosMobilidadeSuporte",
            "SugestãoMelhoriaSuporte"
        ]

        def add_or_set_tag(chosen_tag):
            if chosen_tag.startswith("🏷️"):
                return
            current_tags = [t.strip() for t in ent_edit_tags.get().split(";") if t.strip()]
            if chosen_tag not in current_tags:
                current_tags.append(chosen_tag)
            ent_edit_tags.delete(0, "end")
            ent_edit_tags.insert(0, "; ".join(current_tags))
            cmb_add_tag.set("🏷️ + Adicionar Tag Dashboard")

        cmb_add_tag = ctk.CTkOptionMenu(
            tag_row,
            values=dash_tags,
            width=210,
            height=30,
            fg_color="#323130",
            button_color="#484644",
            font=ctk.CTkFont(size=11),
            command=add_or_set_tag
        )
        cmb_add_tag.set("🏷️ + Adicionar Tag Dashboard")
        cmb_add_tag.grid(row=0, column=2)

        # Row 2 Left: Description editor
        desc_frame = ctk.CTkFrame(body, fg_color="transparent")
        desc_frame.grid(row=2, column=0, sticky="nsew", padx=(12, 6), pady=(0, 10))
        desc_frame.grid_columnconfigure(0, weight=1)
        desc_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            desc_frame,
            text="Description (Descrição da Demanda):",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))

        txt_edit_desc = ctk.CTkTextbox(
            desc_frame,
            font=ctk.CTkFont(size=13),
            fg_color="#1b1a19",
            border_width=1,
            border_color="#484644",
            wrap="word"
        )
        txt_edit_desc.grid(row=1, column=0, sticky="nsew")

        # Row 2 Right: Discussion Comment + New Attachments
        right_edit = ctk.CTkFrame(body, fg_color="transparent")
        right_edit.grid(row=2, column=1, sticky="nsew", padx=(6, 12), pady=(0, 10))
        right_edit.grid_columnconfigure(0, weight=1)
        right_edit.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            right_edit,
            text="💬 Adicionar Comentário (Discussion):",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))

        txt_comment = ctk.CTkTextbox(
            right_edit,
            font=ctk.CTkFont(size=12),
            fg_color="#1b1a19",
            border_width=1,
            border_color="#484644",
            wrap="word",
            height=90
        )
        txt_comment.grid(row=1, column=0, sticky="nsew", pady=(0, 6))

        # --- ÁREA DE PRINTS & ANEXOS ---
        new_att_paths = []
        existing_attachments = []

        att_section = ctk.CTkFrame(right_edit, fg_color="#1c1b1a", corner_radius=6, border_width=1, border_color="#383635")
        att_section.grid(row=2, column=0, sticky="nsew", pady=(2, 0))
        att_section.grid_columnconfigure(0, weight=1)
        att_section.grid_rowconfigure(2, weight=1)

        att_header_box = ctk.CTkFrame(att_section, fg_color="transparent")
        att_header_box.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 4))
        att_header_box.grid_columnconfigure(0, weight=1)

        lbl_edit_att = ctk.CTkLabel(
            att_header_box,
            text="🖼️ Prints e Anexos (0)",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        lbl_edit_att.grid(row=0, column=0, sticky="w")

        att_btn_box = ctk.CTkFrame(att_section, fg_color="transparent")
        att_btn_box.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        att_btn_box.grid_columnconfigure(0, weight=1)
        att_btn_box.grid_columnconfigure(1, weight=1)

        def paste_clip_to_edit():
            clip = ImageGrab.grabclipboard()
            if isinstance(clip, Image.Image):
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                fn = f"print_edit_{ts}.png"
                fp = os.path.join(TEMP_ATTACH_DIR, fn)
                clip.save(fp, "PNG")
                new_att_paths.append(fp)
                render_edit_attachments_list()
                lbl_edit_status.configure(text=f"📸 Print '{fn}' adicionado via Ctrl+V!", text_color="#89e09d")
            elif isinstance(clip, list):
                added = 0
                for p in clip:
                    if os.path.isfile(p):
                        new_att_paths.append(p)
                        added += 1
                if added > 0:
                    render_edit_attachments_list()
                    lbl_edit_status.configure(text=f"📎 {added} arquivo(s) adicionado(s)!", text_color="#89e09d")
            else:
                messagebox.showinfo("Área de Transferência", "Nenhuma imagem encontrada na área de transferência (Ctrl+V).\n\nTire um print (Win+Shift+S) e tente novamente.", parent=dlg)

        def browse_file_to_edit():
            files = filedialog.askopenfilenames(parent=dlg, title="Anexar arquivos à demanda")
            if files:
                new_att_paths.extend(files)
                render_edit_attachments_list()
                lbl_edit_status.configure(text=f"📎 {len(files)} anexo(s) adicionado(s)!", text_color="#89e09d")

        def remove_new_att(idx):
            if 0 <= idx < len(new_att_paths):
                new_att_paths.pop(idx)
                render_edit_attachments_list()

        ctk.CTkButton(
            att_btn_box,
            text="📋 Colar Print (Ctrl+V)",
            height=30,
            fg_color="#2d5a88",
            hover_color="#3972ab",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=paste_clip_to_edit
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))

        ctk.CTkButton(
            att_btn_box,
            text="📁 Anexar Arquivo...",
            height=30,
            fg_color="#323130",
            hover_color="#484644",
            font=ctk.CTkFont(size=11),
            command=browse_file_to_edit
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        edit_att_scroll = ctk.CTkScrollableFrame(
            att_section,
            fg_color="#141414",
            corner_radius=4,
            height=160
        )
        edit_att_scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        edit_att_scroll.grid_columnconfigure(0, weight=1)

        def render_edit_attachments_list():
            for w in edit_att_scroll.winfo_children():
                w.destroy()

            tot_ex = len(existing_attachments)
            tot_new = len(new_att_paths)
            total = tot_ex + tot_new
            lbl_edit_att.configure(
                text=f"🖼️ Prints & Anexos ({total} total: {tot_ex} existentes, {tot_new} novos)",
                text_color="#89e09d" if tot_new > 0 else "white"
            )

            if total == 0:
                ctk.CTkLabel(
                    edit_att_scroll,
                    text="Nenhum print anexado a este card.\nUse Ctrl+V ou o botão acima para adicionar.",
                    font=ctk.CTkFont(size=11),
                    text_color=self.text_muted,
                    justify="center"
                ).pack(pady=16, padx=8)
                return

            if tot_new > 0:
                ctk.CTkLabel(
                    edit_att_scroll,
                    text="Novos Prints (serão salvos no DevOps):",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="#89e09d",
                    anchor="w"
                ).pack(fill="x", padx=4, pady=(4, 2))

                for idx, fp in enumerate(new_att_paths):
                    row = ctk.CTkFrame(edit_att_scroll, fg_color="#2b2d30", corner_radius=4)
                    row.pack(fill="x", padx=2, pady=2)

                    fn = os.path.basename(fp)
                    is_img = fn.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
                    icon = "🖼️" if is_img else "📄"

                    lbl = ctk.CTkLabel(
                        row,
                        text=f"{icon} {fn}",
                        font=ctk.CTkFont(size=11),
                        anchor="w"
                    )
                    lbl.pack(side="left", padx=6, pady=3, fill="x", expand=True)

                    if is_img:
                        ctk.CTkButton(
                            row,
                            text="👁️ Ver",
                            width=52,
                            height=22,
                            fg_color="#2d5a88",
                            hover_color="#3972ab",
                            font=ctk.CTkFont(size=10, weight="bold"),
                            command=lambda p=fp, n=fn: self.open_image_viewer_modal(p, n, is_remote=False)
                        ).pack(side="right", padx=2, pady=2)

                    ctk.CTkButton(
                        row,
                        text="✕",
                        width=22,
                        height=22,
                        fg_color="transparent",
                        hover_color="#5c2d16",
                        text_color="#f1707b",
                        font=ctk.CTkFont(size=11, weight="bold"),
                        command=lambda i=idx: remove_new_att(i)
                    ).pack(side="right", padx=(2, 4), pady=2)

            if tot_ex > 0:
                ctk.CTkLabel(
                    edit_att_scroll,
                    text="Existentes no Azure DevOps:",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="#5bb3ff",
                    anchor="w"
                ).pack(fill="x", padx=4, pady=(6, 2))

                for att in existing_attachments:
                    row = ctk.CTkFrame(edit_att_scroll, fg_color="#212224", corner_radius=4)
                    row.pack(fill="x", padx=2, pady=2)

                    fn = att.get("name", "anexo.png")
                    is_img = fn.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
                    icon = "🖼️" if is_img else "📄"
                    sz_kb = (att.get("size", 0) or 0) / 1024.0
                    sz_str = f" ({sz_kb:.0f} KB)" if sz_kb > 0 else ""

                    lbl = ctk.CTkLabel(
                        row,
                        text=f"{icon} {fn}{sz_str}",
                        font=ctk.CTkFont(size=11),
                        anchor="w"
                    )
                    lbl.pack(side="left", padx=6, pady=3, fill="x", expand=True)

                    if is_img:
                        ctk.CTkButton(
                            row,
                            text="👁️ Ver Print",
                            width=78,
                            height=22,
                            fg_color="#2d5a88",
                            hover_color="#3972ab",
                            font=ctk.CTkFont(size=10, weight="bold"),
                            command=lambda u=att["url"], n=fn: self.open_image_viewer_modal(u, n, is_remote=True)
                        ).pack(side="right", padx=(2, 4), pady=2)

        render_edit_attachments_list()

        # Keyboard shortcut Ctrl+V and active modal tracking
        self._active_edit_dlg = dlg
        dlg.paste_clip = paste_clip_to_edit
        dlg.bind("<Control-v>", lambda e: paste_clip_to_edit())

        def on_dlg_close():
            if getattr(self, "_active_edit_dlg", None) == dlg:
                self._active_edit_dlg = None
            dlg.destroy()

        dlg.protocol("WM_DELETE_WINDOW", on_dlg_close)

        # Footer Bar
        ftr = ctk.CTkFrame(dlg, fg_color="transparent")
        ftr.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 12))
        ftr.grid_columnconfigure(0, weight=1)

        lbl_edit_status = ctk.CTkLabel(ftr, text="", font=ctk.CTkFont(size=12), text_color=self.text_muted, anchor="w")
        lbl_edit_status.grid(row=0, column=0, sticky="w")

        btn_cancel = ctk.CTkButton(
            ftr,
            text="Cancelar",
            width=110,
            height=38,
            fg_color="#323130",
            hover_color="#484644",
            command=on_dlg_close
        )
        btn_cancel.grid(row=0, column=1, padx=(0, 10))

        btn_save_edit = ctk.CTkButton(
            ftr,
            text="💾 Salvar Alterações no DevOps",
            width=230,
            height=38,
            fg_color=self.accent_blue,
            hover_color="#106ebe",
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled"
        )
        btn_save_edit.grid(row=0, column=2)

        original_desc_plain = {"val": ""}

        # Fetch work item details in background
        def load_worker():
            client = AzureDevOpsClient(org, pat)
            try:
                wi = client.get_work_item(project, work_item_id)

                def populate():
                    wi_url_var.set(wi["url"])
                    lbl_wi_badge.configure(
                        text=f"✦ {wi['type'].upper()} #{wi['id']}   |   Projeto: {wi['project']}   |   Anexos existentes: {wi['attachments_count']}"
                    )
                    ent_edit_title.delete(0, "end")
                    ent_edit_title.insert(0, wi["title"])
                    cmb_state.set(wi["state"])
                    ent_assigned.delete(0, "end")
                    ent_assigned.insert(0, wi["assigned_to"])
                    cmb_urg.set(wi["urgency"] or "4")
                    ent_rep.delete(0, "end")
                    ent_rep.insert(0, wi["reported_by"])
                    ent_edit_tags.delete(0, "end")
                    ent_edit_tags.insert(0, wi["tags"])

                    txt_edit_desc.delete("1.0", "end")
                    txt_edit_desc.insert("1.0", wi["description_plain"])
                    original_desc_plain["val"] = wi["description_plain"]

                    existing_attachments.clear()
                    existing_attachments.extend(wi.get("attachments", []))
                    render_edit_attachments_list()

                    btn_save_edit.configure(state="normal")
                    lbl_edit_status.configure(text="Pronto para edição.", text_color=self.text_muted)

                self.after(0, populate)
            except Exception as e:
                err_str = str(e)

                def show_err():
                    lbl_wi_badge.configure(text=f"❌ Erro ao carregar #{work_item_id}", text_color="#f1707b")
                    lbl_edit_status.configure(text=err_str[:80], text_color="#f1707b")

                self.after(0, show_err)

        threading.Thread(target=load_worker, daemon=True).start()

        def save_changes():
            new_title = ent_edit_title.get().strip()
            if not new_title:
                messagebox.showwarning("Título Obrigatório", "O título da demanda não pode ficar vazio.", parent=dlg)
                return

            new_state = cmb_state.get().strip()
            new_assigned = ent_assigned.get().strip()
            new_urg = cmb_urg.get().strip()
            new_rep = ent_rep.get().strip()
            new_tags = ent_edit_tags.get().strip()
            new_desc_plain = txt_edit_desc.get("1.0", "end").strip()
            comment_str = txt_comment.get("1.0", "end").strip()

            # Only overwrite HTML description if user modified description text
            desc_html_to_send = None
            if new_desc_plain != original_desc_plain["val"].strip():
                desc_html_to_send = plain_text_to_html(new_desc_plain)

            btn_save_edit.configure(state="disabled", text="⏳ Salvando...")
            lbl_edit_status.configure(text="Enviando alterações para o Azure DevOps...", text_color="#ffaa73")

            def update_worker():
                client = AzureDevOpsClient(org, pat)
                try:
                    updated = client.update_work_item(
                        project=project,
                        work_item_id=work_item_id,
                        title=new_title,
                        state=new_state,
                        assigned_to=new_assigned,
                        tags=new_tags,
                        urgency=new_urg,
                        reported_by=new_rep,
                        description_html=desc_html_to_send,
                        comment=comment_str,
                        attachment_paths=new_att_paths
                    )

                    def on_saved():
                        # Update local history if present
                        for h in self.history_data:
                            if str(h.get("id")) == str(work_item_id):
                                h["title"] = updated["title"]
                                h["state"] = updated["state"]
                        save_json_file(HISTORY_FILE, self.history_data)
                        self._render_history()

                        self.lbl_feedback.configure(
                            text=f"✅ Demanda #{work_item_id} atualizada com sucesso!",
                            text_color="#89e09d"
                        )
                        on_dlg_close()
                        if self.tabview.get() == "📊 Dashboards":
                            self.refresh_dashboard()

                    self.after(0, on_saved)
                except Exception as e:
                    err_s = str(e)

                    def on_save_err():
                        btn_save_edit.configure(state="normal", text="💾 Salvar Alterações no DevOps")
                        lbl_edit_status.configure(text=f"❌ Erro: {err_s[:70]}", text_color="#f1707b")
                        messagebox.showerror("Erro ao Salvar", f"Não foi possível atualizar a demanda:\n\n{err_s}", parent=dlg)

                    self.after(0, on_save_err)

            threading.Thread(target=update_worker, daemon=True).start()

        btn_save_edit.configure(command=save_changes)

    # -------------------------------------------------------------------------
    # TAB 3: HISTÓRICO
    # -------------------------------------------------------------------------
    def _build_history_tab(self):
        self.tab_history.grid_columnconfigure(0, weight=1)
        self.tab_history.grid_rowconfigure(1, weight=1)

        top_h = ctk.CTkFrame(self.tab_history, fg_color="transparent")
        top_h.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 8))

        ctk.CTkLabel(
            top_h,
            text="Demandas Cadastradas Recentemente",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        ctk.CTkButton(
            top_h,
            text="🗑 Limpar Histórico",
            width=130,
            height=30,
            fg_color="#323130",
            hover_color="#484644",
            command=self._clear_history
        ).pack(side="right")

        self.history_scroll = ctk.CTkScrollableFrame(
            self.tab_history,
            fg_color=self.card_bg,
            corner_radius=8
        )
        self.history_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self.history_scroll.grid_columnconfigure(0, weight=1)

        self._render_history()

    def _render_history(self):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        if not self.history_data:
            ctk.CTkLabel(
                self.history_scroll,
                text="Nenhuma demanda cadastrada por aqui ainda.",
                text_color=self.text_muted,
                font=ctk.CTkFont(size=13)
            ).pack(pady=40)
            return

        for item in self.history_data:
            row_card = ctk.CTkFrame(
                self.history_scroll,
                fg_color="#1b1a19",
                corner_radius=6,
                border_width=1,
                border_color=self.border_color
            )
            row_card.pack(fill="x", padx=8, pady=5)

            left = ctk.CTkFrame(row_card, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=12, pady=8)

            wi_id = item.get("id", "?")
            wi_type = item.get("type", "Spike").upper()
            title = item.get("title", "")
            cliente = item.get("cliente", "")
            modulo = item.get("modulo", "")
            created = item.get("created_at", "")
            project = item.get("project", "One_FrontEnd")

            badge_lbl = ctk.CTkLabel(
                left,
                text=f"✦ {wi_type} #{wi_id}  —  {title}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#ffffff",
                anchor="w"
            )
            badge_lbl.pack(fill="x")

            sub_lbl = ctk.CTkLabel(
                left,
                text=f"Projeto: {project}   |   Cliente: {cliente}   |   Módulo: {modulo}   |   Criado em: {created}",
                font=ctk.CTkFont(size=12),
                text_color=self.text_muted,
                anchor="w"
            )
            sub_lbl.pack(fill="x", pady=(2, 0))

            url = item.get("url", "")
            btn_row = ctk.CTkFrame(row_card, fg_color="transparent")
            btn_row.pack(side="right", padx=12, pady=8)

            if str(wi_id).isdigit():
                btn_edit = ctk.CTkButton(
                    btn_row,
                    text="✏️ Editar",
                    width=90,
                    height=32,
                    fg_color="#2d5a88",
                    hover_color="#3972ab",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    command=lambda i=int(wi_id), p=project: self.open_edit_work_item_modal(i, p)
                )
                btn_edit.pack(side="left", padx=(0, 8))

            if url:
                btn_copy = ctk.CTkButton(
                    btn_row,
                    text="📋 Copiar Link",
                    width=115,
                    height=32,
                    fg_color="#323130",
                    hover_color="#484644",
                    command=lambda u=url: self.copy_to_clipboard(u)
                )
                btn_copy.pack(side="left", padx=(0, 8))

                btn_open = ctk.CTkButton(
                    btn_row,
                    text="🔗 Abrir no DevOps",
                    width=140,
                    height=32,
                    fg_color=self.accent_blue,
                    hover_color="#106ebe",
                    command=lambda u=url: webbrowser.open(u)
                )
                btn_open.pack(side="left")

    def _clear_history(self):
        if messagebox.askyesno("Limpar Histórico", "Deseja limpar o histórico local de demandas cadastradas?"):
            self.history_data = []
            save_json_file(HISTORY_FILE, self.history_data)
            self._render_history()

    # -------------------------------------------------------------------------
    # TAB 4: CONFIGURAÇÕES
    # -------------------------------------------------------------------------
    def _build_settings_tab(self):
        self.tab_settings.grid_columnconfigure(0, weight=1)
        self.tab_settings.grid_rowconfigure(0, weight=1)

        settings_scroll = ctk.CTkScrollableFrame(
            self.tab_settings,
            fg_color=self.card_bg,
            corner_radius=8
        )
        settings_scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=4)
        settings_scroll.grid_columnconfigure(0, weight=1)
        settings_scroll.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            settings_scroll,
            text="Configurações do Azure DevOps & Padrões",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(12, 4))

        help_box = ctk.CTkFrame(settings_scroll, fg_color="#1b1a19", corner_radius=6, border_width=1, border_color="#3b3a39")
        help_box.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(4, 12))
        help_text = (
            "🔑 Como gerar seu Personal Access Token (PAT) no Azure DevOps:\n"
            "1. No Azure DevOps (dev.azure.com/onebelezabemstar), clique no ícone de configurações de usuário (canto superior direito ao lado do seu avatar) > 'Personal access tokens'.\n"
            "2. Clique em '+ New Token', dê um nome (ex: 'CadastroDemandas') e marque o escopo 'Work Items: Read, write, & manage'.\n"
            "3. Copie o token gerado e cole no campo abaixo."
        )
        ctk.CTkLabel(
            help_box,
            text=help_text,
            font=ctk.CTkFont(size=12),
            text_color="#cccccc",
            justify="left",
            anchor="w"
        ).pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(settings_scroll, text="Personal Access Token (PAT):", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, columnspan=2, sticky="w", padx=16, pady=(6, 2))
        pat_frame = ctk.CTkFrame(settings_scroll, fg_color="transparent")
        pat_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 8))
        pat_frame.grid_columnconfigure(0, weight=1)

        self.cfg_pat = ctk.CTkEntry(pat_frame, height=32, show="•")
        self.cfg_pat.insert(0, self.config_data.get("pat", ""))
        self.cfg_pat.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.var_show_pat = False
        self.btn_toggle_pat = ctk.CTkButton(
            pat_frame,
            text="👁",
            width=36,
            height=32,
            fg_color="#323130",
            hover_color="#484644",
            command=self._toggle_pat_visibility
        )
        self.btn_toggle_pat.grid(row=0, column=1)

        ctk.CTkLabel(settings_scroll, text="Tipo de Work Item Padrão (ex: Spike, Bug):", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, sticky="w", padx=16, pady=(6, 2))
        self.cfg_wi_type = ctk.CTkEntry(settings_scroll, height=32)
        self.cfg_wi_type.insert(0, self.config_data.get("work_item_type", "Spike"))
        self.cfg_wi_type.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 8))

        ctk.CTkLabel(settings_scroll, text="Reported By Padrão:", font=ctk.CTkFont(weight="bold")).grid(row=4, column=1, sticky="w", padx=16, pady=(6, 2))
        self.cfg_reported_by = ctk.CTkEntry(settings_scroll, height=32)
        self.cfg_reported_by.insert(0, self.config_data.get("default_reported_by", "Cadastro Rapido"))
        self.cfg_reported_by.grid(row=5, column=1, sticky="ew", padx=16, pady=(0, 8))

        ctk.CTkLabel(settings_scroll, text="Urgency Padrão:", font=ctk.CTkFont(weight="bold")).grid(row=6, column=0, sticky="w", padx=16, pady=(6, 2))
        self.cfg_urgency = ctk.CTkEntry(settings_scroll, height=32)
        self.cfg_urgency.insert(0, str(self.config_data.get("default_urgency", "1")))
        self.cfg_urgency.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 8))

        ctk.CTkLabel(settings_scroll, text="Tags Padrão (separadas por ponto e vírgula):", font=ctk.CTkFont(weight="bold")).grid(row=6, column=1, sticky="w", padx=16, pady=(6, 2))
        self.cfg_tags = ctk.CTkEntry(settings_scroll, height=32)
        self.cfg_tags.insert(0, self.config_data.get("default_tags", "Cr - Cadastro Rapido"))
        self.cfg_tags.grid(row=7, column=1, sticky="ew", padx=16, pady=(0, 8))

        ctk.CTkLabel(settings_scroll, text="Módulos do Sistema (separados por vírgula):", font=ctk.CTkFont(weight="bold")).grid(row=8, column=0, columnspan=2, sticky="w", padx=16, pady=(6, 2))
        self.cfg_modules = ctk.CTkEntry(settings_scroll, height=32)
        self.cfg_modules.insert(0, ", ".join(self.config_data.get("modules_list", DEFAULT_CONFIG["modules_list"])))
        self.cfg_modules.grid(row=9, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 8))

        # Action buttons for settings
        cfg_btn_row = ctk.CTkFrame(settings_scroll, fg_color="transparent")
        cfg_btn_row.grid(row=10, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 10))

        self.btn_test_conn = ctk.CTkButton(
            cfg_btn_row,
            text="🔌 Testar Conexão e Carregar Projetos",
            height=38,
            fg_color="#323130",
            hover_color="#484644",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.test_devops_connection
        )
        self.btn_test_conn.pack(side="left", padx=(0, 12))

        self.btn_save_cfg = ctk.CTkButton(
            cfg_btn_row,
            text="💾 Salvar Configurações",
            height=38,
            fg_color=self.accent_blue,
            hover_color="#106ebe",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.save_settings
        )
        self.btn_save_cfg.pack(side="left", padx=(0, 12))

        self.btn_check_update = ctk.CTkButton(
            cfg_btn_row,
            text="🔄 Verificar Atualizações",
            height=38,
            fg_color="#2d5a88",
            hover_color="#3972ab",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.check_for_updates(manual=True)
        )
        self.btn_check_update.pack(side="left")

        self.lbl_cfg_status = ctk.CTkLabel(
            settings_scroll,
            text=f"Versão instalada: v{APP_VERSION}  |  Repositório: {GITHUB_REPO}",
            font=ctk.CTkFont(size=13),
            anchor="w"
        )
        self.lbl_cfg_status.grid(row=11, column=0, columnspan=2, sticky="ew", padx=16, pady=(4, 12))

    def _toggle_pat_visibility(self):
        self.var_show_pat = not self.var_show_pat
        self.cfg_pat.configure(show="" if self.var_show_pat else "•")

    def save_settings(self):
        org = self.config_data.get("organization", "onebelezabemstar")
        pat = self.cfg_pat.get().strip()
        proj = self.config_data.get("project", "One_FrontEnd")
        wi_type = self.cfg_wi_type.get().strip() or "Spike"
        rep_by = self.cfg_reported_by.get().strip() or "Cadastro Rapido"
        urgency = self.cfg_urgency.get().strip() or "1"
        tags = self.cfg_tags.get().strip() or "Cr - Cadastro Rapido"
        mods_raw = self.cfg_modules.get().strip()
        mods = [m.strip() for m in mods_raw.split(",") if m.strip()] or DEFAULT_CONFIG["modules_list"]

        projects_list = self.config_data.get("projects_list", DEFAULT_CONFIG["projects_list"])

        types_list = self.config_data.get("work_item_types_list", ["Spike", "Bug", "User Story", "Task", "Product Backlog Item"])
        if wi_type not in types_list:
            types_list.insert(0, wi_type)

        self.config_data.update({
            "organization": org,
            "pat": pat,
            "project": proj,
            "projects_list": projects_list,
            "work_item_type": wi_type,
            "work_item_types_list": types_list,
            "default_reported_by": rep_by,
            "default_urgency": urgency,
            "default_tags": tags,
            "modules_list": mods,
            "github_repo": GITHUB_REPO,
            "include_print_em_anexo": self.var_print_anexo.get()
        })
        save_json_file(CONFIG_FILE, self.config_data)

        self.cmb_type.configure(values=types_list)
        self.cmb_type.set(wi_type)
        self.cmb_modulo.configure(values=mods)
        self.ent_tags.delete(0, "end")
        self.ent_tags.insert(0, tags)
        self.ent_reported_by.delete(0, "end")
        self.ent_reported_by.insert(0, rep_by)
        self.cmb_urgency.set(urgency)

        self._update_header_badge()
        self.lbl_cfg_status.configure(text="✅ Configurações salvas com sucesso!", text_color="#89e09d")
        self.lbl_feedback.configure(text="✅ Configurações atualizadas e prontas para uso.", text_color="#89e09d")

    def _download_and_self_update(self, new_version: str, download_url: str):
        """Baixa o novo executável em segundo plano, substitui o atual e reinicia o aplicativo automaticamente."""
        import subprocess

        dlg = ctk.CTkToplevel(self)
        dlg.title("Atualizando Aplicativo...")
        dlg.geometry("450x170")
        dlg.resizable(False, False)
        dlg.configure(fg_color=self.bg_dark)
        dlg.transient(self)
        dlg.grab_set()

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 225
        y = self.winfo_y() + (self.winfo_height() // 2) - 85
        dlg.geometry(f"+{max(0, x)}+{max(0, y)}")

        lbl_info = ctk.CTkLabel(
            dlg,
            text=f"⬇️ Baixando atualização v{new_version}...",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#89e09d"
        )
        lbl_info.pack(padx=20, pady=(20, 10))

        progress_bar = ctk.CTkProgressBar(dlg, width=380, height=14)
        progress_bar.pack(padx=20, pady=(5, 10))
        progress_bar.set(0)

        lbl_status = ctk.CTkLabel(dlg, text="Conectando ao GitHub...", font=ctk.CTkFont(size=12), text_color=self.text_muted)
        lbl_status.pack(padx=20, pady=(0, 15))

        def update_worker():
            try:
                import requests
                headers = {"User-Agent": "DevOps-Demandas-App"}
                resp = requests.get(download_url, headers=headers, stream=True, timeout=30)
                if resp.status_code != 200:
                    raise Exception(f"Falha ao baixar arquivo (HTTP {resp.status_code})")

                total_size = int(resp.headers.get("content-length", 0))
                temp_new_exe = os.path.join(tempfile.gettempdir(), f"DevOpsDemandas_v{new_version}.exe")

                downloaded = 0
                with open(temp_new_exe, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                frac = downloaded / total_size
                                def update_p(p=frac, d=downloaded, t=total_size):
                                    progress_bar.set(p)
                                    mb_d = d / (1024 * 1024)
                                    mb_t = t / (1024 * 1024)
                                    lbl_status.configure(text=f"{mb_d:.1f} MB de {mb_t:.1f} MB ({int(p*100)}%)")
                                self.after(0, update_p)

                def finalize():
                    lbl_info.configure(text="✅ Download concluído! Reiniciando...")
                    lbl_status.configure(text="Aplicando nova versão...")
                    
                    # Caminho do executável atual em execução
                    current_exe = sys.executable if getattr(sys, "frozen", False) else os.path.join(APP_DIR, "..", "DevOpsDemandas.exe")
                    current_exe = os.path.abspath(current_exe)
                    
                    # Cria script batch para substituir o executável assim que este processo fechar e reabrir o novo
                    updater_bat = os.path.join(tempfile.gettempdir(), "devops_self_update.bat")
                    bat_content = f"""@echo off
timeout /t 1 /nobreak > nul
:retry
move /y "{temp_new_exe}" "{current_exe}" > nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak > nul
    goto retry
)
start "" "{current_exe}"
del "%~f0"
"""
                    with open(updater_bat, "w", encoding="utf-8") as bf:
                        bf.write(bat_content)

                    # Executa o batch oculto e fecha o programa atual
                    subprocess.Popen(["cmd.exe", "/c", updater_bat], creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                    self.destroy()
                    sys.exit(0)

                self.after(500, finalize)

            except Exception as e:
                err_m = str(e)
                def on_dl_err():
                    dlg.destroy()
                    messagebox.showerror(
                        "Falha na Atualização",
                        f"Não foi possível baixar e aplicar a atualização automaticamente:\n\n{err_m}\n\nVocê pode baixar manualmente pelo repositório."
                    )
                self.after(0, on_dl_err)

        threading.Thread(target=update_worker, daemon=True).start()

    def check_for_updates(self, manual: bool = False):
        """Verifica no GitHub se existe uma release ou versão mais recente do código."""
        repo = GITHUB_REPO

        self.btn_check_update.configure(state="disabled", text="⏳ Checando...")
        self.lbl_cfg_status.configure(text="Consultando GitHub por atualizações...", text_color="#ffaa73")

        def worker():
            api_url = f"https://api.github.com/repos/{repo}/releases/latest"
            raw_url = f"https://raw.githubusercontent.com/{repo}/main/src/app.py"
            raw_exe_url = f"https://github.com/{repo}/raw/main/DevOpsDemandas.exe"
            try:
                import requests
                headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "DevOps-Demandas-App"}
                
                # 1. Tenta checar versão mais recente no código do branch main
                resp_raw = requests.get(raw_url, headers=headers, timeout=6)
                remote_version = None
                if resp_raw.status_code == 200:
                    for line in resp_raw.text.splitlines():
                        if line.startswith("APP_VERSION ="):
                            remote_version = line.split("=")[1].strip().strip('"').strip("'")
                            break

                # 2. Se houver release oficial no GitHub
                resp = requests.get(api_url, headers=headers, timeout=6)
                release_tag = None
                download_exe_url = raw_exe_url
                if resp.status_code == 200:
                    data = resp.json()
                    release_tag = data.get("tag_name", "").lstrip("v").strip()
                    assets = data.get("assets", [])
                    for a in assets:
                        if a.get("name", "").endswith(".exe"):
                            download_exe_url = a.get("browser_download_url", download_exe_url)
                            break

                new_version = release_tag or remote_version

                def on_result():
                    self.btn_check_update.configure(state="normal", text="🔄 Verificar Atualizações")
                    if new_version and new_version != APP_VERSION:
                        self.lbl_cfg_status.configure(
                            text=f"✨ Nova versão disponível: v{new_version} (Instalada: v{APP_VERSION})",
                            text_color="#ffaa73"
                        )
                        if messagebox.askyesno(
                            "Atualização Disponível!",
                            f"Existe uma nova versão disponível no GitHub!\n\n"
                            f"Versão instalada: v{APP_VERSION}\n"
                            f"Nova versão: v{new_version}\n\n"
                            f"Deseja atualizar agora automaticamente?"
                        ):
                            self._download_and_self_update(new_version, download_exe_url)
                    else:
                        self.lbl_cfg_status.configure(
                            text=f"✅ O aplicativo está atualizado! (v{APP_VERSION})",
                            text_color="#89e09d"
                        )
                        if manual:
                            messagebox.showinfo("Atualizado", f"Seu aplicativo já está na versão mais recente (v{APP_VERSION}).")

                self.after(0, on_result)
            except Exception as e:
                err_msg = str(e)
                def on_exc():
                    self.btn_check_update.configure(state="normal", text="🔄 Verificar Atualizações")
                    self.lbl_cfg_status.configure(text=f"Não foi possível checar atualizações: {err_msg[:40]}", text_color="#f1707b")
                self.after(0, on_exc)

        threading.Thread(target=worker, daemon=True).start()

    def test_devops_connection(self):
        self.save_settings()
        org = self.config_data["organization"]
        pat = self.config_data["pat"]
        proj = self.config_data["project"]

        self.btn_test_conn.configure(state="disabled", text="⏳ Testando...")
        self.lbl_cfg_status.configure(text="Conectando ao Azure DevOps...", text_color="#cccccc")

        def worker():
            client = AzureDevOpsClient(org, pat)
            ok, msg = client.test_connection(proj)
            projects = client.get_projects() if ok else []

            def on_done():
                self.btn_test_conn.configure(state="normal", text="🔌 Testar Conexão e Carregar Projetos")
                if ok:
                    if projects:
                        self.config_data["projects_list"] = projects
                        save_json_file(CONFIG_FILE, self.config_data)
                        self.cmb_project.configure(values=projects)
                        self.cmb_dash_project.configure(values=projects)
                    self.lbl_cfg_status.configure(text=f"✅ {msg}", text_color="#89e09d")
                else:
                    self.lbl_cfg_status.configure(text=f"❌ {msg}", text_color="#f1707b")

            self.after(0, on_done)

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # HELPERS & SHORTCUTS
    # -------------------------------------------------------------------------
    def _bind_shortcuts(self):
        self.bind("<Control-v>", self._on_ctrl_v)
        self.bind("<Control-V>", self._on_ctrl_v)
        self.bind("<Control-Return>", lambda e: self.submit_demand())

    def _on_ctrl_v(self, event=None):
        """Handle global Ctrl+V: if clipboard contains image or files, attach them seamlessly."""
        active_dlg = getattr(self, "_active_edit_dlg", None)
        if active_dlg:
            try:
                if active_dlg.winfo_exists():
                    clip = ImageGrab.grabclipboard()
                    if isinstance(clip, (Image.Image, list)):
                        if hasattr(active_dlg, "paste_clip"):
                            active_dlg.paste_clip()
                            return "break"
            except Exception:
                pass

        if self.tabview.get() != "➕ Nova Demanda":
            return
        try:
            clip = ImageGrab.grabclipboard()
            if isinstance(clip, Image.Image):
                self._save_clipboard_image(clip)
                return "break"
            elif isinstance(clip, list):
                added = 0
                for p in clip:
                    if os.path.isfile(p):
                        self.attachments.append({
                            "path": p,
                            "name": os.path.basename(p),
                            "is_temp": False
                        })
                        added += 1
                if added > 0:
                    self._render_attachments_list()
                    self.var_print_anexo.set(True)
                    self.lbl_feedback.configure(
                        text=f"📎 {added} arquivo(s) colado(s) da área de transferência!",
                        text_color="#89e09d"
                    )
                    return "break"
        except Exception:
            pass

    def paste_from_clipboard(self):
        try:
            clip = ImageGrab.grabclipboard()
            if isinstance(clip, Image.Image):
                self._save_clipboard_image(clip)
            elif isinstance(clip, list):
                added = 0
                for p in clip:
                    if os.path.isfile(p):
                        self.attachments.append({
                            "path": p,
                            "name": os.path.basename(p),
                            "is_temp": False
                        })
                        added += 1
                if added > 0:
                    self._render_attachments_list()
                    self.lbl_feedback.configure(
                        text=f"📎 {added} arquivo(s) adicionado(s) da área de transferência!",
                        text_color="#89e09d"
                    )
                else:
                    messagebox.showinfo("Área de Transferência", "Nenhum print ou arquivo encontrado na área de transferência.")
            else:
                messagebox.showinfo(
                    "Área de Transferência",
                    "Nenhuma imagem encontrada na área de transferência.\n\nTire um print (Win+Shift+S ou PrintScreen) e clique aqui ou pressione Ctrl+V."
                )
        except Exception as e:
            messagebox.showerror("Erro ao colar", f"Não foi possível ler a imagem da área de transferência:\n{e}")

    def _save_clipboard_image(self, img: Image.Image):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_id = str(uuid.uuid4())[:4]
        filename = f"print_{timestamp}_{short_id}.png"
        filepath = os.path.join(TEMP_ATTACH_DIR, filename)
        img.save(filepath, "PNG")

        self.attachments.append({
            "path": filepath,
            "name": filename,
            "is_temp": True
        })
        self._render_attachments_list()
        self.var_print_anexo.set(True)
        self.lbl_feedback.configure(
            text=f"📸 Print '{filename}' anexado com sucesso via área de transferência!",
            text_color="#89e09d"
        )

    def select_attachment_files(self):
        paths = filedialog.askopenfilenames(
            title="Selecionar Prints ou Arquivos para Anexar",
            filetypes=[
                ("Imagens e Documentos", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.pdf;*.txt;*.log;*.zip;*.mp4"),
                ("Todos os arquivos", "*.*")
            ]
        )
        if paths:
            for p in paths:
                self.attachments.append({
                    "path": p,
                    "name": os.path.basename(p),
                    "is_temp": False
                })
            self._render_attachments_list()
            self.var_print_anexo.set(True)
            self.lbl_feedback.configure(
                text=f"📎 {len(paths)} arquivo(s) anexado(s).",
                text_color="#89e09d"
            )

    def _remove_attachment(self, index: int):
        if 0 <= index < len(self.attachments):
            self.attachments.pop(index)
            self._render_attachments_list()

    def _clear_attachments(self):
        self.attachments.clear()
        self._render_attachments_list()

    def _render_attachments_list(self):
        for w in self.att_list_frame.winfo_children():
            w.destroy()

        count = len(self.attachments)
        self.lbl_att_count.configure(text=f"📎 Anexos / Prints ({count})")

        if count == 0:
            ctk.CTkLabel(
                self.att_list_frame,
                text="Nenhum print anexado.\nUse Win+Shift+S e pressione Ctrl+V para colar um print rapidamente.",
                font=ctk.CTkFont(size=11),
                text_color=self.text_muted,
                justify="center"
            ).pack(pady=18, padx=8)
            return

        for idx, att in enumerate(self.attachments):
            item_row = ctk.CTkFrame(self.att_list_frame, fg_color="#252526", corner_radius=4)
            item_row.pack(fill="x", padx=4, pady=3)

            is_img = att["name"].lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))
            icon = "🖼️" if is_img else "📄"

            lbl = ctk.CTkLabel(
                item_row,
                text=f"{icon}  {att['name']}",
                font=ctk.CTkFont(size=12),
                anchor="w"
            )
            lbl.pack(side="left", padx=8, pady=4, fill="x", expand=True)

            if is_img:
                btn_view = ctk.CTkButton(
                    item_row,
                    text="👁️ Ver Print",
                    width=84,
                    height=24,
                    fg_color="#2d5a88",
                    hover_color="#3972ab",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    command=lambda p=att["path"], n=att["name"]: self.open_image_viewer_modal(p, n, is_remote=False)
                )
                btn_view.pack(side="right", padx=(2, 4), pady=2)

            btn_del = ctk.CTkButton(
                item_row,
                text="✕",
                width=26,
                height=24,
                fg_color="transparent",
                hover_color="#5c2d16",
                text_color="#f1707b",
                command=lambda i=idx: self._remove_attachment(i)
            )
            btn_del.pack(side="right", padx=(2, 4), pady=2)

    def _set_noticed_at_now(self):
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.ent_noticed_at.delete(0, "end")
        self.ent_noticed_at.insert(0, now_str)

    def _on_project_changed(self, selected_project: str):
        self.ent_area.delete(0, "end")
        self.ent_area.insert(0, selected_project)
        self.ent_iteration.delete(0, "end")
        self.ent_iteration.insert(0, selected_project)

    def _on_title_manual_edit(self, event=None):
        if self.focus_get() == self.ent_title._entry:
            self.var_auto_title.set(False)

    def _on_erro_key_release(self, event=None):
        if not self.var_auto_title.get():
            return
        erro_text = self.txt_erro.get("1.0", "end").strip()
        if not erro_text:
            self.ent_title.delete(0, "end")
            return

        first_line = erro_text.splitlines()[0].strip()
        dot_idx = first_line.find(". ")
        if dot_idx != -1:
            auto_title = first_line[:dot_idx + 1]
        else:
            auto_title = first_line

        if len(auto_title) > 120:
            auto_title = auto_title[:117] + "..."

        self.ent_title.delete(0, "end")
        self.ent_title.insert(0, auto_title)

    # -------------------------------------------------------------------------
    # DESCRIPTION BUILDER
    # -------------------------------------------------------------------------
    def build_description_content(self):
        cliente = self.ent_cliente.get().strip()
        modulo = self.cmb_modulo.get().strip()
        erro = self.txt_erro.get("1.0", "end").strip()
        inc_print = self.var_print_anexo.get()

        lines_plain = [
            f"Cliente: {cliente}",
            f"Módulo: {modulo}",
            f"Erro: {erro}"
        ]
        if inc_print:
            lines_plain.append(" print em anexo")

        erro_html = erro.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        cliente_html = cliente.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        modulo_html = modulo.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        html_parts = [
            f"<div>Cliente: {cliente_html}</div>",
            f"<div>Módulo: {modulo_html}</div>",
            f"<div>Erro: {erro_html}</div>"
        ]
        if inc_print:
            html_parts.append("<div>&nbsp;print em anexo</div>")

        return "\n".join(lines_plain), "".join(html_parts)

    def _show_description_preview(self):
        plain_text, _ = self.build_description_content()
        messagebox.showinfo("Prévia da Descrição (Description)", plain_text)

    def copy_to_clipboard(self, text: str, btn_widget=None):
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        if btn_widget:
            orig_text = btn_widget.cget("text")
            btn_widget.configure(text="✅ Copiado!")
            self.after(2000, lambda: btn_widget.configure(text=orig_text))
        else:
            self.lbl_feedback.configure(
                text=f"📋 Link copiado para a área de transferência: {text}",
                text_color="#89e09d"
            )

    def _show_success_dialog(self, wi_type: str, wi_id, title: str, cliente: str, modulo: str, wi_url: str, project: str):
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"{wi_type} #{wi_id} Cadastrado com Sucesso!")
        dlg.geometry("600x310")
        dlg.resizable(False, False)
        dlg.configure(fg_color=self.bg_dark)
        dlg.transient(self)
        dlg.grab_set()

        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 300
        y = self.winfo_y() + (self.winfo_height() // 2) - 155
        dlg.geometry(f"+{max(0, x)}+{max(0, y)}")

        card = ctk.CTkFrame(dlg, fg_color=self.card_bg, corner_radius=8, border_width=1, border_color=self.border_color)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            card,
            text=f"✅ {wi_type.upper()} #{wi_id} criado com sucesso!",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#89e09d",
            anchor="w"
        ).pack(fill="x", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            card,
            text=f"Título: {title[:70]}{'...' if len(title) > 70 else ''}\nCliente: {cliente}   |   Módulo: {modulo}",
            font=ctk.CTkFont(size=12),
            text_color="#cccccc",
            justify="left",
            anchor="w"
        ).pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            card,
            text="Link da Demanda:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffffff",
            anchor="w"
        ).pack(fill="x", padx=16, pady=(2, 4))

        link_row = ctk.CTkFrame(card, fg_color="transparent")
        link_row.pack(fill="x", padx=16, pady=(0, 16))
        link_row.grid_columnconfigure(0, weight=1)

        ent_url = ctk.CTkEntry(
            link_row,
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color="#1b1a19",
            border_color="#0078d4"
        )
        ent_url.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ent_url.insert(0, wi_url)
        ent_url.select_range(0, "end")
        ent_url.focus_set()

        btn_copy_dlg = ctk.CTkButton(
            link_row,
            text="📋 Copiar Link",
            width=120,
            height=34,
            fg_color="#1f4e2c",
            hover_color="#286438",
            text_color="#89e09d",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        btn_copy_dlg.configure(command=lambda: self.copy_to_clipboard(ent_url.get(), btn_copy_dlg))
        btn_copy_dlg.grid(row=0, column=1)

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(4, 12))

        ctk.CTkButton(
            actions,
            text="🌐 Abrir no Navegador",
            width=165,
            height=36,
            fg_color=self.accent_blue,
            hover_color="#106ebe",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: (webbrowser.open(wi_url), dlg.destroy())
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            actions,
            text="✏️ Editar Demanda",
            width=150,
            height=36,
            fg_color="#2d5a88",
            hover_color="#3972ab",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: (dlg.destroy(), self.open_edit_work_item_modal(int(wi_id), project))
        ).pack(side="left")

        ctk.CTkButton(
            actions,
            text="Fechar (Esc)",
            width=120,
            height=36,
            fg_color="#323130",
            hover_color="#484644",
            font=ctk.CTkFont(size=13),
            command=dlg.destroy
        ).pack(side="right")

        dlg.bind("<Escape>", lambda e: dlg.destroy())

    def clear_form(self, keep_feedback: bool = False):
        self.ent_title.delete(0, "end")
        self.ent_cliente.delete(0, "end")
        self.txt_erro.delete("1.0", "end")
        self.var_auto_title.set(True)
        self._set_noticed_at_now()
        self._clear_attachments()
        if not keep_feedback:
            self.lbl_feedback.configure(
                text="Campos limpos. Pronto para cadastrar nova demanda.",
                text_color=self.text_muted
            )

    # -------------------------------------------------------------------------
    # SUBMIT TO AZURE DEVOPS
    # -------------------------------------------------------------------------
    def _parse_noticed_at_to_iso(self, raw_str: str):
        raw_str = raw_str.strip()
        if not raw_str:
            return ""
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d %H:%M"):
            try:
                dt = datetime.strptime(raw_str, fmt)
                local_tz = datetime.now().astimezone().tzinfo
                dt_with_tz = dt.replace(tzinfo=local_tz)
                return dt_with_tz.isoformat()
            except ValueError:
                continue
        return ""

    def submit_demand(self):
        pat = self.config_data.get("pat", "").strip()
        org = self.config_data.get("organization", "").strip()

        if not pat:
            messagebox.showwarning(
                "Token PAT Necessário",
                "Você ainda não configurou seu Personal Access Token (PAT) do Azure DevOps.\n\n"
                "Por favor, preencha o token na aba '⚙️ Configurações' antes de cadastrar."
            )
            self.tabview.set("⚙️ Configurações")
            self.cfg_pat.focus_set()
            return

        title = self.ent_title.get().strip()
        cliente = self.ent_cliente.get().strip()
        modulo = self.cmb_modulo.get().strip()
        erro = self.txt_erro.get("1.0", "end").strip()

        if not cliente:
            messagebox.showwarning("Campo Obrigatório", "Informe o nome do Cliente.")
            self.ent_cliente.focus_set()
            return

        if not erro:
            messagebox.showwarning("Campo Obrigatório", "Descreva o Erro / Demanda.")
            self.txt_erro.focus_set()
            return

        if not title:
            self._on_erro_key_release()
            title = self.ent_title.get().strip() or f"[{modulo}] {cliente}"

        project = self.cmb_project.get().strip() or "One_FrontEnd"
        wi_type = self.cmb_type.get().strip() or "Spike"
        tags = self.ent_tags.get().strip()
        area = self.ent_area.get().strip()
        iteration = self.ent_iteration.get().strip()
        noticed_raw = self.ent_noticed_at.get().strip()
        noticed_iso = self._parse_noticed_at_to_iso(noticed_raw)
        reported_by = self.ent_reported_by.get().strip()
        urgency = self.cmb_urgency.get().strip()

        _, description_html = self.build_description_content()
        extra_details_html = (
            f"<br><hr><div><b>Noticed At:</b> {noticed_raw}</div>"
            f"<div><b>Reported By:</b> {reported_by}</div>"
            f"<div><b>Urgency:</b> {urgency}</div>"
        )
        att_paths = [a["path"] for a in self.attachments]

        self.btn_submit.configure(state="disabled", text="⏳ Enviando para o DevOps...")
        self.lbl_feedback.configure(
            text=f"Cadastrando {wi_type} em {org}/{project}...",
            text_color="#ffaa73"
        )

        def worker():
            client = AzureDevOpsClient(org, pat)
            try:
                result = client.create_demand(
                    project=project,
                    work_item_type=wi_type,
                    title=title,
                    description_html=description_html,
                    tags=tags,
                    area_path=area,
                    iteration_path=iteration,
                    noticed_at_iso=noticed_iso,
                    reported_by=reported_by,
                    urgency=urgency,
                    attachment_paths=att_paths,
                    extra_details_in_desc=extra_details_html
                )

                result["cliente"] = cliente
                result["modulo"] = modulo

                def on_success():
                    self.btn_submit.configure(state="normal", text="🚀 Cadastrar no DevOps (Ctrl+Enter)")
                    self.history_data.insert(0, result)
                    save_json_file(HISTORY_FILE, self.history_data[:100])
                    self._render_history()

                    wi_id = result["id"]
                    wi_url = result["url"]

                    self.last_link_frame.grid()
                    self.ent_last_link.configure(state="normal")
                    self.ent_last_link.delete(0, "end")
                    self.ent_last_link.insert(0, wi_url)

                    self.lbl_feedback.configure(
                        text=f"✅ {wi_type} #{wi_id} cadastrado com sucesso!",
                        text_color="#89e09d"
                    )

                    self.clear_form(keep_feedback=True)
                    self._show_success_dialog(wi_type, wi_id, title, cliente, modulo, wi_url, project)

                self.after(0, on_success)

            except Exception as e:
                err_str = str(e)

                def on_error():
                    self.btn_submit.configure(state="normal", text="🚀 Cadastrar no DevOps (Ctrl+Enter)")
                    self.lbl_feedback.configure(
                        text=f"❌ Falha ao cadastrar: {err_str[:90]}",
                        text_color="#f1707b"
                    )
                    messagebox.showerror(
                        "Erro ao Cadastrar no DevOps",
                        f"Não foi possível criar a demanda:\n\n{err_str}"
                    )

                self.after(0, on_error)

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    # Verifica dependências antes de carregar CustomTkinter
    try:
        from check_dependencies import check_missing_packages, run_dependency_gui
        if check_missing_packages():
            ok = run_dependency_gui()
            if not ok:
                sys.exit(0)
    except Exception:
        pass

    app = DevOpsDemandasApp()
    app.mainloop()
