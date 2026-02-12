import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, inspect
import requests
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")



def connect_db(host, user, password, port, database):
    engine = create_engine(
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    )
    return engine



def get_schema(engine):
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    schema = ""
    for table in tables:
        columns = inspector.get_columns(table)
        schema += f"\nTable: {table}\n"
        for col in columns:
            schema += f"- {col['name']} ({col['type']})\n"

    return schema


def generate_sql(prompt, schema):

    full_prompt = f"""
    You are a professional MySQL expert.

    STRICT RULES:
    1. Only use tables and columns provided in schema.
    2. Do NOT invent tables.
    3. Do NOT invent columns.
    4. Return ONLY valid MySQL query.
    5. No explanation. No markdown.

    Database Schema:
    {schema}

    User Question:
    {prompt}
    """

    from google import genai

    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=full_prompt,
    )


    result = response.text.strip()
    result = result.replace("```sql", "").replace("```", "").strip()

    return result



st.set_page_config(page_title="AI SQL Assistant", layout="wide")

st.sidebar.title("🔐 Database Credentials")

host = st.sidebar.text_input("Host", value="localhost")
user = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")
port = st.sidebar.text_input("Port", value="3306")
database = st.sidebar.text_input("Database Name")



st.title("🧠 Text to SQL AI Tool")

question = st.text_area("Ask your question:")



from sqlalchemy import text


if st.button("Generate SQL"):

    try:
        engine = connect_db(host, user, password, port, database)
        schema = get_schema(engine)

        generated_sql = generate_sql(question, schema)

        st.session_state.generated_sql = generated_sql

    except Exception as e:
        st.error(f"Error: {e}")



if "generated_sql" in st.session_state:

    st.subheader("✏️ Edit SQL Query (if needed)")

    edited_sql = st.text_area(
        "SQL Editor",
        value=st.session_state.generated_sql,
        height=200
    )

    if st.button("Run Query"):

        try:
            engine = connect_db(host, user, password, port, database)

            with engine.begin() as conn:
                result = conn.execute(text(edited_sql))

                if edited_sql.strip().lower().startswith("select"):
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
                    st.subheader("📊 Query Result")
                    st.dataframe(df)
                else:
                    st.success("✅ Query executed successfully!")

        except Exception as e:
            st.error(f"Execution Error: {e}")
