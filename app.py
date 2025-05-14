import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from openai import OpenAI
import os

# Use the secure API key from Streamlit Secrets
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

st.set_page_config(page_title="Weidert AI Client Research Tool", page_icon="🧠")

# Clean branded header
st.markdown(
    """
    <div style='text-align: center; padding-top: 10px; padding-bottom: 10px;'>
        <img src='https://github.com/raianrith/AI-Client-Research-Tool/blob/main/Weidert_Logo_primary-logomark-antique.png?raw=true' width='100' style='margin-bottom: 10px;' />
        <h1 style='font-size: 2.4em; margin-bottom: 0;'>Weidert AI Client Research Tool</h1>
        <h3 style='color: gray; margin-top: 4px;'>(The WACR Tool)</h3>
        <p style='margin-top: 10px; font-size: 1.05em;'>Analyze any company website using AI based on your role.</p>
    </div>
    """,
    unsafe_allow_html=True
)


# User input fields
url = st.text_input("🔗 Enter the company website URL:")
role = st.selectbox("🎯 Select your role:", ["Strategist", "Business Development", "Client Success Manager"])

# Helper Functions
def scrape_page(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        text = ' '.join([p.get_text(strip=True) for p in soup.find_all(['p', 'h1', 'h2', 'li'])])
        return soup.title.string if soup.title else "", text, res.text
    except Exception as e:
        return "", f"Error scraping {url}: {e}", ""

def find_related_page(base_url, keyword):
    try:
        soup = BeautifulSoup(requests.get(base_url).text, "html.parser")
        for link in soup.find_all("a", href=True):
            if keyword in link.text.lower() or keyword in link['href'].lower():
                return urljoin(base_url, link['href'])
    except:
        pass
    return None

def extract_people_info(html):
    soup = BeautifulSoup(html, "html.parser")
    people = []
    for section in soup.find_all(['div', 'section'], class_=re.compile("(team|leader|person|staff)", re.I)):
        text = section.get_text(separator=' ', strip=True)
        found = re.findall(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2})\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', text)
        for name, title in found:
            people.append(f"{name} – {title}")
    fallback = re.findall(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,2})\s+(CEO|President|VP|Vice President|CMO|Marketing Director|Sales Director)', html, re.I)
    for name, title in fallback:
        people.append(f"{name} – {title}")
    return list(set(people))

def get_role_prompt(role):
    if role == "Strategist":
        return """
You are a strategist evaluating this company based on its website. Focus on:

1. Market positioning and branding
2. Competitor differentiators
3. Business model (B2B/B2C, pricing hints)
4. Innovation or unique selling points
5. Long-term growth opportunities
"""
    elif role == "Business Development":
        return """
You're a Business Development (BD) professional evaluating this company. Focus on:

Provide a comprehensive bullet-point report including:
1. What the company does
2. Products or services offered
3. Who do they sell to (buyer personas, industries, roles)?
4. About and mission
5. Key differentiators and value propositions
6. Contact info, HQ location (if visible)
7. Social or partner links
8. Key team members with titles (CEO, VP, Marketing/Sales heads)
9. High-level marketing, SEO, or messaging observations
10. Provide a positioning statement in the following format: 
    i ) To: (Target Audience)
    ii) We are the brand of: 
    iii) That: 
    iv) So that you feel: 
    v) That's because unlike:
    vi) We:
11. What is the companys comp advantage
12. What are the primary messaging themes on the site
13. Describe their brand personality and ton
"""
    elif role == "Client Success Manager":
        return """
You're a Client Success Manager evaluating this company. Focus on:

1. Client onboarding process hints
2. Support or resource offerings (FAQ, knowledge base)
3. Key team members who interact with clients
4. Customer success language or case studies
5. Retention, loyalty, or satisfaction messaging
"""
    return "# Unknown role"

# Main app logic
if st.button("🚀 Generate AI Report") and url:
    with st.spinner("Scraping and analyzing the website..."):

        # Scrape pages
        home_title, home_text, _ = scrape_page(url)
        about_url = find_related_page(url, "about")
        services_url = find_related_page(url, "services")

        about_title, about_text, about_html = scrape_page(about_url) if about_url else ("", "", "")
        services_title, services_text, _ = scrape_page(services_url) if services_url else ("", "", "")
        people_info = extract_people_info(about_html)
        people_text = "\n".join(people_info) if people_info else "No team info found."

        # Full website content
        full_text = f"""
Title: {home_title}

--- Home Page ---
{home_text}

--- About Page ({about_url}) ---
{about_text}

--- Services Page ({services_url}) ---
{services_text}

--- Team Info ---
{people_text}
"""

        # Prompt for OpenAI
        role_prompt = get_role_prompt(role)
        prompt = f"""
You're analyzing a company based on its website.

{full_text[:1200000]}

{role_prompt}
"""

        # OpenAI API Call
        try:
            completion = client.chat.completions.create(
                model="o3",
                messages=[{"role": "user", "content": prompt}]
            )
            report = completion.choices[0].message.content
            st.success("✅ Report generated!")
            st.markdown("### 📄 AI-Powered Insights")
            st.markdown(report)
        except Exception as e:
            st.error(f"❌ Error calling OpenAI API: {e}")
