import sqlite3
class ConversationDatabase:
    def __init__(self, db_name, use_llm):
        self.db_name = db_name
        # generate a random trace for the conversation
        self.trace = str(uuid.uuid4())

        # initiate the database and create the trace record
        self.initiate_db(use_llm=use_llm)
   
    def initiate_db(self, use_llm):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS conversations
                     (trace text, question text, use_llm text, iteration_number int, system_prompt text, cached_prompt text, user_prompt text, response text)''')
        self.cursor.execute("INSERT INTO conversations (trace, use_llm, iteration_number) VALUES (?, ?, 0)", (self.trace, use_llm))
        self.conn.commit()


    def save_conversation(self, question, iteration_number, use_llm, llm_tier, system_prompt, cached_prompt, user_prompt, response):
        # Save the conversation to the database
        if self.conn is None:
            self.initiate_db()
        self.cursor.execute("INSERT INTO conversations (trace, question, use_llm, iteration_number, system_prompt, cached_prompt, user_prompt, response) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (self.trace, question, use_llm, iteration_number, system_prompt, cached_prompt, user_prompt, response))
        self.conn.commit()