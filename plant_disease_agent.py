import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
from googletrans import Translator, LANGUAGES

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Plant Disease Prediction Agent",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS for Styling ---
st.markdown("""
<style>
    /* General Styles */
    .stApp {
        background-color: #f0f2f6;
    }
    /* Title */
    h1 {
        color: #00684A;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 2px solid #e0e0e0;
    }
    /* Buttons */
    .stButton>button {
        background-color: #008CBA;
        color: white;
        border-radius: 20px;
        border: none;
        padding: 10px 20px;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #005f73;
    }
    /* Expander */
    .st-expander {
        border: 1px solid #00684A;
        border-radius: 10px;
    }
    .st-expander header {
        background-color: #E6F2ED;
        color: #00684A;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- Gemini API and Translator Configuration ---

# Initialize session state variables
if 'gemini_response' not in st.session_state:
    st.session_state.gemini_response = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'selected_lang_code' not in st.session_state:
    st.session_state.selected_lang_code = 'en'
if 'selected_lang_name' not in st.session_state:
    st.session_state.selected_lang_name = 'English'


# Sidebar for API Key, Navigation, and Language Selection
with st.sidebar:
    st.title("🌿 AI Plant Agent")
    api_key = st.text_input("Enter your Google Gemini API Key", type="password", key="api_key_input")
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            st.success("API Key configured successfully!")
        except Exception as e:
            st.error(f"Failed to configure API Key: {e}")

    st.markdown("---")
    app_mode = st.radio(
        "Choose a feature",
        ["Disease Prediction", "Cure & Recommendations", "Gardening Q&A Chatbot"],
        key="app_mode_selection"
    )
    st.markdown("---")

    # --- Centralized Language Selector (Improved) ---
    st.header("Language Settings")
    # Create a dictionary of { 'English': 'en', 'French': 'fr', ... }
    lang_options = {name.capitalize(): code for name, code in LANGUAGES.items()}
    # Get the list of capitalized language names and sort them alphabetically
    sorted_lang_names = sorted(list(lang_options.keys()))
    # Find the index of 'English' in the sorted list to set it as the default
    try:
        default_index = sorted_lang_names.index('English')
    except ValueError:
        default_index = 0
    # The selectbox now displays the sorted, full language names
    selected_lang_name = st.selectbox(
        "Translate Output To:",
        sorted_lang_names, # Use the sorted list of full names
        index=default_index,
        key="lang_selector"
    )
    # Use the user's selection to find the corresponding code for the API
    st.session_state.selected_lang_code = lang_options[selected_lang_name]
    st.session_state.selected_lang_name = selected_lang_name
    
    st.markdown("---")
    st.info("This app uses AI for informational purposes only.")

# --- Helper Functions ---

def get_gemini_vision_response(image, prompt):
    """Sends an image and prompt to the Gemini Pro Vision model and returns the response."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content([prompt, image])
        # A more robust way to find and parse JSON
        json_text = response.text[response.text.find('{'):response.text.rfind('}')+1]
        return json.loads(json_text)
    except json.JSONDecodeError:
        st.error("Error: Could not decode the response from the AI. The AI may have returned a non-JSON response. Please try again with a clearer image.")
        return None
    except Exception as e:
        st.error(f"An error occurred while calling the Gemini API: {e}")
        return None

def translate_dictionary(data_dict, dest_lang):
    """Translates the string values of a dictionary to the destination language."""
    if not isinstance(data_dict, dict) or dest_lang == 'en':
        return {key.replace('_', ' ').title(): value for key, value in data_dict.items()}
    
    translator = Translator()
    try:
        translated_dict = {}
        for key, value in data_dict.items():
            translated_key = translator.translate(key.replace('_', ' ').title(), dest=dest_lang).text
            # Handle both string and list of strings
            if isinstance(value, list):
                translated_value = [translator.translate(str(item), dest=dest_lang).text for item in value]
            else:
                translated_value = translator.translate(str(value), dest=dest_lang).text
            translated_dict[translated_key] = translated_value
        return translated_dict
    except Exception as e:
        st.error(f"Translation failed: {e}")
        return {key.replace('_', ' ').title(): value for key, value in data_dict.items()} # Return original if fails

def translate_single_text(text, dest_lang):
    """Translates a single string of text."""
    if dest_lang == 'en' or not text:
        return text
    try:
        translator = Translator()
        return translator.translate(text, dest=dest_lang).text
    except Exception as e:
        st.warning(f"Could not translate text: {e}")
        return text # Return original if translation fails


# --- Main App Logic ---

# Page: Disease Prediction
if app_mode == "Disease Prediction":
    st.title("Plant Disease Prediction System")
    st.markdown("Upload an image of a plant leaf to identify potential diseases.")

    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        
        with col1:
            st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
            image = Image.open(uploaded_file)

        if st.button("Analyze Plant Health"):
            if not api_key:
                st.warning("Please enter your Gemini API Key in the sidebar to proceed.")
            else:
                with st.spinner("The AI is analyzing the image... Please wait."):
                    prompt = """
                    Analyze the provided image of a plant. First, identify the plant species.
                    Second, identify any visible diseases. Based on your analysis, provide a detailed report
                    in a structured JSON format. The JSON object must contain the following keys exactly:
                    'plant_name', 'disease_name', 'causes_of_disease', 'symptoms_of_disease', and 'cure_of_disease'.
                    If the plant appears healthy, the value for 'disease_name' should be 'Healthy', and other fields
                    can state that no actions are needed. Ensure the output is only the JSON object.
                    """
                    response_data = get_gemini_vision_response(image, prompt)
                    st.session_state.gemini_response = response_data

        if st.session_state.gemini_response:
            with col2:
                st.subheader("Analysis Result")
                
                with st.spinner(f"Translating to {st.session_state.selected_lang_name}..."):
                    display_data = translate_dictionary(st.session_state.gemini_response, st.session_state.selected_lang_code)

                if display_data:
                    for key, value in display_data.items():
                        st.markdown(f"**{key}:**")
                        # To handle list values gracefully
                        if isinstance(value, list):
                            for item in value:
                                st.markdown(f"- {item}")
                        else:
                            st.markdown(f"> {value}")

# Page: Cure & Recommendations
elif app_mode == "Cure & Recommendations":
    st.title("Cure and Recommendations")
    if st.session_state.gemini_response:
        
        # Translate the data before displaying
        with st.spinner(f"Loading recommendations in {st.session_state.selected_lang_name}..."):
            data = translate_dictionary(st.session_state.gemini_response, st.session_state.selected_lang_code)

        # Use translated keys for display
        plant_name_key = translate_single_text("Plant Name", st.session_state.selected_lang_code)
        disease_name_key = translate_single_text("Disease Name", st.session_state.selected_lang_code)
        symptoms_key = translate_single_text("Symptoms Of Disease", st.session_state.selected_lang_code)
        causes_key = translate_single_text("Causes Of Disease", st.session_state.selected_lang_code)
        cure_key = translate_single_text("Cure Of Disease", st.session_state.selected_lang_code)

        st.header(f"🌿 {translate_single_text('Recommendations for', st.session_state.selected_lang_code)} {data.get(plant_name_key, 'your plant')}")
        
        with st.expander(translate_single_text("Disease Identified", st.session_state.selected_lang_code), expanded=True):
            st.markdown(f"**{disease_name_key}:** `{data.get(disease_name_key, 'N/A')}`")

        with st.expander(translate_single_text("Symptoms to Watch For", st.session_state.selected_lang_code), expanded=True):
            st.markdown(data.get(symptoms_key, 'No symptoms provided.'))

        with st.expander(translate_single_text("Causes", st.session_state.selected_lang_code), expanded=True):
            st.markdown(data.get(causes_key, 'No causes provided.'))

        st.subheader(f"✅ {translate_single_text('Recommended Cure and Actions', st.session_state.selected_lang_code)}")
        st.info(data.get(cure_key, 'No cure information available.'))
        
    else:
        st.warning("Please analyze a plant image on the 'Disease Prediction' page first.")
        st.image("https://placehold.co/600x300/E6F2ED/00684A?text=No+Analysis+Data", use_column_width=True)


# Page: Gardening Q&A Chatbot
elif app_mode == "Gardening Q&A Chatbot":
    st.title("Gardening Q&A Chatbot")
    st.markdown("Ask me anything about plant care, diseases, or general gardening!")
    
    if not api_key:
        st.warning("Please enter your Gemini API Key in the sidebar to enable the chatbot.")
    else:
        # Initialize the model and chat history
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        chat = model.start_chat(history=st.session_state.chat_history)
        
        # Display chat history (translating on the fly)
        for message in chat.history:
            role = "human" if message.role == "user" else "ai"
            with st.chat_message(role):
                text_to_display = message.parts[0].text
                # Only translate AI messages for display
                if role == 'ai':
                    text_to_display = translate_single_text(text_to_display, st.session_state.selected_lang_code)
                st.markdown(text_to_display)

        # Get user input
        user_prompt = st.chat_input("Your question...")
        if user_prompt:
            # Add user message to chat and display
            with st.chat_message("human"):
                st.markdown(user_prompt)
            
            # Send to Gemini and get response
            try:
                response = chat.send_message(user_prompt)
                with st.chat_message("ai"):
                    with st.spinner(f"Translating response to {st.session_state.selected_lang_name}..."):
                        translated_response = translate_single_text(response.text, st.session_state.selected_lang_code)
                    st.markdown(translated_response)
                # Update session state history (always store original English)
                st.session_state.chat_history = chat.history
            except Exception as e:
                st.error(f"Failed to get response from chatbot: {e}")