"""Navegador Playwright com perfil persistente (login do Mercado Livre salvo em disco)."""

from pathlib import Path

from playwright.sync_api import sync_playwright

PROFILE_DIR = Path(__file__).resolve().parent.parent / ".browser-profile"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/158.0.0.0 Safari/537.36"
)


def open_context(pw, headless=True):
    """Abre o Chromium usando o perfil salvo. Retorna o BrowserContext."""
    PROFILE_DIR.mkdir(exist_ok=True)
    return pw.chromium.launch_persistent_context(
        str(PROFILE_DIR),
        headless=headless,
        user_agent=UA,
        locale="pt-BR",
        viewport={"width": 1366, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )


def login():
    """Abre o navegador visível para o usuário fazer login. Termina quando a janela é fechada."""
    with sync_playwright() as pw:
        ctx = open_context(pw, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.mercadolivre.com.br/")
        print("Faça login no Mercado Livre na janela aberta e depois FECHE a janela.")
        page.wait_for_event("close", timeout=0)
        ctx.close()
        print("Perfil salvo em", PROFILE_DIR)


if __name__ == "__main__":
    login()
