import streamlit as st
from st_image_button import st_image_button

# Add some test code to play with the component while it's in development.
# During development, we can run this just as we would any other Streamlit
# app: `$ streamlit run my_component/example.py`

st.subheader("Component with constant args")

num_clicks = st_image_button("Test", "icon.png")

