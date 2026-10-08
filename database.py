
# database.py

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base


Base = declarative_base()

@st.cache_resource
def get_engine():
    database_url = st.secrets["database"]["url"]

    return create_engine(
        database_url,
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
