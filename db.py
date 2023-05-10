import sqlite3

class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()

    def add_candidate(self, user_id, candidate_id, description):
        with self.connection:
            if not self.cursor.execute('SELECT * FROM candidates WHERE id_candidate = ? AND id_user = ?', (candidate_id, user_id)).fetchone():
                self.cursor.execute('INSERT INTO candidates (id_user, id_candidate, description) VALUES (?, ?, ?)', (user_id, candidate_id, description))

    def get_candidates(self, user_id) -> list:
        with self.connection:
            return self.cursor.execute('SELECT id_candidate FROM candidates WHERE id_user = ?', (user_id,)).fetchall()

    def get_description(self, candidate_id) -> str:
        with self.connection:
            return self.cursor.execute('SELECT description FROM candidates WHERE id_candidate = ?', (candidate_id, )).fetchone()[0]

    def add_user(self, user):
        with self.connection:
            try:
                return self.cursor.execute('INSERT INTO users (id, sex, age, city, offset) VALUES (?, ?, ?, ?, 0)', (user.id, user.sex, user.age, user.city))
            
            except sqlite3.IntegrityError:
                return False
    
    def get_user(self, user_id) -> dict:
        with self.connection:
            result = {}
            data = self.cursor.execute('SELECT * FROM users WHERE id=?', (user_id, )).fetchone()

            result['id'] = data[0]
            result['sex'] = data[1]
            result['age'] = data[2]
            result['city'] = data[3]

            return result
    
    def get_offset(self, user_id) -> int:
        with self.connection:
            return int(self.cursor.execute('SELECT offset FROM users WHERE id=?', (user_id ,)).fetchone()[0])
        
    def set_offset(self, user_id, offset):
        with self.connection:
            self.cursor.execute('UPDATE users SET offset=? WHERE id=?', (offset, user_id))
