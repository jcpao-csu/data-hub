import streamlit as st
import cloudinary

config = cloudinary.config(
    cloud_name = st.secrets["cloudinary"]["CLOUD_NAME"], 
    api_key = st.secrets["cloudinary"]["API_KEY"],
    api_secret = st.secrets["cloudinary"]["API_SECRET"],
    secure = True
)

import cloudinary.uploader
import cloudinary.api
import time
from pathlib import Path 

# Define load_asset() 
def load_asset(public_id):
    """Loads asset from Cloudinary with the provided public ID; returns asset src URL that can be read into st.image()/st.markdown()"""
    return cloudinary.CloudinaryImage(public_id).build_url()