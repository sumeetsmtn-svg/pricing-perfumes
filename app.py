import streamlit as st
import asyncio
import os
import pandas as pd
import requests  # Para conectar con la API de Mercado Libre

# Instalación robusta de Playwright en la nube
@st.cache_resource
def install_playwright():
    os.system("python -m playwright install chromium")

install_playwright()

from playwright.async_api import async_playwright

st.set_page_config(page_title="Perfume Pricing Hub", page_icon="🛍️", layout="centered")
st.title("🛍️ Perfume Pricing Hub")
st.write("Escribe el nombre de un perfume para buscar el precio más bajo.")

async def scrape_mercadolibre(query: str):
    # API Oficial de Mercado Libre Chile (Estable, rápida y sin bloqueos)
    url = f"https://api.mercadolibre.com/sites/MLC/search?q={query}&limit=1"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('results'):
            primer_resultado = data['results'][0]
            title = primer_resultado['title']
            price_int = int(primer_resultado['price'])
            link = primer_resultado['permalink']
            
            return {"Marketplace": "Mercado Libre", "Producto": title, "Precio": price_int, "Link": link}
        else:
            return {"Marketplace": "Mercado Libre", "Producto": "No encontrado en ML", "Precio": float('inf'), "Link": ""}
            
    except Exception as e:
        error_corto = str(e)[:45]
        return {"Marketplace": "Mercado Libre", "Producto": f"Error API: {error_corto}", "Precio": float('inf'), "Link": ""}

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
        return {"Marketplace": "Falabella", "Producto": f"Error Anti-Bot: {error_corto}...", "Precio": float('inf'), "Link": url}

async def run_scrapers(query: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        results = await asyncio.gather(
            scrape_mercadolibre(query), # Lógica por API
            scrape_falabella(query, browser) # Lógica por Navegador
        )
        await browser.close()
        return results

query = st.text_input("Introduce el perfume a buscar:", placeholder="Ej: Aventus Creed")

if st.button("Buscar Precios", type="primary"):
    if query:
        with st.spinner("Buscando en tiempo real..."):
            data = asyncio.run(run_scrapers(query))
            df = pd.DataFrame(data)
            df = df.sort_values(by="Precio")
            df["Precio"] = df["Precio"].apply(lambda x: f"${x:,.0f}".replace(",", ".") if x != float('inf') else "No disponible")
            
            st.write("### Tabla de Posiciones:")
            st.dataframe(df, column_config={"Link": st.column_config.LinkColumn("Enlace al Producto")}, hide_index=True, use_container_width=True)
    else:
        st.warning("Por favor, escribe un perfume antes de buscar.")
