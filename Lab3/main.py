
import os
import asyncio
import httpx
import tkinter as tk
from tkinter import scrolledtext
from concurrent.futures import ThreadPoolExecutor

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"


# Функция для получения координат города через Nominatim API (геокодирование)
async def get_coordinates(city: str):
    geocode_url = f"https://nominatim.openstreetmap.org/search?city={city}&format=json"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(geocode_url)
            if response.status_code == 200:
                data = response.json()
                if data:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    return lat, lon
                else:
                    return None, None
            else:
                return None, None
        except httpx.RequestError as e:
            return None, None


# Функция для получения прогноза погоды с Open-Meteo API по коородинатам
async def get_weather_by_coordinates(lat, lon):
    url = f"{OPEN_METEO_API_URL}?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation_probability,weather_code"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                temperature = data['hourly']['temperature_2m'][0]
                precipitation_prob = data['hourly']['precipitation_probability'][0]
                
                return (f"Температура: {temperature}°C\n"
                        f"Вероятность осадков: {precipitation_prob}%\n")
            else:
                return f"Ошибка: {response.status_code} - {response.text}"
        except httpx.RequestError as e:
            return f"Ошибка соединения: {e}"


# Функция для получения прогноза погоды по введенному городу
async def show_weather_for_city(city: str):
    lat, lon = await get_coordinates(city)
    if lat is None or lon is None:
        return "Город не найден или ошибка при получении координат."
    else:
        return await get_weather_by_coordinates(lat, lon)


# Функция для получения ответа от Mistral AI
async def get_chat_response(user_message: str):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}"}
    payload = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": user_message}]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"Ошибка: {response.status_code} - {response.text}"
        except httpx.RequestError as e:
            return f"Ошибка соединения: {e}"


# Функция, которая обрабатывает нажатие кнопки Send
def clicked_send_btn():
    user_input = input_panel.get().strip()
    if user_input == "":
        return
    
    dialog_panel.config(state=tk.NORMAL)
    dialog_panel.insert(tk.END, f"Вы: {user_input}\n\n")
    dialog_panel.config(state=tk.DISABLED)
    
    input_panel.delete(0, tk.END)
    
    executor.submit(asyncio.run, ai_response(user_input))


# Функция для обработки нажатия кнопки Wheather
async def show_weather():
    city = input_panel.get().strip()
    if city:
        weather = await show_weather_for_city(city)
    else:
        weather = "Введите город для получения прогноза погоды."
    
    dialog_panel.config(state=tk.NORMAL)
    dialog_panel.insert(tk.END, f"Погода для {city}:\n{weather}\n")
    dialog_panel.config(state=tk.DISABLED)
    dialog_panel.yview(tk.END)
    
    input_panel.delete(0, tk.END)
    

async def ai_response(user_input):
    response = await get_chat_response(user_input)
    
    dialog_panel.config(state=tk.NORMAL)
    dialog_panel.insert(tk.END, f"Mistral: {response}\n\n")
    dialog_panel.config(state=tk.DISABLED)
    dialog_panel.yview(tk.END)


window = tk.Tk()
window.geometry('700x500')
window.title("Чат с MistralAI")


dialog_panel = scrolledtext.ScrolledText(window, width=82, height=30)
dialog_panel.config(state=tk.DISABLED)
dialog_panel.pack(padx=10, pady=2, fill=tk.BOTH, expand=True)


input_panel = tk.Entry(window, width=50)
input_panel.pack(padx=10, pady=2, fill=tk.X, side=tk.LEFT)
input_panel.focus()

btn = tk.Button(window, text="Send", command=clicked_send_btn)
btn.pack(padx=10, pady=10, side=tk.LEFT)


weather_btn = tk.Button(window, text="Weather", command=lambda: executor.submit(asyncio.run, show_weather()))
weather_btn.pack(padx=10, pady=10, side=tk.LEFT)


executor = ThreadPoolExecutor()

window.mainloop()
