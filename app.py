import streamlit as st
import asyncio
import os
from playwright.async_api import async_playwright
import pandas as pd

# Instalación robusta del navegador
@st.cache_resource
def install_playwright():
    os.system("python -m playwright install chromium")

install_playwright()

st.set_page_config(page_title="Perfume Pricing Hub", page_icon="🛍️", layout="centered")
st.title("🛍️ Perfume Pricing Hub")
st.write("Escribe el nombre de un perfume para buscar el precio más bajo.")

async def scrape_mercadolibre(query: str, browser):
    search_query = query.replace(" ", "-")
    url = f"https://listado.mercadolibre.cl/{search_query}"
    
    # Camuflaje también para Mercado Libre
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    
    try:
        # Aumentamos el tiempo a 20 segundos por si la nube está lenta
        await page.goto(url, timeout=20000)
        # Selectores más amplios por si Mercado Libre cambió el diseño
        await page.wait_for_selector('.ui-search-layout__item, .ui-search-result__wrapper', timeout=10000)
        
        title = await page.locator('.ui-search-item__title').first.inner_text()
        price_text = await page.locator('.andes-money-amount__fraction').first.inner_text()
        link = await page.locator('.ui-search-link').first.get_attribute('href')
        
        price_int = int(price_text.replace(".", "").strip())
        await context.close()
        return {"Marketplace": "Mercado Libre", "Producto": title, "Precio": price_int, "Link": link}
    
    except Exception as e:
        await context.close()
        # Capturamos el error real para saber qué está fallando
        error_corto = str(e).split('\n')[0][:45] 
        return {"Marketplace": "Mercado Libre", "Producto": f"Error: {error_corto}...", "Precio": float('inf'), "Link": url}

async def scrape_falabella(query: str, browser):
    search_query = query.replace(" ", "%20")
    url = f"https://www.falabella.com/falabella-cl/search?Ntt={search_query}"
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    
    try:
        await page.goto(url, timeout=20000)
        await page.wait_for_selector('div[id^="testId-searchResults-products"]', timeout=10000)
        
        title = await page.locator('b[class^="pod-subTitle"]').first.inner_text()
        price_text = await page.locator('ol li div[class^="copy10"]').first.inner_text()
        
        price_clean = price_text.replace("$", "").replace(".", "").strip()
        price_int = int(price_clean)
        
        await context.close()
        return {"Marketplace": "Falabella", "Producto": title, "Precio": price_int, "Link": url}
        
    except Exception as e:
        await context.close()
        error_corto = str(e).split('\n')[0][:45]
        return {"Marketplace": "Falabella", "Producto": f"Error: {error_corto}...", "Precio": float('inf'), "Link": url}

async def run_scrapers(query: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        results = await asyncio.gather(
            scrape_mercadolibre(query, browser),
            scrape_falabella(query, browser)
        )
        await browser.close()
        return results

query = st.text_input("Introduce el perfume a buscar:", placeholder="Ej: Aventus Creed")

if st.button("Buscar Precios", type="primary"):
    if query:
        with st.spinner("Buscando en la nube y evadiendo bloqueos..."):
            data = asyncio.run(run_scrapers(query))
            df = pd.DataFrame(data)
            df = df.sort_values(by="Precio")
            df["Precio"] = df["Precio"].apply(lambda x: f"${x:,.0f}".replace(",", ".") if x != float('inf') else "No disponible")
            
            st.write("### Tabla de Posiciones:")
            st.dataframe(df, column_config={"Link": st.column_config.LinkColumn("Enlace al Producto")}, hide_index=True, use_container_width=True)
