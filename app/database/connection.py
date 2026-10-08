# app/database/connection.py

import streamlit as st
from sqlalchemy import create_engine, text

def get_engine():
    DATABASE_URL = st.secrets["database"]["url"]
    
    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        connect_args={"sslmode": "require"}
    )

def test_connection():
    engine = get_engine()

    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT version()")
        )
        return result.scalar()