import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import base64
import requests
from streamlit_option_menu import option_menu

load_dotenv()
client = OpenAI()

st.set_page_config(layout="wide")

def get_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode()
        
pikachu = get_base64("pikachu-transparent-32599.png")
gengar = get_base64("Gengar-PNG-Picture.png")


st.markdown(
    f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-color: black;
        background-image:
            url("data:image/png;base64,{pikachu}"),
            url("data:image/png;base64,{gengar}"),
            url("data:image/png;base64,{pikachu}"),
            url("data:image/png;base64,{gengar}");
        background-repeat: no-repeat, no-repeat, no-repeat, no-repeat;
        background-size: 150px, 200px, 180px, 220px;
        background-position: 
            5% 10%,
            80% 20%,
            30% 70%,
            90% 80%;
    }}
    
    /* Make the card image fit without scrolling */
    [data-testid="stImage"] img {{
        max-height: 70vh;
        width: auto !important;
        object-fit: contain;
    }}
    </style>
    """,
    unsafe_allow_html=True
)
site_choise = option_menu( "Pokemon Menu", ["Card Finder", "Trade Decider"] )

if site_choise == "Card Finder":
    col1, col2 = st.columns(2)

    with col1:
        st.header("Pokémon Card Finder")
        card_name = st.text_input("Card Name", "")

    if st.button("Find Card") and card_name:
        prompt = f"""
        You are a Pokémon TCG expert.
        Given a possibly misspelled or incomplete Pokémon card name,
        return ONLY the official Pokémon name (without set names or card numbers).
        Example: 'charzard vmax' → 'Charizard VMAX', 'pickachu V' → 'Pikachu V, rakwaza -> Rayquaza'
        The input is: {card_name} reply with ONLY the official Pokémon name (without set names or card numbers)., and other text
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )

        official_name = response.choices[0].message.content.strip()
        
        st.write(f"Searching for: {official_name}")
        
        # Use TCGdex API - search for cards
        api_url = f"https://api.tcgdex.net/v2/en/cards?name={official_name}"
        
        try:
            api_response = requests.get(api_url, timeout=10)
            
            if api_response.status_code == 200:
                cards = api_response.json()
                
                if cards and isinstance(cards, list) and len(cards) > 0:
                    # Get the first card
                    card = cards[0]
                    
                    if isinstance(card, dict):
                        # Get high-res image
                        card_id = card.get('id')
                        
                        if card_id:
                            card_image_url = f"https://api.tcgdex.net/v2/en/cards/{card_id}"
                            card_detail_response = requests.get(card_image_url, timeout=10)
                            
                            if card_detail_response.status_code == 200:
                                card_detail = card_detail_response.json()
                                
                                if isinstance(card_detail, dict):
                                    with col1:
                                        # Get the base image path and add quality/extension
                                        base_image_url = card_detail.get('image')
                                        
                                        if base_image_url:
                                            # Add /high.webp for high quality image
                                            # TCGdex format: base_url + /quality.format
                                            image_url = f"{base_image_url}/high.webp"
                                            st.image(image_url, use_container_width=False)
                                        else:
                                            st.error("Image URL not found in card data")
                                    
                                    # Generate description
                                    card_full_name = card_detail.get('name', official_name)
                                    desc_prompt = f"Write a description of the Pokémon card '{card_full_name}'. include stats, types, rareness, and abilities."
                                    desc_response = client.chat.completions.create(
                                        model="gpt-4o-mini",
                                        messages=[{"role": "user", "content": desc_prompt}]
                                    )
                                    
                                    with col2:
                                        st.markdown(f"### {card_full_name}")
                                        st.write(desc_response.choices[0].message.content)
                                        
                                        # Show card info
                                        if 'set' in card_detail and isinstance(card_detail['set'], dict):
                                            st.write(f"**Set:** {card_detail['set'].get('name', 'Unknown')}")
                                        if 'rarity' in card_detail:
                                            st.write(f"**Rarity:** {card_detail['rarity']}")
                                else:
                                    st.error("Invalid card detail response")
                            else:
                                st.error(f"Failed to fetch card details: {card_detail_response.status_code}")
                        else:
                            st.error("Card ID not found")
                    else:
                        st.error("Invalid card data format")
                else:
                    st.warning(f"No card found with the name '{official_name}'. Try a different search term.")
                    
            elif api_response.status_code == 404:
                st.warning(f"Card '{official_name}' not found. Try a different name.")
            else:
                st.error(f"API error: {api_response.status_code}")
                
        except requests.exceptions.Timeout:
            st.warning("⏳ Request timed out. Please try again.")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Network error: {str(e)}")
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")

if site_choise == "Trade Decider":
    st.title("Trade Decider")
st.write("Compare two Pokémon cards and get an AI-powered trade fairness analysis!")

col1, col2 = st.columns(2)

with col1:
    st.header("Card 1")
    card_name_1 = st.text_input("First Card Name", "", key="card1")

with col2:
    st.header(" Card 2")
    card_name_2 = st.text_input("Second Card Name", "", key="card2")

def get_card_data(card_name):
    """Fetch card data from TCGdex API"""
    if not card_name:
        return None
    
    prompt = f"""
    You are a Pokémon TCG expert.
    Given a possibly misspelled or incomplete Pokémon card name,
    return ONLY the official Pokémon name (without set names or card numbers).
    Example: 'charzard vmax' → 'Charizard VMAX', 'pickachu V' → 'Pikachu V, rakwaza -> Rayquaza'
    The input is: {card_name}
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    official_name = response.choices[0].message.content.strip()
    
    # Use TCGdex API - search for cards
    api_url = f"https://api.tcgdex.net/v2/en/cards?name={official_name}"
    
    try:
        api_response = requests.get(api_url, timeout=10)
        
        if api_response.status_code == 200:
            cards = api_response.json()
            
            if cards and isinstance(cards, list) and len(cards) > 0:
                card = cards[0]
                
                if isinstance(card, dict):
                    card_id = card.get('id')
                    
                    if card_id:
                        card_image_url = f"https://api.tcgdex.net/v2/en/cards/{card_id}"
                        card_detail_response = requests.get(card_image_url, timeout=10)
                        
                        if card_detail_response.status_code == 200:
                            card_detail = card_detail_response.json()
                            
                            if isinstance(card_detail, dict):
                                base_image_url = card_detail.get('image')
                                
                                if base_image_url:
                                    image_url = f"{base_image_url}/high.webp"
                                    
                                    return {
                                        'name': card_detail.get('name', official_name),
                                        'image_url': image_url,
                                        'set': card_detail.get('set', {}).get('name', 'Unknown'),
                                        'rarity': card_detail.get('rarity', 'Unknown'),
                                        'hp': card_detail.get('hp', 'N/A'),
                                        'types': card_detail.get('types', []),
                                        'attacks': card_detail.get('attacks', []),
                                        'retreat': card_detail.get('retreatCost', []),
                                        'card_detail': card_detail
                                    }
        return None
    except Exception as e:
        st.error(f"Error fetching card: {str(e)}")
        return None

if st.button("Analyze Trade", use_container_width=True):
    if not card_name_1 or not card_name_2:
        st.warning("Please enter both card names!")
    else:
        with st.spinner("Fetching card data..."):
            card1_data = get_card_data(card_name_1)
            card2_data = get_card_data(card_name_2)
        
        if not card1_data:
            st.error(f"❌ Could not find card: {card_name_1}")
        if not card2_data:
            st.error(f"❌ Could not find card: {card_name_2}")
        
        if card1_data and card2_data:
            # Display cards side by side
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader(f"🔵 {card1_data['name']}")
                st.image(card1_data['image_url'], use_container_width=False)
                st.write(f"**Set:** {card1_data['set']}")
                st.write(f"**Rarity:** {card1_data['rarity']}")
                st.write(f"**HP:** {card1_data['hp']}")
                if card1_data['types']:
                    st.write(f"**Type:** {', '.join(card1_data['types'])}")
            
            with col2:
                st.subheader(f"🔴 {card2_data['name']}")
                st.image(card2_data['image_url'], use_container_width=False)
                st.write(f"**Set:** {card2_data['set']}")
                st.write(f"**Rarity:** {card2_data['rarity']}")
                st.write(f"**HP:** {card2_data['hp']}")
                if card2_data['types']:
                    st.write(f"**Type:** {', '.join(card2_data['types'])}")
            
            st.divider()
            
            # AI Analysis
            with st.spinner("AI is analyzing the trade..."):
                analysis_prompt = f"""
                You are a Pokémon Trading Card Game expert and trade analyst. 
                
                Compare these two cards and provide a comprehensive trade analysis:
                
                Card 1: {card1_data['name']}
                - Set: {card1_data['set']}
                - Rarity: {card1_data['rarity']}
                - HP: {card1_data['hp']}
                - Types: {', '.join(card1_data['types']) if card1_data['types'] else 'N/A'}
                
                Card 2: {card2_data['name']}
                - Set: {card2_data['set']}
                - Rarity: {card2_data['rarity']}
                - HP: {card2_data['hp']}
                - Types: {', '.join(card2_data['types']) if card2_data['types'] else 'N/A'}
                
                Provide your analysis in the following format:
                
                1. **Trade Verdict**: Is this a fair trade? (Fair Trade / Favors Card 1 / Favors Card 2)
                
                2. **Rarity & Collectibility Analysis**: Compare the rarity, set, and collectibility value of both cards.
                
                3. **Gameplay Value**: Compare the competitive playability and strategic value of both cards.
                
                4. **Market Value Estimation**: Provide a rough estimate of which card is likely more valuable in the current market.
                
                5. **Recommendation**: Should this trade be accepted? Provide clear reasoning.
                
                Be specific, detailed, and fair in your assessment.
                """
                
                analysis_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": analysis_prompt}]
                )
                
                st.header("🤖 AI Trade Analysis")
                st.markdown(analysis_response.choices[0].message.content)
