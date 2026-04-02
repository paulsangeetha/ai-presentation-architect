import streamlit as st
import requests
import json
import io
import re
from pptx import Presentation

# --- CONFIG ---
st.set_page_config(page_title="AI Presentation Architect", layout="wide")

CHAT_API_URL = "https://api.sarvam.ai/v1/chat/completions"
TRANSLATE_API_URL = "https://api.sarvam.ai/translate"

SUPPORTED_LANGUAGES = {
    'en-IN': 'English',
    'hi-IN': 'Hindi',
    'ta-IN': 'Tamil',
    'te-IN': 'Telugu',
    'bn-IN': 'Bengali',
    'kn-IN': 'Kannada',
    'mr-IN': 'Marathi',
    'gu-IN': 'Gujarati'
}

# --- JSON CLEANER ---
def extract_json(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    match = re.search(r"```json(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return match.group(0).strip()

    raise ValueError("No valid JSON found")

# --- GENERATE ---
def generate_english_presentation(topic, api_key, slide_count):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    Generate a {slide_count}-slide presentation on '{topic}'.

    STRICT RULES:
    - Output ONLY valid JSON
    - No explanation
    - Format:
    [
      {{"title": "...", "content": "..."}}
    ]
    """

    payload = {
        "model": "sarvam-m",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(CHAT_API_URL, headers=headers, json=payload)
    response.raise_for_status()

    response_text = response.json()["choices"][0]["message"]["content"]

    clean_text = extract_json(response_text)

    return json.loads(clean_text)

# --- TRANSLATE ---
def translate_content(text, target_lang, api_key):
    if target_lang == "en-IN":
        return text

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "input": text,
        "source_language_code": "en-IN",
        "target_language_code": target_lang
    }

    response = requests.post(TRANSLATE_API_URL, headers=headers, json=payload)
    response.raise_for_status()

    return response.json()["translated_text"]

# --- PPT CREATOR ---
def create_ppt(slides, topic, lang_name):
    prs = Presentation()

    # Title slide
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    slide.shapes.title.text = topic
    slide.placeholders[1].text = f"Generated in {lang_name}"

    # Content slides
    for s in slides:
        slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = s['title']
        slide.placeholders[1].text = s['content']

    ppt_stream = io.BytesIO()
    prs.save(ppt_stream)
    ppt_stream.seek(0)

    return ppt_stream

# --- UI ---
st.title("🤖 Multilingual AI Presentation Generator")

api_key = st.text_input("Enter Sarvam API Key", type="password")
topic = st.text_input("Enter Topic")
language = st.selectbox("Select Language", list(SUPPORTED_LANGUAGES.keys()),
                       format_func=lambda x: SUPPORTED_LANGUAGES[x])
slide_count = st.slider("Number of Slides", 2, 10, 5)

if st.button("Generate Presentation"):

    if not api_key or not topic:
        st.warning("Please enter API key and topic")
    else:
        with st.spinner("Generating presentation..."):

            try:
                # Step 1: Generate
                st.info("Generating content...")
                slides = generate_english_presentation(topic, api_key, slide_count)

                # Step 2: Translate
                st.info("Translating...")
                translated_slides = [
                    {
                        "title": translate_content(s["title"], language, api_key),
                        "content": translate_content(s["content"], language, api_key)
                    }
                    for s in slides
                ]

                translated_topic = translate_content(topic, language, api_key)

                # Step 3: Create PPT
                st.info("Creating PPT...")
                ppt_file = create_ppt(
                    translated_slides,
                    translated_topic,
                    SUPPORTED_LANGUAGES[language]
                )

                # Step 4: Download
                st.success("Done!")
                st.download_button(
                    label="Download PPT",
                    data=ppt_file,
                    file_name=f"{topic}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )

            except Exception as e:
                st.error(f"Error: {e}")