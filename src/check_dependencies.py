import sys
import subprocess
import os

REQUIRED_PACKAGES = [
    ("customtkinter", "customtkinter>=6.0.0"),
    ("PIL", "pillow>=10.0.0"),
    ("requests", "requests>=2.31.0")
]


def check_missing_packages():
    """Retorna lista de pacotes que não estão instalados."""
    missing = []
    for module_name, install_spec in REQUIRED_PACKAGES:
        try:
            __import__(module_name)
        except ImportError:
            missing.append((module_name, install_spec))
    return missing


def install_packages(packages_to_install, callback=None):
    """Instala os pacotes fornecidos via python -m pip install."""
    specs = [spec for _, spec in packages_to_install]
    cmd = [sys.executable, "-m", "pip", "install"] + specs
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        if callback:
            for line in proc.stdout:
                callback(line)
        proc.wait()
        return proc.returncode == 0
    except Exception as e:
        if callback:
            callback(f"Erro ao executar pip: {e}\n")
        return False


def run_dependency_gui():
    """Janela visual nativa (usando tkinter que vem com Python) caso falte dependência."""
    missing = check_missing_packages()
    if not missing:
        return True  # Todas as dependências já estão instaladas

    import tkinter as tk
    from tkinter import ttk, messagebox
    import threading

    root = tk.Tk()
    root.title("Verificação de Dependências - Azure DevOps App")
    root.geometry("540x360")
    root.resizable(False, False)
    root.configure(bg="#1e1e1e")

    # Centraliza janela
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - 270
    y = (root.winfo_screenheight() // 2) - 180
    root.geometry(f"+{max(0, x)}+{max(0, y)}")

    result = {"success": False}

    # Cabeçalho
    lbl_title = tk.Label(
        root,
        text="⚠️ Dependências Necessárias Ausentes",
        font=("Segoe UI", 14, "bold"),
        fg="#ffaa73",
        bg="#1e1e1e"
    )
    lbl_title.pack(anchor="w", padx=20, pady=(18, 6))

    missing_names = ", ".join([spec for _, spec in missing])
    lbl_desc = tk.Label(
        root,
        text=f"O programa precisa dos seguintes pacotes Python para funcionar:\n\n• {missing_names}\n\nDeseja que o programa baixe e instale automaticamente agora?",
        font=("Segoe UI", 11),
        fg="#e1dfdd",
        bg="#1e1e1e",
        justify="left"
    )
    lbl_desc.pack(anchor="w", padx=20, pady=(0, 12))

    # Console de log
    txt_log = tk.Text(
        root,
        height=7,
        bg="#121212",
        fg="#89e09d",
        font=("Consolas", 10),
        relief="flat"
    )
    txt_log.pack(fill="x", padx=20, pady=(0, 14))
    txt_log.insert("end", "Aguardando confirmação para iniciar instalação...\n")
    txt_log.configure(state="disabled")

    btn_frame = tk.Frame(root, bg="#1e1e1e")
    btn_frame.pack(fill="x", padx=20, pady=(0, 16))

    def log(msg):
        def _update():
            txt_log.configure(state="normal")
            txt_log.insert("end", msg)
            txt_log.see("end")
            txt_log.configure(state="disabled")
        root.after(0, _update)

    def start_install():
        btn_install.configure(state="disabled", text="⏳ Baixando e Instalando...")
        btn_cancel.configure(state="disabled")

        def worker():
            log("\nIniciando 'pip install' em segundo plano...\n")
            ok = install_packages(missing, callback=log)
            if ok:
                log("\n✅ Todas as dependências foram instaladas com sucesso!\nIniciando o aplicativo...\n")
                result["success"] = True
                root.after(1200, root.destroy)
            else:
                log("\n❌ Falha ao instalar automaticamente.\nExecute manualmente: pip install -r requirements.txt\n")
                def on_fail():
                    btn_install.configure(state="normal", text="Tentar Novamente")
                    btn_cancel.configure(state="normal")
                root.after(0, on_fail)

        threading.Thread(target=worker, daemon=True).start()

    btn_install = tk.Button(
        btn_frame,
        text="⬇️ Baixar e Instalar Automaticamente",
        font=("Segoe UI", 11, "bold"),
        bg="#0078d4",
        fg="#ffffff",
        activebackground="#106ebe",
        activeforeground="#ffffff",
        relief="flat",
        padx=14,
        pady=6,
        command=start_install
    )
    btn_install.pack(side="left")

    btn_cancel = tk.Button(
        btn_frame,
        text="Cancelar e Sair",
        font=("Segoe UI", 10),
        bg="#323130",
        fg="#cccccc",
        activebackground="#484644",
        activeforeground="#ffffff",
        relief="flat",
        padx=12,
        pady=6,
        command=root.destroy
    )
    btn_cancel.pack(side="right")

    root.mainloop()
    return result["success"]


if __name__ == "__main__":
    ok = run_dependency_gui()
    if ok:
        print("Todas as dependências estão prontas!")
    else:
        print("Instalação de dependências cancelada ou falhou.")
