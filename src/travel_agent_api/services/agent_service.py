class Agent:
    def run(self, messages: list):
        return messages + [
            {"type": "ai", "content": "Test: l'agente non è ancora collegato."}
        ]