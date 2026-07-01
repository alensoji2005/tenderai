import sqlite3
import pandas as pd
conn = sqlite3.connect('d:/projects/tenderai-oman/prisma/dev.db')
df = pd.read_sql_query('SELECT sourceId, title FROM Tender', conn)
for _, row in df.iterrows():
    print(f"{row['sourceId']} | {row['title'].encode('ascii', 'replace').decode('ascii')}")
